# BiPOL Requiem w Google Cloud

Przygotowano wdrożenie aktualnego kodu Flask na **Compute Engine**, z Gunicornem,
kontenerem Docker, Caddy i publicznym HTTPS. Wybrano VM, ponieważ edytowalna baza
SQLite musi przetrwać restarty oraz kolejne wersje aplikacji. Zwykły dysk
kontenera Cloud Run nie zapewnia takiej trwałości.

## Co jest potrzebne

- Projekt Google Cloud z włączonym rozliczaniem.
- Zalogowane konto Google Cloud CLI z uprawnieniami do budowy obrazu, zarządzania
  VM, adresem IP, zaporą, repozytorium Artifact Registry i kontami usługowymi.
  W projekcie zarządzanym przez organizację administrator musi nadać odpowiednie
  uprawnienia. Sam Project ID nie daje dostępu.
- Aktualny, czysty checkout repozytorium. Skrypt nie umieszcza kluczy w kodzie.

Najprościej użyć **Google Cloud Shell** z konsoli swojego projektu — ma już
`gcloud`, Git i uwierzytelnione konto. Alternatywnie skonfiguruj dostęp Google
Cloud w środowisku, w którym pracuje agent.

## Uruchomienie

W Google Cloud Shell:

```sh
git clone --branch master https://github.com/michalfudali/BIPOL.git
cd BIPOL
bash deploy/gcp.sh TWOJ_PROJECT_ID
```

`TWOJ_PROJECT_ID` zastępuje się rzeczywistym identyfikatorem projektu, a nie jego
nazwą wyświetlaną. Usługa nie jest wdrożona, dopóki skrypt nie wykona operacji
w projekcie i publiczny endpoint nie odpowie poprawnie.

Domyślne zasoby:

| Zasób | Konfiguracja |
|---|---|
| VM | `bipol-requiem`, `e2-small`, Ubuntu 24.04, `europe-central2-a` |
| Dysk | 20 GB `pd-balanced`, pozostaje po usunięciu VM |
| Adres | Zarezerwowany IPv4; porty publiczne 80 i 443 |
| HTTPS | Caddy, automatyczny certyfikat; domyślnie nazwa w `sslip.io` |
| Obrazy | Artifact Registry w `europe-central2`; tag to pełny SHA kodu |
| Dane | `/var/lib/bipol/data/aircraft.sqlite3` na dysku VM |
| Start | Gunicorn, dwóch workerów, bez debuggera Flask |

To zasoby rozliczane przez Google Cloud. VM, dysk i zarezerwowany IPv4 mają koszty
również poza aktywnym korzystaniem z aplikacji; dodatkowo rozliczane są obrazy,
budowanie i transfer. Nie jest to deklaracja bezpłatnego hostingu.

Po uruchomieniu skrypt wypisuje nazwę hosta. Przygotowanie VM, pobranie obrazu
i wydanie certyfikatu zajmuje kilka minut. Zweryfikuj:

```sh
curl --fail https://NAZWA_HOSTA/healthz
```

Oczekiwana odpowiedź zawiera `"status":"ok"`. Następnie otwórz stronę i sprawdź
przeliczenie projektu oraz eksport raportu HTML/PDF/DOCX.

## Własna domena i inna lokalizacja

```sh
bash deploy/gcp.sh TWOJ_PROJECT_ID bipol.twoja-domena.pl
```

Rekord A domeny musi wskazywać zarezerwowany adres wypisany przez skrypt. Caddy
wystawi certyfikat po poprawnym skierowaniu DNS i dostępności portów 80/443.
Domyślna domena `sslip.io` nie wymaga kupowania własnej domeny.

Lokalizację i rozmiar nowej VM można wybrać zmiennymi środowiskowymi:

```sh
GCP_REGION=europe-west1 GCP_ZONE=europe-west1-b GCP_MACHINE_TYPE=e2-small \
  bash deploy/gcp.sh TWOJ_PROJECT_ID
```

Nie zmieniaj regionu istniejącego wdrożenia bez zaplanowanej migracji danych.
Skrypt zakłada dostępną sieć `default`; jeśli organizacja jej nie ma, konfigurację
sieci trzeba dostosować do projektu.

## Aktualizacja i dane

Po `git pull --ff-only` ponownie uruchom to samo polecenie. Obraz zostanie
zbudowany z nowego SHA, a VM zrestartowana z nową wersją. Zatrzymanie Gunicorna
jest kontrolowane. Baza jest kopiowana z danych startowych wyłącznie wtedy,
gdy plik na trwałym dysku jeszcze nie istnieje. Własne rekordy nie są zastępowane
katalogiem z nowego obrazu. Uszkodzona baza zatrzymuje start; nie jest kasowana.

Katalog samolotów jest wspólny dla wszystkich odwiedzających, zgodnie z obecnym
API aplikacji. Projekty i poprawki raportów są zapisywane w przeglądarce użytkownika;
zmiana domeny oznacza inne miejsce przechowywania tych danych w przeglądarce.
Sam trwały dysk nie zastępuje kopii zapasowej bazy.

## Kontener lokalnie

```sh
docker build -t bipol-requiem .
docker run --rm -p 127.0.0.1:8080:8080 \
  --mount type=volume,source=bipol-data,target=/var/lib/bipol bipol-requiem
```

Wtedy aplikacja działa pod `http://127.0.0.1:8080`. Obraz nie zawiera lokalnych
materiałów wydziałowych, kluczy, `.env`, katalogu roboczego ani historii Git.
Endpoint `/healthz` sprawdza dostępność bazy i nie ujawnia jej ścieżki.

## Diagnozowanie startu VM

```sh
gcloud compute instances get-serial-port-output bipol-requiem \
  --zone=europe-central2-a --project=TWOJ_PROJECT_ID
```

Skrypt tworzy osobne konta do budowania i uruchomienia obrazu. Konto VM ma jedynie
prawo odczytu repozytorium obrazu. Nie pobieraj ani nie wklejaj kluczy kont usługowych
do repozytorium lub rozmowy; stosowane są krótkotrwałe poświadczenia środowiska.
