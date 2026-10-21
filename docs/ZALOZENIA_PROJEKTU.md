# Założenia projektu i pola zależne

W **Opcjach projektu** dostępne są „Nowy projekt” oraz „Edytuj w kreatorze”.
Kreator pozwala wybrać jeden ze 110 tematów lub własny projekt. Temat wczytuje
parametry właściwe dla swojej klasy, niezależnie od wcześniej otwartego samolotu.
Zasięg, prędkość, liczbę pasażerów i wymaganie VS0 można oznaczyć jako narzucone
w temacie. Niezaznaczone wielkości pozostają założeniami roboczymi.

## Geometria

| Wielkości wejściowe | Wielkość obliczana |
| --- | --- |
| Wymaganie VS0 i wydłużenie | Powierzchnia z bilansu masy, następnie rozpiętość |
| Rozpiętość i wydłużenie | Powierzchnia S = b² / Λ |
| Rozpiętość i powierzchnia | Wydłużenie Λ = b² / S |
| Powierzchnia i wydłużenie | Rozpiętość b = √(S · Λ) |

Przy zadanej powierzchni obciążenie W/S wynika z masy i tej powierzchni. Wymaganie
VS0 pozostaje kryterium do sprawdzenia; nie narzuca jednocześnie innej geometrii.
Parametry zależne są tylko do odczytu, a serwer ponownie oblicza je z wybranych
wejść. Masa startowa i obciążenie powierzchni są wynikami bilansu.

Tematy 7 i 8 motoszybowców rozpoczynają się od rozpiętości 21 m i wydłużenia 24.
Można przyjąć inną rozpiętość większą od 20 m. Przykładowo b = 22 m i Λ = 25 dają
S = 19,36 m². Model nie zwiększa sztucznie wydłużenia przez dobór zbyt małej
powierzchni z samego VS0. Dla tematów 1–6 sprawdzana jest zadana rozpiętość
13,5 lub 15 m. Własny projekt nie ma tych ograniczeń tematycznych.

## Masa płatna i napęd

Masa płatna obejmuje pasażerów z bagażem i cargo, bez załogi. Można podać liczbę
pasażerów i cargo, aby obliczyć sumę, lub sumę i liczbę pasażerów, aby obliczyć
pozostałe cargo. Suma mniejsza od masy pasażerów jest błędem, zamiast być
zastępowana zerowym cargo.

Dla napędu śmigłowego można podać dostępną moc. Ta moc jest używana w obliczeniach
osiągów; wynik nie zastępuje jej większą mocą dobraną automatycznie. W raporcie
rozróżniono moc dostępną i wymaganą. Po wybraniu „bez napędu” lokalizacja silnika,
paliwo, moc, rozbieg z własnym napędem i wznoszenie z napędem nie są pytaniami
konfiguratora. Wybór napędu ponownie przywraca właściwe pola i ich zakresy.

Kreator oblicza projekt przed zapisaniem zmian. Przy błędzie pozostaje otwarty,
a istniejący projekt zachowuje dane. Wybrane założenia i blokady są zapisywane
razem z projektem, również w JSON i wariantach porównawczych.

## Weryfikacja

- `work/venv/bin/python -m pytest tests -q`
- `node tests/studio_core.test.mjs`
- `python tests/browser_design_basis.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium`

Testy obejmują wszystkie tematy motoszybowców, równania geometrii, ponowne
przeliczenie zapisanych danych, bagaż w bilansie masy płatnej, dostępną moc,
zmiany trybu, błędne dane bez utraty projektu i szerokości kreatora 320–1440 px.
