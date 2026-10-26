"""Import 24 modern Polish gliders, motogliders and UAVs into the reference aircraft catalogue."""
import csv
import io
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from calculations import aircraft_store
from calculations.aircraft_db import validate_aircraft, AircraftValidationError, get_aircraft

RAW_CSV = """ID_Nowoczesne,Nazwa_modelu,Wariant_konfiguracji,Producent_Ośrodek,Rok,Klasa_FAI_Kategoria,Liczba_miejsc,Material_struktury,Uklad_platowca,Mechanizacja_skrzydla,Profil_skrzydla,Podwozie,Rozpietosc_b_m,Dlugosc_L_m,Wysokosc_H_m,Powierzchnia_S_m2,Wydluzenie_Lambda,Masa_wlasna_kg,Ladunek_uzyteczny_kg,MTOW_kg,Obciazenie_pow_min_kg_m2,Obciazenie_pow_max_kg_m2,Model_silnika,Typ_zabudowy_napedu,Moc_szczytowa_kW,Moc_ciagla_kW,Moc_szczytowa_KM,Obciazenie_mocy_kg_kW,Smiglo_typ_srednica,Zasobnik_energii_typ,Pojemnosc_energii_kWh_lub_L,Napiecie_V_Masa_baterii_kg,V_ne_kmh,V_przelotowa_kmh,V_min_przeciagniecia_kmh,V_przy_opadaniu_2ms_kmh,Wznoszenie_max_ms,Doskonalosc_max_E,V_optymalna_E_kmh,Opadanie_min_ms,V_opadania_min_kmh,Wspolczynniki_obciazen_g_Systemy_BRS
MOD-PL-01,SZD-56-3 Diana 3 FES,Klasa 18-metrowa FES,Diana Sailplanes / Avionic,2020,FAI 18 m (wyczynowy),1,Kompozyt weglowo-aramidowy-epoksydowy,Srednioplat wolnonosny,Klapy + lotki + hamulce aerodynamiczne,Boermans / zmodyfikowany laminarny,Jednotorowe chowane,18.00,7.15,1.35,9.80,33.06,280,320,600,28.57,61.22,LZ Design FES-M100 (bezszczotkowy synchroniczny),FES w nosie kadluba,22.0,17.0,29.9,27.27,2-lopatowe weglowe skladane na obrysie nosa (~1.0 m),Akumulatory Li-Po (2 pakiety FES),4.2 kWh,116 V / ok. 31 kg,280,145,66,185-225,2.30,54.0,115,0.48,80,+5.3 / -2.65 g (balast wodny)
MOD-PL-02,SZD-56-2 Diana 2 FES,Klasa 15-metrowa FES,Bogumil Beres / Avionic / Diana Sailplanes,2018,FAI 15 m (wyczynowy),1,Kompozyt weglowo-aramidowy-epoksydowy,Srednioplat wolnonosny,Klapy + lotki + hamulce aerodynamiczne,Boermans DU-series laminarny,Jednotorowe chowane,15.00,6.88,1.35,8.64,26.04,210,290,500,24.31,57.87,LZ Design FES-M100 (bezszczotkowy synchroniczny),FES w nosie kadluba,22.0,17.0,29.9,22.73,2-lopatowe weglowe skladane na obrysie nosa (~1.0 m),Akumulatory Li-Po (2 pakiety FES),4.2 kWh,116 V / ok. 31 kg,270,140,64,180-215,2.50,50.0,115,0.50,78,+5.3 / -2.65 g (balast wodny)
MOD-PL-03,GP 15 Jeta SE (5.2 kWh),Klasa 15 m - bateria standard,Grzegorz i Marcin Peszke / GP Gliders Krosno,2018,FAI 15 m (samostartujacy / sustainer),1,Kompozyt weglowy (laminaty pod kolor),Srednioplat wolnonosny,Klapy + lotki + hamulce aerodynamiczne,Peszke cienki profil laminarny,Jednotorowe chowane,15.00,6.46,1.224,7.78,28.92,220,305,525,28.28,67.48,Silnik elektryczny GP 30 kW,Chowany w kadlubie (pantograf),30.0,25.0,40.8,17.50,2-lopatowe pchajace aeroelastyczne,Akumulatory Li-Ion w skrzydlach,5.19 kWh,120 V / 31 kg,300,150,67,182-219,4.70,49.0,120,0.55,85,BRS w standardzie + amortyzowany fotel
MOD-PL-04,GP 15 Jeta SE (9.2 kWh),Klasa 15 m - bateria dalekiego zasiegu,Grzegorz i Marcin Peszke / GP Gliders Krosno,2018,FAI 15 m (samostartujacy),1,Kompozyt weglowy (laminaty pod kolor),Srednioplat wolnonosny,Klapy + lotki + hamulce aerodynamiczne,Peszke cienki profil laminarny,Jednotorowe chowane,15.00,6.46,1.224,7.78,28.92,241,284,525,30.98,67.48,Silnik elektryczny GP 30 kW,Chowany w kadlubie (pantograf),30.0,25.0,40.8,17.50,2-lopatowe pchajace aeroelastyczne,Akumulatory Li-Ion w skrzydlach (powiekszone),9.23 kWh,120 V / 52 kg,300,150,67,182-219,4.40,49.0,120,0.55,85,BRS w standardzie + opcja sys. gasniczego
MOD-PL-05,GP 14 Velo E / GP 14 SE,Klasa 13.5 m (Velocita),Grzegorz i Marcin Peszke / GP Gliders Krosno,2017,FAI 13.5 m World Class,1,Kompozyt weglowo-epoksydowy,Srednioplat wolnonosny,Klapy + lotki + hamulce aerodynamiczne,Peszke profil laminarny,Jednotorowe chowane,13.45,6.46,1.22,7.24,24.99,160,230,390,22.10,53.87,Silnik elektryczny GP 15 kW,Chowany w kadlubie (pantograf),15.0,12.0,20.4,26.00,2-lopatowe pchajace aeroelastyczne,Akumulatory Li-Ion w skrzydlach,4.00 kWh,120 V / ok. 26 kg,270,140,65,178-204,4.70,45.0,100,0.50,73,BRS + balast wodny w skrzydlach i kadlubie
MOD-PL-06,GP 11 Pulse E,Ultralekki wyczynowy,Peszke S.C. / GP Gliders Krosno,2015,Ultralekki (UL) / 13.5 m,1,Kompozyt weglowo-epoksydowy,Srednioplat wolnonosny,Klapy + lotki + hamulce,Peszke profil laminarny,Jednotorowe chowane,13.45,6.34,1.22,7.24,24.99,145,155,300,20.03,41.44,Silnik elektryczny GP RES/FES,Chowany w kadlubie (pantograf),15.0,12.0,20.4,20.00,2-lopatowe pchajace aeroelastyczne,Akumulatory Li-Ion,4.00 kWh,bd,240,130,62,170-195,3.50,42.0,95,0.53,72,System ratunkowy BRS
MOD-PL-07,GP 12 Flex E,Projekt ultralekki 13.5 m,Grzegorz Peszke / GP Gliders Krosno,2015,Ultralekki (UL) projekt,1,Kompozyt weglowo-epoksydowy,Srednioplat wolnonosny,Klapy + lotki,Peszke profil laminarny,Jednotorowe chowane,13.45,6.34,1.22,7.24,24.99,150,160,310,20.72,42.82,Silnik elektryczny GP 15 kW,Chowany w kadlubie (pantograf),15.0,12.0,20.4,20.67,2-lopatowe pchajace,Akumulatory Li-Ion,4.00 kWh,bd,240,130,63,bd,3.50,42.0,95,0.53,72,System ratunkowy BRS
MOD-PL-08,GP 10 Axis,Prototyp doswiadczalny,Grzegorz Peszke / Peszke S.C. Krosno,2010,Ultralekki doswiadczalny,1,Kompozyt weglowo-epoksydowy,Srednioplat wolnonosny,Lotki + hamulce,Peszke profil laminarny,Jednotorowe chowane,13.60,6.34,1.22,7.30,25.34,140,160,300,19.18,41.10,Silnik elektryczny GP,Chowany w kadlubie (pantograf),15.0,12.0,20.4,20.00,2-lopatowe pchajace,Akumulatory Li-Po / Li-Ion,bd,bd,240,130,62,bd,3.50,41.0,95,0.55,72,Prototyp linii rozwojowej GP
MOD-PL-09,AOS-H2 (PW-X10) - Zaloga 2-os.,Motoszybowiec wodorowy (MTOW),Politechnika Warszawska i Politechnika Rzeszowska,2022,Doswiadczalny CS-22 (wodorowy),2,Kompozyt hybrydowy (szklano-weglowy),Gornoplat wolnonosny,Lotki popychaczowe + hamulce plytowe,NN-18/17 zmodyfikowany,Jednotorowe ze stalym kolem,16.00,8.11,2.50,15.25,16.79,390,200,590,25.57,38.69,Silnik el. 30 kW + ogniwo paliwowe H2,Chowany w kadlubie za kabina,30.0,25.0,40.8,19.67,2-lopatowe z kompozytu weglowego,Zbiornik wodoru H2 + bateria buforowa,Hybryda H2 + Li-Po,bd,265,135,73,bd,1.70,34.0,92,0.75,78,+5.3 / -2.65 g (ladunek w kabinie 200 kg)
MOD-PL-10,AOS-H2 (PW-X10) - Lot Solo,Motoszybowiec wodorowy (1 pilot),Politechnika Warszawska i Politechnika Rzeszowska,2022,Doswiadczalny CS-22 (wodorowy),1,Kompozyt hybrydowy (szklano-weglowy),Gornoplat wolnonosny,Lotki popychaczowe + hamulce plytowe,NN-18/17 zmodyfikowany,Jednotorowe ze stalym kolem,16.00,8.11,2.50,15.25,16.79,390,100,490,25.57,32.13,Silnik el. 30 kW + ogniwo paliwowe H2,Chowany w kadlubie za kabina,30.0,25.0,40.8,16.33,2-lopatowe z kompozytu weglowego,Zbiornik wodoru H2 + bateria buforowa,Hybryda H2 + Li-Po,bd,265,135,67,bd,2.50,34.0,85,0.68,72,+5.3 / -2.65 g (konfiguracja 1-osobowa)
MOD-PL-11,AOS-71 (PW-10),Pierwszy polski motoszybowiec elektr.,PW + PRz + ZS Jezow + Stocznia Olecko,2012,Doswiadczalny / Szkolno-badawczy,2,Kompozyt hybrydowy jednodzwigarowy,Gornoplat wolnonosny (kabina obok siebie),Lotki popychaczowe + hamulce plytowe gorne,NN-18/17,Jednotorowe stale,16.40,7.70,2.50,15.80,17.02,470,180,650,29.75,41.14,Sineton A37K015 (3-fazowy synchroniczny),Chowany w kadlubie za kabina,30.0,25.0,40.8,21.67,2-lopatowe z kompozytu weglowego,Akumulatory litowo-polimerowe Kokam,ok. 8-10 kWh,bd,260,130,72,bd,2.50,31.0,90,0.80,78,Zasieg na silniku 100 km (calkowity 150 km)
MOD-PL-12,PW-5M Pegaz,Motoszybowiec klasy swiatowej,Politechnika Warszawska / PZL Swidnik,1998,FAI World Class (z napedem),1,Kompozyt szklano-epoksydowy,Srednioplat wolnonosny,Lotki + hamulce aerodynamiczne,NN-27 (rodzina PW),Jednotorowe polchowane,13.44,6.22,1.86,10.16,17.78,205,115,320,20.18,31.50,Solo 2101 (1-cyl. 2-suw spalinowy),Chowany w kadlubie za kabina,16.2,14.5,22.0,19.75,2-lopatowe pchajace na wysiegniku,Zbiornik paliwa benzyna/mieszanka,ok. 12 L,Nie dotyczy (spalinowy),220,110,62,bd,2.00,32.0,88,0.75,74,+5.3 / -2.65 g
MOD-PL-13,PW-5 Smyk (szybowiec bazowy),Szybowiec klasy swiatowej FAI,Politechnika Warszawska / PZL Swidnik /ZS Jezow,1993,FAI World Class (bezsilnikowy),1,Kompozyt szklano-epoksydowy,Srednioplat wolnonosny,Lotki + hamulce aerodynamiczne,NN-27,Jednotorowe stale z owiewka,13.44,6.22,1.86,10.16,17.78,190,110,300,18.70,29.53,Brak (szybowiec wzorcowy dla PW-5M),Brak,0.0,0.0,0.0,bd,Brak,Brak,0.0,Brak,220,115,60,155,0.00,33.0,90,0.64,73,+5.3 / -2.65 g
MOD-PL-14,PW-4 Pelikan,Motoszybowiec szkolno-badawczy,Roman Switkiewicz / PW / ZS Jezow,1995,TMG (Touring Motor Glider),2,Kompozyt szklano-epoksydowy,Gornoplat z belka ogonowa,Lotki + hamulce aerodynamiczne,NN-18/17,Jednotorowe / podwozie stale,16.20,8.00,2.40,18.74,14.00,450,220,670,24.01,35.75,Limbach L2000 EC1 (4-cyl. bokser),Smiglo pchajace stale za platem,59.6,55.0,80.0,11.24,2-lopatowe pchajace Hamilton (sredn. 1.55 m),Zbiornik paliwa,ok. 40 L,Instalacja 12 V,180,140,70,bd,2.80,19.4,89,1.25,82,Dobieg 450 m / zasieg 450 km
MOD-PL-15,MDM Moto-Fox Malgosia (SP-0053),Motoszybowiec doswiadczalny z MDM-1 Fox,Edward Marganski / ZRiPSL Bielsko-Biala,1996,Experimental (samolot slabosilnikowy / TMG),2,Kompozyt szklano- i weglowo-epoksydowy,Dolnoplat wolnonosny (z przesunietym platem),Klapy krokodylowe do ladowania + lotki,Profil akrobacyjny z MDM-1 Fox,Trojkolowe stale z kolkiem przednim (ze Sky Arrow),14.00,8.00,2.36,12.34,15.88,445,205,650,36.06,52.67,Rotax 912 UL (4-cyl. bokser 4-suw),Smiglo ciagnace stale w dziobie,58.0,55.0,79.0,11.21,2-lopatowe ciagnace stale,Zbiornik paliwa w skrzydlach/kadlubie,Zasieg do 1000 km,Przyrzady VFR/IFR VOR ILS,200,190,95,bd,4.50,20.0,110,1.30,100,Przebudowany w 2011-2012 na uklad kaczki Malgosia II
MOD-PL-16,J-6 Fregata,Seryjny motoszybowiec kompozytowy,Jaroslaw Janowski / J&AS Aerospace Lodz,1999,Ultralekki motoszybowiec wyczynowy,1,Kompozyt szklano-weglowo-epoksydowy,Gornoplat wolnonosny,Lotki + klapy/hamulce,Wortmann FX 67K 170/17,Stale + kolka podporowe na koncach skrzydel,12.55,5.65,1.45,9.135,17.24,220,140,360,24.08,39.41,Aerohonda BF 45 A (3-cyl. rzedowy chlodzony ciecza),Smiglo pchajace stale za kabina,37.5,35.0,52.0,9.60,2-lopatowe drewniane pchajace J6H (sredn. 1.25 m),Zbiornik paliwa,Zasieg 1100 km,6000 obr./min na wale,220,180,65,bd,6.00,24.0,100,1.20,80,+5.3 / -2.65 g (pulap 7000 m)
MOD-PL-17,BAE HERTI 1D (baza J-5/J-6),Bezzalogowy motoszybowiec rozpoznawczy,J&AS Aerospace Lodz / BAE Systems,2005,UAV / MALE na bazie motoszybowca J-6,0,Kompozyt szklano-weglowo-epoksydowy,Gornoplat wolnonosny,Pelna automatyka sterowania,Wortmann FX 67K 170/17,Stale trojkolowe,12.00,5.65,1.50,9.14,15.75,260,190,450,28.45,49.23,Rotax 914F Turbo (4-cyl. bokser),Smiglo pchajace,84.6,73.5,115.0,5.32,2-lopatowe pchajace,Zbiorniki paliwa dalekiego zasiegu,Lot autonomiczny >20 h,Systemy elektrooptyczne,230,185,68,bd,7.50,24.0,105,1.20,85,Baza platowcowa produkowana w Lodzi
MOD-PL-18,J-5A Marco (rozpietosc 11.3 m),Wersja rozwojowa SP-FAB,Jaroslaw Janowski / Marco-Electronic Lodz,1990,Ultralekki (FAI C-1a/0 do 300 kg),1,Kompozyt szklano-epoksydowy,Srednioplat wolnonosny z usterzeniem motylkowym V,Lotki + klapolotki,Wortmann laminarny,Stale dwukolowe lub jednotorowe,11.30,4.80,1.58,8.20,15.57,150,120,270,18.29,32.93,KFM 107ER / Rotax 447 (2-cyl. 2-suw),Smiglo pchajace stale nad belka ogonowa,29.4,25.0,40.0,9.18,2-lopatowe drewniane pchajace,Zbiornik paliwa,Zasieg 800 km,bd,180,140,60,bd,3.80,22.0,85,1.05,72,Oblatany 24.07.1990 r.
MOD-PL-19,Pietruszka Axel,Ultralekki szybowiec/motoszybowiec,Janusz Pietruszka / ZS Jezow / Opole,2002,Ultralekki szybowiec z napedem (UL),1,Kompozyt szklano-weglowo-epoksydowy,Srednioplat wolnonosny,Lotki + hamulce aerodynamiczne,Profil laminarny cienki,Jednotorowe chowane / stale,12.20,5.39,1.15,10.90,13.66,78,107,185,7.16,16.97,Silnik elektryczny lub spalinowy Solo,Pchajacy na wysiegniku lub FES,11.0,9.0,15.0,16.82,2-lopatowe skladane,Bateria Li-Ion lub zbiornik paliwa,Zasieg 150 km,Ultralekka struktura <80 kg,135,90,56,bd,2.00,26.0,70,0.80,62,Jedna z najlzejszych konstrukcji w klasie
MOD-PL-20,Pietruszka Gekon,Ultralekki motoszybowiec amatorski,Janusz Pietruszka,1998,Ultralekki motoszybowiec,1,Kompozyt szklano-epoksydowy,Srednioplat wolnonosny,Lotki + hamulce,Profil laminarny,Jednotorowe stale,11.80,5.50,1.35,9.80,14.21,130,100,230,13.27,23.47,Solo 210 (1-cyl. 2-suw),Smiglo pchajace na wiezyczce,10.3,9.0,14.0,22.33,2-lopatowe drewniane pchajace,Zbiornik paliwa,Zasieg 250 km,bd,140,90,52,bd,1.80,20.0,75,0.95,65,Konstrukcja kompozytowa
MOD-PL-21,SZD-9 Moto-Bocian M2000,Wersja patrolowa Lasow Panstwowych,Baza Uslug Lotniczych / Modernizacja SZD-9,1995,Motoszybowiec patrolowo-specjalny,2,Drewniana półskorupowa z nowa owiewka tloczona,Srednioplat wolnonosny,Lotki szczelinowe + hamulce plytowe,NACA 43018A / 43012A,Trojkolowe stale z kolkiem przednim (amortyzowane sznurem gumowym),18.00,7.90,2.40,20.00,16.20,480,200,680,24.00,34.00,Limbach L2000 E02 (2000 cm3 4-cyl. bokser),Smiglo ciagnace stale w dziobie,59.0,52.0,80.0,11.53,2-lopatowe drewniane stale,Zbiorniki paliwa na 9 h lotu,Zasieg 1100 km,Radiostacja UHF,180,125,65,bd,3.00,18.0,90,1.35,85,Doskonalosc 18 ze stojacym smiglem (czas lotu 9 h)
MOD-PL-22,Korol-Romanowski Moto-Puchatek,Konwersja szybowca dwumiejscowego,K. Korol i A. Romanowski,1993,Modyfikacja amatorska / eksperymentalna,2,Mieszana (kompozytowo-drewniana/metalowa),Gornoplat wolnonosny,Lotki + hamulce plytowe,FX 61-168 / FX 60-1261,Stale,16.67,7.37,2.00,18.00,15.44,430,200,630,23.89,35.00,Limbach L2000 / Volkswagen VW 1800,Smiglo ciagnace stale w dziobie,47.8,42.0,65.0,13.18,2-lopatowe ciagnace stale,Zbiornik paliwa,Zasieg 400 km,bd,150,110,65,bd,2.10,24.0,85,1.10,75,Dwumiejscowy motoszybowiec turystyczny
MOD-PL-23,Wieckowski Moto Mucha Standard (SP-2332),Zmotoryzowany SZD-22C z rozrusznikiem,Jan Wieckowski (nr fabr. 719),2001,Modyfikacja amatorska (Baza Baryt),1,Drewniana kryta plotnem + przod kadluba laminatowy,Gornoplat wolnonosny,Lotki + hamulce aerodynamiczne,Gö 549 / M-12,Klasyczne dwukolowe amortyzowane (wlasnego projektu),14.98,7.00,1.50,14.50,15.48,290,105,395,20.00,27.24,Volkswagen VW 1600 (4-cyl. bokser),Smiglo ciagnace stale na lozu z rur lotniczych,33.1,30.0,45.0,11.93,2-lopatowe drewniane ciagnace,Zbiornik paliwa,Zasieg 350 km,Rozrusznik elektryczny do restartu w locie,130,95,58,bd,2.00,23.0,78,0.90,68,Nalot ogolny 1460 h (inspirowany Kocjanem Bakiem)
MOD-PL-24,SZD-41AT Moto-Jantar,Wyczynowy szybowiec z chowanym napedem,Adam Kurbiel / SZD Bielsko-Biala,1980,FAI Standard Class (15 m),1,Kompozyt szklano-epoksydowy (laminat),Srednioplat wolnonosny z usterzeniem T,Lotki + hamulce aerodynamiczne,NN-8,Jednotorowe chowane,15.00,7.11,1.51,10.66,21.11,295,95,390,27.67,36.59,Solo 210 / KFM 107ER (dwusuw),Chowany w kadlubie na wysiegniku za kabina,14.7,12.5,20.0,26.53,2-lopatowe pchajace chowane,Zbiornik paliwa w kadlubie,Zasieg 300 km,bd,250,130,66,165,1.80,38.0,95,0.65,75,Pionierska polska konwersja szybowca laminatowego"""


def parse_val(v, typ=float):
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == 'bd' or s == '-':
        return None
    try:
        return typ(s)
    except (ValueError, TypeError):
        return None


def extract_prop_diameter(s):
    if not s:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*m', s)
    if m:
        val = float(m.group(1))
        if 0 < val < 20:
            return val
    return None


def extract_range(r):
    # Check text fields for range mention
    for text in (r.get('Pojemnosc_energii_kWh_lub_L', ''), r.get('Napiecie_V_Masa_baterii_kg', ''), r.get('Wspolczynniki_obciazen_g_Systemy_BRS', '')):
        m = re.search(r'[Zz]asieg\s+(?:na silniku\s+\d+\s+km\s+\(calkowity\s+)?(?:do\s+)?(\d+)\s*km', text)
        if m:
            return float(m.group(1))
    return None


def parse_aircraft_rows():
    reader = csv.DictReader(io.StringIO(RAW_CSV.strip()))
    records = []
    for r in reader:
        raw_id = r['ID_Nowoczesne'].strip().lower()
        model = r['Nazwa_modelu'].strip()
        mfr = r['Producent_Ośrodek'].strip()
        year = parse_val(r['Rok'], int)

        # Class & propulsion
        if raw_id == 'mod-pl-13':
            ac_type = 'glider'
            eng_type = 'none'
            n_eng = 0
            p_kw = None
        elif raw_id == 'mod-pl-17':
            ac_type = 'uav'
            eng_type = 'prop'
            n_eng = 1
            p_kw = parse_val(r['Moc_szczytowa_kW']) or parse_val(r['Moc_ciagla_kW'])
        else:
            ac_type = 'motoglider'
            eng_type = 'prop'
            n_eng = 1
            p_kw = parse_val(r['Moc_szczytowa_kW']) or parse_val(r['Moc_ciagla_kW'])

        m0 = parse_val(r['MTOW_kg'])
        me = parse_val(r['Masa_wlasna_kg'])
        b = parse_val(r['Rozpietosc_b_m'])
        s = parse_val(r['Powierzchnia_S_m2'])

        v_cr = parse_val(r['V_przelotowa_kmh'])
        v_st = parse_val(r['V_min_przeciagniecia_kmh'])
        v_max = parse_val(r['V_ne_kmh'])
        climb = parse_val(r['Wznoszenie_max_ms'])
        ld = parse_val(r['Doskonalosc_max_E'])
        w_z = parse_val(r['Opadanie_min_ms'])
        prop_d = extract_prop_diameter(r['Smiglo_typ_srednica'])
        rng = extract_range(r)

        # Family extraction
        family = model.split()[0]
        if family in ('GP', 'SZD-56-3', 'SZD-56-2', 'SZD-41AT', 'SZD-9', 'AOS-H2', 'AOS-71', 'PW-5M', 'PW-5', 'PW-4', 'J-6', 'J-5A'):
            parts = model.split()
            family = ' '.join(parts[:2]) if len(parts) > 1 and parts[0] == 'GP' else parts[0]

        source_loc = f"{r['Wariant_konfiguracji']} · {r['Typ_zabudowy_napedu']}"
        source_ref = (
            f"{mfr} ({year}). Klasa: {r['Klasa_FAI_Kategoria']}. Profil: {r['Profil_skrzydla']}. "
            f"Struktura: {r['Material_struktury']}. Układ: {r['Uklad_platowca']}. "
            f"Mechanizacja: {r['Mechanizacja_skrzydla']}. Podwozie: {r['Podwozie']}. "
            f"Silnik: {r['Model_silnika']} ({r['Moc_szczytowa_kW']} kW / {r['Moc_szczytowa_KM']} KM). "
            f"Śmigło: {r['Smiglo_typ_srednica']}. "
            f"Zasobnik: {r['Zasobnik_energii_typ']} ({r['Pojemnosc_energii_kWh_lub_L']}). "
            f"Osiągi: Doskonałość E={r['Doskonalosc_max_E']} przy {r['V_optymalna_E_kmh']} km/h, "
            f"opadanie min {r['Opadanie_min_ms']} m/s. {r['Wspolczynniki_obciazen_g_Systemy_BRS']}."
        )

        doc = {
            'id': raw_id,
            'source_id': 'motogliders',
            'model': model,
            'manufacturer': mfr,
            'family': family,
            'aircraft_type': ac_type,
            'year': year,
            'year_basis': 'certification',
            'source_locator': source_loc,
            'source_references': source_ref,
            'empty_mass_definition': 'OEW / operating empty weight',
            'm0': m0,
            'me': me,
            's': s,
            'b': b,
            'variable_sweep': False,
            'engine_type': eng_type,
            'n_engines': n_eng,
            'engine_model': r['Model_silnika'] if eng_type != 'none' else None,
            'p_kw': p_kw,
            't_kn': None,
            'prop_diameter_m': prop_d,
            'prop_type': r['Smiglo_typ_srednica'] if eng_type != 'none' else None,
            'v_cruise_kmh': v_cr,
            'v_max': v_max,
            'v_stall_kmh': v_st,
            'range_km': rng,
            'climb_rate_ms': climb,
            'ld_max': ld,
            'w_z_min_ms': w_z,
        }

        clean = validate_aircraft(doc, is_create=True)
        records.append(clean)
    return records


def import_to_database(db_path=None):
    db_file = Path(db_path or aircraft_store.database_path())
    print(f"Opening database: {db_file}")
    records = parse_aircraft_rows()
    print(f"Parsed and validated {len(records)} aircraft records.")

    inserted_count = 0
    updated_count = 0

    with aircraft_store.transaction(db_file) as con:
        for r in records:
            aid = r['id']
            # Check if exists
            row = con.execute("SELECT id FROM aircraft WHERE id = ?", (aid,)).fetchone()
            if row:
                # Update existing
                aircraft_store.update(con, aid, r)
                updated_count += 1
            else:
                aircraft_store.insert(con, r)
                inserted_count += 1

    print(f"Import complete! Inserted: {inserted_count}, Updated: {updated_count}.")


if __name__ == '__main__':
    import_to_database()
