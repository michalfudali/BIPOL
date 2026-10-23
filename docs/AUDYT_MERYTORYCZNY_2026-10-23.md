# Audyt obliczeń i pracy projektanta — 23.10.2026

## Zakres

Sprawdzono lokalny ciąg projektowania: założenia misji → bilans masy → dobór skrzydła i napędu → geometria → aerodynamika → osiągi → wyważenie i obwiednia obciążeń → raporty. Dodatkowo sprawdzono zastosowanie danych z trendów, obsługę wspólnej bazy samolotów w istniejących testach oraz widok samolotu i eksport danych.

Zmiany dotyczą wspólnego silnika obliczeń. Projekty korzystają z nich po ponownym przeliczeniu. Zapisane wcześniej wyniki wariantów pozostają historycznymi wynikami; należy przeliczyć wariant przed porównaniem z nowym modelem.

## Potwierdzone i poprawione problemy

| Obszar | Problem | Zmiana i sposób sprawdzenia |
| --- | --- | --- |
| Dane z trendów | Część przycisków zmieniała pomocnicze pola bez wpływu na solver; udział masy pustej był ignorowany. | Sugestie ustawiają właściwy tryb i parametry wejściowe. Stały udział masy pustej uczestniczy w bilansie; można wrócić do korelacji klasy. Testy JS i rzeczywiste kliknięcia w przeglądarce. |
| Jednostki trendów | Obciążenie masowe skrzydła mogło być mylone z W/S. | m₀/S ma jednostkę kg/m²; przyjęcie sugestii oblicza S z aktualnej masy. Moc jest wyznaczana z kg/kW i włączany jest tryb narzuconej mocy. Ponowny bilans może zmienić obciążenie — interfejs to wyjaśnia. |
| Asynchroniczne sugestie | Opóźniona odpowiedź mogła podmienić sugestie po zmianie projektu. | Aktualizuje je tylko odpowiedź dotycząca ostatniego żądania; podczas pobierania nie można przyjąć starych wartości. |
| Paliwo i masy faz | Różne etapy przyjmowały różne masy, m.in. zastępcze 15% paliwa. | Jeden bilans mas faz misji, niezaokrąglane mnożniki paliwowe, rzeczywiste masy początku i końca przelotu oraz lądowania. Rezerwa nie jest ponownie zaliczana do paliwa przelotowego. Sprawdzone dla wszystkich 110 tematów. |
| Napęd i osiągi | Niespójne spadki mocy/ciągu z wysokością; zastępcze dodatnie prędkości przy niedostatecznym napędzie. | Wspólny model dostępnej mocy/ciągu, rzeczywisty bilans mocy i wyszukiwanie zakresu lotu poziomego. Przy 0,001 kW aplikacja zgłasza brak lotu poziomego, ujemne wznoszenie i brak osiągalnego zasięgu. |
| SFC | Możliwe ciche zastępowanie wartości po pomyleniu jednostek. | Walidacja oddziela g/kWh dla śmigłowych i 1/h dla odrzutowych; dokładna konwersja TSFC do kg/(daN·h). Niezależny test równania Bregueta. |
| Mechanizacja | Dobór skrzydła i osiągi używały różnych Cz,max; przyrost klap stosowano do całego skrzydła. | Wspólny model 20°/40°; przyrosty skalowane udziałem powierzchni wyposażonej w klapy/sloty. Iteracja zamyka zależność powierzchnia skrzydła ↔ powierzchnia mechanizacji. Mniejsza rozpiętość klap obniża Cz,max i zmienia wymiarowanie. |
| Obrys skrzydła | ŚDA i pola powierzchni sterowych nie zawsze odpowiadały wybranemu obrysowi. | Poprawione położenie ŚDA, skos i całkowanie powierzchni rzeczywistego obrysu. Idealne nieskośne skrzydło eliptyczne nie otrzymuje poprawki Glauerta z wielomianu dla trapezu. |
| Lotki | Tłumienie przechylenia było dwukrotnie za duże dla trapezu; inne obrysy również traktowano jak trapez. | Całkowanie y²c(y) po rzeczywistym obrysie. Niezależne graniczne przypadki: prostokąt C_l,p = −a/6, elipsa C_l,p = −a/8. Usunięto automatyczne stwierdzenie zgodności CS-23/22. |
| Usterzenie i wyważenie | Ramię używane do doboru usterzenia nie odpowiadało przesuniętemu skrzydłu; tabelaryczne momenty mas różniły się od solvera. | Iteracyjne uzgodnienie ramion z położeniem ¼ ŚDA i usterzenia. Wspólne środki mas grup, rzeczywiste momenty pasażerów i ładunku. Sprawdzone ramiona i sumy momentów w 110 tematach. |
| Lądowanie | Dobieg korzystał z masy startowej i obcinał ujemny składnik Cd−μCL. | Masa na początku fazy lądowania, biegunowa do lądowania i prawidłowy wpływ siły nośnej na nacisk kół. |
| Pułap i czas wznoszenia | Wykres osiągów i analityczny czas opierały się na różnych przebiegach wznoszenia; pułap teoretyczny mógł mieć czas 0 s. | Całkowanie dt = dh/wy,max(h) z tego samego modelu przy stałej masie. Pułap teoretyczny ma brak skończonego czasu dolotu. Pułap praktyczny: w_y,max = 0,5 m/s dla każdego napędu (Paturski, Projekt 6). |
| Atmosfera i obciążenia | W obwiedni EAS używano przelotowej TAS; atmosfera była zaokrąglana przed obliczeniami. | Konwersja TAS → EAS i ciągłe wartości parametrów ISA wewnątrz solvera. |
| Temat 82 | Ogólne założenia lekkiego samolotu STOL przesłaniały klasę 70-miejscowego samolotu regionalnego; kadłub skalowano od ogromnej rozpiętości. | Priorytet parametrów klasy regionalnej oraz jawne założenia układu kabiny. Dla obecnego wejścia: b ≈ 42,39 m, S ≈ 163,38 m², L ≈ 25,08 m. To nadal koncepcja wymagająca oceny; model zgłasza niespełniony zasięg. |
| Analiza wrażliwości | Wyniki zmian parametrów były przybliżane stałymi mnożnikami. | Dla każdej zmiany ponownie rozwiązywany jest nieliniowy bilans masy. |
| Raporty i profil | Fikcyjne rzędne profilu, nieudokumentowane biegunowe kandydatów, stałe „poprawne” kąty i prześwity. | Braki oznaczone jawnie; usunięto pozorne wyniki. Momenty bezwładności opisano jako oszacowanie z mas skupionych bez bezwładności własnej grup. |
| Krytyczna ocena osiągów | Fikcyjne wcześniejsze założenia (np. 0,97 MTOW), arbitralna różnica 1,5% między metodami zasięgu i bezwarunkowo pozytywne komentarze. | Porównanie rzeczywistych wejść i wyników, metody Bregueta z jednej biegunowej i paliwa przelotowego, osobny test zasięgu przy zadanej prędkości. Projekt niewykonalny nie dostaje pochwały osiągów. Szybowiec nie otrzymuje zmyślonego zasięgu paliwowego. |
| Podgląd i eksport | Położenia usterzeń i skosy części obrysów odbiegały od obliczeń; nieosiągalna Vmax trafiała do porównań jako 0. | Geometria podglądu i rysunków korzysta z obliczonych punktów; porównania i CSV pokazują brak dostępnej Vmax. Testy obrotów, powierzchni sterowych i eksportu SVG. |


## Poprawki po przeglądzie merytorycznym (BIPOL I, CS-22/23/25)

| Obszar | Problem | Zmiana i sposób sprawdzenia |
| --- | --- | --- |
| Obwiednia szybowca | Szybowce i motoszybowce liczono jak CS-23 (VC, podmuchy 50/25 ft/s, cięciwa ŚCA). | CS-22 Amdt 2: n₁ = 5,3 przy VA, n₂ = 4,0 i n₃ = −1,5 przy VD, n₄ = −2,65 (kat. A: 7/7/−5/−5); VB = VA, brak VC; VD ≥ 18·∛((W/S)/Cd,min), dla motoszybowca też ≥ 1,35 VH; podmuchy 15 m/s przy VB i 7,5 m/s przy VD; μ z cięciwy S/b; przyrost ≤ 1,25 (V/VS1)²; klapy n = 4,0 i ±7,5 m/s. PW-5: VD ≈ 233 km/h (VNE PW-5 = 220 km/h). |
| VC i VD dla CS-23 | Stałe współczynniki 33·√(W/S) i 1,40 niezależnie od obciążenia powierzchni. | §23.335 Amdt 4: powyżej 20 lbf/ft² liniowy spadek do 28,6 i 1,35 przy 100 lbf/ft²; współczynniki kategorii utility (1,50) i akrobacyjnej (36; 1,55). |
| VD dla CS-25 | Reguła CS-23 stosowana do samolotów transportowych. | VD = VC/0,8 (CS-25.335(b)). |
| Opór szybowca | Progi statystyczne samolotów z napędem (Tabele A–C) zawyżały Cx0 szybowca do 0,0345 (Kmax ≈ 16). Kadłub 1,0–1,25 m niezależnie od liczby miejsc. | Kadłub z owiewką w przekroju czołowym (Cx 0,08–0,15), koło jednośladowe częściowo wpuszczone, bez „innych części” bez napędu, K_interf 0,02/0,04. Średnica zastępcza 0,72 m (1 miejsce), 0,82 m (tandem), 1,10 m (obok siebie). PW-5: Cx0 = 0,0157, Kmax = 26; motoszybowiec: Kmax 16 → 23,7. Tabele A–C oznaczone jako niedotyczące szybowców. |
| Kadłub UAV | Średnica 1,25 m również dla UAV o masie 125 kg; progi kabiny załogowej. | d = 0,08·m₀^⅓ (0,25–1,4 m), L = 0,55 b, bez owiewki kabiny i bez progu CxS kadłuba. |
| Podwozie | Dwie różne reguły domyślne (aerodynamika i Paturski); motoszybowiec dostawał podwozie chowane w konfiguracji do lądowania. | Jedna reguła `default_retractable_gear` i pole „Podwozie” (automatycznie / stałe / chowane) w formularzu i kreatorze. |
| P3: płat | Brak Cz(α), Cm(α), Cx(Cz) płata; stałe Cm0 = −0,055. | Tabela i wykresy z Tabeli 2.2 Paturskiego; Cm względem noska ŚCA = Cm,SA − x̄SA·Cz z danych profilu. |
| P4: samolot | Brak Cz(α), Cm(α), K i E w funkcji α i Cz; biegunowa prędkości „dla dwóch położeń ŚC” miała identyczne wartości. | Biegunowe wyważone (Tabela 2.2) dla przedniego, średniego i tylnego ŚC; Cm(α) jako jawne przybliżenie liniowe przy ustalonym sterze z punktem neutralnym z wyważenia; Vek, wmin, Vopt, Kmax dla obu położeń. |
| Pułap praktyczny | Dla odrzutowców przyjęto w_y = 1,5 m/s. | 0,5 m/s dla każdego napędu (Paturski, Projekt 6). |
| Koszty | Nieudokumentowany mnożnik klasy 0,28/0,55, stały CPI 3,12, ryczałtowe ceny silników, jedna faza. | Metoda BIPOL_2: współczynniki 1970 i 1986, liniowa ekstrapolacja godzin i stawek do roku `cost_year` (domyślnie 2026), osobne fazy RDT&E i produkcji, cena wg wzoru 5.10. Silnik turbinowy z wzoru (15) (Θ z założonej temperatury przed turbiną); dla tłokowych i turbośmigłowych jawne założenie USD/kW. Zależności Corke'a zawyżają koszt lekkich samolotów — raport to zaznacza. |
| Spójność P2/P4 | Brak porównania biegunowej założonej w P2 z obliczoną w P4. | Kontrola w przeglądzie prowadzącego (Kmax ±20%). Preset UAV MALE poprawiony (Cx0 0,026, e 0,78). |
| P5: ocena osiągów | Raport nie zawierał wymaganej oceny osiągów (2 pkt). | Tabela założenia–wynik i krytyczna ocena z przyczyną: np. bilans paliwa z K = 0,94·Kmax, a przy prędkości przelotowej K z P4 jest mniejsze; potrzebna moc przelotowa większa od dostępnej przy Cx0 z P4. |

Część presetów nadal nie spełnia zadanego zasięgu lub prędkości przelotowej. Przyczyną jest reguła K = 0,94·Kmax w bilansie masy przy prędkości przelotowej znacznie większej od prędkości największego zasięgu. Raport P5 podaje to z liczbami; presetów nie dopasowywano do wyniku.

## Weryfikacja

- Pełna seria Python: **886 zaliczonych testów**, 62,44 s. Obejmuje wszystkie 110 tematów oraz testy obliczeń, API, wspólnej bazy samolotów, trendów i raportów. Nowy plik audytu zawiera 132 testy.
- 33 testy JavaScript: wszystkie zaliczone. Obejmują podgląd, edytor danych, import samolotu do projektu, warianty/CSV i przenoszenie trendów.
- Scenariusz Chrome: rzeczywiste przyjęcie udziału masy pustej, reset korelacji, przyjęcie VH, powierzchni skrzydła i mocy; obliczenie projektu z za słabym silnikiem; eksport P3; temat 82; szerokości 1600, 390 i 320 px. Bez wyjątków JavaScript i bez poziomego przepełnienia widoku.
- `git diff --check`: bez błędów białych znaków.
- Po przeglądzie merytorycznym: **920 zaliczonych testów** Python (nowy plik `tests/test_course_review_fixes.py`, 30 testów); render P2–P6 i pełnego raportu dla wszystkich presetów bez błędów; wykresy P3/P4 sprawdzone w Chrome headless (każdy kontener ma SVG, bez wyjątków JS); 1500 losowych zapytań `/api/calculate` (z szybowcami i trybami podwozia) bez błędu 500. Testów Node nie uruchomiono (brak Node.js w środowisku).
- Integracja diagnostyki edytora była niedostępna; walidację wykonano przez pytest, Node i Chrome.

Testy regresji dodano w `tests/test_aeronautical_audit.py`, `tests/trend_inputs.test.mjs` i `tests/browser_aeronautical_audit.mjs`. Pozostałe testy poprawiono tam, gdzie utrwalały poprzednie błędne założenie, np. przyrost nośności klap bez udziału powierzchni.

### Ponowienie testów

```powershell
python -m pytest tests -q
node --test tests/trend_inputs.test.mjs tests/aircraft_preview.test.mjs tests/studio_core.test.mjs tests/aircraft_editor.test.mjs tests/aircraft_project.test.mjs
```

Test przeglądarkowy wymaga działającego lokalnie Flask na porcie 5055 i oddzielnej instancji Chrome z portem debugowania 9228. Adresy można ustawić przez `APP_URL` i `CHROME_CDP_URL`:

```powershell
node tests/browser_aeronautical_audit.mjs
```

## Źródła i sprawdzenia wzorów

- Lokalny `scraped_materials/bipol/BIPOL_2.pdf`, s. 4: skalowanie przyrostu nośności udziałem powierzchni z mechanizacją. Na s. 2 wizualnie potwierdzono pierwiastek we wzorze startowym; nie usuwano go z poprawnej implementacji.
- Lokalne materiały Paturskiego, projekty 2–6: konwencje geometrii, biegunowej, napędu i osiągów. W miejscach bez danych konkretnego profilu pozostawiono jawne oszacowania zamiast oznaczać je jako pomiar.
- [EASA CS-23 Amendment 4, §23.335](https://www.easa.europa.eu/sites/default/files/dfu/CS-23%20Amendment%204.pdf): prędkości obliczeniowe są EAS. Program używa tej historycznej metody dydaktycznej; wynik nie stanowi potwierdzenia zgodności z aktualną podstawą certyfikacyjną.
- EASA CS-22 Amendment 2 (biblioteka dokumentów EASA): §22.333–22.345 i §22.1505 (obwiednia, podmuchy, klapy, VNE szybowców i motoszybowców).
- BIPOL_2 (C. Galiński, Studium wykonalności), s. 7–10: współczynniki 1970/1986 wzorów 13–21, stawki Tab. 5.9, wzór (15) ceny silnika i wzór 5.10 ceny samolotu.
- Opis projektów BIPOL I (M. Figat): P3 — Cz(α), Cm(α), Cx(Cz) płata; P4 — Cz(α), Cm(α), Cz(Cx), K i E w funkcji α i Cz, biegunowa prędkości dla dwóch skrajnych położeń ŚC; P5 — ocena osiągów.
- Z. Paturski, Przewodnik po projektach z Mechaniki Lotu, Projekt 6: pułap praktyczny przy w_max = 0,5 m/s.
- Niezależne sprawdzenia matematyczne: całki obrysu i tłumienia przechylenia, wymiar jednostek TSFC, bilans mas i momentów, analityczny czas przy stałym i liniowo malejącym wznoszeniu.

## Granice wyniku

Jest to zweryfikowany zestaw poprawek do narzędzia projektowania wstępnego. Przejście testów nie oznacza, że każda koncepcja jest wykonalnym samolotem ani że wykryto każdy możliwy błąd.

Model nadal wymaga rzeczywistych danych profilu, charakterystyk konkretnego silnika i śmigła, opracowania struktury, kinematyki sterowania i układu kabiny. Wstępny bilans paliwa używa założonej doskonałości, a końcowe osiągi biegunowej obliczonej w P4; dlatego końcowe sprawdzenie zasięgu może odrzucić początkowy bilans. W takim przypadku trzeba zmienić projekt, nie ukrywać rozbieżność.

Przyrosty mechanizacji są oszacowaniami dla przyjętych wychyleń. Model nie odwzorowuje pełnej zależności od geometrii szczelin i cięciwy urządzenia. Biegunowa paraboliczna nie zawiera oporu falowego; dla dużej liczby Macha pojawia się ostrzeżenie. Charakterystyki dostępnego napędu są przybliżeniami, a całkowanie czasu wznoszenia zakłada stałą masę. Metody zasięgu zakładają stałe zużycie jednostkowe i sprawność; zmienne profile wysokości wymagają odrębnej weryfikacji dostępnej mocy.

Rozkład mas grup, opory pomocniczych zespołów, koszty i część położeń w podglądzie pozostają oszacowaniami koncepcyjnymi. Podgląd nie jest dokumentacją konstrukcyjną. Nie wykonywano zmian ani publikacji na remote.
