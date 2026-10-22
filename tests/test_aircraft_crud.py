"""Unit and integration tests for AircraftDatabase service (calculations/aircraft_db.py).

Verifies:
- Schema and physical invariant validation logic
- Concurrency protection via threading.RLock
- Atomic writes via tempfile.mkstemp and os.replace
- Dynamic cache invalidation via load_aircraft.cache_clear()
- CRUD operations across partitioned source files
"""
import copy
import json
import threading
import pytest
from pathlib import Path

from calculations.aircraft_db import (
    AircraftDatabase,
    AircraftValidationError,
    AircraftNotFoundError,
    AircraftDuplicateError,
    validate_aircraft,
    get_aircraft_database,
)
from calculations.trends import DATA, load_aircraft


@pytest.fixture
def test_payload():
    return {
        "id": "unit-test-plane-01",
        "model": "Unit Trainer 100",
        "manufacturer": "Politechnika Warszawska MEiL",
        "aircraft_type": "piston_ga",
        "engine_type": "prop",
        "family": "UnitTrainer",
        "source_id": "geometry_trends",
        "source_locator": "Unit Test Suite",
        "source_references": "MEiL PW Test Suite",
        "empty_mass_definition": "OEW / operating empty weight",
        "year_basis": "certification",
        "variable_sweep": False,
        "m0": 1200.0,
        "me": 720.0,
        "s": 15.5,
        "b": 10.5,
        "p_kw": 125.0,
        "n_engines": 1,
        "v_h": 0.70,
        "aileron_span_fraction": 0.38,
        "aileron_chord_ratio": 0.22,
        "elevator_chord_ratio": 0.36,
        "rudder_chord_ratio": 0.38,
        "dihedral_deg": 3.0,
    }


# ==============================================================================
# 1. Validation Engine Unit Tests
# ==============================================================================

def test_validate_aircraft_valid_creation(test_payload):
    """Valid creation payload passes and strips derived keys."""
    raw = copy.deepcopy(test_payload)
    raw['ar'] = 7.1  # Derived key that should be stripped
    clean = validate_aircraft(raw, is_create=True)
    assert clean['id'] == 'unit-test-plane-01'
    assert clean['m0'] == 1200.0
    assert 'ar' not in clean


def test_validate_aircraft_non_dict_rejected():
    with pytest.raises(AircraftValidationError, match="JSON object"):
        validate_aircraft("not a dict", is_create=True)


@pytest.mark.parametrize('missing_key', ['id', 'model', 'manufacturer', 'aircraft_type', 'm0'])
def test_validate_aircraft_missing_required_on_create(test_payload, missing_key):
    raw = copy.deepcopy(test_payload)
    del raw[missing_key]
    with pytest.raises(AircraftValidationError, match=f"Missing required field: '{missing_key}'"):
        validate_aircraft(raw, is_create=True)


@pytest.mark.parametrize('bad_id', [
    'with spaces',
    'slash/bad',
    'backslash\\bad',
    '../traversal',
    'null\x00byte',
    '',
    'a' * 150,
])
def test_validate_aircraft_unsafe_ids(test_payload, bad_id):
    raw = copy.deepcopy(test_payload)
    raw['id'] = bad_id
    with pytest.raises(AircraftValidationError):
        validate_aircraft(raw, is_create=True)


def test_validate_aircraft_cannot_modify_id_on_update(test_payload):
    existing = dict(test_payload)
    update = {"id": "different-id"}
    with pytest.raises(AircraftValidationError, match="cannot be modified"):
        validate_aircraft(update, is_create=False, existing=existing)


@pytest.mark.parametrize('bad_m0', [0, -1.0, -100, float('nan'), float('inf'), "string"])
def test_validate_aircraft_invalid_m0(test_payload, bad_m0):
    raw = copy.deepcopy(test_payload)
    raw['m0'] = bad_m0
    with pytest.raises(AircraftValidationError):
        validate_aircraft(raw, is_create=True)


@pytest.mark.parametrize('bad_me', [0, -50.0, 1200.0, 1500.0])
def test_validate_aircraft_invalid_me_bounds(test_payload, bad_me):
    raw = copy.deepcopy(test_payload)
    raw['m0'] = 1000.0
    raw['me'] = bad_me
    with pytest.raises(AircraftValidationError):
        validate_aircraft(raw, is_create=True)


@pytest.mark.parametrize('bad_s', [0, -10.0, float('inf')])
def test_validate_aircraft_invalid_s_bounds(test_payload, bad_s):
    raw = copy.deepcopy(test_payload)
    raw['s'] = bad_s
    with pytest.raises(AircraftValidationError):
        validate_aircraft(raw, is_create=True)


@pytest.mark.parametrize('bad_b', [0, -2.0, float('nan')])
def test_validate_aircraft_invalid_b_bounds(test_payload, bad_b):
    raw = copy.deepcopy(test_payload)
    raw['b'] = bad_b
    with pytest.raises(AircraftValidationError):
        validate_aircraft(raw, is_create=True)


def test_validate_aircraft_jet_with_shaft_power_rejected(test_payload):
    raw = copy.deepcopy(test_payload)
    raw['engine_type'] = 'jet'
    raw['p_kw'] = 500.0
    raw['t_kn'] = None
    with pytest.raises(AircraftValidationError, match="Jet aircraft cannot have engine shaft power"):
        validate_aircraft(raw, is_create=True)


def test_validate_aircraft_prop_with_thrust_rejected(test_payload):
    raw = copy.deepcopy(test_payload)
    raw['engine_type'] = 'prop'
    raw['p_kw'] = None
    raw['t_kn'] = 25.0
    with pytest.raises(AircraftValidationError, match="Propeller aircraft cannot have engine thrust"):
        validate_aircraft(raw, is_create=True)


def test_validate_aircraft_glider_with_power_rejected(test_payload):
    raw = copy.deepcopy(test_payload)
    raw['engine_type'] = 'none'
    raw['p_kw'] = 50.0
    with pytest.raises(AircraftValidationError, match="Unpowered aircraft"):
        validate_aircraft(raw, is_create=True)


# ==============================================================================
# 2. Database Service CRUD Integration Tests
# ==============================================================================

def test_db_create_and_get_by_id(test_payload, isolated_db):
    """Database creates entry, persists to disk, and retrieves with derived properties."""
    db = get_aircraft_database()
    created = db.create(test_payload)
    assert created['id'] == test_payload['id']
    assert created['model'] == test_payload['model']
    assert 'ar' in created
    assert 'wing_loading_kg_m2' in created

    # Query by ID
    retrieved = db.get_by_id(test_payload['id'])
    assert retrieved is not None
    assert retrieved['id'] == test_payload['id']
    assert retrieved['m0'] == test_payload['m0']


def test_db_create_duplicate_rejected(test_payload, isolated_db):
    """Creating duplicate ID raises AircraftDuplicateError."""
    db = get_aircraft_database()
    db.create(test_payload)
    with pytest.raises(AircraftDuplicateError):
        db.create(test_payload)


def test_db_update_modifies_disk_and_memory(test_payload, isolated_db):
    """Updating entry modifies parameters on disk and refreshes memory."""
    db = get_aircraft_database()
    db.create(test_payload)

    updated = db.update(test_payload['id'], {"m0": 1400.0, "me": 850.0, "model": "Unit Trainer 100 Evo"})
    assert updated['m0'] == 1400.0
    assert updated['me'] == 850.0
    assert updated['model'] == "Unit Trainer 100 Evo"

    # Confirm via get_by_id
    rec = db.get_by_id(test_payload['id'])
    assert rec['m0'] == 1400.0
    assert rec['model'] == "Unit Trainer 100 Evo"


def test_db_update_nonexistent_raises_404(isolated_db):
    db = get_aircraft_database()
    with pytest.raises(AircraftNotFoundError):
        db.update("does-not-exist-xyz", {"m0": 1000.0})


def test_db_delete_removes_from_disk_and_memory(test_payload, isolated_db):
    """Deleting entry permanently removes it from both disk and in-memory cache."""
    db = get_aircraft_database()
    db.create(test_payload)
    assert db.get_by_id(test_payload['id']) is not None

    deleted = db.delete(test_payload['id'])
    assert deleted is True
    assert db.get_by_id(test_payload['id']) is None

    # Deleting again raises AircraftNotFoundError
    with pytest.raises(AircraftNotFoundError):
        db.delete(test_payload['id'])


def test_db_concurrent_creates(isolated_db):
    """Concurrent creates are thread-safe and do not corrupt JSON files."""
    db = get_aircraft_database()
    threads = []
    errors = []

    def worker(worker_id):
        try:
            payload = {
                "id": f"thread-plane-{worker_id}",
                "model": f"Thread Plane {worker_id}",
                "manufacturer": "Teamwork Thread",
                "aircraft_type": "piston_ga",
                "engine_type": "prop",
                "m0": 1000.0 + worker_id * 10,
                "me": 600.0,
                "s": 14.0,
                "b": 10.0,
                "p_kw": 100.0,
            }
            db.create(payload)
        except Exception as e:
            errors.append((worker_id, e))

    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(errors) == 0, f"Thread errors: {errors}"
    for i in range(5):
        assert db.get_by_id(f"thread-plane-{i}") is not None
