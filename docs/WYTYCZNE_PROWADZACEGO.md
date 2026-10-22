# Wytyczne prowadzącego — zastosowanie w BIPOL

Podstawą jest pięć fotografii notatek przekazanych przez użytkownika 21.10.2026.
Notatki dotyczą wymagań projektu dydaktycznego. Nie są przepisami certyfikacyjnymi.
Jawne wskazówki z zajęć mają pierwszeństwo przed wcześniejszymi wartościami
domyślnymi programu; nieczytelnych dopisków nie zamieniono w równania.

## Odczyt i wdrożenie

| Fotografia | Wytyczna | Działanie programu |
|---|---|---|
| IMG20261021122713 | P1: gładkie A4, rysunek odręczny, trzy rzuty; dziób w lewo / do góry | Raport P1 ma trzy rzuty. Przycisk „Wzór A4 gładki” drukuje osobny arkusz w jednej skali, bez raportu i pasków narzędzi. Wymóg własnego rysunku odręcznego pozostaje jawny. |
| IMG20261021122713 | P3: papier milimetrowy; wskazać mocowanie podwozia | Przycisk „Wzór A4 z siatką”; siatka 1/10 mm przy wydruku 100%. Mocowanie do kadłuba lub skrzydła wybiera się w konfiguracji. Położenie głównego podwozia pochodzi z bilansu, rozstaw z geometrii. Rysunek mocowań jest koncepcyjny. |
| IMG20261021122713 | Materiały Figata i Grabowskiego, katalogi Jane’s, Excel | Zachowano materiały i bibliografię. CSV zawiera próbę, obciążenia i źródła. Import uzupełnień CSV wymaga identyfikatora konstrukcji oraz źródła i warunków. Jane’s jest wskazanym miejscem poszukiwania danych, nie fikcyjnym źródłem użytym w obliczeniach. |
| IMG20261021122725 | Wznoszenie, zasięg, długość startu/lądowania; „nie rozbieg” | Osobne pola `takeoff_distance_m`, `landing_distance_m` i kontrole całkowitych odległości nad/znad 15 m. Dawny `takeoff_run_m` pozostaje dodatkowym ograniczeniem rozbiegu; jego wartości nie przemianowano na pełny start. |
| IMG20261021122725 | 6 wykresów: 5 parametrów + 1 masowy, 2–3 w funkcji lat | Raport P1 zawiera dokładnie sześć miejsc na wykresy: jeden masowy, dwa czasowe, trzy zależności parametrów. Preferowane są wznoszenie od obciążenia napędu, zasięg od wydłużenia i start od obciążenia powierzchni. Jeśli brak obserwacji, wybierana jest inna jawnie opisana zależność z tej samej próby. Brak wymaganego wznoszenia pozostaje w kontroli kompletności. Brak danych do wykresu nie oznacza zera ani gotowej regresji. |
| IMG20261021122725 | Obciążenie powierzchni/mocy, ostrożnie z P/m i m/P | Dostępne m₀/S [kg/m²], W/S [N/m²], m₀/P [kg/kW], P/m₀ [kW/kg], T/W [−]. Raporty nie używają samej mocy silnika ani samej powierzchni jako zamiennika tych obciążeń. Jednostki pozostają na osiach i w CSV. |
| IMG20261021122735 | Co najmniej 8 podobnych samolotów, opadające mₑ/m₀=f(m₀) | Kontrola minimum 8 rodzin i próby każdej zależności. C≥0 wywołuje wynik „do uzupełnienia”; regresja zachowuje rzeczywiste punkty i znak. Nie dobiera się automatycznie danych tylko po to, by wymusić wynik. Zalecenie 20 konstrukcji z PDF jest odróżnione od minimum z zajęć. |
| IMG20261021122735 | Cechy geometryczne: V_H, lotki, stery, wznios; 2–3 przykłady | Dla każdego parametru do raportu trafiają trzy przykłady z tej samej klasy. Brak klasy nie jest już maskowany średnią lub regresją całej bazy. Względną rozpiętość jednej lotki odnosi się do b/2; nie myli się jej z b. |
| IMG20261021122735 | Sloty nie są odlodzeniem | Opis w raporcie aerodynamicznym; poprawiono rozpoznawanie identyfikatora `slats_auto`, który wcześniej nie uruchamiał poprawki modelu przedskrzydeł. |
| IMG20261021122735 | 115 kg = pasażer z bagażem; pasażer/cargo/paliwo | Nowe projekty i tematy otrzymują 115 kg. Istniejące jawne założenia masy nie są nadpisywane; różnica jest wskazana w kontroli. P2 zawiera bilans zamiany masy pasażerów na paliwo przy stałym MTOW. Jest to granica masowa, bez przyjmowania nieznanej pojemności zbiorników. |
| IMG20261021122739 | Klapy 20° do startu i 40° do lądowania (potwierdzone przez użytkownika 22.10.2026) | Stałe konfiguracje 0°/20°/40° w modelu aerodynamicznym, wynikach API i tabelach P4. Wychylenia są narzucone metodyką; przyrosty Cz/Cx pozostają przybliżeniami dla wybranego rodzaju mechanizacji. |
| IMG20261021122739 | Nie maksymalizować bezrefleksyjnie Cz,max; n=L/W, n=1 w locie poziomym | Raport wyjaśnia kompromis nośność/opór i poprawny związek n=1+a_z/g. Obciążenia do wymiarowania nadal wynikają z kategorii i podmuchów; współczynnik bezpieczeństwa jest oddzielny. |
| IMG20261021122751 | Masa maleje w przelocie; ok. 5 iteracji | Fazy misji zmniejszają masę o spalone paliwo. Minimum pięć iteracji, dalsze obliczenia do zbieżności. Raport pokazuje pierwsze pięć i końcową, z resztą równania. Nie zatrzymuje się niezbieżnego bilansu po piątym kroku. |
| IMG20261021122751 | 0,970≤m₁/m_TO≤0,975 | Przyjęto 0,975; rozruch i start stanowią jeden ubytek. Brak podwójnego naliczania paliwa. Dla szybowca wszystkie ułamki wynoszą 1. |
| IMG20261021122751 | K_przelot=0,94 K_max i równanie Bregueta | 0,94 zastępuje wcześniejsze 0,8 także po wczytaniu starego projektu. Pole jest wynikiem przyjętej metodyki. Raport rozróżnia jednostki TSFC/SFC i wzory dla ciągu oraz mocy; K_max z modelu wstępnego jest podane liczbowo. |

## Dopiski wymagające interpretacji

- „2/3 wyk. w funkcji lat” odczytano jako **dwa lub trzy wykresy**; realizowane są dwa.
- „~30 lat” traktujemy jako zalecany przekrój historyczny. Dat nie uzupełnia się
  umownie, a certyfikacji nie przedstawia jako daty produkcji. Rok i źródło można
  uzupełnić przez CSV, ale kolumna `year` nadal oznacza certyfikację.
- Znak jednostki przy klapach został wyjaśniony przez użytkownika 22.10.2026:
  chodzi o **20° i 40°**, nie procenty. Reguła została wdrożona. Rzeczywiste
  przyrosty nośności i oporu dla danego profilu wymagają danych doświadczalnych.
- „m>5 t → CS-25”, ogólne 3,6 i „pasażerskie 2,5” są skrótami notatkowymi,
  nie kompletną podstawą klasyfikacji. Nie zastępują kryteriów kategorii,
  liczby miejsc, prędkości ani zależnych od masy przepisów obciążeń.
- Zapis T/W=Cx,min/Cz,max nie jest tożsamością dla dowolnego punktu biegunowej:
  minimum oporu i maksimum nośności zwykle występują przy innych kątach natarcia.
  Zachowano T/W=Cx/Cz dla jednego punktu pracy, a n i wznoszenie liczono osobno.
- Nieczytelne pojedyncze hasła i cytat nie stanowią danych wejściowych.

## Dane i brakujące obserwacje

Importer FAST/CADO zachowuje oznaczenie TOFL/LFL jako **field length**. Nie
przyjmuje automatycznie wysokości przeszkody 15 m dla katalogowej wartości.
Wartości bez określenia podstawy (np. samo `takeoff_m` w starszej bazie
motoszybowców) nie trafiają do analizy całkowitego startu. Opadania motoszybowca
nie używa się jako prędkości wznoszenia. Nieznana wartość pozostaje pusta.

W zakładce „Dobór samolotów” można pobrać szablon CSV UTF-8 i wczytać dane
z dokumentacją źródłową. Nagłówki: `id`, `model`, `climb_rate_ms`,
`takeoff_distance_m`, `landing_distance_m`, `year`, `source`. Źródło powinno
zawierać dokument, stronę/URL, masę, atmosferę i wysokość przeszkody.
Przecinek dziesiętny jest obsługiwany dla plików rozdzielanych średnikami.
Wczytane wartości zapisują się w projekcie; wspólna baza nie jest zmieniana.

Kontrola wytycznych jest oddzielona od osiągów i zdatności. Samo istnienie
sześciu rysunków nie potwierdza wystarczającej próby, jakości regresji ani
spełnienia wymagań prowadzącego. Raport zachowuje informacje o brakach.

## Sprawdzenie

Regresje w `tests/test_instructor.py` obejmują wzory misji, wymianę pasażera
na paliwo, pełny start i lądowanie, niewystarczającą moc, sześć wykresów,
rosnącą regresję masową oraz walidację i pochodzenie uzupełnień CSV.
Test przeglądarkowy sprawdza kreator, import i zapis, raport offline oraz
wydruk arkusza A4 w jednej skali.
