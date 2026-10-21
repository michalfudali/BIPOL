# BIPOL Studio - System Wstępnego Projektowania Samolotów (MEiL PW)

Kompletne środowisko projektowo-obliczeniowe wspierające przedmioty **BIPOL I** (NK307 *Budowa i Projektowanie Obiektów Latających I*) w **Zakładzie Samolotów i Śmigłowców (ZSiS)** oraz **Mechanika Lotu I** (ML.NK472) w **Zakładzie Mechaniki (ZM)** na **Wydziale Mechanicznym Energetyki i Lotnictwa Politechniki Warszawskiej (MEiL PW)**.

---

## Uruchomienie i sprawdzenie zmian

Python 3.12 lub nowszy:

```sh
python -m venv work/venv
work/venv/bin/pip install -r requirements-dev.txt
work/venv/bin/python -m flask --app app run --port 5000
```

Testy regresji: `work/venv/bin/python -m pytest tests -q`.
Testy narzędzi pracowni: `node tests/studio_core.test.mjs` (bez zależności npm).
Raporty są dokumentami HTML, które można wydrukować do PDF w przeglądarce.

Raport zbiorczy i osobne sprawozdania P1–P6 mają wspólny skład A4: stronę
tytułową, opis metody, wyniki, wnioski zależne od obliczeń oraz bibliografię.
Tabele, rysunki i wzory są numerowane. Próba porównawcza trafia do załącznika.
Dane autora uzupełnia się w widoku raportów lub przed wydrukiem; program nie
wstawia przykładowej tożsamości. Datę i rok akademicki można zmienić.
Wzory, fonty i wykresy pozostają dostępne w pobranym HTML bez internetu.

Test wydruków i raportów offline (wymaga Chromium, `requirements-browser.txt`
i narzędzia `pdftotext`):
`python tests/browser_reports.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium`.

Pracownia zawiera kokpit z nawigacją boczną, porównanie do ośmiu zapisanych
wariantów, eksport CSV/SVG, raport z wyborem etapów P1–P6, dane i wnioski autora
oraz dokładną biegunową lotu szybowego. Raport można pobrać jako samodzielny HTML.
Szczegóły integracji i testów są w `docs/INTEGRACJA_STUDIO.md`.

Interfejs otwiera od razu zapisany projekt. Założenia mają osobny widok, analizy
pokazują szczegóły na żądanie, a w trendach widoczny jest jeden wybrany wykres.
Układ, dostępność i testy opisuje [`docs/INTERFEJS.md`](docs/INTERFEJS.md).

Kreator pozwala wybrać temat i niezależne założenia: rozpiętość, powierzchnię lub
wydłużenie skrzydła, masę płatną, liczbę pasażerów i dostępną moc. Parametry
zależne są tylko do odczytu. Motoszybowce powyżej 20 m otrzymują spójną geometrię.
Szczegóły i testy: [`docs/ZALOZENIA_PROJEKTU.md`](docs/ZALOZENIA_PROJEKTU.md).

Widok **Baza i analiza trendów** zawiera **840 konstrukcji i wariantów** z FAST
Aerobase oraz ENAC CADO: filtry i ręczny dobór próby, regresję udziału masy pustej,
trendy czasowe z prognozą +5 lat, zależności osiągów i eksport danych ze źródłami.
Daty certyfikacji są jawnie odróżnione od lat produkcji, a brakujące dane pozostają
oznaczone. Wdrożenie obu materiałów P1 i ograniczenia metod opisuje
[`docs/ANALIZA_TRENDOW.md`](docs/ANALIZA_TRENDOW.md), a pochodzenie i licencje baz
[`data/aircraft/README.md`](data/aircraft/README.md).

Model służy do obliczeń dydaktycznych. Sprawdza wybrane warunki i nie stanowi
potwierdzenia certyfikacji. Wszystkie poziomy CS-23 1–4 obejmuje limit 8618 kg
i maksymalnie 19 miejsc pasażerskich. Poziomu osiągów nie określa się z Vcr TAS;
wymagane są VMO/VNO KCAS oraz MMO. Kategorie operacji UAS wynikają z oceny
ryzyka, a nie z podziału na masy poniżej i powyżej 600 kg.

Źródła: [EASA CS 23.2005](https://www.easa.europa.eu/en/downloads/22283/en),
[EASA: kategorie operacji UAS](https://www.easa.europa.eu/en/domains/drones-air-mobility/operating-drone).

---

## 🌐 Adresy uruchomionej aplikacji

- **Główny kokpit projektowy:** 👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
- **Podgląd sprawozdania i wydruk PDF:** **[http://127.0.0.1:5000/report](http://127.0.0.1:5000/report)**
- **API oficjalnych tematów wydziałowych:** `http://127.0.0.1:5000/api/topics`
- **API pobranych materiałów dydaktycznych:** `http://127.0.0.1:5000/api/scraped-files`

---

## 🚀 Nowe funkcjonalności wdrożone na życzenie użytkownika

### 1. Pełna baza 110 oficjalnych tematów projektowych z listy wydziałowej (`BIPOL1_samoloty.pdf`):
Aplikacja zawiera wszystkie **110 tematów** podzielonych na **13 kategorii**:
1. **Motoszybowce** (1- i 2-miejscowe; rozpiętości 13,5m, 15m, >20m; silnik ciągnący, pchający, chowany)
2. **Samoloty ultralekkie (ULM / LSA)** (1- i 2-miejscowe, dolnopłaty i górnopłaty, układ tandem / obok siebie)
3. **Odrzutowe samoloty rekreacyjne** (1- i 2-miejscowe, 1 lub 2 silniki odrzutowe)
4. **Samoloty wyścigowe i akrobacyjne** (Formuła 1, klasa Sport, Red Bull Air Race, akrobacyjne)
5. **Samoloty szkolne i szkolno-treningowe** (do 100 kW, do 200 kW, turbośmigłowe, odrzutowe)
6. **Samoloty turystyczne i STOL** (2- i 4-miejscowe, daleka turystyka)
7. **Samoloty medyczne i sanitarne** (pilot, lekarz, chory leżący, STOL, 1- i 2-silnikowe)
8. **Samoloty dyspozycyjne (Business Jets & Turboprops)** (4-, 6-, 8-, 10-, 15-, 20-miejscowe, zasięgi 500 – 3000 km)
9. **Samoloty transportowe STOL** (ładunek użyteczny 1300 kg – 23 000 kg z rampą załadunkową)
10. **Samoloty pasażerskie** (40, 70, 100, 200 miejsc; turbośmigłowe i odrzutowe; dolnopłaty i górnopłaty)
11. **Samoloty rolnicze i pożarnicze** (zbiorniki chemikaliów i wody 500 – 6000 kg)
12. **Wodnosamoloty i łodzie latające** (turystyczne 4-miejscowe i transportowe 1000 – 3000 kg)
13. **Samoloty szturmowe i specjalne** (1- i 2-miejscowe, turbośmigłowe i odrzutowe)

### 2. Pełna swoboda wpisywania i dostosowywania parametrów przez użytkownika:
- **Wymagana rozpiętość $b$ [m]:** możliwość narzucenia dokładnej rozpiętości (np. 13.5m, 15m dla motoszybowca) lub wpisania `0` dla doboru automatycznego z optymalnego wydłużenia $\Lambda$ i powierzchni nośnej $S$.
- **Zasięg $R$ [km]** oraz wysokość przelotu $H$ [m].
- **Masa płatna:** liczba pasażerów, masa załogi, ładunek cargo $m_{cargo}$ [kg].
- **Rodzaj napędu:** tłokowy (piston), turbośmigłowy (turboprop), odrzutowy (turbofan/turbojet).
- **Położenie zespołu napędowego:** dziób (ciągnący), skrzydła (gondole wielosilnikowe), tył kadłuba (pchający), chowany w kadłubie.
- **Konfiguracja płatowca:** dolnopłat, górnopłat (np. STOL), średniopłat; skos skrzydła $\chi_{25\%}$, wznos $\Gamma$.

### 3. Zescrapowane i zintegrowane materiały wydziałowe (27 plików PDF dostępnych w aplikacji):
- **BIPOL I (ZSiS MEiL PW):**
  - `BIPOL1_samoloty.pdf` – Oficjalna lista 110 tematów projektowych
  - `BIPOL1_Opis_Projektow.pdf` – Szczegółowe wymagania i punktacja projektów P1–P6 (dr inż. Marcin Figat)
  - `BIPOL1_regulamin.pdf` – Regulamin zaliczenia
  - `BIPOL_1_wzory.pdf` – Wyprowadzenia wzorów i metodyka obliczeń
  - `BIPOL_1.pdf` – Analizy wstępne
  - `BIPOL_2.pdf` – Studium wykonalności
  - `BIPOL_3_2010.pdf` i `BIPOL_3_przyklad.pdf` – Projekt wstępny i analiza masowa
  - `Usterzenie_wymiary.pdf` – Wymiarowanie usterzeń metodą współczynników objętościowych
  - `Schemat_projektu.pdf` – Metodyka rysowania kadłuba
  - `BIPOL_4.pdf` i `BIPOL_5.pdf` – Aerodynamika i osiągi
  - Handouty wykładów prof. C. Galińskiego (od 1 do 8).
- **Mechanika Lotu I (ZM MEiL PW):**
  - `Projekt_1.pdf` – Wybór samolotu i bazy danych
  - `Projekt_2.pdf` – Charakterystyki aerodynamiczne płata
  - `Projekt_3.pdf` – Opory części samolotu i biegunowa całego płatowca
  - `Projekt_4.pdf` – Lot szybowy i biegunowa prędkości
  - `Projekt_5.pdf` – Charakterystyki zespołu napędowego
  - `Projekt_6.pdf` – Osiągi samolotu w locie ustalonym
  - `Literatura.pdf` – Wykaz zalecanej literatury.

Wszystkie te pliki są dostępne do bezpośredniego podglądu i pobrania w zakładce **"📥 Materiały z Wydziału"**.

---

## 📊 Wykresy inżynierskie i schematy (Renderowane Standalone)

1. **Diagram doboru parametrów (Matching Chart):** Ograniczenia $W/S$ vs $T/W$ lub $P/W$ z zaznaczonym punktem projektowym.
2. **Biegunowa aerodynamiczna $C_z(C_x)$:** Konfiguracja gładka, startowa oraz z klapami do lądowania i wysuniętym podwoziem.
3. **Rozkład siły nośnej wg Schrenka:** Wykres obciążenia trapezowego, eliptycznego i wypadkowego rozkładu Schrenka wzdłuż rozpiętości.
4. **Krzywa prędkości wznoszenia $w_y(V)$:** Biegunowa prędkości i punkt maksymalnego wznoszenia $w_{y,max}$.
5. **Obwiednia obciążeń dopuszczalnych $V-n$:** Obwiednia manewrowa i linie podmuchów pionowych wg przepisów CS-23/CS-25.
6. **Diagram wyważenia:** Wykres wędrówki Środka Masy w % ŚDA dla stanów OEW, ZFW, MTOW, MLW względem Punktu Neutralnego.
7. **Rysunek zestawieniowy 3-widokowy SVG (CAD):** Parametryczny rzut z góry, z przodu i z boku uwzględniający górnopłat/dolnopłat, rozpiętość, kadłub i usterzenia.
