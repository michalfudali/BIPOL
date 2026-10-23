# Zgodność programu z BIPOL_1.pdf

Data aktualizacji: 23.10.2026. Źródło: lokalny plik
`scraped_materials/bipol/BIPOL_1.pdf` (6 stron) oraz `docs/WYTYCZNE_PROWADZACEGO.md`.

**Wniosek.** Analiza trendów (rozdział 1 materiału) jest realizowana metodą
z BIPOL_1, a każda sugerowana wartość ma pokazane pochodzenie. Pozostają
różnice wynikające z danych: baza podaje rok certyfikacji zamiast roku
produkcji, część klas ma mniej niż 20 konstrukcji, a V_V jest udokumentowane
tylko dla motoszybowców. Rozdziały 3–4 (bilans masy) są zrealizowane
częściowo; szczegóły w tabeli.

## Analiza trendów (BIPOL_1, s. 1–2)

| Wymaganie | Realizacja |
|---|---|
| Co najmniej 20 podobnych samolotów | Próba: ta sama klasa i rodzaj napędu, domyślnie 50 konstrukcji najbliższych masą. Mniej niż 20 konstrukcji, rodzin lub obserwacji danej wielkości daje ostrzeżenie. Kontrola zaliczenia wymaga 8 rodzin (wytyczne prowadzącego). |
| Zależności od roku produkcji, ekstrapolacja na 5 lat naprzód | Regresja liniowa w funkcji roku i prognoza na rok opracowania + 5 lat (w 2026 r.: 2031). Podana jest długość ekstrapolacji poza najnowszą obserwację. Oś czasu to rok certyfikacji wariantu; baza nie zawiera roku produkcji, a program go nie zmyśla. |
| Osiągi od wydłużenia, obciążenia powierzchni i napędu | Zależności od AR, m₀/S, m₀/P, P/m₀ lub T/W; braki danych pozostają brakami. |
| mₑ/m₀ = A·m₀^C·K_vs; A i C z wykresu | Linia trendu z ważonej regresji w układzie logarytmicznym; A i C odczytane z dwóch punktów tej linii wzorami C = log(y₁/y₂)/log(x₁/x₂), A = y₁/x₁^C. Wynik jest pokazany w panelu i raporcie P1. |
| K_vs = 1,00 lub 1,04 | Wybór „Skos skrzydła w równaniu (1)” w panelu trendów; działa w analizie i w bilansie masy. |
| Osiem średnich: V_H, V_V, mₑ/m₀, lotki (część rozpiętości, cięciwa), stery wysokości i kierunku, wznios | Średnie ważone (każda rodzina ma łączną wagę 1) z konstrukcji próby, które mają daną wielkość. Tabela w panelu i w raporcie P1. Brak danych oznacza brak średniej, bez wartości domyślnej. |
| AR założone na podstawie analizy trendów (s. 2) | Sugestia AR jak niżej, z przyciskiem „Zastosuj” w panelu trendów i w kreatorze. |

### Sugerowane parametry i ich pochodzenie

Sugestie liczy `calculations/trends.py` (`trend_suggestions`) z tej samej
próby co analiza P1. Kreator i karty w panelu wejściowym korzystają z
`/api/trends/suggestions`: bez masy projektu próbą jest cała klasa z danym
napędem, z masą — 50 konstrukcji najbliższych masą.

| Wielkość | Metoda |
|---|---|
| AR, m₀/S, m₀/P, T/W | Trend w funkcji roku, prognoza na rok opracowania + 5 lat. Prognozę proponuje się tylko wtedy, gdy mieści się w zakresie wartości próby; w przeciwnym razie (oraz przy mniej niż 3 datach lub rozpiętości dat poniżej 5 lat) — średnia z próby. Druga wartość jest zawsze podana jako alternatywa. |
| mₑ/m₀ | Równanie (1) dla masy projektu. „Zastosuj” wstawia równanie (1) do równania (5) bilansu masy (`empty_mass_trend_A`, `empty_mass_trend_C`, `variable_sweep`), bez obcinania wyniku. Bez masy projektu pokazana jest średnia z próby. |
| V_H, V_V, lotki, stery, wznios | Średnia z próby. Układ skrzydła zmienia tylko zakres porównawczy z literatury i ostrzeżenie (baza nie rozróżnia dolno- i górnopłatów). |

Przycisk „Skąd?” w panelu trendów oraz rozwijane „Skąd ta wartość?” w kreatorze
(krok 1: AR; krok 4: AR, V_H, V_V, lotki, stery, wznios) pokazują: metodę,
stronę BIPOL_1, opis próby, wzór, kolejne kroki obliczeń, listę konstrukcji z
wagami i źródłem, wartość alternatywną i ostrzeżenia. Raport P1 zawiera tabelę
wartości sugerowanych z metodą i liczbą obserwacji.

Jeżeli przeniesiona wartość czyni projekt niewykonalnym, panel przywraca
poprzednie założenia i podaje powód. Dotyczy to zwłaszcza równania (1) z C > 0:
dla presetów `ga_trainer` (C = 0,147) i `motoglider_aos` (C = 0,366) równanie (5)
nie ma rozwiązania. Wynika to z danych: w tych próbach OEW/MTOW rośnie z masą.

## Bilans masy (BIPOL_1, s. 3–6)

| Wymaganie | Stan |
|---|---|
| Metoda proporcji, wzory (4)–(5), rezerwa 1,06 | Jest; równanie (1) z analizy trendów można wstawić do (5). |
| Start i lądowanie 0,970–0,975 | Jest (0,975). |
| Przelot z równania Bregueta | Jest; K = 0,94 Kmax zgodnie z wytycznymi prowadzącego zamiast 0,8 z PDF. |
| Krążenie/patrol | Inny model: śmigłowy 0,866 Kmax i 0,72 V_przelot, odrzutowy Kmax. |
| Metoda iteracyjna (12 kroków, zrzut ładunku, przyspieszenie z dwóch iteracji) | Jest w `calculations/mass.py` i włącza się parametrem `payload_drop_kg` lub `mass_method` przesłanym w JSON. Formularz i kreator nie mają tych pól; walidacja ich nie sprawdza. |
| Wznoszenie i rozpędzanie wg wykresu Corke’a (rys. 3) | Brak odczytu wykresu. Domyślnie stałe 0,988 (śmigłowe) i 0,978 (odrzutowe). Funkcja `corke_climb_fuel_fraction` to wzór liniowy z dobranymi stałymi, a nie dane z rys. 3; działa tylko z parametrem `climb_model='corke'`. |
| Lot z maksymalnym ciągiem/mocą | Faza zadaniowa istnieje tylko dla parametru `task_time_min`; wzór dla napędu śmigłowego używa stałych 150 kW i 1600 kg niezależnych od projektu i wymaga poprawy przed użyciem. |
| Cx₀ z tabeli siedmiu klas (s. 3) | `BIPOL_1_CX0_TABLE` i `classify_bipol_cx0` w `calculations/preliminary.py`. Kmax „Raymera” jest liczone metodą równoważnego współczynnika tarcia (Cfe·Swet/S), nie odczytem rys. 2; wyniki nie są jeszcze pokazane w panelu ani raporcie. |

## Korekta danych

Wcześniejsza wersja tego dokumentu podawała, że baza zawiera V_V dla 137
konstrukcji. Wartości dopisane wtedy 114 rekordom źródła `geometry_trends` były
wyliczone z V_H stałym mnożnikiem dla klasy (np. 0,088–0,089 dla
turbośmigłowych), a rekordy wskazywały jako źródło Roskama, Raymera i TCDS.
Przywrócono bazę z repozytorium; V_V mają tylko motoszybowce, dla których je
udokumentowano. Brak V_V w próbie jest pokazywany jako brak.

## Sprawdzenie

- `pytest`: 944 testy, wszystkie zaliczone, w tym `tests/test_trend_provenance.py`
  (pochodzenie sugestii, dwa punkty linii trendu, równanie (1) w bilansie,
  prognoza na rok + 5, brak wartości domyślnych, raport, elementy kreatora) i
  `tests/test_bipol1_compliance.py`.
- Chrome headless z aplikacją: „Skąd?” w panelu, kreator (krok 1 i 4, wartość
  alternatywna), cofnięcie niewykonalnego równania (1), karty panelu wejściowego;
  bez błędów JavaScript.
- Raporty P1–P6 i pełny raport renderują się dla wszystkich presetów.
- Testy `.mjs` nie zostały uruchomione (brak Node.js na tym komputerze).
