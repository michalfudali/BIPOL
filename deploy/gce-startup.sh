#!/usr/bin/env bash
# Executed by Google Compute Engine as root. Do not enable shell tracing.
set -euo pipefail

metadata() {
  curl --fail --silent --show-error --retry 5 \
    -H 'Metadata-Flavor: Google' \
    "http://metadata.google.internal/computeMetadata/v1/$1"
}

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends docker.io curl ca-certificates jq
systemctl enable --now docker

image=$(metadata instance/attributes/bipol-image)
domain=$(metadata instance/attributes/bipol-domain)
registry=${image%%/*}
install -d -o 10001 -g 10001 -m 0750 /var/lib/bipol/data
install -d -m 0700 /var/lib/bipol/docker
export DOCKER_CONFIG=/var/lib/bipol/docker

# Short-lived VM identity token, piped directly to Docker; never logged.
metadata instance/service-accounts/default/token | jq -r .access_token | \
  docker login --username oauth2accesstoken --password-stdin "$registry"
docker pull "$image"
docker network inspect bipol >/dev/null 2>&1 || docker network create bipol

if docker container inspect bipol-app >/dev/null 2>&1; then
  docker stop --time 60 bipol-app
  docker rm bipol-app
fi
docker run -d --name bipol-app --restart unless-stopped --network bipol \
  --log-opt max-size=10m --log-opt max-file=3 \
  --security-opt no-new-privileges --cap-drop ALL \
  --mount type=bind,src=/var/lib/bipol/data,dst=/var/lib/bipol \
  --env PORT=8080 --env FLASK_DEBUG=0 --env WEB_CONCURRENCY=2 \
  --env BIPOL_AIRCRAFT_DB=/var/lib/bipol/aircraft.sqlite3 "$image"

cat >/var/lib/bipol/Caddyfile <<EOF
$domain {
    encode zstd gzip
    reverse_proxy bipol-app:8080
}
EOF
docker rm -f bipol-https 2>/dev/null || true
docker run -d --name bipol-https --restart unless-stopped --network bipol \
  --log-opt max-size=10m --log-opt max-file=3 \
  --publish 80:80 --publish 443:443 --publish 443:443/udp \
  --mount type=bind,src=/var/lib/bipol/Caddyfile,dst=/etc/caddy/Caddyfile,readonly \
  --mount type=volume,src=bipol-caddy-data,dst=/data \
  --mount type=volume,src=bipol-caddy-config,dst=/config caddy:2
echo "BiPOL Requiem: containers started; HTTPS certificate will be issued for $domain."
