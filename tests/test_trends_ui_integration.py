import pytest
import json
from app import app
from calculations.trends import CLASSES

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c

def test_template_rendering_and_ui_elements(client):
    """Verify that templates render with HTTP 200 and include all required UI elements."""
    res = client.get('/')
    assert res.status_code == 200
    html = res.data.decode('utf-8')

    # Trend Suggestions Panel in trends tab
    assert 'id="trendSuggestionsPanel"' in html
    assert 'id="btnApplyAllTrendSuggestions"' in html
    assert 'id="trendSuggestionsRows"' in html

    # Aircraft Editor in trends tab
    assert 'id="btnAddAircraftBtn"' in html
    assert 'id="trendAircraftModal"' in html
    assert 'id="saveTrendAircraftBtn"' in html
    assert 'id="closeTrendModalBtn"' in html
    assert 'id="trendAircraftRows"' in html

    # Wizard trend integration
    assert 'id="wizApplyTrendGeometryBtn"' in html
    assert 'id="wizSuggestTrendsBtn"' in html

def test_api_trends_suggestions_all_classes(client):
    """Verify suggestions endpoint returns empirical values for all 7 classes."""
    for ac_class in CLASSES:
        res = client.get(f'/api/trends/suggestions?aircraft_type={ac_class}')
        assert res.status_code == 200, f"Failed for class {ac_class}"
        data = res.get_json()
        assert data['status'] == 'ok'
        assert data['aircraft_type'] == ac_class
        suggestions = data['suggestions']
        assert 'ws' in suggestions
        assert 'ar' in suggestions
        assert 'me_m0' in suggestions
        assert 'vh' in suggestions or 'v_h' in suggestions
        assert 'dihedral_deg' in suggestions
        assert suggestions['ar']['suggested_value'] > 0
        assert len(suggestions['ar']['typical_range']) == 2

def test_api_aircraft_lifecycle_reactive_recalc(client):
    """Verify adding, updating, and deleting aircraft via REST API with instant cache recalculation."""
    ac_id = 'ui_integration_test_plane_001'
    new_ac = {
        'id': ac_id,
        'model': 'UI Integration Test Plane',
        'manufacturer': 'Test Corp',
        'family': 'TestFamily',
        'year': 2026,
        'aircraft_type': 'piston_ga',
        'engine_type': 'prop',
        'n_engines': 1,
        'm0': 1200.0,
        'me': 720.0,
        's': 15.0,
        'b': 10.5,
        'p_kw': 130.0,
        'v_cruise_kmh': 210.0,
        'v_stall_kmh': 85.0,
        'v_h': 0.70,
        'dihedral_deg': 4.5
    }

    # 1. Create
    res_post = client.post('/api/aircraft', json=new_ac)
    assert res_post.status_code == 201, res_post.data
    post_data = res_post.get_json()
    assert post_data['id'] == ac_id

    try:
        # 2. Verify in catalog
        res_cat = client.get('/api/aircraft')
        assert res_cat.status_code == 200
        cat = res_cat.get_json()
        found = [a for a in cat['aircraft'] if a['id'] == ac_id]
        assert len(found) == 1
        assert found[0]['model'] == 'UI Integration Test Plane'

        # 3. Update
        updated_data = dict(new_ac)
        updated_data['model'] = 'UI Integration Test Plane (Updated)'
        updated_data['m0'] = 1250.0
        res_put = client.put(f'/api/aircraft/{ac_id}', json=updated_data)
        assert res_put.status_code == 200
        assert res_put.get_json()['model'] == 'UI Integration Test Plane (Updated)'

        # 4. Check suggestions dynamic update
        res_sugg = client.get('/api/trends/suggestions?aircraft_type=piston_ga&m0=1250')
        assert res_sugg.status_code == 200

    finally:
        # 5. Delete cleanup
        res_del = client.delete(f'/api/aircraft/{ac_id}')
        assert res_del.status_code == 200
        res_get_deleted = client.get(f'/api/aircraft/{ac_id}')
        assert res_get_deleted.status_code == 404
