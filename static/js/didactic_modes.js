/**
 * BiPOL Requiem — tryb dydaktyczny i konstrukcyjny.
 * 1. Uzupełnia PARAMETER_ENCYCLOPEDIA o brakujące parametry.
 * 2. Każdemu parametrowi dodaje objaśnienie „prosto mówiąc”.
 * 3. Dokleja ikonkę (i) i objaśnienie pod każdym polem formularza, kreatora,
 *    panelu BIPOL I i analizy trendów.
 * 4. Przełącza tryb: 🎓 dydaktyczny (objaśnienia widoczne) / 🛠️ konstrukcyjny (zwarty).
 */
(function () {
  if (typeof PARAMETER_ENCYCLOPEDIA === 'undefined') return;

  const E = (symbol, title, plain, more, typ, extra = {}) => ({
    symbol, title, short_desc: plain, plain, more, typical_ranges: typ,
    full_definition: extra.def || '', formula: extra.formula || '—',
    effect_increase: more, galinski_note: extra.note || '—'
  });

  // ---- Brakujące parametry ----
  Object.assign(PARAMETER_ENCYCLOPEDIA, {
    name: E('Nazwa', 'Nazwa projektu samolotu',
      'Własna nazwa projektowanego statku powietrznego lub oficjalne oznaczenie konstrukcyjne (np. PZL-102 Kos, SZD-56 Diana 3).',
      'Pojawia się na stronie tytułowej sprawozdania, rysunku technicznym A3Z i liście zapisanych projektów.',
      'Dowolny czytelny identyfikator, np. nazwa modelu lub akronim.'),
    topic: E('Temat', 'Oficjalny temat projektu BIPOL I',
      'Numer i pełna treść jednego ze 110 tematów wydziałowych ZSiS MEiL PW. Wybór tematu automatycznie ustawia parametry wyjściowe samolotu.',
      'Zmiana tematu przestawia sugerowane osiągi, konfigurację płata i zespół napędowy.',
      'Tematy 1–110 z wydziałowej listy BIPOL I.'),
    student_name: E('Autor', 'Imię i nazwisko studenta-konstruktora',
      'Dane autora projektu. Trafiają na stronę tytułową sprawozdania (Projekt 1–6) oraz do tabliczki rysunku technicznego.',
      'Uzupełnij, aby wygenerować kompletne sprawozdanie do oddania prowadzącemu.',
      'Jan Kowalski'),
    album_no: E('Nr albumu', 'Numer albumu (indeksu)',
      'Sześciocyfrowy numer indeksu na Politechnice Warszawskiej, identyfikujący projektanta.',
      'Drukowany w nagłówkach obliczeń i na okładce teczki projektu.',
      'Np. 123456'),
    group_no: E('Grupa', 'Numer grupy dziekańskiej lub projektowej',
      'Oznaczenie grupy ćwiczeniowej / projektowej na Wydziale MEiL PW.',
      'Ułatwia prowadzącemu identyfikację terminu zajęć i wpis oceny.',
      'Np. G1, D1, L2'),
    supervisor: E('Prowadzący', 'Imię i nazwisko prowadzącego projekt',
      'Tytuł i nazwisko nauczyciela akademickiego oceniającego projekt (np. dr inż. / prof. PW).',
      'Trafi do metryczki formalnej sprawozdań semestralnych P1–P6.',
      'Np. dr inż. Jan Nowak'),
    submission_date: E('Data', 'Data oddania projektu do oceny',
      'Data złożenia projektu lub wygenerowania sprawozdania semestralnego.',
      'Drukowana na stronie tytułowej i w nagłówkach wydruku.',
      'Format DD.MM.RRRR, np. 30.10.2026'),
    academic_year: E('Rok akad.', 'Rok akademicki realizacji',
      'Rok akademicki studiów, w którym realizowany jest przedmiot BIPOL I.',
      'Umieszczany w stopce wydziałowej strony tytułowej.',
      'Np. 2026/2027'),
    m_payload: E('m_płatna [kg]', 'Ładunek płatny łącznie',
      'Wszystko, za co ktoś „płaci” za przewiezienie: pasażerowie z bagażem plus towar. Załoga i paliwo się tu nie liczą.',
      'Każdy dodatkowy kilogram ładunku podnosi masę startową o 2–3 kg (bo trzeba większego skrzydła, silnika i więcej paliwa).',
      'Szkolny 2-os.: 90–200 kg | Turystyczny 4-os.: 300–450 kg | Dyspozycyjny: 600–1500 kg.',
      { formula: 'm_płatna = n_pax · m_os + m_cargo' }),
    wing_area_m2: E('S [m²]', 'Powierzchnia skrzydła',
      'Ile metrów kwadratowych ma skrzydło widziane z góry (razem z kawałkiem „schowanym” w kadłubie). To ono nosi samolot.',
      'Większe skrzydło = wolniejsze, bezpieczniejsze lądowanie i krótszy start, ale większy opór i masa w przelocie.',
      'ULM: 9–13 m² | Cessna 172: 16,2 m² | Szybowiec 15 m: 9–11 m² | ATR 42: 54,5 m².',
      { formula: 'S = m₀·g / (W/S)' }),
    wing_planform: E('Obrys', 'Kształt skrzydła w rzucie z góry',
      'Jak wygląda skrzydło z góry: prostokąt (najprostszy w budowie), trapez (lżejszy, lepszy aerodynamicznie) albo prostokąt przechodzący w trapez.',
      'Bardziej zbieżny obrys zmniejsza opór i masę, ale komplikuje produkcję (każde żebro inne).',
      'Szkolne/ULM: prostokątne | GA: prostokątno-trapezowe | Szybowce i odrzutowce: trapezowe.'),
    break_span_ratio: E('η_zał [-]', 'Miejsce załamania obrysu',
      'W skrzydle prostokątno-trapezowym: w którym miejscu rozpiętości (ułamek połowy rozpiętości) kończy się część prostokątna i zaczyna trapez.',
      'Większa wartość = dłuższa część prostokątna: prostsza produkcja, ale trochę większy opór indukowany.',
      'Typowo 0,35–0,60 (np. Piper PA-28 ≈ 0,5).'),
    gear_attachment: E('Podwozie', 'Mocowanie podwozia głównego',
      'Gdzie przykręcone są główne koła: do skrzydła czy do kadłuba. Zmienia rozstaw kół, masę goleni i rysunek trzech rzutów.',
      'Mocowanie do skrzydła daje szeroki, stabilny rozstaw kół; do kadłuba — krótsze, lżejsze golenie, ale węższy rozstaw.',
      'Dolnopłaty: zwykle skrzydło | Górnopłaty: zwykle kadłub lub owiewki przykadłubowe.'),
    gear_retraction: E('Chowanie', 'Podwozie stałe czy chowane',
      'Czy koła zostają cały czas na zewnątrz (stałe), czy chowają się w locie (chowane).',
      'Chowane podwozie zmniejsza opór (ok. 15–25 % oporu szkodliwego), ale dodaje 2–4 % masy i komplikację.',
      'Poniżej ~250 km/h: stałe | Powyżej ~250 km/h: chowane.'),
    takeoff_distance_m: E('S_TO,15 [m]', 'Całkowita droga startu do 15 m',
      'Odległość od ruszenia z miejsca do chwili, gdy samolot jest 15 m (50 ft) nad pasem. Obejmuje rozbieg i początek wznoszenia.',
      'Większa dopuszczalna droga = można dać słabszy silnik i mniejsze skrzydło.',
      'STOL: 150–300 m | GA: 400–700 m | Regionalne: 1000–1400 m | Odrzutowe: 1500–2500 m.'),
    landing_distance_m: E('S_LDG,15 [m]', 'Całkowita droga lądowania z 15 m',
      'Odległość od przelotu nad przeszkodą 15 m do całkowitego zatrzymania na pasie.',
      'Krótsza wymagana droga = trzeba niższej prędkości lądowania, czyli większego skrzydła lub lepszych klap.',
      'STOL: 150–300 m | GA: 400–650 m | Regionalne: 900–1200 m | Odrzutowe: 1200–2000 m.'),
    n_engines: E('n_s [-]', 'Liczba silników',
      'Ile silników ma samolot. Jeden — prościej i taniej; dwa — samolot może bezpiecznie lecieć dalej, gdy jeden zgaśnie.',
      'Więcej silników = większa niezawodność, ale wyższa masa, koszt i opór gondoli.',
      'Szkolne/turystyczne: 1 | Dyspozycyjne i regionalne: 2 | Ciężkie transportowe: 2–4.'),
    engine_power_kw: E('P [kW]', 'Moc silnika (zadana)',
      'Ile kilowatów daje silnik na wale. 1 kW ≈ 1,36 KM. Wpisz, jeśli temat narzuca konkretny silnik; inaczej program dobierze moc sam.',
      'Większa moc = krótszy start, lepsze wznoszenie i wyższa prędkość, ale cięższy silnik i większe zużycie paliwa.',
      'Rotax 912: 59–73 kW | Lycoming O-360: 134 kW | PT6A: 450–1100 kW.'),
    power_input_mode: E('Tryb mocy', 'Skąd bierze się moc silnika',
      '„Dobierana” — program sam liczy, ile mocy potrzeba do spełnienia wymagań. „Zadana” — Ty wpisujesz moc konkretnego silnika, a program sprawdza, czy wystarczy.',
      'Moc zadana jest wygodna, gdy temat lub katalog silników narzuca jednostkę napędową.',
      'Na początku projektu: dobierana | Po wyborze silnika z katalogu: zadana.'),
    wing_input_mode: E('Dane skrzydła', 'Które wymiary skrzydła podajesz sam',
      'Skrzydło opisują trzy powiązane liczby: rozpiętość b, powierzchnia S i wydłużenie Λ = b²/S. Wystarczy podać dwie — trzecią program wyliczy. W trybie „z obciążenia” podajesz tylko Λ, a S wynika z masy i prędkości lądowania.',
      'Wybierz tryb zgodny z tematem: jeśli temat narzuca rozpiętość (np. 15 m), podaj b i Λ.',
      'Brak ograniczeń: z obciążenia | Narzucona rozpiętość: b + Λ.'),
    payload_input_mode: E('Ładunek', 'Jak podajesz ładunek',
      '„Miejsca” — podajesz liczbę osób i masę jednej osoby. „Masa” — podajesz od razu łączną masę ładunku płatnego.',
      'Dla samolotów pasażerskich wygodniej podać miejsca, dla transportowych i rolniczych — masę.',
      'Pasażerskie: miejsca | Cargo, rolnicze, pożarnicze: masa.'),
    v_h: E('V_H [-]', 'Współczynnik objętości usterzenia poziomego',
      'Miara „siły” statecznika poziomego: jego powierzchnia razy odległość od skrzydła, podzielone przez powierzchnię i cięciwę skrzydła.',
      'Większy V_H = samolot stateczniejszy podłużnie, ale cięższy usterzeniem i z większym oporem.',
      'GA: 0,6–0,8 | Szybowce: 0,5–0,7 | Komunikacyjne: 0,9–1,1.'),
    v_v: E('V_V [-]', 'Współczynnik objętości usterzenia pionowego',
      'To samo co V_H, ale dla statecznika pionowego (kierunkowego). Mówi, jak mocno samolot „trzyma kierunek”.',
      'Większy V_V = lepsza stateczność kierunkowa, ważna przy awarii silnika w dwusilnikowcu.',
      'GA: 0,035–0,05 | Dwusilnikowe: 0,06–0,08 | Szybowce: 0,02–0,03.'),
    mass_method: E('Metoda masy', 'Jak liczona jest masa startowa (P2)',
      'Wybór sposobu oszacowania masy: z prawa statystycznego (masa pusta zależy od masy startowej) albo ze stałego udziału masy pustej.',
      'Metoda statystyczna jest dokładniejsza, stała proporcja — prostsza do ręcznego sprawdzenia.',
      'Projekt P2: zwykle statystyczna (Raymer / własny trend).'),
    empty_mass_model: E('Model m_e', 'Prawo masy pustej',
      'Wzór, który mówi, jaką część masy startowej stanowi pusty samolot (bez paliwa, ludzi i ładunku). Pochodzi z danych podobnych samolotów.',
      'Model z własnej bazy trendów jest najbardziej „Twój”; model z literatury — najszybszy.',
      'Typowo m_e/m₀ = 0,55–0,70 dla GA, 0,60–0,70 dla szybowców.'),
    mass_initial_guess: E('m₀,start [kg]', 'Pierwsze przybliżenie masy',
      'Liczba, od której program zaczyna zgadywanie masy startowej w pętli iteracji. Na wynik końcowy prawie nie wpływa.',
      'Za duża lub za mała wartość wydłuży tylko iterację.',
      'Wpisz masę podobnego samolotu z bazy.'),
    empty_mass_a: E('A [-]', 'Współczynnik A prawa masy pustej',
      'Mnożnik we wzorze m_e/m₀ = A·m₀^C. Ustala „poziom” krzywej: ile waży pusty samolot danej klasy.',
      'Większe A = cięższa konstrukcja, większa masa startowa.',
      'Raymer, lotnictwo ogólne: A ≈ 1,5–2,4.', { formula: 'm_e/m₀ = A · m₀^C' }),
    empty_mass_c: E('C [-]', 'Wykładnik C prawa masy pustej',
      'Wykładnik we wzorze m_e/m₀ = A·m₀^C. Mówi, jak udział masy pustej zmienia się, gdy samolot rośnie (zwykle lekko maleje — C ujemne).',
      'Bardziej ujemne C = duże samoloty są relatywnie lżejsze.',
      'Typowo C = −0,05 … −0,15.', { formula: 'm_e/m₀ = A · m₀^C' }),
    empty_mass_fraction: E('m_e/m₀ [-]', 'Stały udział masy pustej',
      'Jaką część masy startowej stanowi pusty samolot, jeśli przyjmujesz stałą wartość zamiast wzoru.',
      'Większy udział = mniej miejsca na paliwo i ładunek, więc masa startowa szybko rośnie.',
      'Kompozytowe ULM: 0,50–0,58 | GA metalowe: 0,58–0,66 | Szybowce: 0,60–0,70.'),
    return_range_km: E('R_powrót [km]', 'Zasięg drogi powrotnej',
      'Jeśli misja jest „tam i z powrotem” (np. zrzut ładunku), to długość odcinka powrotu.',
      'Dłuższy powrót = więcej paliwa i większa masa startowa.',
      'Misja zwykła: 0 | Rolnicza/pożarnicza: 20–100 km.'),
    payload_drop_kg: E('m_zrzut [kg]', 'Ładunek zrzucany w locie',
      'Ile kilogramów samolot zostawia po drodze (woda gaśnicza, środki ochrony roślin, zasobnik). Po zrzucie leci lżejszy.',
      'Większy zrzut = lżejszy lot powrotny, czyli mniej paliwa na powrót.',
      'Rolniczy: 500–2500 kg | Pożarniczy: 2000–6000 kg.'),
    loiter_speed_kmh: E('V_krąż [km/h]', 'Prędkość krążenia / oczekiwania',
      'Prędkość, z jaką samolot czeka w powietrzu (krąży nad lotniskiem albo patroluje). Zwykle bliska prędkości najmniejszego zużycia paliwa.',
      'Za szybkie krążenie spala więcej paliwa na godzinę.',
      'GA: 130–180 km/h | Regionalne: 250–350 km/h.'),
    max_power_time_min: E('t_Pmax [min]', 'Czas pracy na mocy maksymalnej',
      'Ile minut silnik pracuje na pełnej mocy (start i początek wznoszenia). Potrzebne do policzenia paliwa na start.',
      'Dłuższy czas = więcej paliwa na fazę startu.',
      'Typowo 1–5 min.'),
    max_power_kw: E('P_max [kW]', 'Moc maksymalna do bilansu paliwa',
      'Moc silnika w fazie startu, używana do policzenia, ile paliwa zużyje start.',
      'Większa moc startowa = więcej paliwa w tej fazie.',
      'Zgodnie z kartą katalogową silnika.'),
    max_thrust_kn: E('T_max [kN]', 'Ciąg maksymalny do bilansu paliwa',
      'Ciąg silnika odrzutowego w fazie startu, używany do policzenia paliwa na start.',
      'Większy ciąg = więcej paliwa w fazie startu.',
      'VLJ: 4–8 kN | Biznesowe: 15–40 kN | Regionalne: 60–120 kN.'),
    max_power_sfc: E('c_Pmax', 'Zużycie paliwa na mocy maksymalnej',
      'Ile paliwa spala silnik na jednostkę mocy (lub ciągu), gdy pracuje na pełnej mocy. Zwykle więcej niż w przelocie.',
      'Wyższe zużycie = cięższy bilans paliwa startu.',
      'Tłokowe: 270–320 g/(kW·h) | Odrzutowe: 0,6–0,9 1/h.'),
    climb_fraction_mode: E('Udział wznoszenia', 'Jak liczony jest ułamek masy na wznoszenie',
      'Wybór, czy zużycie paliwa na wznoszenie bierzemy z tabeli statystycznej, czy liczymy z wysokości i prędkości (wykres Corke’a).',
      'Metoda z wykresu jest dokładniejsza, tabelaryczna — szybsza.',
      'Szkic P2: tabela | Dokładniej: wykres Corke’a.'),
    climb_start_altitude_m: E('H_0 [m]', 'Wysokość początku wznoszenia',
      'Wysokość lotniska, z którego samolot startuje (nad poziomem morza).',
      'Wyżej położone lotnisko = rzadsze powietrze, dłuższy start.',
      'Typowo 0–500 m.'),
    climb_start_speed_kmh: E('V_0 [km/h]', 'Prędkość początku wznoszenia',
      'Prędkość, od której liczymy wznoszenie na wykresie energii (zwykle prędkość tuż po starcie).',
      'Wpływa tylko na odczyt z wykresu udziału paliwa na wznoszenie.',
      'Ok. 1,2–1,3 × prędkość przeciągnięcia.'),
    corke_start_ordinate: E('Odczyt 1', 'Rzędna początkowa z wykresu Corke’a',
      'Wartość odczytana z wykresu dla stanu na początku wznoszenia.',
      'Służy do policzenia ułamka masy zużytego na wznoszenie.',
      'Odczytaj z wykresu dla H_0 i V_0.'),
    corke_end_ordinate: E('Odczyt 2', 'Rzędna końcowa z wykresu Corke’a',
      'Wartość odczytana z wykresu dla stanu na wysokości przelotu.',
      'Większa różnica odczytów = więcej paliwa na wznoszenie.',
      'Odczytaj z wykresu dla H i V_cr.'),
    preliminary_polar_mode: E('Biegunowa wstępna', 'Skąd bierzemy wstępną biegunową',
      'Biegunowa to związek siły nośnej z oporem. Na początku projektu można ją oszacować ze szkicu (powierzchnia omywana), z rodziny Raymera albo z klasy porównawczej.',
      'Metoda ze szkicu jest najbardziej „Twoja”, ale wymaga szkicu samolotu.',
      'P1/P2: szkic lub Raymer.'),
    sketch_swet_ratio: E('S_wet/S [-]', 'Stosunek powierzchni omywanej do powierzchni skrzydła',
      'Ile razy cała zewnętrzna „skóra” samolotu (owiewana powietrzem) jest większa od powierzchni skrzydła. Odczytujesz to ze szkicu.',
      'Większy stosunek = więcej tarcia, większy opór szkodliwy, niższa doskonałość.',
      'Szybowce: 3,5–4,5 | GA: 4–5,5 | Komunikacyjne: 5,5–6,5.'),
    raymer_family: E('Rodzina', 'Rodzina samolotów wg Raymera',
      'Grupa samolotów, z której Raymer podaje typową doskonałość i opór. Wybierz najbardziej podobną do Twojej.',
      'Zła rodzina da zbyt optymistyczną lub pesymistyczną doskonałość.',
      'Np. GA jednosilnikowe, szybowce, odrzutowce biznesowe.'),
    raymer_kmax: E('K_max [-]', 'Doskonałość maksymalna z Raymera',
      'Ile metrów samolot przeleci do przodu, tracąc 1 m wysokości przy najlepszej prędkości — wg danych Raymera.',
      'Wyższa doskonałość = mniej paliwa na trasę, mniejsza masa startowa.',
      'GA: 10–14 | Szybowce: 35–60 | Komunikacyjne: 15–20.'),
    cx0_reference_class: E('Klasa C_x0', 'Klasa porównawcza oporu szkodliwego',
      'Grupa samolotów, z której bierzemy typową wartość oporu szkodliwego C_x0 (tabele A, B, C Paturskiego).',
      'Bardziej „czysta” klasa = niższy opór, wyższa prędkość, mniejsza moc.',
      'Chowane podwozie: 0,020–0,025 | Stałe: 0,027–0,036.'),
    trend_year_basis: E('Rok', 'Rok bazowy trendu',
      'Rok, dla którego odczytujemy wartości z analizy trendów (np. jaki będzie typowy samolot w roku wejścia do służby).',
      'Późniejszy rok = lżejsza, nowocześniejsza konstrukcja według trendu.',
      'Zwykle bieżący rok lub planowany rok oblotu.'),
    trend_source: E('Źródło', 'Skąd biorą się samoloty do trendu',
      'Zbiór samolotów porównawczych: wbudowana baza, własne dane lub oba naraz.',
      'Więcej podobnych samolotów = wiarygodniejszy trend.',
      'Minimum 6–10 samolotów podobnej klasy.'),
    trend_count: E('Liczba', 'Ile samolotów bierzemy do trendu',
      'Ilu najbardziej podobnych samolotów program użyje do wyliczenia linii trendu.',
      'Za mało — przypadkowy wynik; za dużo — wchodzą samoloty niepodobne.',
      'Typowo 8–20.'),
    trend_engine_count: E('Silniki', 'Filtr liczby silników',
      'Bierzemy do porównania tylko samoloty z taką samą liczbą silników jak Twój.',
      'Filtr zwiększa podobieństwo, ale zmniejsza liczbę samolotów.',
      '1 lub 2.'),
    trend_year_min: E('Od roku', 'Najstarszy rocznik w trendzie',
      'Samoloty starsze niż ten rok są pomijane.',
      'Wyższa wartość = trend opisuje tylko nowsze konstrukcje.',
      'Np. 1970–2000.'),
    trend_year_max: E('Do roku', 'Najnowszy rocznik w trendzie',
      'Samoloty nowsze niż ten rok są pomijane.',
      'Zwykle zostaw bieżący rok.',
      'Bieżący rok.'),
    trend_weighting: E('Wagi', 'Jak ważone są samoloty w trendzie',
      'Czy każdy samolot liczy się tak samo, czy bardziej podobne (lub nowsze) mają większy wpływ na linię trendu.',
      'Ważenie podobieństwem daje wynik bliższy Twojemu projektowi.',
      'Równe lub wg podobieństwa.'),
    trend_variable_sweep: E('Przegląd', 'Którą zależność badasz',
      'Para wielkości (np. masa pusta od masy startowej), dla której rysowany jest wykres i dopasowywana linia trendu.',
      'Zmień, aby zobaczyć inne zależności z bazy.',
      'm_e(m₀), S(m₀), P(m₀) itp.'),
    mission_phase_model: E('Fazy misji', 'Model profilu lotu',
      'Z jakich etapów składa się lot (start, wznoszenie, przelot, krążenie, lądowanie). Każdy etap „zjada” część paliwa.',
      'Więcej faz = dokładniejszy bilans paliwa.',
      'Standard BIPOL: 6–7 faz.'),
    fuel_reserve_factor: E('Rezerwa [-]', 'Zapas paliwa',
      'O ile więcej paliwa zabieramy niż potrzeba na samą trasę (na objście burzy, lotnisko zapasowe, błędy).',
      'Większa rezerwa = bezpieczniej, ale cięższy samolot.',
      'Typowo 1,05–1,10 (5–10 %) lub 45 min lotu.'),
    mission_ld_factor: E('K_misji/K_max', 'Doskonałość w misji względem maksymalnej',
      'W prawdziwym przelocie samolot rzadko leci z najlepszą doskonałością. Ten współczynnik mówi, jaką jej część faktycznie osiąga.',
      'Wyższy współczynnik = mniej paliwa w obliczeniach.',
      'Śmigłowe: 0,85–1,0 | Odrzutowe: 0,85–0,95.')
  });

  // ---- „Prosto mówiąc” dla parametrów już opisanych w encyklopedii ----
  const PLAIN = {
    aircraft_type: ['Jaki to rodzaj maszyny: tłokowy samolot sportowy, motoszybowiec, szybowiec, turbośmigłowiec, odrzutowiec albo dron. Od tego zależą wszystkie statystyki masy i domyślne wartości.', 'Zmiana klasy przestawia współczynniki statystyczne i domyślne osiągi.'],
    category: ['Według jakich przepisów samolot byłby dopuszczony do lotów. Przepisy mówią m.in., ile osób może zabrać i jakie przeciążenia musi wytrzymać.', 'Ostrzejsza kategoria (np. akrobacyjna) = mocniejsza i cięższa konstrukcja.'],
    wingspan_m: ['Odległość od końca lewego do końca prawego skrzydła. Wpisz 0, jeśli program ma ją policzyć sam.', 'Większa rozpiętość = mniejszy opór przy wolnym locie, ale większy moment gnący i cięższe skrzydło.'],
    wing_config: ['Na jakiej wysokości kadłuba jest skrzydło: na dole (dolnopłat), w środku (średniopłat), na górze (górnopłat), na górze z podporami (zastrzałowy).', 'Wpływa na podwozie, miejsce w kabinie, stateczność i opór.'],
    aspect_ratio: ['Jak „smukłe” jest skrzydło: długie i wąskie (duże Λ, jak w szybowcu) czy krótkie i szerokie (małe Λ, jak w akrobacji).', 'Większe Λ = mniejszy opór, lepsze szybowanie i zasięg, ale cięższe, bardziej wiotkie skrzydło.'],
    taper_ratio: ['Ile razy końcówka skrzydła jest węższa od nasady. 1 = prostokąt, 0,5 = końcówka o połowę węższa.', 'Mniejsza wartość = lżejsze skrzydło i mniejszy opór, ale poniżej 0,35 końcówki łatwo przeciągają.'],
    sweep_quarter_deg: ['O ile stopni skrzydło jest „odchylone do tyłu”, jak strzała. Potrzebne dopiero w szybkich odrzutowcach.', 'Większy skos pozwala latać szybciej (blisko prędkości dźwięku), ale pogarsza zachowanie przy małej prędkości.'],
    dihedral_deg: ['Kąt, pod jakim skrzydła są uniesione ku górze (litera V widziana z przodu). Dzięki temu samolot sam wraca do poziomu po przechyleniu.', 'Większy wznios = spokojniejszy, stateczniejszy samolot, ale mniej zwrotny.'],
    range_km: ['Jak daleko samolot ma dolecieć bez tankowania z pełnym ładunkiem.', 'Większy zasięg = więcej paliwa, większy i cięższy samolot.'],
    cruise_altitude_m: ['Na jakiej wysokości samolot leci w przelocie. Wyżej powietrze jest rzadsze.', 'Wyżej = mniejszy opór i szybszy lot, ale silnik tłokowy traci moc, a powyżej ~3 km ludzie potrzebują tlenu.'],
    n_pax: ['Ilu pasażerów zabiera samolot — bez pilotów.', 'Każdy pasażer to ok. 100 kg i miejsce w kabinie, więc samolot rośnie.'],
    m_cargo: ['Masa towaru wożonego oprócz pasażerów (bagaż dodatkowy, ładunek, chemikalia, sprzęt drona).', '100 kg ładunku więcej to zwykle 220–300 kg więcej masy startowej.'],
    n_crew: ['Ilu pilotów i członków załogi musi lecieć. Dron ma 0.', 'Więcej załogi = mniej miejsca i masy dla ładunku.'],
    m_pax: ['Ile liczymy na jedną osobę razem z bagażem.', 'Większa masa osoby = większa masa startowa.'],
    cruise_speed_kmh: ['Z jaką prędkością samolot leci na trasie.', 'Opór rośnie z kwadratem prędkości, a potrzebna moc — z sześcianem: +20 % prędkości to ok. +70 % mocy.'],
    v_stall_kmh: ['Najmniejsza prędkość, przy której samolot z wypuszczonymi klapami jeszcze leci. Poniżej skrzydło traci siłę nośną.', 'Wyższa dopuszczalna = mniejsze skrzydło, ale szybsze i dłuższe lądowanie.'],
    takeoff_run_m: ['Ile metrów pasa samolot przejedzie po ziemi, zanim oderwie koła.', 'Krótszy rozbieg wymaga mocniejszego silnika lub większego skrzydła.'],
    climb_rate_ms: ['Ile metrów na sekundę samolot wznosi się w pionie zaraz po starcie.', 'Szybsze wznoszenie wymaga większego zapasu mocy.'],
    engine_type: ['Czym samolot jest napędzany: śmigłem (silnik tłokowy, elektryczny, turbośmigłowy), silnikiem odrzutowym albo wcale (szybowiec).', 'Śmigło jest oszczędniejsze przy małych prędkościach, odrzut — przy dużych.'],
    engine_location: ['Gdzie jest silnik: w nosie, na skrzydłach, z tyłu kadłuba, czy chowany (motoszybowiec).', 'Silnik jest ciężki, więc jego położenie przesuwa środek ciężkości i miejsce skrzydła.'],
    sfc: ['Ile paliwa silnik spala na godzinę na każdy kilowat mocy (lub na każdy niuton ciągu).', 'Większe zużycie = więcej paliwa na trasę, cięższy samolot.'],
    prop_efficiency: ['Jaka część mocy silnika zamienia się na ciąg śmigła. Reszta „ucieka” w wir i ciepło.', 'Wyższa sprawność = lepsze osiągi przy tej samej mocy.'],
    flap_type: ['Jakie klapy są na tylnej krawędzi skrzydła. Wysuwane przy lądowaniu zwiększają siłę nośną, więc można lądować wolniej.', 'Lepsza klapa (szczelinowa, Fowlera) = mniejsze skrzydło przy tej samej prędkości lądowania, ale cięższy mechanizm.'],
    aileron_type: ['Jakie lotki są na końcach skrzydła. Lotki przechylają samolot na boki (jedna w górę, druga w dół).', 'Lotki różnicowe lub Frise zmniejszają niechciane „zarzucanie” nosem w zakręcie.'],
    slat_type: ['Czy na przedniej krawędzi skrzydła jest slot (szczelina), który pozwala lecieć na większym kącie bez przeciągnięcia.', 'Slot obniża prędkość przeciągnięcia, ale dodaje opór lub mechanizm.'],
    flap_span_ratio: ['Jaką część rozpiętości skrzydła zajmują klapy (reszta zostaje na lotki).', 'Dłuższe klapy = wolniejsze lądowanie, ale krótsze lotki i słabsze sterowanie przechyleniem.'],
    aileron_span_ratio: ['Jaką część rozpiętości skrzydła zajmują lotki.', 'Dłuższe lotki = szybsze przechylanie, ale mniej miejsca na klapy.'],
    cx0: ['Opór samolotu, który istnieje zawsze — nawet gdy skrzydło nie wytwarza siły nośnej (tarcie skóry, kształt kadłuba, podwozie, anteny).', 'Większy opór szkodliwy = niższa prędkość maksymalna i większe zużycie paliwa.'],
    oswald_e: ['Jak blisko ideału (e = 1) jest rozkład siły nośnej na skrzydle. Kadłub, gondole i kształt skrzydła go psują.', 'Wyższe e = mniejszy opór przy wolnym locie, wznoszeniu i zakrętach.'],
    cz_max_clean: ['Największa siła nośna, jaką da skrzydło bez wysuniętych klap, tuż przed przeciągnięciem.', 'Wyższa wartość = niższa prędkość przeciągnięcia bez klap.'],
    cz_max_lnd: ['Największa siła nośna skrzydła z wysuniętymi klapami do lądowania.', 'Wyższa wartość = można zrobić mniejsze skrzydło przy tej samej prędkości lądowania.']
  };
  for (const [k, [plain, more]] of Object.entries(PLAIN)) {
    const e = PARAMETER_ENCYCLOPEDIA[k];
    if (e) { e.plain = plain; e.more = more; }
  }

  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const keyFor = id => String(id || '').replace(/^wiz_basis_/, '').replace(/^wiz_/, '');
  const hintHtml = info => `<strong>Prosto mówiąc:</strong> ${esc(info.plain || info.short_desc)}`
    + (info.more ? `<span class="hint-more"><strong>Gdy zwiększysz:</strong> ${esc(info.more)}</span>` : '')
    + (info.typical_ranges ? `<span class="hint-range">📏 Typowo: ${esc(info.typical_ranges)}</span>` : '');
  window.BipolDidacticHintHtml = hintHtml;

  // Popover: najpierw prosty opis, potem pełna definicja
  const basePopover = window.showDidacticPopover;
  if (typeof basePopover === 'function') {
    window.showDidacticPopover = function (key, anchor) {
      basePopover(key, anchor);
      const info = PARAMETER_ENCYCLOPEDIA[key];
      const desc = document.getElementById('popDesc');
      if (!info || !desc) return;
      desc.innerHTML = `<strong>Prosto mówiąc:</strong> ${esc(info.plain || info.short_desc)}`
        + (info.full_definition ? `<br><span style="color:#475569;">${esc(info.full_definition)}</span>` : '');
      const f = document.getElementById('popFormula');
      if (f) f.textContent = info.formula && info.formula !== '—' ? `Wzór: ${info.formula}` : 'Wzór: —';
    };
  }

  const SCOPES = '#designForm, #projectWizardBackdrop, #bipol1Panel, #trendControls, #tab-trends';

  function decorate() {
    document.querySelectorAll(SCOPES).forEach(scope => {
      scope.querySelectorAll('input[id], select[id]').forEach(field => {
        if (field.type === 'hidden' || field.type === 'checkbox' || field.type === 'file') return;
        const key = keyFor(field.id);
        const info = PARAMETER_ENCYCLOPEDIA[key];
        if (!info) return;
        const group = field.closest('.input-group, .form-group, .wizard-field, label') || field.parentElement;
        if (!group || group.dataset.didacticDone === '1') return;
        group.dataset.didacticDone = '1';
        // Ikonka (i)
        let label = document.querySelector(`label[for="${CSS.escape(field.id)}"]`) || group.querySelector('label') || (group.tagName === 'LABEL' ? group : null);
        if (label && !label.querySelector('.info-circle-icon')) {
          const icon = document.createElement('span');
          icon.className = 'info-circle-icon';
          icon.dataset.param = key;
          icon.dataset.dyn = '1';
          icon.tabIndex = 0;
          icon.setAttribute('role', 'button');
          icon.setAttribute('aria-label', `Objaśnienie: ${info.title}`);
          icon.textContent = 'i';
          (label.querySelector('.label-text') || label).appendChild(icon);
        }
        // Objaśnienie pod polem
        let hint = group.querySelector('.param-didactic-hint');
        if (!hint) {
          hint = document.createElement('div');
          hint.className = 'param-didactic-hint';
          hint.dataset.hintFor = key;
          const anchor = field.parentElement && field.parentElement !== group && field.parentElement.closest('.input-group, .form-group, .wizard-field, label') === group ? field.parentElement : field;
          anchor.insertAdjacentElement('afterend', hint);
        }
        hint.innerHTML = hintHtml(info);
      });
    });
  }

  // Delegacja zdarzeń dla dynamicznie dodanych ikonek
  let hideTimer = null;
  const show = icon => { clearTimeout(hideTimer); window.showDidacticPopover?.(icon.dataset.param, icon); };
  const hide = () => { clearTimeout(hideTimer); hideTimer = setTimeout(() => { if (typeof scheduleHideDidacticPopover === 'function') scheduleHideDidacticPopover(); }, 60); };
  document.addEventListener('mouseover', e => { const i = e.target.closest?.('.info-circle-icon[data-dyn]'); if (i) show(i); });
  document.addEventListener('mouseout', e => { if (e.target.closest?.('.info-circle-icon[data-dyn]')) hide(); });
  document.addEventListener('focusin', e => { const i = e.target.closest?.('.info-circle-icon[data-dyn]'); if (i) show(i); });
  document.addEventListener('focusout', e => { if (e.target.closest?.('.info-circle-icon[data-dyn]')) hide(); });
  document.addEventListener('click', e => {
    const i = e.target.closest?.('.info-circle-icon[data-dyn]');
    if (i) { e.preventDefault(); e.stopPropagation(); show(i); }
  }, true);
  document.addEventListener('keydown', e => {
    const i = e.target.closest?.('.info-circle-icon[data-dyn]');
    if (i && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); show(i); }
  });

  // ---- Tryby pracy ----
  const MODE_KEY = 'bipol_work_mode';
  function setAppWorkMode(mode) {
    mode = mode === 'construction' ? 'construction' : 'didactic';
    document.body.classList.toggle('mode-didactic', mode === 'didactic');
    document.body.classList.toggle('mode-construction', mode === 'construction');
    document.querySelectorAll('[data-work-mode]').forEach(b => {
      const on = b.dataset.workMode === mode;
      b.classList.toggle('active', on);
      b.setAttribute('aria-pressed', String(on));
    });
    if (mode === 'construction' && typeof setSidebarMode === 'function') setSidebarMode('advanced');
    try { localStorage.setItem(MODE_KEY, mode); } catch (_) {}
  }
  window.setAppWorkMode = setAppWorkMode;

  function injectSwitch() {
    const bar = document.querySelector('.project-bar-right');
    if (!bar || bar.querySelector('.work-mode-switch')) return;
    const box = document.createElement('div');
    box.className = 'work-mode-switch';
    box.setAttribute('role', 'group');
    box.setAttribute('aria-label', 'Tryb pracy');
    box.innerHTML = '<button type="button" data-work-mode="didactic" title="Pod każdym polem widać proste objaśnienie: co to jest, co się stanie, gdy zmienisz wartość, i jakie wartości są typowe.">🎓 Tryb dydaktyczny</button>'
      + '<button type="button" data-work-mode="construction" title="Zwarty widok bez objaśnień pod polami i ze wszystkimi parametrami. Objaśnienia nadal są pod ikonką (i).">🛠️ Tryb konstrukcyjny</button>';
    box.addEventListener('click', e => { const b = e.target.closest('[data-work-mode]'); if (b) setAppWorkMode(b.dataset.workMode); });
    bar.insertBefore(box, bar.firstChild);
  }

  document.addEventListener('DOMContentLoaded', () => {
    injectSwitch();
    decorate();
    let saved = null;
    try { saved = localStorage.getItem(MODE_KEY); } catch (_) {}
    setAppWorkMode(saved || 'didactic');
    // Pola dodawane później (kreator, panele ładowane dynamicznie)
    let pending = null;
    new MutationObserver(() => { clearTimeout(pending); pending = setTimeout(decorate, 120); })
      .observe(document.body, { childList: true, subtree: true });
  });
})();
