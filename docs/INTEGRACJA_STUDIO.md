# Integracja projektu z załączonego ZIP-a

Zmiany są oparte na `73d09d0` i zachowują usunięcie przykładów z interfejsu,
czytelniejsze formularze oraz typy `glider` i `motoglider` z tego commita.

Z `BIPOL_Studio_kod_zrodlowy.zip` zaadaptowano:

- nawigację boczną, kokpit, parametryczną sylwetkę i wykres SVG;
- niezmienne migawki parametrów i wyników, porównanie do 8 wariantów;
- eksport CSV z jednostkami, UTF-8 i ochroną tekstu przed formułami arkusza;
- wybór etapów raportu, dane autora, notatki i samodzielny HTML;
- dokładną równowagę sił w ustalonym locie szybowym;
- rozróżnienie trwałego zapisu i pracy wyłącznie w pamięci karty.

Istniejący silnik Pythona pozostaje wspólnym źródłem obliczeń. Nie dodano
drugiego silnika JavaScript. Funkcje rysunków z `dist/visuals.js` źródłowego
projektu są dostosowane w `static/js/studio-visuals.js` do wyników obecnego API.
Skos ćwierci cięciwy jest przeliczany na skos krawędzi natarcia dla tej sylwetki.
Schemat poglądowy nie zastępuje oddzielnego modułu CAD.

## Model szybowania

`calculations/glide.py` wyznacza dla kolejnych Cz:

```
Cx = Cx0 + k Cz²
γ = atan(Cx / Cz)
V = sqrt[2mg / (ρ S sqrt(Cz² + Cx²))]
w = V sin γ
V_pozioma = V cos γ
```

Dzięki temu spełnione są obie składowe równowagi: `L = W cos γ` i `D = W sin γ`.
Wysokość to zadana wysokość przelotu w ISA; masa jest równa MTOW. Model
nie uwzględnia wiatru, ciągu ani oporu trymowania. Starsze moduły dydaktyczne
zachowują swoje modele i przybliżenia; dokładny wynik znajduje się w
`performance.glide` i w nowym widoku lotu szybowego.

## Dane i raporty

Projekty zachowują klucz `bipol_projects_v2` i format importu/eksportu JSON.
Notatki autora są zapisane w `project.editorial`. Warianty używają oddzielnego
klucza `bipol_studio_variants_v1` i przechowują parametry oraz zestaw metryk,
zamiast pełnych, dużych tablic obliczeniowych.

Przywrócenie wariantu tworzy nowy projekt. Edycja aktualnego projektu nie zmienia
zapisanych migawek. Przy błędzie localStorage zmiany pozostają dostępne w pamięci
karty; interfejs informuje o potrzebie pobrania JSON. Uszkodzony JSON w trwałej
pamięci nie jest automatycznie zastępowany wartościami domyślnymi.

`/report?sections=p1,p3,p5` generuje wybrane etapy. Brak `sections` oznacza cały
raport; nieprawidłowy lub pusty zakres daje HTTP 400. Style, skrypty i dane są
dołączone do dokumentu, więc pobrany HTML nie potrzebuje serwera aplikacji.
Podsumowanie, ograniczenia i podane przez autora źródła są zawsze dołączane.

## Sprawdzenie

```sh
work/venv/bin/python -m pytest tests -q
node tests/studio_core.test.mjs
```

Opcjonalny pełny test przeglądarkowy, po uruchomieniu aplikacji:

```sh
work/venv/bin/pip install -r requirements-browser.txt
work/venv/bin/python -m playwright install chromium
work/venv/bin/python tests/browser_studio.py --base-url http://127.0.0.1:5000
```

Istniejącą instalację Chromium można wskazać przez `--browser-path`.
Zrzuty ekranu i pliki testowe trafiają do ignorowanego katalogu `work/studio-qa`.
Test obejmuje eksporty, raport bez sieci, dane autora, warianty i ich limit,
szybowiec, tryb semestralny, trwałość danych, niedostępny localStorage oraz
szerokości ekranu 320–1600 px.
