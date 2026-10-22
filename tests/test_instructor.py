"""Lecture requirements, independent physical checks, and traceable supplements."""
import copy
import io
import math
import pytest

from app import app
from calculations import AIRCRAFT_PRESETS, run_bipol_project
from calculations.runway import takeoff_distance
from calculations.trends import analyze_trends, load_aircraft
from calculations.trend_observations import import_observations


def test_lecture_mission_supersedes_old_defaults_and_preserves_mass_balance():
    r = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'mission_ld_factor': .8, 'mission_phase_model': 'standard'})
    m = r['mass']; assumptions = m['mission_assumptions']
    assert m['ld_cruise_used'] == pytest.approx(.94 * assumptions['k_max_preliminary'], abs=.005)
    assert m['fuel_fractions_detail']['warmup'] == 1
    assert .970 <= m['fuel_fractions_detail']['takeoff'] <= .975
    assert len(m['iterations']) >= 5 and assumptions['mass_residual_relative'] <= .001
    assert m['m0'] == pytest.approx(sum(m[k] for k in ('m_empty','m_fuel','m_payload','m_crew')), abs=.3)


@pytest.mark.parametrize('name', ['ga_trainer','vlj_jet'])
def test_full_takeoff_requirement_controls_power_and_never_uses_roll_as_total(name):
    p = copy.deepcopy(AIRCRAFT_PRESETS[name]); p['takeoff_distance_m'] = 800
    first = run_bipol_project(p)
    p['takeoff_distance_m'] = 500
    second = run_bipol_project(p)
    for r in (first,second):
        takeoff = r['performance']['takeoff']
        assert takeoff['available']
        assert takeoff['distance_to_15m'] > takeoff['ground_roll_m']
        assert takeoff['distance_to_15m'] == pytest.approx(takeoff['ground_roll_m'] + takeoff['transition_m'] + takeoff['climb_to_15m_m'], abs=.2)
        assert takeoff['distance_to_15m'] <= r['params']['takeoff_distance_m']
        check = next(c for c in r['compliance_checks'] if 'Całkowita długość startu' in c['parameter'])
        assert check['passed']
    key = 'thrust_kn' if p['engine_type'] == 'jet' else 'power_kw'
    assert second['sizing']['design_point'][key] >= first['sizing']['design_point'][key]


def test_tiny_fixed_engine_is_not_given_fictitious_positive_takeoff_climb():
    r = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'power_input_mode': 'fixed', 'engine_power_kw': .001})
    assert r['sizing']['design_point']['power_kw'] == .001
    assert not r['performance']['takeoff']['available']
    assert r['performance']['takeoff']['distance_to_15m'] is None
    assert not next(c for c in r['compliance_checks'] if 'Całkowita długość startu' in c['parameter'])['passed']


def test_landing_criterion_uses_airborne_part_too():
    r = run_bipol_project({**AIRCRAFT_PRESETS['ga_trainer'], 'landing_distance_m': 200})
    lnd = r['performance']['landing']
    assert lnd['distance_from_15m'] > lnd['ground_roll_m']
    assert not next(c for c in r['compliance_checks'] if 'Całkowita długość lądowania' in c['parameter'])['passed']


def test_passenger_fuel_exchange_closes_at_fixed_mass_and_recovers_original_range():
    r = run_bipol_project(AIRCRAFT_PRESETS['ga_trainer']); rows = r['mass']['payload_range']
    assert rows[0]['range_km'] == pytest.approx(r['params']['range_km'], abs=.1)
    assert rows[0]['payload_kg'] - rows[1]['payload_kg'] == 115
    assert rows[1]['fuel_kg'] - rows[0]['fuel_kg'] == pytest.approx(115, abs=.1)
    assert rows[1]['range_km'] > rows[0]['range_km']
    assert len({round(row['fuel_kg'] + row['payload_kg'], 0) for row in rows}) == 1


def test_missing_ground_distance_definition_is_not_promoted_to_full_takeoff():
    rows = load_aircraft()
    assert all(r['takeoff_distance_m'] is None for r in rows if not r.get('takeoff_basis'))
    assert any(r['takeoff_distance_m'] for r in rows if r['source_id'] == 'cado')
    assert any(r['landing_distance_m'] for r in rows if r['source_id'] == 'cado')


@pytest.mark.parametrize('name', ['ga_trainer','motoglider_aos','vlj_jet','glider_pw5'])
def test_six_distinct_report_charts_include_two_time_plots_and_one_mass_plot(name):
    r = run_bipol_project(AIRCRAFT_PRESETS[name]); charts = r['bipol_projects']['p1']['trend_analysis']['report_charts']
    assert len(charts) == len({c['mode'] for c in charts}) == 6
    assert [c['kind'] for c in charts].count('time') == 2
    assert [c['kind'] for c in charts].count('mass') == 1
    assert not any(c['mode'].startswith(('s:', 'p_kw:')) for c in charts)


def test_increasing_mass_trend_is_flagged_without_changing_the_fitted_observations(monkeypatch):
    import calculations.trends as trends
    rows=[]
    base=next(r for r in load_aircraft() if r['aircraft_type']=='piston_ga')
    for i in range(8):
        mass=500+i*100
        rows.append({**base,'id':str(i),'family':str(i),'m0':mass,'empty_fraction':.3+mass*.0001})
    monkeypatch.setattr(trends,'select_references',lambda params,m0:rows)
    a=analyze_trends({'aircraft_type':'piston_ga','engine_type':'prop'},1000,600)
    assert a['mass_fit']['C'] > 0 and not a['mass_trend_decreasing']
    assert any('nie jest malejący' in w for w in a['warnings'])


def test_csv_supplements_are_validated_persisted_and_do_not_mutate_shared_catalogue():
    base=next(r for r in load_aircraft() if r['aircraft_type']=='piston_ga')
    text=f'id;source;climb_rate_ms;takeoff_distance_m\n{base["id"]};AFM str. 10, ISA SL, MTOW, przeszkoda 15 m;4,5;600\n'
    observations=import_observations(text)
    assert observations[0]['climb_rate_ms'] == 4.5
    params={'aircraft_type':'piston_ga','engine_type':'prop','trend_aircraft_ids':[base['id']], 'trend_observations':observations}
    a=run_bipol_project(params)['bipol_projects']['p1']['trend_analysis']
    row=a['similar_aircraft'][0]
    assert row['climb_rate_ms']==4.5 and row['takeoff_distance_m']==600
    assert 'AFM str. 10' in row['source_references']
    assert next(r for r in load_aircraft() if r['id']==base['id'])['climb_rate_ms'] is None
    with app.test_client() as client:
        assert client.post('/api/trends/import',data={'file':(io.BytesIO(text.encode()),'dane.csv')}).status_code==200
        assert client.post('/api/trends/import',data={'file':(io.BytesIO(b''),'dane.csv')}).status_code==400
    for bad in (text.replace('4,5','NaN'),text.replace('AFM str. 10, ISA SL, MTOW, przeszkoda 15 m',''),text.replace(base['id'],'unknown')):
        with pytest.raises(ValueError):import_observations(bad)


def test_reports_include_six_plots_lecture_formulas_iterations_and_a4_reference_sheet():
    with app.test_client() as client:
        html=client.get('/report?sections=p1,p2,p3').get_data(as_text=True)
    assert html.count('data-course-chart=')==6
    assert '0{,}94' in html and 'Pierwsze pięć iteracji' in html
    assert 'id="print-drawing-grid"' in html and 'id="millimeter"' in html
    assert 'dziób w lewo' in html and 'Mocowanie podwozia' in html
    assert 'Wzór do rysunku odręcznego' in html
