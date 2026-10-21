"""Source-backed reference aircraft and descriptive regressions for BIPOL P1.

All masses use kg. Regressions are exploratory and never silently replace sizing.
Missing observations stay missing; each fit reports its own sample size.
"""
from collections import Counter
from functools import lru_cache
from pathlib import Path
import json
import math

from calculations.atmosphere import G0

DATA = Path(__file__).resolve().parents[1] / 'data' / 'aircraft'
CLASSES = {
    'piston_ga': 'Samoloty tłokowe GA', 'turboprop_regional': 'Samoloty turbośmigłowe',
    'jet_business': 'Odrzutowce biznesowe', 'jet_transport': 'Odrzutowce transportowe',
    'glider': 'Szybowce', 'motoglider': 'Motoszybowce', 'uav': 'Bezzałogowe płatowce',
}
SOURCES = {
    'fast': {'name': 'FAST Aerobase — University of Michigan IDEAS Lab',
        'url': 'https://github.com/ideas-um/FAST/tree/482e77b921d616d00d9cdb5c0c673d55f511c52b/+DatabasePkg',
        'license': 'Apache-2.0', 'license_file': 'FAST-Apache-2.0.txt',
        'citation': 'FAST / IDEAS Lab, The Regents of the University of Michigan. Snapshot 482e77b (2026).'},
    'cado': {'name': 'ENAC CADO Airplane Database v1.0',
        'url': 'https://doi.org/10.57745/LLRJO0', 'license': 'ODbL-1.0', 'license_file': 'CADO-ODbL-1.0.txt',
        'citation': 'Monrolin, Druot, Peteilh, Roches, Kambiri (2024). CADO airplane database. DOI:10.57745/LLRJO0.',
        'attribution': 'Contains information from CADO Airplane Database, which is made available here under the Open Database License (ODbL).'},
    'motogliders': {'name': 'Baza Motoszybowców EASA CS-22 / ULC / MEiL PW',
        'url': 'https://www.easa.europa.eu/en/document-library/type-certificate-data-sheets',
        'license': 'Public-Data', 'license_file': 'EASA-TCDS.txt',
        'citation': 'EASA TCDS (CS-22), ULC, dokumentacja techniczna MEiL PW / PRz oraz instrukcje użytkowania w locie AFM/POH.',
        'attribution': 'Zestawienie certyfikowanych motoszybowców turystycznych TMG i z napędem chowanym o szerokiej rozpiętości śmigieł (0.83–1.75 m).'},
    'geometry_trends': {'name': 'Baza Cech Geometrycznych i Sterów (Raymer, Roskam, Corke, TCDS, MEiL PW)',
        'url': 'https://www.easa.europa.eu/en/document-library/type-certificate-data-sheets',
        'license': 'Public-Data', 'license_file': 'EASA-TCDS.txt',
        'citation': 'Roskam (Airplane Design II & III), Raymer (Aircraft Design Table 6.4), Corke (Design of Aircraft Table 5.1/5.2), Gudmundsson, EASA/FAA TCDS, MEiL PW BIPOL.',
        'attribution': 'Zestawienie empiryczne 82 certyfikowanych statków powietrznych obejmujące cechy objętościowe usterzeń V_H, względne cięciwy sterów (b_ail/b, c_ail/c, c_e/c_H, c_r/c_V) oraz kąt wzniosu Gamma.'},
}


def derived(row):
    r = dict(row)
    mass, area, span = r['m0'], r.get('s'), r.get('b')
    r['ar'] = span * span / area if span and area else None
    r['empty_fraction'] = r['me'] / mass if r.get('me') else None
    r['wing_loading_kg_m2'] = mass / area if area else None
    r['wing_loading_n_m2'] = G0 * mass / area if area else None
    r['power_loading_kg_kw'] = mass / r['p_kw'] if r.get('p_kw') else None
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
    r['quality_notes'] = []
    if r['empty_fraction'] is not None and not .15 < r['empty_fraction'] < .95:
        r['quality_notes'].append('Nietypowy udział OEW/MTOW — pominięto w regresji masowej.')
    if r['ar'] is not None and not 2 <= r['ar'] <= 60:
        r['quality_notes'].append('Nietypowe wydłużenie — sprawdź źródło geometrii.')
    return r


@lru_cache(maxsize=1)
def load_aircraft():
    records = []
    for source in SOURCES:
        src_path = DATA / f'{source}.json'
        if src_path.exists():
            records.extend(derived(r) for r in json.loads(src_path.read_text(encoding='utf-8')))
    return tuple(records)


def reference_catalog():
    rows = load_aircraft()
    return {'schema': 1, 'total': len(rows), 'classes': CLASSES, 'sources': SOURCES,
            'counts': dict(Counter(r['aircraft_type'] for r in rows)), 'aircraft': rows}


def select_references(params, m0):
    cls, engine = params.get('aircraft_type', 'piston_ga'), params.get('engine_type', 'prop')
    pool = [r for r in load_aircraft() if r['aircraft_type'] == cls and r['engine_type'] == engine]
    source = params.get('trend_source', 'all')
    if source != 'all':
        pool = [r for r in pool if r['source_id'] == source]
    engines = int(params.get('trend_engine_count', 0))
    if engines:
        pool = [r for r in pool if r['n_engines'] == engines]
    ymin, ymax = int(params.get('trend_year_min', 0)), int(params.get('trend_year_max', 0))
    if ymin or ymax:
        pool = [r for r in pool if r['year'] is not None and (not ymin or r['year'] >= ymin) and (not ymax or r['year'] <= ymax)]
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
        'formula_latex': r'\frac{b_{ail}}{b/2} \quad \left(\text{lub } \frac{b_{ail}}{b}\right)',
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
        'desc': 'Kąt wzniosu geometrycznego skrzydła gwarantujący poprzeczną stateczność statyczną.',
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
        class_stats = compute_vector_stats(class_vals) or all_stats

        proj_val = proj_vals.get(key)

        # Regressions for class (or full database if class subset is small)
        reg_source = class_subset if len(class_subset) >= 4 else all_subset
        fit_m0 = fit_regression([(r['m0'], r[key]) for r in reg_source if r.get('m0')])
        fit_b = fit_regression([(r['b'], r[key]) for r in reg_source if r.get('b')])

        # Evaluation against typical literature range
        typ_min, typ_max, lit_note = info['typical_ranges'].get(ac_type, (class_stats['min'], class_stats['max'], 'Wg próby empirycznej'))
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
            verdict = f'W normie literaturowej i empirycznej dla klasy ({lit_note}).'
        elif proj_val is not None and proj_val < typ_min:
            status = 'warning'
            verdict = f'Poniżej typowego zakresu ({lit_note}); zweryfikuj zapas stateczności lub skuteczność.'
        elif proj_val is not None and proj_val > typ_max:
            status = 'info' if key in ('aileron_span_fraction', 'aileron_chord_ratio') else 'warning'
            verdict = f'Powyżej wartości przeciętnej ({lit_note}); zwiększona skuteczność sterowania.'
        else:
            status = 'unknown'
            verdict = 'Brak danych do weryfikacji.'

        # Samples for inspection
        samples = sorted(class_subset, key=lambda r: abs(r[key] - (proj_val if proj_val is not None else class_stats['mean'])))[:8]

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
        subset = [r for r in rows if r['year'] is not None and r.get(key) is not None]
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
    x_keys = ['ar', 'wing_loading_kg_m2', 'thrust_to_weight' if params.get('engine_type') == 'jet' else 'power_loading_kg_kw']
    x_labels = {'ar': ('Wydłużenie AR', '−'), 'wing_loading_kg_m2': ('Obciążenie powierzchni', 'kg/m²'),
                'thrust_to_weight': ('T / W', '−'), 'power_loading_kg_kw': ('Obciążenie mocy m₀ / P', 'kg/kW')}
    if any(r.get('prop_diameter_m') is not None for r in rows):
        x_keys.append('prop_diameter_m')
        x_labels['prop_diameter_m'] = ('Średnica śmigła d_prop', 'm')
    y_keys = ['v_cruise_kmh', 'cruise_mach', 'range_km', 'takeoff_m']
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

    return {'database_total': len(load_aircraft()), 'selected_n': len(rows), 'families_n': len(counts),
        'class_label': CLASSES[params.get('aircraft_type', 'piston_ga')], 'weighting': weighting,
        'reg_A': mass_fit['A'] if mass_fit else None, 'reg_C': mass_fit['C'] if mass_fit else None,
        'mass_fit': mass_fit, 'k_vs': k_vs, 'we_wo_trend': trend_value, 'we_wo_actual': m_empty/m0 if m0 else None,
        'similar_aircraft': rows, 'averages': averages, 'warnings': warnings,
        'time_trends': time_trends, 'relationships': relationships, 'sources': SOURCES,
        'year_basis': 'Rok certyfikacji wariantu (nie rok produkcji)',
        'method': 'Ważona regresja log(OEW/MTOW) = log(A) + C·log(m₀ [kg]). Domyślnie rodziny mają równą wagę.',
        'limitations': 'OEW obejmuje wyposażenie operacyjne i nie jest tożsama z masą własną każdego projektu. Cechy geometryczne i sterów (V_H, lotki, stery, wznios) oparto na 82 certyfikowanych konstrukcjach (Raymer, Roskam, Corke, TCDS, MEiL PW). Rodziny są grupowane heurystycznie. Korelacja nie dowodzi przyczynowości.',
        'geometry_trends_analysis': geometry_trends_analysis}
