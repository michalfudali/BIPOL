"""Module for parameter locking, dependency resolution and initial constraint suggestions.

Implements bidirectional physical triads for aircraft conceptual design:
1. Wing geometry triad: S * AR = b^2
2. Wing loading triad: W/S = (m0 * g) / S
3. Payload triad: m_payload = n_pax * m_pax_unit + m_cargo
4. Propulsion triad: P_avail = P_max * eta_prop >= P_req
5. Stall speed triad: V_s0 = sqrt(2 * m0 * g / (rho * S * Cz_max))
"""
import math
from calculations.atmosphere import G0, RHO0

LOCKABLE_PARAMETERS = {
    'wingspan_m': {'label': 'Rozpiętość skrzydła b', 'unit': 'm', 'stage': 'P3', 'triad': 'wing_geom'},
    'aspect_ratio': {'label': 'Wydłużenie skrzydła Λ (AR)', 'unit': '−', 'stage': 'P3', 'triad': 'wing_geom'},
    'wing_area_m2': {'label': 'Powierzchnia skrzydła S', 'unit': 'm²', 'stage': 'P3', 'triad': 'wing_geom'},
    'wing_loading_kg_m2': {'label': 'Obciążenie powierzchni m₀/S', 'unit': 'kg/m²', 'stage': 'P2', 'triad': 'wing_loading'},
    'm0': {'label': 'Maksymalna masa startowa MTOW', 'unit': 'kg', 'stage': 'P2', 'triad': 'mass'},
    'n_pax': {'label': 'Liczba pasażerów', 'unit': 'os.', 'stage': 'P1', 'triad': 'payload'},
    'n_crew': {'label': 'Liczba załogi (pilotów)', 'unit': 'os.', 'stage': 'P1', 'triad': 'payload'},
    'm_cargo': {'label': 'Ładunek cargo / wyposażenie', 'unit': 'kg', 'stage': 'P1', 'triad': 'payload'},
    'm_payload': {'label': 'Masa płatna łączna', 'unit': 'kg', 'stage': 'P1', 'triad': 'payload'},
    'engine_power_kw': {'label': 'Maksymalna moc silnika P_max', 'unit': 'kW', 'stage': 'P5', 'triad': 'propulsion'},
    'range_km': {'label': 'Maksymalny zasięg obliczeniowy R', 'unit': 'km', 'stage': 'P1', 'triad': 'mission'},
    'cruise_speed_kmh': {'label': 'Prędkość przelotowa V_cr', 'unit': 'km/h', 'stage': 'P1', 'triad': 'mission'},
    'v_stall_kmh': {'label': 'Prędkość przeciągnięcia Vs0', 'unit': 'km/h', 'stage': 'P1', 'triad': 'stall'},
    'wing_planform': {'label': 'Obrys skrzydła', 'unit': 'typ', 'stage': 'P3', 'triad': 'planform'},
}

WING_PLANFORMS = {
    'trapezoidal': {
        'id': 'trapezoidal',
        'name_pl': 'Trapezowy (zbieżny klasyczny)',
        'description': 'Optymalny kompromis aerodynamiczno-wytrzymałościowy. Zbieżność redukuje masę dźwigarów i moment gnący w nasadzie.',
        'stall_behavior': 'Początek przeciążenia w części środkowej skrzydła (η ~ 0.4–0.6), lotki przy końcówkach zachowują sterowność.'
    },
    'rectangular': {
        'id': 'rectangular',
        'name_pl': 'Prostokątny (stała cięciwa)',
        'description': 'Maksymalna prostota technologiczna (jednakowe żebra i poszycie wzdłuż całej rozpiętości). Wyższy opór indukowany niż w skrzydle trapezowym.',
        'stall_behavior': 'Najbezpieczniejszy charakter przeciągnięcia: oderwanie strug rozpoczyna się przy kadłubie (η = 0.0), lotki zachowują pełną skuteczność.'
    },
    'compound_trapezoid': {
        'id': 'compound_trapezoid',
        'name_pl': 'Prostokątno-trapezowy',
        'description': 'Centropłat prostokątny ułatwia montaż klap, podwozia i zbiorników; końcówki trapezowe redukują indukowany opór (układ Piper Cherokee/Archer, Cessna 172, Wilga).',
        'stall_behavior': 'Przeciążenie inicjowane w części przykadłubowej, łagodny spadek siły nośnej bez tendencji do gwałtownego zwalenia na skrzydło.'
    },
    'elliptical': {
        'id': 'elliptical',
        'name_pl': 'Eliptyczny (minimalny opór indukowany)',
        'description': 'Teoretycznie optymalny rozkład siły nośnej wg Prandtla (współczynnik e = 1.0). Bardzo wysoki koszt produkcji i trudna technologia wykonania żeber (układ Supermarine Spitfire).',
        'stall_behavior': 'Równomierny rozkład obciążenia (cz1 = 1.0) powoduje jednoczesne przeciągnięcie na całej rozpiętości – nagła utrata skuteczności lotek.'
    },
    'swept_trapezoidal': {
        'id': 'swept_trapezoidal',
        'name_pl': 'Skośny trapezowy',
        'description': 'Skos krawędzi natarcia przesuwa krytyczną liczbę Macha ku wyższym prędkościom. Stosowany w odrzutowcach dyspozycyjnych i komunikacyjnych.',
        'stall_behavior': 'Tendencja do spływu warstwy przyściennej ku końcówkom i wczesnego przeciągnięcia końcówek skrzydła (wymaga zwichrzenia lub grzebieni aerodynamicznych).'
    }
}


def get_initial_constraint_suggestions(category: str, aircraft_type: str) -> list[dict]:
    """Generates intelligent initial constraints and tactical-technical recommendations."""
    suggestions = []
    
    # 1. Stall speed constraint (CS-23 / CS-22 / CS-VLA)
    if aircraft_type in ('piston_ga', 'turboprop_regional'):
        if category in ('cs_vla', 'cs_lsa', 'easa_optout_ul'):
            suggestions.append({
                'id': 'sugg_vs0_vla',
                'param': 'v_stall_kmh',
                'title': 'Limit prędkości przeciągnięcia CS-VLA / LSA (Vs0 ≤ 45 kt)',
                'value': 83.0,
                'unit': 'km/h',
                'description': 'Przepis CS-VLA / CS-LSA wymaga, aby prędkość przeciągnięcia w konfiguracji do lądowania nie przekraczała 45 węzłów (83 km/h).',
                'standard': 'EASA CS-VLA.49 / CS-LSA',
                'icon': '🛑'
            })
        else:
            suggestions.append({
                'id': 'sugg_vs0_cs23',
                'param': 'v_stall_kmh',
                'title': 'Limit prędkości lądowania CS-23 (Vs0 ≤ 61 kt)',
                'value': 113.0,
                'unit': 'km/h',
                'description': 'Dla jednosilnikowych samolotów CS-23 prędkość przeciągnięcia z klapami nie może przekraczać 61 węzłów (113 km/h).',
                'standard': 'EASA CS-23.2110',
                'icon': '🛑'
            })
    elif aircraft_type in ('glider', 'motoglider'):
        suggestions.append({
            'id': 'sugg_vs0_cs22',
            'param': 'v_stall_kmh',
            'title': 'Prędkość przeciągnięcia lądowania CS-22 (Vs ≤ 75 km/h)',
            'value': 75.0,
            'unit': 'km/h',
            'description': 'Bezpieczne lądowanie w terenie przygodnym szybowca/motoszybowca wymaga niskiej prędkości przyziemienia.',
            'standard': 'EASA CS-22.49',
            'icon': '🛑'
        })

    # 2. Wingspan constraints (Hangar / FAI classes)
    if aircraft_type in ('glider', 'motoglider'):
        suggestions.append({
            'id': 'sugg_span_fai15',
            'param': 'wingspan_m',
            'title': 'Rozpiętość klasy Standard / 15-metrowej FAI (b = 15.0 m)',
            'value': 15.0,
            'unit': 'm',
            'description': 'Klasa wyczynowa FAI i klubowa (np. PW-5 Smyk, SZD-55 Promyk).',
            'standard': 'FAI Sporting Code Section 3',
            'icon': '📏'
        })
        suggestions.append({
            'id': 'sugg_span_fai18',
            'param': 'wingspan_m',
            'title': 'Rozpiętość klasy 18-metrowej FAI / TMG (b = 18.0 m)',
            'value': 18.0,
            'unit': 'm',
            'description': 'Optymalna doskonałość motoszybowców turystycznych (np. Pipistrel Sinus, Stemme S10).',
            'standard': 'EASA CS-22 Subpart B',
            'icon': '📏'
        })
    elif aircraft_type == 'piston_ga':
        suggestions.append({
            'id': 'sugg_span_hangar',
            'param': 'wingspan_m',
            'title': 'Limit hangarowy GA (b ≤ 11.5 m)',
            'value': 10.8,
            'unit': 'm',
            'description': 'Typowa rozpiętość umożliwiająca bazowanie w standardowych boksach hangarowych aeroklubów (Cessna 172: 11.0 m, PA-28: 10.8 m).',
            'standard': 'Praktyka eksploatacyjna GA',
            'icon': '🏠'
        })

    # 3. Market powerplant constraints (Popular certified engines)
    if aircraft_type in ('piston_ga', 'motoglider'):
        suggestions.append({
            'id': 'sugg_engine_rotax912',
            'param': 'engine_power_kw',
            'title': 'Silnik rynkowy: Rotax 912 ULS (73.5 kW / 100 KM)',
            'value': 73.5,
            'unit': 'kW',
            'description': 'Najpopularniejszy 4-cylindrowy silnik tłokowy w klasie VLA/LSA i motoszybowców. Niskie zużycie paliwa (Mogas/Avgas).',
            'standard': 'Certyfikat EASA.E.121',
            'icon': '⚡'
        })
        suggestions.append({
            'id': 'sugg_engine_lycoming320',
            'param': 'engine_power_kw',
            'title': 'Silnik rynkowy: Lycoming O-320 (112.0 kW / 150 KM)',
            'value': 112.0,
            'unit': 'kW',
            'description': 'Klasyczny certyfikowany napęd samolotów 4-miejscowych (Cessna 172, Piper Cherokee).',
            'standard': 'FAA TCDS E-274',
            'icon': '⚡'
        })
    elif aircraft_type == 'turboprop_regional':
        suggestions.append({
            'id': 'sugg_engine_pt6',
            'param': 'engine_power_kw',
            'title': 'Silnik turbośmigłowy: P&WC PT6A-27 (507.0 kW / 680 KM)',
            'value': 507.0,
            'unit': 'kW',
            'description': 'Standard rynkowy dla samolotów dyspozycyjnych i pasażerskich klasy Commuter.',
            'standard': 'FAA TCDS E4EA',
            'icon': '⚡'
        })

    # 4. Standard passenger & crew masses
    suggestions.append({
        'id': 'sugg_pax_cs23',
        'param': 'm_pax',
        'title': 'Masa pasażera z bagażem podręcznym (85 kg/os.)',
        'value': 85.0,
        'unit': 'kg',
        'description': 'Zgodnie z przepisami CS-23: masa referencyjna 77 kg (osoba) + 8 kg bagaż podręczny.',
        'standard': 'EASA CS-23.25 / AMC-1',
        'icon': '👥'
    })

    # 5. Takeoff ground roll target
    suggestions.append({
        'id': 'sugg_sto_grass',
        'param': 'takeoff_run_m',
        'title': 'Rozbieg na trawiastym pasie aeroklubowym (Sto ≤ 280 m)',
        'value': 280.0,
        'unit': 'm',
        'description': 'Umożliwia operowanie z większości polskich lotnisk trawiastych i lądowisk gminnych.',
        'standard': 'Wytyczne ULC / BIPOL 1',
        'icon': '🛫'
    })

    return suggestions


def resolve_and_lock_parameters(params: dict, locked_keys: list = None) -> tuple[dict, dict, list]:
    """
    Enforces bidirectional physical triads and resolves derived parameters.
    
    Returns:
      (resolved_params, parameter_states, warnings)
    """
    p = dict(params)
    locked = set(locked_keys or p.get('locked_params', []))
    states = {}
    warnings = []

    m_pax_unit = float(p.get('m_pax', 85.0))
    n_pax = int(p.get('n_pax', 1))
    n_crew = int(p.get('n_crew', 1))

    # --- TRIADA 1: LICZBA MIEJSC I MASY PŁATNE ---
    # m_payload = n_pax * m_pax_unit + m_cargo
    if 'm_payload' in locked and 'n_pax' in locked:
        p_payload = float(p.get('m_payload', 100.0))
        computed_cargo = max(0.0, p_payload - n_pax * m_pax_unit)
        p['m_cargo'] = round(computed_cargo, 1)
        states['m_cargo'] = {
            'state': 'derived',
            'formula': 'm_cargo = m_payload − n_pax · 85 kg',
            'sources': ['m_payload', 'n_pax'],
            'value': p['m_cargo']
        }
        states['m_payload'] = {'state': 'locked', 'value': p_payload}
        states['n_pax'] = {'state': 'locked', 'value': n_pax}
    elif 'n_pax' in locked or 'm_cargo' in locked:
        m_cargo = float(p.get('m_cargo', 0.0))
        tot_payload = n_pax * m_pax_unit + m_cargo
        p['m_payload'] = round(tot_payload, 1)
        states['m_payload'] = {
            'state': 'derived',
            'formula': 'm_payload = n_pax · 85 kg + m_cargo',
            'sources': ['n_pax', 'm_cargo'],
            'value': p['m_payload']
        }
        if 'n_pax' in locked:
            states['n_pax'] = {'state': 'locked', 'value': n_pax}
        if 'm_cargo' in locked:
            states['m_cargo'] = {'state': 'locked', 'value': m_cargo}

    # --- TRIADA 2: ROZPIĘTOŚĆ b, WYDŁUŻENIE AR ORAZ POWIERZCHNIA S ---
    # b^2 = S * AR
    has_b = 'wingspan_m' in locked and float(p.get('wingspan_m', 0)) > 0.5
    has_ar = 'aspect_ratio' in locked and float(p.get('aspect_ratio', 0)) > 1.0
    has_s = 'wing_area_m2' in locked and float(p.get('wing_area_m2', 0)) > 1.0

    if has_b and has_ar:
        b_val = float(p['wingspan_m'])
        ar_val = float(p['aspect_ratio'])
        s_val = round((b_val ** 2) / ar_val, 2)
        p['wing_area_m2'] = s_val
        states['wing_area_m2'] = {
            'state': 'derived',
            'formula': 'S = b² / AR',
            'sources': ['wingspan_m', 'aspect_ratio'],
            'value': s_val
        }
        states['wingspan_m'] = {'state': 'locked', 'value': b_val}
        states['aspect_ratio'] = {'state': 'locked', 'value': ar_val}
    elif has_s and has_b:
        s_val = float(p['wing_area_m2'])
        b_val = float(p['wingspan_m'])
        ar_val = round((b_val ** 2) / s_val, 2)
        p['aspect_ratio'] = ar_val
        states['aspect_ratio'] = {
            'state': 'derived',
            'formula': 'AR = b² / S',
            'sources': ['wingspan_m', 'wing_area_m2'],
            'value': ar_val
        }
        states['wing_area_m2'] = {'state': 'locked', 'value': s_val}
        states['wingspan_m'] = {'state': 'locked', 'value': b_val}
    elif has_s and has_ar:
        s_val = float(p['wing_area_m2'])
        ar_val = float(p['aspect_ratio'])
        b_val = round(math.sqrt(s_val * ar_val), 2)
        p['wingspan_m'] = b_val
        states['wingspan_m'] = {
            'state': 'derived',
            'formula': 'b = √(S · AR)',
            'sources': ['wing_area_m2', 'aspect_ratio'],
            'value': b_val
        }
        states['wing_area_m2'] = {'state': 'locked', 'value': s_val}
        states['aspect_ratio'] = {'state': 'locked', 'value': ar_val}
    elif has_b:
        states['wingspan_m'] = {'state': 'locked', 'value': float(p['wingspan_m'])}
    elif has_ar:
        states['aspect_ratio'] = {'state': 'locked', 'value': float(p['aspect_ratio'])}
    elif has_s:
        states['wing_area_m2'] = {'state': 'locked', 'value': float(p['wing_area_m2'])}

    # --- TRIADA 3: MOC MAKSYMALNA SILNIKA ---
    if 'engine_power_kw' in locked:
        p_max = float(p['engine_power_kw'])
        states['engine_power_kw'] = {'state': 'locked', 'value': p_max}
        # In prop GA, locking P_max means available power is fixed:
        p['p_max_kw'] = p_max

    # --- ZASIĘG I PRĘDKOŚĆ ---
    if 'range_km' in locked:
        states['range_km'] = {'state': 'locked', 'value': float(p['range_km'])}
    if 'cruise_speed_kmh' in locked:
        states['cruise_speed_kmh'] = {'state': 'locked', 'value': float(p['cruise_speed_kmh'])}
    if 'v_stall_kmh' in locked:
        states['v_stall_kmh'] = {'state': 'locked', 'value': float(p['v_stall_kmh'])}

    # --- OBRYS SKRZYDŁA ---
    planform = p.get('wing_planform', 'trapezoidal')
    if planform not in WING_PLANFORMS:
        planform = 'trapezoidal'
    p['wing_planform'] = planform
    states['wing_planform'] = {'state': 'locked' if 'wing_planform' in locked else 'auto', 'value': planform}

    # Record locked parameters list in params
    p['locked_params'] = list(locked)
    
    return p, states, warnings
