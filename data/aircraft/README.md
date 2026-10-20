# Baza referencyjna do analiz P1

716 pozycji: 428 wariantów z FAST i 288 z CADO. To liczba rekordów,
nie liczba niezależnych rodzin. Te same konstrukcje mogą występować w obu
źródłach pod różnymi nazwami. Do analizy wrażliwości wybierz jedno źródło.
Pliki stanowią oddzielne, lokalne migawki; aplikacja nie pobiera ich w trakcie pracy.

## FAST Aerobase

Copyright 2024 The Regents of the University of Michigan,
The Integrated Design of Efficient Aerospace Systems Laboratory.

Źródło: [ideas-um/FAST, +DatabasePkg](https://github.com/ideas-um/FAST/tree/482e77b921d616d00d9cdb5c0c673d55f511c52b/+DatabasePkg),
arkusz `EAP_Databases_Offline.xlsx`, rewizja
`482e77b921d616d00d9cdb5c0c673d55f511c52b`, pobrano 2026-10-20.
SHA-256: `3f31aadde6b71dab9c8a41b46d9b9707aceb9f2f4e35c02b9b5436b7f02eeaa4`.

Licencja: [Apache-2.0](licenses/FAST-Apache-2.0.txt).
`fast.json` to zmodyfikowana reprezentacja danych: wybrano pola z arkuszy
Jet Aircraft i Propeller Aircraft, ujednolicono nazwy i jednostki,
obliczono łączne parametry napędu i dodano klasy oraz grupowanie rodzin.
Każdy rekord wskazuje arkusz/kolumnę i zachowuje pole Sources.
Dla ciągu z tabeli silników zapisano także lokalizację dopasowanego silnika.
Pominięto rekordy bez MTOW lub źródła i powtórzoną identyczną nazwę wariantu.
Nie uzupełniano brakujących parametrów przez zgadywanie lub regresję.

Autorzy bazy proszą o cytowanie prac o FAST / Aerobase:
Mokotoff et al., *FAST: A Future Aircraft Sizing Tool for Conventional and
Electrified Aircraft Design*, DOI: [10.2514/1.C038452](https://doi.org/10.2514/1.C038452),
oraz Arnson, Aljaber i Çınar, *Predicting Aircraft Design Parameters Using Gaussian
Process Regressions on Historical Data*. Pełna bibliografia jest w repozytorium źródłowym.

## ENAC CADO v1.0

Monrolin, N.; Druot, T.; Peteilh, N.; Roches, P.; Kambiri, Y.-A. (2024),
*CADO airplane database*, Recherche Data Gouv,
[DOI:10.57745/LLRJO0](https://doi.org/10.57745/LLRJO0).

Contains information from CADO Airplane Database, which is made available here
under the Open Database License (ODbL).

`cado.json` jest przekształconą bazą pochodną udostępnioną na
[ODbL-1.0](licenses/CADO-ODbL-1.0.txt). Zmiany: wybrano kolumny, dodano identyfikatory,
klasy i heurystyczne rodziny, przeliczono moc/ciąg pojedynczego silnika na sumę,
oddzielono wartości Mach od km/h oraz odczytano lata z niepustych dat certyfikacji.
Numery w `source_locator` odpowiadają fizycznym wierszom oryginalnego CSV
(z nagłówkiem i dwoma wierszami jednostek).

Plik źródłowy `CADO_airplane_database_v1.0.csv`, identyfikator pliku Data Gouv
`188268`, pobrano 2026-10-20.
SHA-256: `6b986349811e66f50039347f7c3450636f8700b1ed0ad5ee7e523d89b8777180`.
Nie zmieniano wartości liczbowych katalogu poza jawną konwersją jednostek.
Nazwy i jakość danych zachowują ograniczenia oryginału; to baza do projektu
wstępnego, a nie do planowania rzeczywistych operacji lotniczych.

## Odtworzenie

Pobierz powyższe, przypięte wersje źródeł oraz:

```sh
python -m pip install -r requirements-data.txt
python tools/import_aircraft_data.py --fast /path/EAP_Databases_Offline.xlsx --cado /path/CADO_airplane_database_v1.0.csv
```

Importer sprawdza SHA-256 i nie wymaga sieci. Nowa wersja źródła wymaga przeglądu
mapowania pól i świadomej aktualizacji skrótu. Do uruchomienia aplikacji nie jest
potrzebny openpyxl ani dostęp do źródeł zewnętrznych.
