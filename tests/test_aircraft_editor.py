"""Read-only editor preview and persistence of optional catalogue data."""
import pytest

from calculations.trends import DATA, load_aircraft


def test_preview_recalculates_without_touching_shared_files(client):
    record = dict(load_aircraft()[0])
    before = {path.name: path.read_bytes() for path in DATA.glob('*.json')}
    response = client.post('/api/aircraft/preview', json={
        'id': record['id'], 'record': {'m0': record['m0'] * 1.1}})
    assert response.status_code == 200
    preview = response.json['aircraft']
    assert preview['m0'] == pytest.approx(record['m0'] * 1.1)
    assert preview['wing_loading_kg_m2'] == pytest.approx(preview['m0'] / record['s'])
    assert client.get('/api/aircraft/' + record['id']).json['m0'] == record['m0']
    assert {path.name: path.read_bytes() for path in DATA.glob('*.json')} == before


def test_editor_allows_missing_optional_values_and_can_clear_them(client, isolated_db):
    record = dict(id='editor-check-plane', model='Editor plane', manufacturer='Test',
                  aircraft_type='piston_ga', engine_type='prop', m0=1200,
                  source_references='Test source, page 1', range_km=800, year=2001)
    assert client.post('/api/aircraft/preview', json={'record': record}).status_code == 200
    assert client.get('/api/aircraft/editor-check-plane').status_code == 404
    assert client.post('/api/aircraft', json=record).status_code == 201
    response = client.put('/api/aircraft/editor-check-plane', json={'range_km': None, 'year': None})
    assert response.status_code == 200
    assert response.json['range_km'] is None and response.json['year'] is None
    assert response.json['ar'] is None


@pytest.mark.parametrize('changes', [
    {'m0': None}, {'climb_rate_ms': -1}, {'v_v': 2},
    {'range_km': 'abc'}, {'cruise_mach': 9}, {'source_references': []},
    {'v_cruise_kmh': 100, 'v_stall_kmh': 120},
])
def test_preview_rejects_invalid_changes(client, changes):
    record = load_aircraft()[0]
    response = client.post('/api/aircraft/preview', json={'id': record['id'], 'record': changes})
    assert response.status_code == 400


def test_engine_switch_can_clear_previous_rating(client, isolated_db):
    record = dict(id='editor-engine-plane', model='Engine plane', manufacturer='Test',
                  aircraft_type='piston_ga', engine_type='prop', m0=1200, p_kw=100)
    assert client.post('/api/aircraft', json=record).status_code == 201
    response = client.put('/api/aircraft/editor-engine-plane', json={
        'engine_type': 'none', 'p_kw': None, 't_kn': None, 'n_engines': 0})
    assert response.status_code == 200
    assert response.json['p_kw'] is None and response.json['n_engines'] == 0
