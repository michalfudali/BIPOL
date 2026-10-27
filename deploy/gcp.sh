#!/usr/bin/env bash
# Deploy the current checkout to Google Cloud. Uses the caller's normal gcloud login.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo 'Użycie: bash deploy/gcp.sh PROJECT_ID [DOMAIN]' >&2
  exit 2
fi
project=$1
custom_domain=${2:-}
region=${GCP_REGION:-europe-central2}
zone=${GCP_ZONE:-$region-a}
instance=${GCP_INSTANCE:-bipol-requiem}
repository=bipol-requiem
machine=${GCP_MACHINE_TYPE:-e2-small}
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
if ! [[ $project =~ ^[a-z][a-z0-9-]{4,28}[a-z0-9]$ ]]; then
  echo 'Nieprawidłowy Project ID Google Cloud.' >&2
  exit 2
fi
if [[ -n $custom_domain ]] && ! [[ $custom_domain =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9]$ ]]; then
  echo 'Podaj samą nazwę domeny, bez https:// ani ścieżki.' >&2
  exit 2
fi
if ! command -v gcloud >/dev/null; then
  echo 'Uruchom skrypt w Google Cloud Shell albo zainstaluj Google Cloud CLI.' >&2
  exit 2
fi
if [[ -z $(gcloud auth list --filter=status:ACTIVE --format='value(account)' --limit=1) ]]; then
  echo 'Najpierw zaloguj swoje konto: gcloud auth login' >&2
  exit 2
fi
if [[ -n $(git status --porcelain --untracked-files=normal) ]]; then
  echo 'Przed wdrożeniem zapisz zmiany w Git. Wdrażany checkout musi być czysty.' >&2
  exit 2
fi
revision=$(git rev-parse HEAD)
echo "Wdrażanie BiPOL Requiem $revision w projekcie $project ($zone)."
echo 'Powstają zasoby GCP: VM e2-small, dysk 20 GB, adres IPv4 i rejestr obrazu; podlegają rozliczeniom GCP.'
gcloud services enable compute.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com --project="$project"

if ! gcloud artifacts repositories describe "$repository" --location="$region" --project="$project" >/dev/null 2>&1; then
  gcloud artifacts repositories create "$repository" --repository-format=docker --location="$region" \
    --description='Obrazy BiPOL Requiem' --project="$project"
fi
image="$region-docker.pkg.dev/$project/$repository/app:$revision"
builder_name=bipol-builder
builder="$builder_name@$project.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$builder" --project="$project" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$builder_name" --display-name='BiPOL Requiem image builder' --project="$project"
fi
gcloud artifacts repositories add-iam-policy-binding "$repository" --location="$region" \
  --member="serviceAccount:$builder" --role=roles/artifactregistry.writer --project="$project" >/dev/null
gcloud projects add-iam-policy-binding "$project" --member="serviceAccount:$builder" \
  --role=roles/logging.logWriter --condition=None >/dev/null
source_bucket="gs://$project-bipol-build-source"
if ! gcloud storage buckets describe "$source_bucket" --project="$project" >/dev/null 2>&1; then
  gcloud storage buckets create "$source_bucket" --location="$region" --uniform-bucket-level-access --project="$project"
fi
gcloud storage buckets add-iam-policy-binding "$source_bucket" --member="serviceAccount:$builder" \
  --role=roles/storage.objectViewer >/dev/null
gcloud builds submit --config=deploy/cloudbuild.yaml --substitutions="_IMAGE=$image" \
  --service-account="projects/$project/serviceAccounts/$builder" \
  --gcs-source-staging-dir="$source_bucket/source" --project="$project" .

account_name=bipol-runtime
account="$account_name@$project.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$account" --project="$project" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$account_name" --display-name='BiPOL Requiem runtime' --project="$project"
fi
gcloud artifacts repositories add-iam-policy-binding "$repository" --location="$region" \
  --member="serviceAccount:$account" --role=roles/artifactregistry.reader --project="$project" >/dev/null

address_name="$instance-ip"
if ! gcloud compute addresses describe "$address_name" --region="$region" --project="$project" >/dev/null 2>&1; then
  gcloud compute addresses create "$address_name" --region="$region" --project="$project"
fi
ip=$(gcloud compute addresses describe "$address_name" --region="$region" --project="$project" --format='value(address)')
domain=${custom_domain:-bipol-requiem.$ip.sslip.io}
firewall="$instance-web"
if ! gcloud compute firewall-rules describe "$firewall" --project="$project" >/dev/null 2>&1; then
  gcloud compute firewall-rules create "$firewall" --network=default --allow=tcp:80,tcp:443,udp:443 \
    --source-ranges=0.0.0.0/0 --target-tags="$instance-web" --project="$project"
fi

if gcloud compute instances describe "$instance" --zone="$zone" --project="$project" >/dev/null 2>&1; then
  managed=$(gcloud compute instances describe "$instance" --zone="$zone" --project="$project" \
    --format='json(metadata.items)' | python3 -c 'import json,sys; print(next((x.get("value","") for x in json.load(sys.stdin).get("metadata",{}).get("items",[]) if x.get("key")=="bipol-managed"),""))')
  if [[ $managed != true ]]; then
    echo "Istniejąca VM $instance nie jest oznaczona jako zarządzana przez wdrożenie BiPOL. Nie zmieniono jej." >&2
    exit 2
  fi
  gcloud compute instances add-metadata "$instance" --zone="$zone" --project="$project" \
    --metadata="bipol-managed=true,bipol-image=$image,bipol-domain=$domain" \
    --metadata-from-file="startup-script=$root/deploy/gce-startup.sh"
  gcloud compute instances reset "$instance" --zone="$zone" --project="$project"
else
  gcloud compute instances create "$instance" --zone="$zone" --project="$project" \
    --machine-type="$machine" --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB --boot-disk-type=pd-balanced --no-boot-disk-auto-delete \
    --service-account="$account" --scopes=https://www.googleapis.com/auth/cloud-platform \
    --address="$ip" --tags="$instance-web" \
    --metadata="bipol-managed=true,bipol-image=$image,bipol-domain=$domain" \
    --metadata-from-file="startup-script=$root/deploy/gce-startup.sh"
fi
echo "Adres po zakończeniu startu i wystawieniu certyfikatu: https://$domain"
echo "Kontrola działania: https://$domain/healthz"
echo 'Uruchomienie VM i pobranie obrazu może potrwać kilka minut. Podany adres wymaga sprawdzenia przed ogłoszeniem wdrożenia.'
