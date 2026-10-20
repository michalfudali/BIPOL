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
        records.extend(derived(r) for r in json.loads((DATA / f'{source}.json').read_text(encoding='utf-8')))
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
    'v_cruise_kmh': ('Prędkość przelotowa', 'km/h'), 'cruise_mach': ('Liczba Macha przelotu', 'Ma'),
    'range_km': ('Zasięg katalogowy', 'km'), 'takeoff_m': ('Długość startu katalogowa', 'm'),
}


def analyze_trends(params, m0, m_empty):
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
    for x_key in x_keys:
        for key in ('v_cruise_kmh', 'cruise_mach', 'range_km', 'takeoff_m'):
            subset = [r for r in rows if r.get(x_key) is not None and r.get(key) is not None
                      and not (x_key == 'ar' and not 2 <= r['ar'] <= 60)]
            fit = fit_regression([(r[x_key], r[key]) for r in subset], weights(subset))
            relationships.append({'x_key': x_key, 'x_label': x_labels[x_key][0], 'x_unit': x_labels[x_key][1],
                'y_key': key, 'y_label': METRICS[key][0], 'y_unit': METRICS[key][1], 'fit': fit,
                'points': [{'x': r[x_key], 'y': r[key], 'model': r['model']} for r in subset]})
    averages = {}
    for key in ('empty_fraction', 'ar', 'wing_loading_kg_m2', 'h_tail_area', 'v_tail_area'):
        subset = [r for r in rows if r.get(key) is not None]
        ws = weights(subset)
        averages[key] = {'mean': sum(r[key]*w for r,w in zip(subset,ws))/sum(ws) if subset else None, 'n': len(subset)}
    return {'database_total': len(load_aircraft()), 'selected_n': len(rows), 'families_n': len(counts),
        'class_label': CLASSES[params.get('aircraft_type', 'piston_ga')], 'weighting': weighting,
        'reg_A': mass_fit['A'] if mass_fit else None, 'reg_C': mass_fit['C'] if mass_fit else None,
        'mass_fit': mass_fit, 'k_vs': k_vs, 'we_wo_trend': trend_value, 'we_wo_actual': m_empty/m0,
        'similar_aircraft': rows, 'averages': averages, 'warnings': warnings,
        'time_trends': time_trends, 'relationships': relationships, 'sources': SOURCES,
        'year_basis': 'Rok certyfikacji wariantu (nie rok produkcji)',
        'method': 'Ważona regresja log(OEW/MTOW) = log(A) + C·log(m₀ [kg]). Domyślnie rodziny mają równą wagę.',
        'limitations': 'OEW obejmuje wyposażenie operacyjne i nie jest tożsama z masą własną każdego projektu. Bazy mogą opisywać te same warianty pod różnymi nazwami; wybierz pojedyncze źródło do analizy wrażliwości. Rodziny są grupowane heurystycznie. Osiągi katalogowe mają różne warunki pomiaru. Korelacja nie dowodzi przyczynowości; prognoza nie ma przedziału ufności.'}
