# Interfejs pracowni

Zmiany uwzględniają commit `76d212d`, w tym blokady parametrów, nowe obrysy,
bazę geometryczną, motoszybowce i metodykę Paturskiego.

## Widoki

- Przegląd otwiera zapisany projekt bez obowiązkowego okna startowego.
  Pokazuje cztery główne wskaźniki, rysunek i bilans masy.
- Drzewo obliczeń prowadzi od niezależnych założeń przez kolejne poziomy wyników.
  Pokazuje wartości, wzory i główne zależności bieżącego projektu. Uwzględnia wybrany
  tryb skrzydła, masy płatnej i napędu; nawigacja po poprzednikach otwiera również
  schowane założenia. Edycja danych oznacza widoczne wyniki jako wymagające przeliczenia.
- Założenia mają własną stronę; formularz nie poprzedza analiz na telefonie.
  Główna grupa misji jest rozwinięta, pozostałe grupy otwiera użytkownik.
  Tryb zaawansowany, blokady i sugerowane ograniczenia pozostają dostępne.
- Analizy szczegółowe są w rozwijanej grupie nawigacji. Pierwsza sekcja wyniku
  jest otwarta; dalsze tabele i wykresy otwiera użytkownik. Wzory są pod osobnym
  rozwinięciem. Opisy kolumn można włączyć przyciskiem „Objaśnienia”.
- Trendy mają zakładki Wyniki, Dobór samolotów oraz Metoda i źródła.
  W wynikach wybiera się jeden wykres; w doborze działają te same filtry,
  ręczna próba, wyszukiwanie i eksporty. Uwagi pozostają dostępne pod wyraźnym
  rozwinięciem z liczbą komunikatów.
- Opcje projektu zbierają nowy projekt, menedżer, kopię i eksport JSON.
  Raporty oddzielają zakres od danych autora, notatek i dodatkowych formatów.

Kontekstowe objaśnienia i źródła pozostają dostępne, bez powtarzania wszystkich
opisów na każdym ekranie. Zmiany układu nie ograniczają danych w eksporcie.

## Dostępność i błędy

Akordeony formularza obsługują Enter i Spację. Zakładki trendów obsługują strzałki,
Home i End, mają role tab/tabpanel i właściwe aria-selected. Stan blokady jest
ogłaszany przez aria-pressed. Menu mobilne obejmuje fokusem widoczne elementy
i zamyka się Escape; okna projektu przywracają fokus na widoczne opcje.

Błąd obliczeń pojawia się również poza edytorem. „Sprawdź założenia” otwiera
edytor, odpowiednią grupę i nieprawidłowe pole. Stare wyniki pozostają oznaczone
jako nieaktualne. Brak krzywej wznoszenia szybowca daje komunikat zamiast błędu JS.

## Raporty

KaTeX 0.16.9 wraz z fontami jest dołączony lokalnie. Raport zawiera dane fontów,
CSS i JavaScript, więc skład wzorów działa bez CDN i bez połączenia z aplikacją.
Poprawiono uszkodzone sekwencje TeX w szablonach oraz podwójne indeksy.
Najdłuższe porównania podzielono na krótsze wzory i tekstowe statystyki.

Precyzja danych biegunowej szybowania pozostaje pełna; zaokrąglenia dotyczą
prezentacji. Testy zachowują nowy model wydłużenia efektywnego oraz rozszerzone
zbiory referencyjne z `76d212d`.

## Weryfikacja

```sh
work/venv/bin/python -m pytest tests -q
node tests/studio_core.test.mjs
python tests/browser_workspace.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium
python tests/browser_studio.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium
python tests/browser_trends.py --base-url http://127.0.0.1:5000 --browser-path /usr/bin/chromium
```

Testy przeglądarkowe wymagają `requirements-browser.txt` i uruchomionej aplikacji.
Obejmują edycję i blokady, objaśnienia, odzyskiwanie po błędzie, wybór próby,
warianty, eksporty, tryb semestralny, zapis, niedostępną pamięć oraz szerokości
320–1600 px. Raporty P1–P6 sprawdzono pod kątem poprawnego renderowania matematyki.
