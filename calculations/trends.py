"""Source-backed reference aircraft and descriptive regressions for BIPOL P1.

All masses use kg. Regressions are exploratory and never silently replace sizing.
Missing observations stay missing; each fit reports its own sample size.
"""
from collections import Counter
import math
import threading

from calculations import aircraft_store
from calculations.aircraft_store import CLASSES, DATA
from calculations.atmosphere import G0
from calculations.instructor import MIN_AIRCRAFT

# Provenance and licence of each data set, stored with the records.
SOURCES = aircraft_store.load_sources()


def derived(row):
    r = dict(row)
    r['year'] = r.get('year')
    mass, area, span = r['m0'], r.get('s'), r.get('b')
    r['ar'] = span * span / area if span and area else None
    r['empty_fraction'] = r['me'] / mass if r.get('me') else None
    r['wing_loading_kg_m2'] = mass / area if area else None
    r['wing_loading_n_m2'] = G0 * mass / area if area else None
    r['power_loading_kg_kw'] = mass / r['p_kw'] if r.get('p_kw') else None
    r['specific_power_kw_kg'] = r['p_kw'] / mass if r.get('p_kw') else None
    r['thrust_to_weight'] = r['t_kn'] * 1000 / (mass * G0) if r.get('t_kn') else None
    r['prop_diameter_m'] = r.get('prop_diameter_m')
    r['prop_type'] = r.get('prop_type')
    r['ld_max'] = r.get('ld_max')
    r['w_z_min_ms'] = r.get('w_z_min_ms')
    r['v_h'] = r.get('v_h')
    r['aileron_span_fraction'] = r.get('aileron_span_fraction')
    r['aileron_chord_ratio'] = r.get('aileron_chord_ratio')
    r['elevator_chord_ratio'] = r.get('elevator_chord_ratio')
    r['rudder_chord_ratio'] = r.get('rudder_chord_ratio')
    r['dihedral_deg'] = r.get('dihedral_deg')
    # A catalogue's unlabeled take-off number may be ground roll. Do not
    # silently promote it to obstacle distance (the lecture explicitly forbids it).
    r['takeoff_distance_m'] = r.get('takeoff_m') if r.get('takeoff_basis') in ('15m', '50ft', 'field_length') else None
    r['landing_distance_m'] = r.get('landing_m') if r.get('landing_basis') in ('15m', '50ft', 'field_length') else None
    r['climb_rate_ms'] = r.get('climb_rate_ms')
    r['quality_notes'] = []
    if r['empty_fraction'] is not None and not .15 < r['empty_fraction'] < .95:
        r['quality_notes'].append('Nietypowy udział OEW/MTOW — pominięto w regresji masowej.')
    if r['ar'] is not None and not 2 <= r['ar'] <= 60:
        r['quality_notes'].append('Nietypowe wydłużenie — sprawdź źródło geometrii.')
    return r


_catalog = {'revision': None, 'rows': ()}
_catalog_lock = threading.Lock()


def load_aircraft():
    """All reference aircraft with derived values, reloaded only when the database revision changes."""
    with _catalog_lock:
        revision, records = aircraft_store.read_catalog(_catalog['revision'])
        if records is not None:
            _catalog.update(revision=revision, rows=tuple(derived(r) for r in records))
        return _catalog['rows']


def _clear_catalog_cache():
    with _catalog_lock:
        _catalog.update(revision=None, rows=())


load_aircraft.cache_clear = _clear_catalog_cache


def sources_in_use(rows):
    """Sources with at least one record; an empty user source is neither listed nor cited."""
    used = {r['source_id'] for r in rows}
    return {key: meta for key, meta in SOURCES.items() if key in used}


def reference_catalog():
    rows = load_aircraft()
    return {'schema': 1, 'total': len(rows), 'classes': CLASSES, 'sources': sources_in_use(rows),
            'counts': dict(Counter(r['aircraft_type'] for r in rows)), 'aircraft': rows}


def select_references(params, m0):
    cls, engine = params.get('aircraft_type', 'piston_ga'), params.get('engine_type', 'prop')
    pool = [r for r in load_aircraft() if r['aircraft_type'] == cls and r['engine_type'] == engine]
    overrides = {r['id']: r for r in params.get('trend_observations', [])}
    pool = [{**r, **{k: v for k, v in overrides.get(r['id'], {}).items() if k != 'source'},
             'source_references': r['source_references'] + ('; Uzupełnienie autora: ' + overrides[r['id']]['source'] if r['id'] in overrides else '')}
            for r in pool]
    source = params.get('trend_source', 'all')
    if source != 'all':
        pool = [r for r in pool if r['source_id'] == source]
    engines = int(params.get('trend_engine_count', 0))
    if engines:
        pool = [r for r in pool if r['n_engines'] == engines]
    ymin, ymax = int(params.get('trend_year_min', 0)), int(params.get('trend_year_max', 0))
    if ymin or ymax:
        pool = [r for r in pool if r.get('year') is not None and (not ymin or r.get('year') >= ymin) and (not ymax or r.get('year') <= ymax)]
    ids = params.get('trend_aircraft_ids')
    if ids is not None:
        pool = [r for r in pool if r['id'] in ids]
    pool = sorted(pool, key=lambda r: (abs(math.log(r['m0'] / max(m0, 1))), r['id']))
    count = int(params.get('trend_count', 50))
    return pool[:count] if count else pool


def fit_regression(points, weights=None, power=False):
    """Weighted OLS with centered sums; reject constant x and insufficient data."""
    points = [(x, y, w) for (x, y), w in zip(points, weights or [1.] * len(points))
              if x is not None and y is not None and math.isfinite(x) and math.isfinite(y)
              and w > 0 and (not power or x > 0 and y > 0)]
    if len(points) < 3:
        return None
    tx = [math.log(x) if power else x for x, _, _ in points]
    ty = [math.log(y) if power else y for _, y, _ in points]
    ws = [w for _, _, w in points]
    total = sum(ws)
    xm, ym = sum(x*w for x, w in zip(tx, ws))/total, sum(y*w for y, w in zip(ty, ws))/total
    sxx = sum(w * (x-xm)**2 for x, w in zip(tx, ws))
    syy = sum(w * (y-ym)**2 for y, w in zip(ty, ws))
    if sxx <= 1e-16:
        return None
    slope = sum(w*(x-xm)*(y-ym) for x, y, w in zip(tx, ty, ws)) / sxx
    intercept = ym - slope*xm
    if power and not -700 < intercept < 700:
        return None  # Ill-conditioned near-constant mass cohort, not a usable law.
    residual = sum(w*(y-intercept-slope*x)**2 for x, y, w in zip(tx, ty, ws))
    return {'kind': 'power' if power else 'linear', 'n': len(points), 'slope': slope,
            'intercept': intercept, 'A': math.exp(intercept) if power else None,
            'C': slope if power else None, 'r2': 1-residual/syy if syy > 1e-16 else None,
            'rmse': math.sqrt(residual/total), 'x_min': min(x for x, _, _ in points),
            'x_max': max(x for x, _, _ in points), 'y_min': min(y for _, y, _ in points),
            'y_max': max(y for _, y, _ in points)}


def predict(fit, x):
    if not fit:
        return None
    try:
        value = math.exp(fit['intercept'] + fit['C']*math.log(x)) if fit['kind'] == 'power' else fit['intercept'] + fit['slope']*x
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


METRICS = {
    'm0': ('MTOW', 'kg'), 'empty_fraction': ('OEW / MTOW', '−'), 'ar': ('Wydłużenie AR', '−'),
    'wing_loading_kg_m2': ('Obciążenie powierzchni', 'kg/m²'),
    'prop_diameter_m': ('Średnica / rozpiętość śmigła', 'm'),
    'v_cruise_kmh': ('Prędkość przelotowa', 'km/h'), 'cruise_mach': ('Liczba Macha przelotu', 'Ma'),
    'range_km': ('Zasięg katalogowy', 'km'), 'takeoff_m': ('Długość startu katalogowa', 'm'),
    'takeoff_distance_m': ('Całkowita długość startu (wg źródła)', 'm'),
    'landing_distance_m': ('Całkowita długość lądowania (wg źródła)', 'm'),
    'climb_rate_ms': ('Prędkość wznoszenia', 'm/s'),
    'power_loading_kg_kw': ('Obciążenie mocy m₀/P', 'kg/kW'),
    'specific_power_kw_kg': ('Moc jednostkowa P/m₀', 'kW/kg'),
    'thrust_to_weight': ('Obciążenie ciągu T/W', '−'),
    'ld_max': ('Doskonałość maksymalna', '−'),
    'v_h': ('Cecha objętościowa usterzenia poziomego V_H', '−'),
    'aileron_span_fraction': ('Część rozpiętości objęta lotkami b_ail/(b/2)', '−'),
    'aileron_chord_ratio': ('Względna cięciwa lotek c_ail/c', '−'),
    'elevator_chord_ratio': ('Względna cięciwa steru wysokości c_e/c_H', '−'),
    'rudder_chord_ratio': ('Względna cięciwa steru kierunku c_r/c_V', '−'),
    'dihedral_deg': ('Kąt wzniosu skrzydła Γ', '°'),
}

GEOMETRY_METRICS_INFO = {
    'v_h': {
        'label': 'Cecha objętościowa usterzenia poziomego',
        'symbol': 'V_H',
        'formula_latex': r'\bar{V}_H = \frac{S_H \cdot l_H}{S \cdot c_a}',
        'unit': '−',
        'desc': 'Współczynnik objętościowy usterzenia poziomego decydujący o statycznej stateczności podłużnej i zapasie stateczności.',
        'typical_ranges': {
            'piston_ga': (0.50, 0.85, '0.50 – 0.85 (Raymer Tab. 6.4: ~0.70)'),
            'turboprop_regional': (0.75, 1.05, '0.75 – 1.05 (Roskam Tab. 2.1: ~0.90)'),
            'jet_business': (0.65, 1.00, '0.65 – 1.00 (Raymer Tab. 6.4: ~0.80)'),
            'jet_transport': (0.80, 1.15, '0.80 – 1.15 (Roskam Tab. 2.1: ~1.00)'),
            'glider': (0.45, 0.60, '0.45 – 0.60 (MEiL PW / Thomas: ~0.50)'),
            'motoglider': (0.50, 0.65, '0.50 – 0.65 (EASA CS-22: ~0.58)'),
            'uav': (0.45, 0.75, '0.45 – 0.75 (Gudmundsson: ~0.60)')
        }
    },
    'aileron_span_fraction': {
        'label': 'Część rozpiętości objęta lotkami',
        'symbol': 'b_{ail} / (b/2)',
        'formula_latex': r'\frac{b_{ail,1}}{b/2}=\frac{2b_{ail,1}}{b}',
        'unit': '−',
        'desc': 'Udział rozpiętości skrzydła zajęty przez lotkę; determinuje skuteczność przechylania pb/(2V).',
        'typical_ranges': {
            'piston_ga': (0.30, 0.55, '0.30 – 0.55 (typowo ~0.40; Raymer/Roskam)'),
            'turboprop_regional': (0.25, 0.40, '0.25 – 0.40 (typowo ~0.32)'),
            'jet_business': (0.24, 0.35, '0.24 – 0.35 (typowo ~0.30)'),
            'jet_transport': (0.20, 0.30, '0.20 – 0.30 (typowo ~0.24 + spoilery)'),
            'glider': (0.40, 0.55, '0.40 – 0.55 (typowo ~0.48)'),
            'motoglider': (0.40, 0.70, '0.40 – 0.70 (klapolotki do ~0.75)'),
            'uav': (0.35, 0.60, '0.35 – 0.60 (typowo ~0.45)')
        }
    },
    'aileron_chord_ratio': {
        'label': 'Względna cięciwa lotek',
        'symbol': 'c_{ail} / c',
        'formula_latex': r'\frac{c_{ail}}{c}',
        'unit': '−',
        'desc': 'Stosunek cięciwy lotki do lokalnej cięciwy skrzydła w rejonie krawędzi spływu.',
        'typical_ranges': {
            'piston_ga': (0.18, 0.28, '0.18 – 0.28 (Raymer rozdz. 12: ~0.22)'),
            'turboprop_regional': (0.18, 0.25, '0.18 – 0.25 (typowo ~0.21)'),
            'jet_business': (0.17, 0.24, '0.17 – 0.24 (typowo ~0.20)'),
            'jet_transport': (0.15, 0.22, '0.15 – 0.22 (typowo ~0.18)'),
            'glider': (0.15, 0.22, '0.15 – 0.22 (typowo ~0.17)'),
            'motoglider': (0.16, 0.24, '0.16 – 0.24 (typowo ~0.19)'),
            'uav': (0.18, 0.28, '0.18 – 0.28 (typowo ~0.23)')
        }
    },
    'elevator_chord_ratio': {
        'label': 'Względna cięciwa steru wysokości',
        'symbol': 'c_e / c_H',
        'formula_latex': r'\frac{c_e}{c_H}',
        'unit': '−',
        'desc': 'Stosunek cięciwy steru wysokości do cięciwy statecznika poziomego (lub 1.00 dla płytowego).',
        'typical_ranges': {
            'piston_ga': (0.28, 0.45, '0.28 – 0.45 (lub 1.00 stabilator; Raymer ~0.35)'),
            'turboprop_regional': (0.28, 0.38, '0.28 – 0.38 (typowo ~0.33)'),
            'jet_business': (0.26, 0.35, '0.26 – 0.35 (typowo ~0.30)'),
            'jet_transport': (0.25, 0.35, '0.25 – 0.35 (typowo ~0.28)'),
            'glider': (0.30, 0.45, '0.30 – 0.45 (typowo ~0.36)'),
            'motoglider': (0.30, 0.42, '0.30 – 0.42 (typowo ~0.36)'),
            'uav': (0.25, 0.40, '0.25 – 0.40 (typowo ~0.34)')
        }
    },
    'rudder_chord_ratio': {
        'label': 'Względna cięciwa steru kierunku',
        'symbol': 'c_r / c_V',
        'formula_latex': r'\frac{c_r}{c_V}',
        'unit': '−',
        'desc': 'Stosunek cięciwy steru kierunku do cięciwy statecznika pionowego.',
        'typical_ranges': {
            'piston_ga': (0.30, 0.48, '0.30 – 0.48 (Raymer rozdz. 12: ~0.38)'),
            'turboprop_regional': (0.30, 0.42, '0.30 – 0.42 (typowo ~0.35)'),
            'jet_business': (0.28, 0.38, '0.28 – 0.38 (typowo ~0.31)'),
            'jet_transport': (0.25, 0.35, '0.25 – 0.35 (typowo ~0.28)'),
            'glider': (0.38, 0.52, '0.38 – 0.52 (typowo ~0.45; adverse yaw)'),
            'motoglider': (0.36, 0.48, '0.36 – 0.48 (typowo ~0.42)'),
            'uav': (0.28, 0.42, '0.28 – 0.42 (typowo ~0.35)')
        }
    },
    'dihedral_deg': {
        'label': 'Kąt wzniosu skrzydła',
        'symbol': r'\Gamma',
        'formula_latex': r'\Gamma \; [^\circ]',
        'unit': '°',
        'desc': 'Kąt wzniosu geometrycznego skrzydła wpływający na poprzeczną stateczność statyczną.',
        'typical_ranges': {
            'piston_ga': (0.0, 7.0, 'Dolnopłat: 4°–7°; Górnopłat: 0°–2° (Roskam Tab. 3.1)'),
            'turboprop_regional': (0.0, 7.0, 'Dolnopłat: 4°–6°; Górnopłat: 0°–3°'),
            'jet_business': (2.0, 6.0, '2°–6° (skos skrzydeł obniża wymagany wznios)'),
            'jet_transport': (3.0, 7.0, '4°–7° (skrzydła skośne ze skręceniem ujemnym)'),
            'glider': (1.5, 4.5, '2°–4° (typowo ~3.3°; stateczność spiralna)'),
            'motoglider': (1.5, 4.0, '2°–3.5° (typowo ~3.0°)'),
            'uav': (0.0, 6.0, '0°–5° (zależnie od położenia skrzydła i usterzenia V)')
        }
    }
}


def compute_vector_stats(values):
    if not values:
        return None
    n = len(values)
    mean = sum(values) / n
    s_vals = sorted(values)
    med = s_vals[n // 2] if n % 2 != 0 else (s_vals[n // 2 - 1] + s_vals[n // 2]) / 2.0
    var = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
    std = math.sqrt(var)
    return {'n': n, 'mean': mean, 'median': med, 'std': std, 'min': min(values), 'max': max(values)}


def analyze_geometry_trends(params, geom_res=None):
    """Conduct comprehensive trend and compliance analysis for the 6 primary geometric parameters."""
    all_aircraft = load_aircraft()
    ac_type = params.get('aircraft_type', 'piston_ga')
    wing_cfg = params.get('wing_configuration', params.get('wing_config', 'low'))

    # Extract project values
    ctrl = geom_res.get('control_surfaces', {}) if geom_res else {}
    htail = geom_res.get('horizontal_tail', {}) if geom_res else {}
    wing = geom_res.get('wing', {}) if geom_res else {}
    ailerons = ctrl.get('ailerons', {})

    proj_vals = {
        'v_h': htail.get('vh_coeff', float(params.get('v_h', 0.70))),
        'aileron_span_fraction': ailerons.get('ba_over_b', float(params.get('aileron_span_ratio', 0.35))),
        'aileron_chord_ratio': ailerons.get('ca_over_c', float(params.get('aileron_chord_ratio', 0.20))),
        'elevator_chord_ratio': float(params.get('elevator_chord_ratio', params.get('ce_ch', 0.35))),
        'rudder_chord_ratio': float(params.get('rudder_chord_ratio', params.get('cr_cv', 0.35))),
        'dihedral_deg': wing.get('dihedral_deg', float(params.get('dihedral_deg', 3.0))),
    }

    metrics_analysis = []
    for key, info in GEOMETRY_METRICS_INFO.items():
        all_subset = [r for r in all_aircraft if r.get(key) is not None]
        class_subset = [r for r in all_subset if r.get('aircraft_type') == ac_type]

        all_vals = [r[key] for r in all_subset]
        class_vals = [r[key] for r in class_subset]

        all_stats = compute_vector_stats(all_vals)
        class_stats = compute_vector_stats(class_vals)

        proj_val = proj_vals.get(key)

        # Do not mix classes to conceal missing data in the selected class.
        reg_source = class_subset
        fit_m0 = fit_regression([(r['m0'], r[key]) for r in reg_source if r.get('m0')])
        fit_b = fit_regression([(r['b'], r[key]) for r in reg_source if r.get('b')])

        # Evaluation against typical literature range
        typ_min, typ_max, lit_note = info['typical_ranges'][ac_type]
        if key == 'dihedral_deg' and ac_type in ('piston_ga', 'turboprop_regional'):
            if wing_cfg in ('high', 'braced_high'):
                typ_min, typ_max = 0.0, 2.5
                lit_note = 'Górnopłat: 0°–2.5° (efekt wahadła kadłuba)'
            else:
                typ_min, typ_max = 3.5, 7.0
                lit_note = 'Dolnopłat: 3.5°–7.0° (wymagany zapas Cl_beta < 0)'

        diff_pct = ((proj_val - class_stats['mean']) / class_stats['mean'] * 100.0) if (proj_val is not None and class_stats and class_stats['mean'] != 0) else None

        is_in_range = (typ_min <= proj_val <= typ_max) if proj_val is not None else None

        if is_in_range:
            status = 'ok'
            verdict = f'W typowym zakresie literaturowym ({lit_note}); skuteczność wymaga osobnego sprawdzenia.'
        elif proj_val is not None and proj_val < typ_min:
            status = 'warning'
            verdict = f'Poniżej typowego zakresu ({lit_note}); zweryfikuj zapas stateczności lub skuteczność.'
        elif proj_val is not None and proj_val > typ_max:
            status = 'info' if key in ('aileron_span_fraction', 'aileron_chord_ratio') else 'warning'
            verdict = f'Powyżej typowego zakresu ({lit_note}); sprawdź skuteczność i opór.'
        else:
            status = 'unknown'
            verdict = 'Brak danych do weryfikacji.'

        # Samples for inspection
        samples = sorted(class_subset, key=lambda r: abs(r[key] - (proj_val if proj_val is not None else class_stats['mean'])))[:3]

        metrics_analysis.append({
            'key': key,
            'label': info['label'],
            'symbol': info['symbol'],
            'formula_latex': info['formula_latex'],
            'unit': info['unit'],
            'desc': info['desc'],
            'project_value': proj_val,
            'class_stats': class_stats,
            'all_stats': all_stats,
            'fit_m0': fit_m0,
            'fit_b': fit_b,
            'diff_pct': diff_pct,
            'typical_range_str': lit_note,
            'status': status,
            'verdict': verdict,
            'samples': [{'model': s['model'], 'm0': s.get('m0'), 'b': s.get('b'), 'val': s[key], 'source': s.get('source_locator', s.get('source_id'))} for s in samples]
        })

    # Cross-class comparison table
    cross_class_matrix = []
    for c_id, c_name in CLASSES.items():
        row_stats = {'class_id': c_id, 'class_name': c_name, 'is_active': (c_id == ac_type)}
        c_models = [r for r in all_aircraft if r.get('aircraft_type') == c_id]
        row_stats['n_models'] = len(c_models)
        for k in GEOMETRY_METRICS_INFO:
            k_vals = [r[k] for r in c_models if r.get(k) is not None]
            st = compute_vector_stats(k_vals)
            row_stats[k] = st
        cross_class_matrix.append(row_stats)

    return {
        'metrics': metrics_analysis,
        'cross_class_matrix': cross_class_matrix,
        'active_class': ac_type,
        'active_class_name': CLASSES.get(ac_type, ac_type),
        'total_geometry_models': len([r for r in all_aircraft if any(r.get(k) is not None for k in GEOMETRY_METRICS_INFO)]),
    }


def analyze_trends(params, m0, m_empty, geom_res=None):
    rows = select_references(params, m0)
    counts = Counter(r['family'] for r in rows)
    weighting = params.get('trend_weighting', 'family')
    def weights(subset):
        # Recount within each fit: missing data must not reduce a family's total weight.
        families = Counter(r['family'] for r in subset)
        return [1/families[r['family']] if weighting == 'family' else 1. for r in subset]
    valid_mass = [r for r in rows if r['empty_fraction'] is not None and .15 < r['empty_fraction'] < .95]
    mass_fit = fit_regression([(r['m0'], r['empty_fraction']) for r in valid_mass], weights(valid_mass), power=True)
    k_vs = 1.04 if params.get('variable_sweep', False) else 1.
    prediction = predict(mass_fit, m0)
    trend_value = prediction * k_vs if prediction is not None else None
    warnings = []
    if len(counts) < MIN_AIRCRAFT:
        warnings.append(f'Wymaganie prowadzącego: minimum 8 podobnych konstrukcji. Wybrano {len(counts)} rodzin; uzupełnij próbę.')
    if mass_fit and mass_fit['C'] >= 0:
        warnings.append('Trend OEW/MTOW nie jest malejący (C ≥ 0). Sprawdź dobór podobnych konstrukcji, definicje mas i źródła; nie odwracaj sztucznie regresji.')
    if len(rows) < 20:
        warnings.append(f'Wybrano {len(rows)} konstrukcji. Materiał BIPOL_1 zaleca co najmniej 20 podobnych samolotów; poszerz dobór lub uzupełnij źródła.')
    if rows and len(counts) < 20:
        warnings.append(f'Próba zawiera {len(counts)} rodzin i {len(rows)} wariantów. Warianty jednej rodziny nie są niezależnymi projektami.')
    if len(valid_mass) < 20:
        warnings.append(f'Regresja masowa ma {len(valid_mass)} kompletnych obserwacji; wynik jest poglądowy.')
    if mass_fit and not mass_fit['x_min'] <= m0 <= mass_fit['x_max']:
        warnings.append('Masa projektu leży poza zakresem próby — porównanie masowe jest ekstrapolacją.')
    if trend_value is not None and not 0 < trend_value < 1:
        warnings.append('Ekstrapolacja daje niefizyczny udział masy. Nie używaj jej do bilansu mas.')
    time_trends = []
    for key, (label, unit) in METRICS.items():
        subset = [r for r in rows if r.get('year') is not None and r.get(key) is not None]
        fit = fit_regression([(r['year'], r[key]) for r in subset], weights(subset))
        # Do not pretend to extrapolate a single generation of aircraft.
        if fit and fit['x_max'] - fit['x_min'] < 5:
            fit = None
        forecast_year = int(fit['x_max']) + 5 if fit else None
        forecast = predict(fit, forecast_year) if fit else None
        time_trends.append({'key': key, 'label': label, 'unit': unit, 'fit': fit,
            'available_n': len(subset), 'points': [{'x': r['year'], 'y': r[key], 'model': r['model']} for r in subset],
            'forecast_year': forecast_year, 'forecast': forecast,
            'forecast_physical': forecast is not None and forecast > 0 and (key != 'empty_fraction' or forecast < 1),
            'provisional': len(subset) < 20})
    if max((t['available_n'] for t in time_trends), default=0) < 20:
        warnings.append('Za mało udokumentowanych dat dla pełnej analizy czasowej. Dat certyfikacji nie zastępujemy domyślnym rokiem produkcji.')
    relationships = []
    x_keys = ['ar', 'wing_loading_kg_m2']
    if params.get('engine_type') == 'jet':
        x_keys.append('thrust_to_weight')
    elif params.get('engine_type', 'prop') == 'prop':
        x_keys.extend(['power_loading_kg_kw', 'specific_power_kw_kg'])
    x_labels = {'ar': ('Wydłużenie AR', '−'), 'wing_loading_kg_m2': ('Obciążenie powierzchni', 'kg/m²'),
                'thrust_to_weight': ('T / W', '−'), 'power_loading_kg_kw': ('Obciążenie mocy m₀ / P', 'kg/kW'),
                'specific_power_kw_kg': ('Moc jednostkowa P / m₀', 'kW/kg')}
    if any(r.get('prop_diameter_m') is not None for r in rows):
        x_keys.append('prop_diameter_m')
        x_labels['prop_diameter_m'] = ('Średnica śmigła d_prop', 'm')
    y_keys = ['v_cruise_kmh', 'cruise_mach', 'range_km', 'takeoff_distance_m', 'landing_distance_m', 'climb_rate_ms', 'ld_max',
              'v_h', 'aileron_span_fraction', 'aileron_chord_ratio', 'dihedral_deg']
    if any(r.get('prop_diameter_m') is not None for r in rows):
        y_keys.append('prop_diameter_m')
    for x_key in x_keys:
        for key in y_keys:
            if x_key == key:
                continue
            subset = [r for r in rows if r.get(x_key) is not None and r.get(key) is not None
                      and not (x_key == 'ar' and not 2 <= r['ar'] <= 60)]
            fit = fit_regression([(r[x_key], r[key]) for r in subset], weights(subset))
            relationships.append({'x_key': x_key, 'x_label': x_labels[x_key][0], 'x_unit': x_labels[x_key][1],
                'y_key': key, 'y_label': METRICS[key][0], 'y_unit': METRICS[key][1], 'fit': fit,
                'points': [{'x': r[x_key], 'y': r[key], 'model': r['model']} for r in subset]})
    averages = {}
    for key in ('empty_fraction', 'ar', 'wing_loading_kg_m2', 'prop_diameter_m', 'h_tail_area', 'v_tail_area',
                'v_h', 'aileron_span_fraction', 'aileron_chord_ratio', 'elevator_chord_ratio', 'rudder_chord_ratio', 'dihedral_deg'):
        subset = [r for r in rows if r.get(key) is not None]
        ws = weights(subset)
        averages[key] = {'mean': sum(r[key]*w for r,w in zip(subset,ws))/sum(ws) if subset else None, 'n': len(subset)}

    geometry_trends_analysis = analyze_geometry_trends(params, geom_res)

    # A fixed report structure: one mass plot, two plots against year and
    # three physical relationships. Missing observations remain explicit.
    def time_chart(key):
        t = next(t for t in time_trends if t['key'] == key)
        return {'mode': key, 'kind': 'time', 'label': f"{t['label']} w funkcji roku",
                'parameter': key, 'n': t['available_n'], 'fit': t['fit']}

    def relation_chart(x, y):
        r = next(r for r in relationships if r['x_key'] == x and r['y_key'] == y)
        return {'mode': f'{x}:{y}', 'kind': 'relation', 'label': f"{r['y_label']} a {r['x_label']}",
                'parameter': y, 'n': len(r['points']), 'fit': r['fit']}

    propulsion_key = 'thrust_to_weight' if params.get('engine_type') == 'jet' else 'power_loading_kg_kw'
    performance_key = ('cruise_mach' if sum(r.get('cruise_mach') is not None for r in rows) >
                       sum(r.get('v_cruise_kmh') is not None for r in rows) else 'v_cruise_kmh')
    time_options = [time_chart(key) for key in (performance_key, 'ar', 'wing_loading_kg_m2', 'v_h', 'dihedral_deg')]
    # Prefer complete observations instead of a blank speed/year plot when
    # speed and certification dates belong to different source records.
    time_options.sort(key=lambda c: not (c['n'] >= MIN_AIRCRAFT and c['fit']))
    report_charts = [{'mode': 'mass', 'kind': 'mass', 'label': 'Udział masy pustej w funkcji masy startowej',
                      'n': len(valid_mass), 'fit': mass_fit}, *time_options[:2]]
    if params.get('engine_type') == 'none':
        choices = [('ar','ld_max'), ('wing_loading_kg_m2','v_cruise_kmh'),
                   ('ar','v_h'), ('ar','aileron_chord_ratio'), ('wing_loading_kg_m2','dihedral_deg')]
    else:
        climb_chart = relation_chart(propulsion_key, 'climb_rate_ms')
        choices = [('ar','range_km'), (propulsion_key,'climb_rate_ms'),
                   ('wing_loading_kg_m2','takeoff_distance_m'), (propulsion_key,performance_key),
                   ('ar','ld_max'), ('wing_loading_kg_m2','v_h'), ('ar','aileron_chord_ratio'),
                   ('wing_loading_kg_m2','dihedral_deg'), ('wing_loading_kg_m2','landing_distance_m')]
        if climb_chart['n'] < MIN_AIRCRAFT:
            warnings.append('Wznoszenie a obciążenie napędu: uzupełnij katalogowe prędkości wznoszenia. Gdy ich brakuje, zestaw pięciu parametrów wykorzystuje inne jawnie opisane obserwacje.')
    candidates = [relation_chart(x, y) for x, y in choices]
    candidates.sort(key=lambda c: not (c['n'] >= MIN_AIRCRAFT and c['fit']))
    used_parameters = {c['parameter'] for c in report_charts if c['kind'] != 'mass'}
    for candidate in candidates:
        if candidate['parameter'] in used_parameters:
            continue
        report_charts.append(candidate)
        used_parameters.add(candidate['parameter'])
        if len(report_charts) == 6:
            break
    if any(c['n'] < MIN_AIRCRAFT for c in report_charts):
        warnings.append('Część sześciu wymaganych wykresów ma mniej niż 8 par danych. Uzupełnij dane źródłowe; nie zastępuj pełnego startu rozbiegiem ani wznoszenia opadaniem.')

    return {'database_total': len(load_aircraft()), 'selected_n': len(rows), 'families_n': len(counts),
        'class_label': CLASSES[params.get('aircraft_type', 'piston_ga')], 'weighting': weighting,
        'reg_A': mass_fit['A'] if mass_fit else None, 'reg_C': mass_fit['C'] if mass_fit else None,
        'mass_fit': mass_fit, 'k_vs': k_vs, 'we_wo_trend': trend_value, 'we_wo_actual': m_empty/m0 if m0 else None,
        'similar_aircraft': rows, 'averages': averages, 'warnings': warnings,
        'time_trends': time_trends, 'relationships': relationships, 'sources': sources_in_use(load_aircraft()),
        'report_charts': report_charts,
        'mass_trend_decreasing': mass_fit['C'] < 0 if mass_fit else None,
        'year_basis': 'Rok certyfikacji wariantu (nie rok produkcji)',
        'method': 'Ważona regresja log(OEW/MTOW) = log(A) + C·log(m₀ [kg]). Domyślnie rodziny mają równą wagę.',
        'limitations': 'OEW obejmuje wyposażenie operacyjne i nie jest tożsama z masą własną każdego projektu. Cechy geometryczne i sterów (V_H, lotki, stery, wznios) oparto na 82 certyfikowanych konstrukcjach (Raymer, Roskam, Corke, TCDS, MEiL PW). Rodziny są grupowane heurystycznie. Korelacja nie dowodzi przyczynowości.',
        'geometry_trends_analysis': geometry_trends_analysis}


SUGGESTION_TYPICAL_RANGES = {
    'ws': {
        'piston_ga': [60.0, 130.0],
        'turboprop_regional': [180.0, 360.0],
        'jet_business': [220.0, 500.0],
        'jet_transport': [400.0, 750.0],
        'glider': [28.0, 52.0],
        'motoglider': [30.0, 55.0],
        'uav': [15.0, 120.0],
    },
    'ar': {
        'piston_ga': [6.0, 9.5],
        'turboprop_regional': [8.5, 13.0],
        'jet_business': [6.5, 10.0],
        'jet_transport': [7.0, 11.5],
        'glider': [16.0, 32.0],
        'motoglider': [14.0, 28.0],
        'uav': [8.0, 20.0],
    },
    'me_m0': {
        'piston_ga': [0.55, 0.72],
        'turboprop_regional': [0.52, 0.68],
        'jet_business': [0.50, 0.68],
        'jet_transport': [0.44, 0.62],
        'glider': [0.45, 0.70],
        'motoglider': [0.52, 0.74],
        'uav': [0.45, 0.65],
    },
    'pw': {
        'piston_ga': [5.5, 10.5],
        'turboprop_regional': [3.8, 7.5],
        'motoglider': [8.0, 25.0],
    },
    'tw': {
        'jet_business': [0.25, 0.48],
        'jet_transport': [0.22, 0.40],
    },
}


def get_trend_suggestions(aircraft_type, m0=None, wing_configuration=None):
    """Compute empirical design parameter suggestions for a given aircraft class.

    Supports dynamic evaluation if m0 is provided, otherwise returns cohort median/mean.
    Gracefully handles small cohorts (N < 3 or low variance) and class-specific propulsion.
    """
    if aircraft_type not in CLASSES:
        raise ValueError(f"Unknown aircraft_type: '{aircraft_type}'")

    if m0 is not None:
        try:
            m0 = float(m0)
            if not math.isfinite(m0) or m0 <= 0:
                raise ValueError("m0 must be a positive finite number")
        except (TypeError, ValueError):
            raise ValueError("m0 must be a positive finite number")

    all_ac = load_aircraft()
    class_ac = [r for r in all_ac if r.get('aircraft_type') == aircraft_type]

    def _format_stats(st):
        if not st:
            return None
        return {
            'min': round(st['min'], 3),
            'max': round(st['max'], 3),
            'mean': round(st['mean'], 3),
            'median': round(st['median'], 3),
        }

    suggestions = {}

    # 1. Wing Loading (ws)
    pts_ws = [(r['m0'], r['wing_loading_kg_m2']) for r in class_ac if r.get('m0') and r.get('wing_loading_kg_m2')]
    st_ws = compute_vector_stats([y for _, y in pts_ws])
    fit_ws = fit_regression(pts_ws, power=True)
    if fit_ws and fit_ws.get('A') and fit_ws.get('C'):
        eq_ws = f"W/S = {fit_ws['A']:.4g} · m0^{fit_ws['C']:.4g}"
        eq_ws_tex = f"W/S = {fit_ws['A']:.4g} \\cdot m_0^{{{fit_ws['C']:.4g}}}"
        r2_ws = round(fit_ws['r2'], 4) if fit_ws.get('r2') is not None else None
        model_ws = 'power'
        if m0 is not None:
            pred_ws = predict(fit_ws, m0)
            val_ws = round(max(10.0, pred_ws), 2) if pred_ws else (round(st_ws['median'], 2) if st_ws else 80.0)
        else:
            val_ws = round(st_ws['median'], 2) if st_ws else 80.0
    else:
        model_ws = 'median'
        val_ws = round(st_ws['median'], 2) if st_ws else 80.0
        r2_ws = None
        eq_ws = f"W/S = {val_ws}"
        eq_ws_tex = f"W/S = {val_ws}"

    suggestions['ws'] = {
        'key': 'ws',
        'name': 'Wing Loading',
        'symbol': 'W/S',
        'unit': 'kg/m²',
        'suggested_value': val_ws,
        'model_type': model_ws,
        'equation': eq_ws,
        'equation_latex': eq_ws_tex,
        'r2': r2_ws,
        'n': len(pts_ws),
        'stats': _format_stats(st_ws),
        'typical_range': SUGGESTION_TYPICAL_RANGES['ws'].get(aircraft_type, [50.0, 150.0]),
    }

    # 2. Aspect Ratio (ar)
    pts_ar = [(r['m0'], r['ar']) for r in class_ac if r.get('m0') and r.get('ar') and 2 <= r['ar'] <= 60]
    st_ar = compute_vector_stats([y for _, y in pts_ar])
    fit_ar = fit_regression(pts_ar, power=False)
    if fit_ar and fit_ar.get('r2') is not None and fit_ar['r2'] >= 0.20:
        sign = '+' if fit_ar['intercept'] >= 0 else '-'
        eq_ar = f"AR = {fit_ar['slope']:.6g} · m0 {sign} {abs(fit_ar['intercept']):.4g}"
        eq_ar_tex = f"\\Lambda = {fit_ar['slope']:.6g} \\cdot m_0 {sign} {abs(fit_ar['intercept']):.4g}"
        r2_ar = round(fit_ar['r2'], 4)
        model_ar = 'linear'
        if m0 is not None:
            pred_ar = predict(fit_ar, m0)
            val_ar = round(min(50.0, max(3.0, pred_ar)), 2) if pred_ar else (round(st_ar['median'], 2) if st_ar else 7.5)
        else:
            val_ar = round(st_ar['median'], 2) if st_ar else 7.5
    else:
        model_ar = 'median'
        val_ar = round(st_ar['median'], 2) if st_ar else 7.5
        r2_ar = round(fit_ar['r2'], 4) if fit_ar and fit_ar.get('r2') is not None else None
        eq_ar = f"AR = {val_ar}"
        eq_ar_tex = f"\\Lambda = {val_ar}"

    suggestions['ar'] = {
        'key': 'ar',
        'name': 'Aspect Ratio',
        'symbol': 'AR',
        'unit': '−',
        'suggested_value': val_ar,
        'model_type': model_ar,
        'equation': eq_ar,
        'equation_latex': eq_ar_tex,
        'r2': r2_ar,
        'n': len(pts_ar),
        'stats': _format_stats(st_ar),
        'typical_range': SUGGESTION_TYPICAL_RANGES['ar'].get(aircraft_type, [6.0, 10.0]),
    }

    # 3. Empty Mass Fraction (me_m0)
    pts_me = [(r['m0'], r['empty_fraction']) for r in class_ac if r.get('m0') and r.get('empty_fraction') and 0.15 < r['empty_fraction'] < 0.95]
    st_me = compute_vector_stats([y for _, y in pts_me])
    fit_me = fit_regression(pts_me, power=True)
    if fit_me and fit_me.get('A') and fit_me.get('C'):
        eq_me = f"m_e/m0 = {fit_me['A']:.4g} · m0^{fit_me['C']:.4g}"
        eq_me_tex = f"m_e/m_0 = {fit_me['A']:.4g} \\cdot m_0^{{{fit_me['C']:.4g}}}"
        r2_me = round(fit_me['r2'], 4) if fit_me.get('r2') is not None else None
        model_me = 'power'
        if m0 is not None:
            pred_me = predict(fit_me, m0)
            val_me = round(min(0.90, max(0.20, pred_me)), 3) if pred_me else (round(st_me['median'], 3) if st_me else 0.60)
        else:
            val_me = round(st_me['median'], 3) if st_me else 0.60
    else:
        model_me = 'median'
        val_me = round(st_me['median'], 3) if st_me else 0.60
        r2_me = None
        eq_me = f"m_e/m0 = {val_me}"
        eq_me_tex = f"m_e/m_0 = {val_me}"

    suggestions['me_m0'] = {
        'key': 'me_m0',
        'name': 'Empty Mass Fraction',
        'symbol': 'm_e/m_0',
        'unit': '−',
        'suggested_value': val_me,
        'model_type': model_me,
        'equation': eq_me,
        'equation_latex': eq_me_tex,
        'r2': r2_me,
        'n': len(pts_me),
        'stats': _format_stats(st_me),
        'typical_range': SUGGESTION_TYPICAL_RANGES['me_m0'].get(aircraft_type, [0.50, 0.70]),
    }

    # 4. Power Loading (pw) - Prop and motoglider classes
    if aircraft_type in ('piston_ga', 'turboprop_regional', 'motoglider'):
        pts_pw = [(r['m0'], r['power_loading_kg_kw']) for r in class_ac if r.get('m0') and r.get('power_loading_kg_kw')]
        st_pw = compute_vector_stats([y for _, y in pts_pw])
        fit_pw = fit_regression(pts_pw, power=True)
        if fit_pw and fit_pw.get('A') and fit_pw.get('C'):
            eq_pw = f"m0/P = {fit_pw['A']:.4g} · m0^{fit_pw['C']:.4g}"
            eq_pw_tex = f"m_0/P = {fit_pw['A']:.4g} \\cdot m_0^{{{fit_pw['C']:.4g}}}"
            r2_pw = round(fit_pw['r2'], 4) if fit_pw.get('r2') is not None else None
            model_pw = 'power'
            if m0 is not None:
                pred_pw = predict(fit_pw, m0)
                val_pw = round(max(2.0, pred_pw), 2) if pred_pw else (round(st_pw['median'], 2) if st_pw else 7.5)
            else:
                val_pw = round(st_pw['median'], 2) if st_pw else 7.5
        else:
            model_pw = 'median'
            val_pw = round(st_pw['median'], 2) if st_pw else 7.5
            r2_pw = None
            eq_pw = f"m0/P = {val_pw}"
            eq_pw_tex = f"m_0/P = {val_pw}"

        suggestions['pw'] = {
            'key': 'pw',
            'name': 'Power Loading',
            'symbol': 'P/W',
            'unit': 'kg/kW',
            'suggested_value': val_pw,
            'model_type': model_pw,
            'equation': eq_pw,
            'equation_latex': eq_pw_tex,
            'r2': r2_pw,
            'n': len(pts_pw),
            'stats': _format_stats(st_pw),
            'typical_range': SUGGESTION_TYPICAL_RANGES['pw'].get(aircraft_type, [4.0, 12.0]),
        }
    else:
        suggestions['pw'] = {
            'key': 'pw',
            'name': 'Power Loading',
            'symbol': 'P/W',
            'unit': 'kg/kW',
            'suggested_value': None,
            'model_type': None,
            'equation': None,
            'equation_latex': None,
            'r2': None,
            'n': 0,
            'stats': None,
            'typical_range': None,
        }

    # 5. Thrust Loading (tw) - Jet classes
    if aircraft_type in ('jet_business', 'jet_transport'):
        pts_tw = [(r['m0'], r['thrust_to_weight']) for r in class_ac if r.get('m0') and r.get('thrust_to_weight')]
        st_tw = compute_vector_stats([y for _, y in pts_tw])
        fit_tw = fit_regression(pts_tw, power=False)
        if fit_tw:
            sign = '+' if fit_tw['intercept'] >= 0 else '-'
            eq_tw = f"T/W = {fit_tw['slope']:.7g} · m0 {sign} {abs(fit_tw['intercept']):.4g}"
            eq_tw_tex = f"T/W = {fit_tw['slope']:.7g} \\cdot m_0 {sign} {abs(fit_tw['intercept']):.4g}"
            r2_tw = round(fit_tw['r2'], 4) if fit_tw.get('r2') is not None else None
            model_tw = 'linear'
            if m0 is not None:
                pred_tw = predict(fit_tw, m0)
                val_tw = round(min(0.80, max(0.15, pred_tw)), 3) if pred_tw else (round(st_tw['median'], 3) if st_tw else 0.30)
            else:
                val_tw = round(st_tw['median'], 3) if st_tw else 0.30
        else:
            model_tw = 'median'
            val_tw = round(st_tw['median'], 3) if st_tw else 0.30
            r2_tw = None
            eq_tw = f"T/W = {val_tw}"
            eq_tw_tex = f"T/W = {val_tw}"

        suggestions['tw'] = {
            'key': 'tw',
            'name': 'Thrust Loading',
            'symbol': 'T/W',
            'unit': '−',
            'suggested_value': val_tw,
            'model_type': model_tw,
            'equation': eq_tw,
            'equation_latex': eq_tw_tex,
            'r2': r2_tw,
            'n': len(pts_tw),
            'stats': _format_stats(st_tw),
            'typical_range': SUGGESTION_TYPICAL_RANGES['tw'].get(aircraft_type, [0.20, 0.45]),
        }
    else:
        suggestions['tw'] = {
            'key': 'tw',
            'name': 'Thrust Loading',
            'symbol': 'T/W',
            'unit': '−',
            'suggested_value': None,
            'model_type': None,
            'equation': None,
            'equation_latex': None,
            'r2': None,
            'n': 0,
            'stats': None,
            'typical_range': None,
        }

    # 6. Horizontal Tail Volume (vh)
    pts_vh = [(r['m0'], r['v_h']) for r in class_ac if r.get('m0') and r.get('v_h') is not None]
    st_vh = compute_vector_stats([y for _, y in pts_vh])
    fit_vh = fit_regression(pts_vh, power=False)
    vh_typ_range = list(GEOMETRY_METRICS_INFO['v_h']['typical_ranges'][aircraft_type][:2])
    if fit_vh and fit_vh.get('r2') is not None and fit_vh['r2'] >= 0.50:
        sign = '+' if fit_vh['intercept'] >= 0 else '-'
        eq_vh = f"V_H = {fit_vh['slope']:.7g} · m0 {sign} {abs(fit_vh['intercept']):.4g}"
        eq_vh_tex = f"V_H = {fit_vh['slope']:.7g} \\cdot m_0 {sign} {abs(fit_vh['intercept']):.4g}"
        r2_vh = round(fit_vh['r2'], 4)
        model_vh = 'linear'
        if m0 is not None:
            pred_vh = predict(fit_vh, m0)
            val_vh = round(min(1.5, max(0.3, pred_vh)), 2) if pred_vh else (round(st_vh['median'], 2) if st_vh else 0.70)
        else:
            val_vh = round(st_vh['median'], 2) if st_vh else 0.70
    else:
        model_vh = 'median'
        val_vh = round(st_vh['median'], 2) if st_vh else 0.70
        r2_vh = round(fit_vh['r2'], 4) if fit_vh and fit_vh.get('r2') is not None else None
        eq_vh = f"V_H = {val_vh}"
        eq_vh_tex = f"V_H = {val_vh}"

    suggestions['vh'] = {
        'key': 'vh',
        'name': 'Horizontal Tail Volume',
        'symbol': 'V_H',
        'unit': '−',
        'suggested_value': val_vh,
        'model_type': model_vh,
        'equation': eq_vh,
        'equation_latex': eq_vh_tex,
        'r2': r2_vh,
        'n': len(pts_vh),
        'stats': _format_stats(st_vh),
        'typical_range': vh_typ_range,
    }

    # 7. Aileron Span Ratio (b_ail_ratio)
    pts_ba = [r['aileron_span_fraction'] for r in class_ac if r.get('aileron_span_fraction') is not None]
    st_ba = compute_vector_stats(pts_ba)
    val_ba = round(st_ba['median'], 2) if st_ba else 0.40
    suggestions['b_ail_ratio'] = {
        'key': 'b_ail_ratio',
        'name': 'Aileron Span Ratio',
        'symbol': 'b_ail/(b/2)',
        'unit': '−',
        'suggested_value': val_ba,
        'model_type': 'median',
        'equation': f"b_ail/(b/2) = {val_ba}",
        'equation_latex': f"\\frac{{b_{{ail}}}}{{b/2}} = {val_ba}",
        'r2': None,
        'n': len(pts_ba),
        'stats': _format_stats(st_ba),
        'typical_range': list(GEOMETRY_METRICS_INFO['aileron_span_fraction']['typical_ranges'][aircraft_type][:2]),
    }

    # 8. Aileron Chord Ratio (c_ail_ratio)
    pts_ca = [r['aileron_chord_ratio'] for r in class_ac if r.get('aileron_chord_ratio') is not None]
    st_ca = compute_vector_stats(pts_ca)
    val_ca = round(st_ca['median'], 2) if st_ca else 0.20
    suggestions['c_ail_ratio'] = {
        'key': 'c_ail_ratio',
        'name': 'Aileron Chord Ratio',
        'symbol': 'c_ail/c',
        'unit': '−',
        'suggested_value': val_ca,
        'model_type': 'median',
        'equation': f"c_ail/c = {val_ca}",
        'equation_latex': f"\\frac{{c_{{ail}}}}{{c}} = {val_ca}",
        'r2': None,
        'n': len(pts_ca),
        'stats': _format_stats(st_ca),
        'typical_range': list(GEOMETRY_METRICS_INFO['aileron_chord_ratio']['typical_ranges'][aircraft_type][:2]),
    }

    # 9. Elevator Chord Ratio (c_e_ratio)
    pts_ce = [r['elevator_chord_ratio'] for r in class_ac if r.get('elevator_chord_ratio') is not None]
    st_ce = compute_vector_stats(pts_ce)
    val_ce = round(st_ce['median'], 2) if st_ce else 0.35
    suggestions['c_e_ratio'] = {
        'key': 'c_e_ratio',
        'name': 'Elevator Chord Ratio',
        'symbol': 'c_e/c_H',
        'unit': '−',
        'suggested_value': val_ce,
        'model_type': 'median',
        'equation': f"c_e/c_H = {val_ce}",
        'equation_latex': f"\\frac{{c_e}}{{c_H}} = {val_ce}",
        'r2': None,
        'n': len(pts_ce),
        'stats': _format_stats(st_ce),
        'typical_range': list(GEOMETRY_METRICS_INFO['elevator_chord_ratio']['typical_ranges'][aircraft_type][:2]),
    }

    # 10. Rudder Chord Ratio (c_r_ratio)
    pts_cr = [r['rudder_chord_ratio'] for r in class_ac if r.get('rudder_chord_ratio') is not None]
    st_cr = compute_vector_stats(pts_cr)
    val_cr = round(st_cr['median'], 2) if st_cr else 0.35
    suggestions['c_r_ratio'] = {
        'key': 'c_r_ratio',
        'name': 'Rudder Chord Ratio',
        'symbol': 'c_r/c_V',
        'unit': '−',
        'suggested_value': val_cr,
        'model_type': 'median',
        'equation': f"c_r/c_V = {val_cr}",
        'equation_latex': f"\\frac{{c_r}}{{c_V}} = {val_cr}",
        'r2': None,
        'n': len(pts_cr),
        'stats': _format_stats(st_cr),
        'typical_range': list(GEOMETRY_METRICS_INFO['rudder_chord_ratio']['typical_ranges'][aircraft_type][:2]),
    }

    # 11. Dihedral (dihedral_deg)
    pts_dih = [r['dihedral_deg'] for r in class_ac if r.get('dihedral_deg') is not None]
    st_dih = compute_vector_stats(pts_dih)
    is_high_wing = (wing_configuration in ('high', 'braced_high', 'strut_braced'))
    if is_high_wing:
        if aircraft_type in ('piston_ga', 'turboprop_regional'):
            typ_dih = [0.0, 2.5]
            val_dih = 1.5
        else:
            typ_dih = [0.0, 3.0]
            val_dih = 1.5
        model_dih = 'literature'
    else:
        if aircraft_type == 'piston_ga':
            typ_dih = [3.5, 7.0]
            val_dih = round(st_dih['median'], 1) if (st_dih and 3.5 <= st_dih['median'] <= 7.0) else 5.0
        elif aircraft_type == 'turboprop_regional':
            typ_dih = [4.0, 6.5]
            val_dih = 5.0
        else:
            typ_dih = list(GEOMETRY_METRICS_INFO['dihedral_deg']['typical_ranges'][aircraft_type][:2])
            val_dih = round(st_dih['median'], 1) if st_dih else 3.0
        model_dih = 'median' if (st_dih and not wing_configuration) else 'literature'

    suggestions['dihedral_deg'] = {
        'key': 'dihedral_deg',
        'name': 'Dihedral Angle',
        'symbol': 'Gamma',
        'unit': '°',
        'suggested_value': val_dih,
        'model_type': model_dih,
        'equation': f"Gamma = {val_dih}°",
        'equation_latex': f"\\Gamma = {val_dih}^\\circ",
        'r2': None,
        'n': len(pts_dih),
        'stats': _format_stats(st_dih),
        'typical_range': typ_dih,
    }

    return {
        'status': 'ok',
        'aircraft_type': aircraft_type,
        'class_name': CLASSES[aircraft_type],
        'm0': m0,
        'suggestions': suggestions,
    }

