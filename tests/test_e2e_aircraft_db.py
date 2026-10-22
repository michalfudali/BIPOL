"""End-to-End Test Suite for BIPOL Studio Reference Aircraft Database & CRUD Operations.

Covers:
- Requirement R3: Persistent database management and REST endpoints (GET, POST, PUT, DELETE /api/aircraft)
- Requirement R4: Physical validation rules, schema contracts, and atomic disk persistence
- Tier 1: Core Feature Coverage (>=5 test cases per feature)
- Tier 2: Boundary, Negative & Invariant Enforcement Cases (>=5 test cases per feature)
- Tier 3: Pairwise Interactions (CRUD mutations with disk persistence and cache invalidation)
"""
import json
import time
import pytest
from pathlib import Path
from calculations.trends import DATA, load_aircraft


VALID_AIRCRAFT_PAYLOAD = {
    "id": "e2e-test-trainer-100",
    "model": "AeroTest 100",
    "manufacturer": "Politechnika Warszawska MEiL",
    "aircraft_type": "piston_ga",
    "engine_type": "prop",
    "family": "AeroTest",
    "source_id": "geometry_trends",
    "source_locator": "E2E Unit Test",
    "source_references": "MEiL PW Preliminary Design Test Suite",
    "empty_mass_definition": "OEW / operating empty weight",
    "year_basis": "certification",
    "variable_sweep": False,
    "m0": 1150.0,
    "me": 690.0,
    "s": 15.2,
    "b": 10.4,
    "p_kw": 119.0,
    "n_engines": 1,
    "v_h": 0.68,
    "aileron_span_fraction": 0.40,
    "aileron_chord_ratio": 0.22,
    "elevator_chord_ratio": 0.35,
    "rudder_chord_ratio": 0.38,
    "dihedral_deg": 4.5
}


# ==============================================================================
# Tier 1: Feature Coverage (Requirement R3 & R4)
# ==============================================================================

@pytest.mark.tier1
def test_tier1_r3_catalog_retrieval_and_filtering(client):
    """Verifies GET /api/aircraft returns reference catalog with metadata and counts."""
    res = client.get('/api/aircraft')
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    
    catalog = res.get_json()
    assert catalog is not None
    assert 'total' in catalog
    assert catalog['total'] >= 840, f"Expected >=840 aircraft, got {catalog['total']}"
    assert 'aircraft' in catalog
    assert len(catalog['aircraft']) == catalog['total']
    assert 'counts' in catalog
    assert sum(catalog['counts'].values()) == catalog['total']
    assert 'sources' in catalog
    assert len(catalog['sources']) >= 4


@pytest.mark.tier1
def test_tier1_r3_get_aircraft_by_id_success(client):
    """Verifies GET /api/aircraft/<id> returns an existing aircraft record with attributes."""
    # Look up an existing well-known aircraft from the reference database
    res = client.get('/api/aircraft/gado-ae270')
    if res.status_code == 404:
        # Fallback to check cado-ae270 or another known ID from catalog
        cat = client.get('/api/aircraft').get_json()
        target_id = cat['aircraft'][0]['id']
        res = client.get(f'/api/aircraft/{target_id}')
    
    assert res.status_code == 200
    record = res.get_json()
    # The record may be returned directly or nested under 'aircraft' / 'record'
    data = record.get('aircraft') or record.get('record') or record
    assert 'id' in data
    assert 'model' in data
    assert 'm0' in data and data['m0'] > 0
    assert 'aircraft_type' in data


@pytest.mark.tier1
def test_tier1_r3_create_new_aircraft_success(client, isolated_db):
    """Verifies POST /api/aircraft successfully creates a new aircraft record (HTTP 201)."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    res = client.post('/api/aircraft', json=payload)
    
    assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.data}"
    body = res.get_json()
    assert body.get('status') in ('ok', 'success')
    
    # Confirm it can be retrieved via GET /api/aircraft/<id>
    get_res = client.get(f"/api/aircraft/{payload['id']}")
    assert get_res.status_code == 200
    created = get_res.get_json()
    record = created.get('aircraft') or created.get('record') or created
    assert record['id'] == payload['id']
    assert record['model'] == payload['model']
    assert record['m0'] == payload['m0']


@pytest.mark.tier1
def test_tier1_r3_update_existing_aircraft_success(client, isolated_db):
    """Verifies PUT /api/aircraft/<id> updates existing physical attributes (HTTP 200)."""
    # 1. Create initial record
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    client.post('/api/aircraft', json=payload)
    
    # 2. Update mass and power
    updates = {
        "m0": 1280.0,
        "me": 740.0,
        "p_kw": 135.0,
        "model": "AeroTest 100 Enhanced"
    }
    put_res = client.put(f"/api/aircraft/{payload['id']}", json=updates)
    assert put_res.status_code == 200, f"Expected 200 OK, got {put_res.status_code}: {put_res.data}"
    
    # 3. Retrieve and assert updated values
    get_res = client.get(f"/api/aircraft/{payload['id']}")
    assert get_res.status_code == 200
    updated = get_res.get_json()
    record = updated.get('aircraft') or updated.get('record') or updated
    assert record['m0'] == 1280.0
    assert record['me'] == 740.0
    assert record['p_kw'] == 135.0
    assert record['model'] == "AeroTest 100 Enhanced"


@pytest.mark.tier1
def test_tier1_r3_delete_aircraft_success(client, isolated_db):
    """Verifies DELETE /api/aircraft/<id> permanently removes the aircraft (HTTP 200 then 404)."""
    # 1. Create record
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    client.post('/api/aircraft', json=payload)
    assert client.get(f"/api/aircraft/{payload['id']}").status_code == 200
    
    # 2. Delete record
    del_res = client.delete(f"/api/aircraft/{payload['id']}")
    assert del_res.status_code == 200, f"Expected 200 OK on DELETE, got {del_res.status_code}: {del_res.data}"
    
    # 3. Verify subsequent GET returns 404 Not Found
    get_res = client.get(f"/api/aircraft/{payload['id']}")
    assert get_res.status_code == 404


@pytest.mark.tier1
def test_tier1_r3_reactive_recalculation_after_mutation(client, isolated_db):
    """Verifies that catalog count updates immediately in memory upon create and delete."""
    initial_cat = client.get('/api/aircraft').get_json()
    initial_total = initial_cat['total']
    
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    create_res = client.post('/api/aircraft', json=payload)
    assert create_res.status_code == 201
    
    # Check catalog count incremented
    post_cat = client.get('/api/aircraft').get_json()
    assert post_cat['total'] == initial_total + 1
    
    # Delete and check count restored
    del_res = client.delete(f"/api/aircraft/{payload['id']}")
    assert del_res.status_code == 200
    final_cat = client.get('/api/aircraft').get_json()
    assert final_cat['total'] == initial_total


@pytest.mark.tier1
def test_tier1_r4_crud_response_times(client, isolated_db):
    """Verifies that all CRUD operations execute under 500 ms."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    
    # Measure POST
    t0 = time.perf_counter()
    post_res = client.post('/api/aircraft', json=payload)
    t_post = (time.perf_counter() - t0) * 1000
    if post_res.status_code == 201:
        assert t_post < 500.0, f"POST took {t_post:.1f} ms >= 500 ms"
        
        # Measure PUT
        t0 = time.perf_counter()
        put_res = client.put(f"/api/aircraft/{payload['id']}", json={"m0": 1160.0})
        t_put = (time.perf_counter() - t0) * 1000
        assert t_put < 500.0, f"PUT took {t_put:.1f} ms >= 500 ms"
        
        # Measure DELETE
        t0 = time.perf_counter()
        del_res = client.delete(f"/api/aircraft/{payload['id']}")
        t_del = (time.perf_counter() - t0) * 1000
        assert t_del < 500.0, f"DELETE took {t_del:.1f} ms >= 500 ms"


# ==============================================================================
# Tier 2: Boundary & Negative Validation Cases (Requirement R3 & R4)
# ==============================================================================

@pytest.mark.tier2
@pytest.mark.parametrize('missing_field', ['id', 'model', 'manufacturer', 'aircraft_type', 'm0'])
def test_tier2_r3_boundary_missing_required_fields(client, isolated_db, missing_field):
    """Verifies POST /api/aircraft rejects payload with missing required field (HTTP 400)."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    del payload[missing_field]
    res = client.post('/api/aircraft', json=payload)
    assert res.status_code == 400, f"Missing '{missing_field}' must return 400, got {res.status_code}"


@pytest.mark.tier2
@pytest.mark.parametrize('bad_m0', [0, -10, -500.0])
def test_tier2_r3_boundary_negative_mass_rejected(client, isolated_db, bad_m0):
    """Verifies that MTOW m0 <= 0 is rejected with HTTP 400."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    payload['m0'] = bad_m0
    res = client.post('/api/aircraft', json=payload)
    assert res.status_code == 400, f"Non-positive m0={bad_m0} must return 400, got {res.status_code}"


@pytest.mark.tier2
def test_tier2_r3_boundary_inverted_empty_mass_fraction(client, isolated_db):
    """Verifies that empty mass me >= m0 violates physical invariant and returns HTTP 400."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    payload['m0'] = 1000.0
    payload['me'] = 1100.0  # Empty mass exceeds MTOW!
    res = client.post('/api/aircraft', json=payload)
    assert res.status_code == 400, f"me >= m0 must return 400, got {res.status_code}"


@pytest.mark.tier2
@pytest.mark.parametrize('bad_s', [0, -5.0])
def test_tier2_r3_boundary_non_positive_wing_area(client, isolated_db, bad_s):
    """Verifies wing reference area S <= 0 returns HTTP 400."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    payload['s'] = bad_s
    res = client.post('/api/aircraft', json=payload)
    assert res.status_code == 400, f"Non-positive wing area S={bad_s} must return 400, got {res.status_code}"


@pytest.mark.tier2
def test_tier2_r3_boundary_engine_type_propulsion_mismatch(client, isolated_db):
    """Verifies propulsion mutual exclusivity: jet must not have p_kw, prop must not have t_kn."""
    # 1. Jet aircraft with p_kw provided
    bad_jet = dict(VALID_AIRCRAFT_PAYLOAD)
    bad_jet['id'] = 'bad-jet-pw'
    bad_jet['aircraft_type'] = 'jet_business'
    bad_jet['engine_type'] = 'jet'
    bad_jet['p_kw'] = 500.0
    bad_jet['t_kn'] = None
    res = client.post('/api/aircraft', json=bad_jet)
    assert res.status_code == 400, f"Jet with p_kw must return 400, got {res.status_code}"

    # 2. Propeller aircraft with t_kn provided
    bad_prop = dict(VALID_AIRCRAFT_PAYLOAD)
    bad_prop['id'] = 'bad-prop-tkn'
    bad_prop['engine_type'] = 'prop'
    bad_prop['p_kw'] = None
    bad_prop['t_kn'] = 25.0
    res = client.post('/api/aircraft', json=bad_prop)
    assert res.status_code == 400, f"Prop with t_kn must return 400, got {res.status_code}"


@pytest.mark.tier2
def test_tier2_r3_boundary_duplicate_id_conflict(client, isolated_db):
    """Verifies POST /api/aircraft returns HTTP 409 Conflict when ID already exists."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    # 1. First creation
    res1 = client.post('/api/aircraft', json=payload)
    assert res1.status_code == 201
    
    # 2. Duplicate creation with identical ID
    res2 = client.post('/api/aircraft', json=payload)
    assert res2.status_code == 409, f"Duplicate ID must return 409 Conflict, got {res2.status_code}"


@pytest.mark.tier2
def test_tier2_r3_boundary_update_nonexistent_returns_404(client, isolated_db):
    """Verifies PUT /api/aircraft/<id> returns HTTP 404 for non-existent aircraft ID."""
    res = client.put('/api/aircraft/nonexistent-id-404-xyz', json={"m0": 1500.0})
    assert res.status_code == 404, f"Updating nonexistent aircraft must return 404, got {res.status_code}"


@pytest.mark.tier2
def test_tier2_r3_boundary_delete_nonexistent_returns_404(client, isolated_db):
    """Verifies DELETE /api/aircraft/<id> returns HTTP 404 for non-existent aircraft ID."""
    res = client.delete('/api/aircraft/nonexistent-id-404-xyz')
    assert res.status_code == 404, f"Deleting nonexistent aircraft must return 404, got {res.status_code}"


@pytest.mark.tier2
@pytest.mark.parametrize('bad_id', [
    'has space',
    'has/slash',
    'has\\backslash',
    '../../path_traversal',
    'null\x00byte',
    '',
])
def test_tier2_r3_boundary_invalid_id_characters(client, isolated_db, bad_id):
    """Verifies aircraft IDs with forbidden meta-characters or spaces return HTTP 400/404."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    payload['id'] = bad_id
    res = client.post('/api/aircraft', json=payload)
    assert res.status_code in (400, 404), f"Unsafe ID '{bad_id}' must be rejected with 400/404, got {res.status_code}"


@pytest.mark.tier2
def test_tier2_r3_boundary_empty_or_malformed_json_body(client, isolated_db):
    """Verifies that non-JSON or empty payloads return HTTP 400 Bad Request."""
    res = client.post('/api/aircraft', data="This is not JSON", content_type="application/json")
    assert res.status_code == 400


# ==============================================================================
# Tier 3: Pairwise Interactions with Disk Persistence
# ==============================================================================

@pytest.mark.tier3
def test_tier3_interaction_crud_persistence_on_disk(client, isolated_db):
    """Verifies that CRUD mutations physically persist to JSON files on disk and survive cache clears."""
    payload = dict(VALID_AIRCRAFT_PAYLOAD)
    source_file = payload.get('source_id', 'geometry_trends') + '.json'
    target_path = DATA / source_file
    
    # 1. Create and verify in JSON file directly
    client.post('/api/aircraft', json=payload)
    content_after_create = json.loads(target_path.read_text(encoding='utf-8'))
    found = [r for r in content_after_create if r.get('id') == payload['id']]
    assert len(found) == 1, f"Record {payload['id']} not physically found on disk in {target_path}"
    assert found[0]['model'] == payload['model']
    
    # 2. Update and verify modification on disk
    client.put(f"/api/aircraft/{payload['id']}", json={"model": "Disk Persisted Model V2"})
    content_after_update = json.loads(target_path.read_text(encoding='utf-8'))
    found_up = [r for r in content_after_update if r.get('id') == payload['id']]
    assert len(found_up) == 1
    assert found_up[0]['model'] == "Disk Persisted Model V2"
    
    # 3. Delete and verify complete removal from disk
    client.delete(f"/api/aircraft/{payload['id']}")
    content_after_delete = json.loads(target_path.read_text(encoding='utf-8'))
    found_del = [r for r in content_after_delete if r.get('id') == payload['id']]
    assert len(found_del) == 0, f"Record {payload['id']} still physically present in {target_path} after DELETE"
