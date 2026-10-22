"""
Moduł oficjalnych tematów projektowych BIPOL I (MEiL PW - ZSiS)
Zawiera wszystkie 110 tematów z listy wydziałowej BIPOL1_samoloty.pdf
wraz z przypisanymi kategoriami, sugerowanymi parametrami taktyczno-technicznymi.
"""
import re
from pathlib import Path

OFFICIAL_CATEGORIES = {
    "motoszybowce": "Motoszybowce (rozpiętość 13.5m, 15m, >20m)",
    "ultralight": "Samoloty ultralekkie (ULM / LSA)",
    "odrzutowe_rekreacyjne": "Odrzutowe samoloty rekreacyjne",
    "wyscigowe_akro": "Samoloty wyścigowe i akrobacyjne (Red Bull, F1)",
    "szkolne": "Samoloty klubowe, szkolne i szkolno-treningowe",
    "turystyczne": "Samoloty turystyczne i STOL",
    "medyczne": "Samoloty sanitarne i medyczne",
    "dyspozycyjne": "Samoloty dyspozycyjne (Business / Commuter)",
    "transportowe": "Samoloty transportowe i ładunkowe STOL",
    "pasazerskie": "Samoloty pasażerskie (40, 70, 100, 200 miejsc)",
    "rolnicze_pozarnicze": "Samoloty rolnicze i pożarnicze",
    "lodzie_latajace": "Wodnosamoloty i łodzie latające",
    "szturmowe": "Samoloty szturmowe i specjalne"
}

# Załaduj i sparsuj 110 tematów
def build_official_topics():
    topics = []
    try:
        with (Path(__file__).resolve().parent.parent / "bipol_topics_list.txt").open(encoding="utf-8") as f:
            content = f.read()
        items = re.findall(r'(\d+)\s*\n([^\n\d][^\n]+)', content)
        for num_str, title in items:
            num = int(num_str)
            t_clean = title.strip().replace('  ', ' ')
            
            # Kategoryzacja i parametry domyślne na podstawie tekstu tematu
            t_lower = t_clean.lower()
            
            # Domyślne wartości
            cat = "turystyczne"
            ac_type = "piston_ga"
            engine_type = "prop"
            engine_loc = "nose"
            n_pax = 1
            m_cargo = 0.0
            range_km = 800.0
            span_limit = None
            altitude_m = 2500.0
            speed_kmh = 200.0
            climb_ms = 4.5
            wing_config = "low"
            seats_config = "side"
            
            # 1. Motoszybowce (tematy 1-14)
            if 1 <= num <= 14:
                cat = "motoszybowce"
                ac_type = "motoglider"
                engine_type = "prop"
                n_pax = 0 if "jednomiejscowy" in t_lower else 1
                range_km = 600.0
                altitude_m = 2000.0
                speed_kmh = 140.0
                climb_ms = 3.0
                wing_config = "mid"
                if "13,5m" in t_lower or "13.5m" in t_lower:
                    span_limit = 13.5
                elif "15m" in t_lower:
                    span_limit = 15.0
                elif "20m" in t_lower:
                    span_limit = 21.0
                else:
                    span_limit = 17.0
                    
                if "pchaj" in t_lower:
                    engine_loc = "rear"
                elif "chowany" in t_lower:
                    engine_loc = "retractable"
                else:
                    engine_loc = "nose"
                    
                if "tandem" in t_lower:
                    seats_config = "tandem"
                    
            # 2. Samoloty ultralekkie ULM (tematy 15-19)
            elif 15 <= num <= 19:
                cat = "ultralight"
                ac_type = "piston_ga"
                n_pax = 0 if "jednomiejscowy" in t_lower else 1
                range_km = 550.0
                speed_kmh = 160.0
                climb_ms = 4.0
                span_limit = 9.0
                wing_config = "high" if "górnopłat" in t_lower or "grnopat" in t_lower else "low"
                seats_config = "tandem" if "tandem" in t_lower else "side"
                
            # 3. Odrzutowe rekreacyjne (20-22, 103-104)
            elif (20 <= num <= 22) or (103 <= num <= 104):
                cat = "odrzutowe_rekreacyjne"
                ac_type = "jet_business"
                engine_type = "jet"
                engine_loc = "rear"
                n_pax = 0 if "jednomiejscowy" in t_lower else 1
                range_km = 1200.0
                speed_kmh = 450.0
                altitude_m = 6000.0
                climb_ms = 12.0
                seats_config = "tandem" if "tandem" in t_lower else "side"
                
            # 4. Wyścigowe i akro (23-29)
            elif 23 <= num <= 29:
                cat = "wyscigowe_akro"
                ac_type = "piston_ga"
                n_pax = 0 if "jednomiejscowy" in t_lower else 1
                range_km = 700.0
                speed_kmh = 380.0 if "wycig" in t_lower or "wyścig" in t_lower else 280.0
                climb_ms = 14.0
                
            # 5. Szkolne i szkolno-treningowe (30-38)
            elif 30 <= num <= 38:
                cat = "szkolne"
                n_pax = 5 if "6" in t_lower else 1
                range_km = 750.0
                if "odrzutowy" in t_lower:
                    ac_type = "jet_business"
                    engine_type = "jet"
                    engine_loc = "rear"
                    speed_kmh = 550.0
                    altitude_m = 7000.0
                    climb_ms = 16.0
                else:
                    ac_type = "piston_ga"
                    engine_type = "prop"
                    speed_kmh = 210.0
                    climb_ms = 5.0
                seats_config = "tandem" if "tandem" in t_lower else "side"
                
            # 6. Turystyczne i STOL (39-42)
            elif 39 <= num <= 42:
                cat = "turystyczne"
                ac_type = "piston_ga"
                n_pax = 3 if "cztero" in t_lower or "4" in t_lower else 1
                range_km = 1600.0 if "dalekiej" in t_lower else 900.0
                speed_kmh = 240.0
                climb_ms = 4.8
                wing_config = "high" if "stol" in t_lower else "low"
                
            # 7. Medyczne (43-44)
            elif 43 <= num <= 44:
                cat = "medyczne"
                ac_type = "turboprop_regional" if "dwusilnikowy" in t_lower else "piston_ga"
                engine_type = "prop"
                engine_loc = "wing" if "dwusilnikowy" in t_lower else "nose"
                n_pax = 2 # Lekarz + 1 chory
                m_cargo = 100.0 # Sprzęt medyczny
                range_km = 1200.0
                speed_kmh = 280.0
                climb_ms = 6.0
                wing_config = "high"
                
            # 8. Dyspozycyjne (45-65)
            elif 45 <= num <= 65:
                cat = "dyspozycyjne"
                # Liczba miejsc
                m_pax_match = re.search(r'(\d+)\s*s?miejscowy', t_lower)
                pax_cnt = int(m_pax_match.group(1)) - 1 if m_pax_match else 5
                n_pax = max(1, pax_cnt)
                
                # Zasięg
                r_match = re.search(r'(\d+)\s*km', t_lower)
                range_km = float(r_match.group(1)) if r_match else 1200.0
                
                if "odrzutowy" in t_lower:
                    ac_type = "jet_business"
                    engine_type = "jet"
                    engine_loc = "rear"
                    speed_kmh = 700.0
                    altitude_m = 11000.0
                    climb_ms = 12.0
                elif "turbo" in t_lower:
                    ac_type = "turboprop_regional"
                    engine_type = "prop"
                    engine_loc = "wing"
                    speed_kmh = 520.0
                    altitude_m = 7000.0
                    climb_ms = 8.5
                else:
                    ac_type = "piston_ga"
                    engine_type = "prop"
                    engine_loc = "wing" if "dwusilnikowy" in t_lower else "nose"
                    speed_kmh = 320.0
                    altitude_m = 3500.0
                    climb_ms = 6.5
                    
            # 9. Transportowe STOL (66-74)
            elif 66 <= num <= 74:
                cat = "transportowe"
                ac_type = "turboprop_regional"
                engine_type = "prop"
                engine_loc = "wing"
                n_pax = 0
                cargo_m = re.search(r'(\d+)\s*kg', t_lower)
                m_cargo = float(cargo_m.group(1)) if cargo_m else 2500.0
                range_km = 1800.0
                speed_kmh = 420.0
                altitude_m = 5000.0
                climb_ms = 6.0
                wing_config = "high"
                
            # 10. Pasażerskie (75-85, 105-108)
            elif (75 <= num <= 85) or (105 <= num <= 108):
                cat = "pasazerskie"
                pax_cnt_m = re.search(r'(\d+)\s*miejscowy', t_lower)
                pax_tot = int(pax_cnt_m.group(1)) if pax_cnt_m else 40
                n_pax = pax_tot
                range_km = 2200.0
                if "odrzutowy" in t_lower:
                    ac_type = "jet_transport"
                    engine_type = "jet"
                    engine_loc = "wing"
                    speed_kmh = 820.0
                    altitude_m = 10500.0
                    climb_ms = 11.0
                else:
                    ac_type = "turboprop_regional"
                    engine_type = "prop"
                    engine_loc = "wing"
                    speed_kmh = 500.0
                    altitude_m = 6500.0
                    climb_ms = 7.0
                wing_config = "high" if "górnopłat" in t_lower or "grnopat" in t_lower else "low"
                
            # 11. Rolnicze i pożarnicze (86-94, 109-110)
            elif (86 <= num <= 94) or (109 <= num <= 110):
                cat = "rolnicze_pozarnicze"
                ac_type = "turboprop_regional"
                engine_type = "prop"
                n_pax = 0
                cargo_m = re.search(r'(\d+)\s*kg', t_lower)
                m_cargo = float(cargo_m.group(1)) if cargo_m else 1500.0
                range_km = 800.0
                speed_kmh = 240.0
                climb_ms = 5.5
                wing_config = "low" if "rolniczy" in t_lower else "high"
                
            # 12. Łodzie latające (95-98)
            elif 95 <= num <= 98:
                cat = "lodzie_latajace"
                ac_type = "turboprop_regional"
                engine_type = "prop"
                engine_loc = "wing"
                n_pax = 3 if "cztero" in t_lower else 0
                cargo_m = re.search(r'(\d+)\s*kg', t_lower)
                m_cargo = float(cargo_m.group(1)) if cargo_m else 1000.0
                range_km = 1200.0
                speed_kmh = 260.0
                wing_config = "high"
                
            # 13. Szturmowe (99-102)
            elif 99 <= num <= 102:
                cat = "szturmowe"
                n_pax = 0 if "jednomiejscowy" in t_lower else 1
                m_cargo = 1500.0 # Uzbrojenie
                range_km = 1400.0
                if "odrzutowy" in t_lower:
                    ac_type = "jet_business"
                    engine_type = "jet"
                    engine_loc = "rear"
                    speed_kmh = 650.0
                    climb_ms = 18.0
                else:
                    ac_type = "turboprop_regional"
                    engine_type = "prop"
                    engine_loc = "nose"
                    speed_kmh = 480.0
                    climb_ms = 14.0

            topics.append({
                "id": f"topic_{num}",
                "num": num,
                "title": f"Temat {num}: {t_clean}",
                "category": cat,
                "defaults": {
                    "aircraft_type": ac_type,
                    "engine_type": engine_type,
                    "engine_location": engine_loc,
                    "wing_config": wing_config,
                    "seats_config": seats_config,
                    "span_limit": span_limit,
                    "n_pax": n_pax,
                    "m_cargo": m_cargo,
                    "range_km": range_km,
                    "cruise_altitude_m": altitude_m,
                    "cruise_speed_kmh": speed_kmh,
                    "climb_rate_ms": climb_ms
                }
            })
    except Exception as e:
        print("Błąd wczytywania tematów:", e)
        
    return topics

ALL_TOPICS = build_official_topics()


def topic_parameters(topic):
    """Start each topic from its own class, never from the previous open aircraft."""
    from calculations.presets import AIRCRAFT_PRESETS
    d = topic['defaults']
    baseline = {'motoglider': 'motoglider_aos', 'piston_ga': 'ga_trainer',
                'jet_business': 'vlj_jet', 'jet_transport': 'vlj_jet',
                'turboprop_regional': 'regional_turboprop'}.get(d['aircraft_type'], 'ga_trainer')
    p = {**AIRCRAFT_PRESETS[baseline], **{k: v for k, v in d.items() if v is not None}}
    passengers = d['n_pax']
    p.update(name=topic['title'], topic_id=topic['num'], topic_origin='official',
             n_crew=2 if passengers > 19 else 1, m_pax=115.0, m_bag=0.0,
             wingspan_m=d.get('span_limit') or 0, wing_area_m2=0,
             wing_input_mode='span_aspect' if d.get('span_limit') else 'loading',
             payload_input_mode='seats', power_input_mode='sized', engine_power_kw=0,
             locked_params=['n_pax','range_km'] + (['wingspan_m'] if d.get('span_limit') else []))
    p['category'] = ('cs22_motoglider' if topic['category'] == 'motoszybowce' else
                     'easa_optout_ul' if topic['category'] == 'ultralight' else
                     'cs25_transport' if d['aircraft_type'] == 'jet_transport' or passengers > 19 else
                     'cs23_commuter' if passengers > 9 else 'cs23_level3' if passengers > 6 else
                     'cs23_level2' if passengers > 1 else 'cs23_level1')
    title = topic['title'].lower()
    if topic['category'] == 'motoszybowce':
        p.update(aspect_ratio=24.0 if d['span_limit'] > 20 else 18.0,
                 flap_type='flaperon', aileron_type='flaperon', slat_type='none',
                 v_stall_kmh=72.0, takeoff_run_m=220.0)
    elif 'stol' in title or 'rolnicz' in title:
        p.update(flap_type='junkers', slat_type='fixed_slot', v_stall_kmh=75.0, takeoff_run_m=180.0)
    elif d['aircraft_type'] in ('jet_transport','turboprop_regional'):
        p.update(flap_type='fowler', slat_type='slats_auto',
                 v_stall_kmh=185.0 if d['aircraft_type'] == 'jet_transport' else 140.0,
                 takeoff_run_m=1400.0 if d['aircraft_type'] == 'jet_transport' else 750.0)
    else:
        p.update(flap_type='single_slotted', aileron_type='differential', slat_type='none',
                 v_stall_kmh=90.0, takeoff_run_m=280.0)
    # Full obstacle distances are distinct working assumptions, not renamed ground rolls.
    p['takeoff_distance_m'] = {'motoglider': 500, 'jet_transport': 2200,
                             'jet_business': 1600, 'turboprop_regional': 1300}.get(d['aircraft_type'], 600)
    p['landing_distance_m'] = {'jet_transport': 1800, 'jet_business': 1200,
                             'turboprop_regional': 1100}.get(d['aircraft_type'], 600)
    return p


def validate_topic_geometry(params, geometry):
    if params.get('topic_origin') != 'official':
        return
    number = int(params.get('topic_id', 0))
    span = float(params.get('wingspan_m') or geometry['wing']['b'])
    if number in (7, 8) and span <= 20:
        raise ValueError('Wybrany temat wymaga rozpiętości większej niż 20 m. '
                         'Zmień niezależne założenia skrzydła albo wybierz własny temat.')
    prescribed = 13.5 if number in (1, 2, 3) else 15.0 if number in (4, 5, 6) else None
    if prescribed and abs(span - prescribed) > .005:
        raise ValueError(f'Wybrany temat wymaga rozpiętości {prescribed:g} m. '
                         'Zachowaj tę rozpiętość albo wybierz własny temat.')


for _topic in ALL_TOPICS:
    _topic['parameters'] = topic_parameters(_topic)
