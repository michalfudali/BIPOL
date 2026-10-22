"""Server-side reference aircraft database management and CRUD persistence.

Provides thread-safe, atomic file modifications on data/aircraft/*.json with
dynamic cache invalidation of descriptive regressions.
"""
import json
import math
import os
import re
import tempfile
import threading
import time
from pathlib import Path

from calculations.trends import DATA, CLASSES, SOURCES, derived, load_aircraft

VALID_CLASSES = set(CLASSES.keys())
VALID_ENGINE_TYPES = {'prop', 'jet', 'none'}
KNOWN_SOURCES = ('geometry_trends', 'motogliders', 'cado', 'fast')
SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_\-]+$')

DERIVED_KEYS = {
    'ar', 'empty_fraction', 'wing_loading_kg_m2', 'wing_loading_n_m2',
    'power_loading_kg_kw', 'specific_power_kw_kg', 'thrust_to_weight',
    'takeoff_distance_m', 'landing_distance_m', 'quality_notes'
}


class AircraftDatabaseError(Exception):
    """Base exception for aircraft database errors."""
    pass


class AircraftValidationError(AircraftDatabaseError):
    """Raised when record data fails schema or physical validation rules (HTTP 400)."""
    pass


class AircraftNotFoundError(AircraftDatabaseError, LookupError):
    """Raised when requested aircraft ID is not found in any source file (HTTP 404)."""
    pass


class AircraftDuplicateError(AircraftDatabaseError):
    """Raised when attempting to create an aircraft with an existing ID (HTTP 409)."""
    pass


def validate_aircraft(data: dict, is_create: bool = True, existing: dict | None = None) -> dict:
    """Validates aircraft record data against physical invariants and structural rules.

    Returns cleaned record dict ready for persistence (without derived keys).
    """
    if not isinstance(data, dict):
        raise AircraftValidationError("Payload must be a JSON object.")

    # Check required fields on creation
    if is_create:
        for req in ('id', 'model', 'manufacturer', 'aircraft_type', 'm0'):
            if req not in data or data[req] is None:
                raise AircraftValidationError(f"Missing required field: '{req}'.")

    # Validate ID
    aircraft_id = data.get('id')
    if aircraft_id is not None:
        if not isinstance(aircraft_id, str):
            raise AircraftValidationError("Field 'id' must be a string.")
        aircraft_id_clean = aircraft_id.strip()
        if not aircraft_id_clean:
            raise AircraftValidationError("Field 'id' cannot be empty.")
        if not SAFE_ID_REGEX.match(aircraft_id_clean):
            raise AircraftValidationError(
                f"Invalid aircraft ID '{aircraft_id}'. Only alphanumeric characters, dashes, and underscores are allowed."
            )
        if len(aircraft_id_clean) > 128:
            raise AircraftValidationError("Aircraft ID cannot exceed 128 characters.")
        if not is_create and existing and aircraft_id_clean != existing.get('id'):
            raise AircraftValidationError("Aircraft ID cannot be modified.")
    elif is_create:
        raise AircraftValidationError("Field 'id' is required.")

    # Validate model
    model = data.get('model')
    if model is not None:
        if not isinstance(model, str) or not model.strip():
            raise AircraftValidationError("Field 'model' must be a non-empty string.")

    # Validate manufacturer
    manufacturer = data.get('manufacturer')
    if manufacturer is not None:
        if not isinstance(manufacturer, str) or not manufacturer.strip():
            raise AircraftValidationError("Field 'manufacturer' must be a non-empty string.")

    # Validate aircraft_type
    act = data.get('aircraft_type')
    if act is not None:
        if act not in VALID_CLASSES:
            raise AircraftValidationError(
                f"Invalid aircraft_type: '{act}'. Must be one of {sorted(VALID_CLASSES)}."
            )

    # Validate m0 (MTOW)
    m0 = data.get('m0')
    if m0 is not None:
        if isinstance(m0, bool) or not isinstance(m0, (int, float)):
            raise AircraftValidationError("Field 'm0' must be a numeric value.")
        if not math.isfinite(m0) or m0 <= 0:
            raise AircraftValidationError("Field 'm0' (MTOW) must be a strictly positive number.")

    # Validate me (OEW)
    me = data.get('me')
    if me is not None:
        if isinstance(me, bool) or not isinstance(me, (int, float)):
            raise AircraftValidationError("Field 'me' must be a numeric value.")
        if not math.isfinite(me) or me <= 0:
            raise AircraftValidationError("Field 'me' (OEW) must be a strictly positive number.")
        if m0 is not None and me >= m0:
            raise AircraftValidationError(
                f"Empty mass 'me' ({me} kg) must be strictly less than MTOW 'm0' ({m0} kg)."
            )

    # Validate wing area s
    s = data.get('s')
    if s is not None:
        if isinstance(s, bool) or not isinstance(s, (int, float)):
            raise AircraftValidationError("Field 's' must be a numeric value.")
        if not math.isfinite(s) or s <= 0:
            raise AircraftValidationError("Field 's' (wing area) must be a strictly positive number.")

    # Validate wingspan b
    b = data.get('b')
    if b is not None:
        if isinstance(b, bool) or not isinstance(b, (int, float)):
            raise AircraftValidationError("Field 'b' must be a numeric value.")
        if not math.isfinite(b) or b <= 0:
            raise AircraftValidationError("Field 'b' (wingspan) must be a strictly positive number.")

    # Validate propulsion / engine fields
    p_kw = data.get('p_kw')
    if p_kw is not None:
        if isinstance(p_kw, bool) or not isinstance(p_kw, (int, float)):
            raise AircraftValidationError("Field 'p_kw' must be a numeric value.")
        if not math.isfinite(p_kw) or p_kw <= 0:
            raise AircraftValidationError("Field 'p_kw' must be a strictly positive number.")

    t_kn = data.get('t_kn')
    if t_kn is not None:
        if isinstance(t_kn, bool) or not isinstance(t_kn, (int, float)):
            raise AircraftValidationError("Field 't_kn' must be a numeric value.")
        if not math.isfinite(t_kn) or t_kn <= 0:
            raise AircraftValidationError("Field 't_kn' must be a strictly positive number.")

    engine_type = data.get('engine_type')
    if engine_type is not None:
        # Normalize piston / turboprop to prop if passed
        if engine_type in ('piston', 'turboprop'):
            engine_type = 'prop'
        if engine_type not in VALID_ENGINE_TYPES:
            raise AircraftValidationError(
                f"Invalid engine_type: '{engine_type}'. Must be one of {sorted(VALID_ENGINE_TYPES)}."
            )

    # Check propulsion mutual exclusivity
    if engine_type == 'jet':
        if p_kw is not None:
            raise AircraftValidationError("Jet aircraft cannot have engine shaft power 'p_kw'.")
    elif engine_type == 'prop':
        if t_kn is not None:
            raise AircraftValidationError("Propeller aircraft cannot have engine thrust 't_kn'.")
    elif engine_type == 'none':
        if p_kw is not None or t_kn is not None:
            raise AircraftValidationError("Unpowered aircraft (gliders) cannot specify power or thrust.")
    else:
        # engine_type not explicitly given, infer or ensure no contradiction
        if p_kw is not None and t_kn is not None:
            raise AircraftValidationError("Cannot specify both shaft power 'p_kw' and thrust 't_kn'.")
        if p_kw is not None:
            engine_type = 'prop'
        elif t_kn is not None:
            engine_type = 'jet'
        elif act == 'glider':
            engine_type = 'none'
        else:
            engine_type = 'prop'

    # Validate geometry and control ratios if provided
    for ratio_field in ('v_h', 'aileron_span_fraction', 'aileron_chord_ratio',
                        'elevator_chord_ratio', 'rudder_chord_ratio'):
        val = data.get(ratio_field)
        if val is not None:
            if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val <= 0:
                raise AircraftValidationError(f"Field '{ratio_field}' must be a positive number.")

    dihedral = data.get('dihedral_deg')
    if dihedral is not None:
        if isinstance(dihedral, bool) or not isinstance(dihedral, (int, float)) or not math.isfinite(dihedral):
            raise AircraftValidationError("Field 'dihedral_deg' must be a finite number.")

    n_engines = data.get('n_engines')
    if n_engines is not None:
        if isinstance(n_engines, bool) or not isinstance(n_engines, int) or n_engines < 0:
            raise AircraftValidationError("Field 'n_engines' must be a non-negative integer.")

    year = data.get('year')
    if year is not None:
        if isinstance(year, bool) or not isinstance(year, int) or not (1900 <= year <= 2100):
            raise AircraftValidationError("Field 'year' must be an integer between 1900 and 2100.")

    # Build clean output dictionary (stripping dynamically derived keys)
    clean = {k: v for k, v in data.items() if k not in DERIVED_KEYS}
    clean['year'] = int(year) if year is not None else None
    if aircraft_id:
        clean['id'] = aircraft_id.strip()
    if engine_type:
        clean['engine_type'] = engine_type
    if m0 is not None:
        clean['m0'] = float(m0)
    if me is not None:
        clean['me'] = float(me)
    if s is not None:
        clean['s'] = float(s)
    if b is not None:
        clean['b'] = float(b)
    if p_kw is not None:
        clean['p_kw'] = float(p_kw)
    if t_kn is not None:
        clean['t_kn'] = float(t_kn)
    if n_engines is not None:
        clean['n_engines'] = int(n_engines)
    elif is_create and 'n_engines' not in clean:
        clean['n_engines'] = 0 if engine_type == 'none' else 1

    return clean


class AircraftDatabase:
    """Thread-safe persistent database service for reference aircraft records in JSON files."""

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = Path(data_dir) if data_dir else DATA
        self.lock = threading.RLock()

    def get_all(self) -> tuple:
        """Returns all reference aircraft with derived attributes."""
        return load_aircraft()

    def get_by_id(self, aircraft_id: str) -> dict | None:
        """Finds aircraft by unique ID and returns full derived record, or None if not found."""
        for r in load_aircraft():
            if r.get('id') == aircraft_id:
                return dict(r)
        return None

    def find_source_file(self, aircraft_id: str) -> tuple[Path, list, int] | None:
        """Finds the JSON file path, record list, and list index containing aircraft_id."""
        with self.lock:
            # Check known sources in preferred order
            for source in KNOWN_SOURCES:
                path = self.data_dir / f"{source}.json"
                if not path.exists():
                    continue
                records = None
                for attempt in range(5):
                    try:
                        text = path.read_text(encoding='utf-8')
                        records = json.loads(text) if text.strip() else []
                        break
                    except (PermissionError, OSError, json.JSONDecodeError):
                        if attempt == 4:
                            break
                        time.sleep(0.025 * (2 ** attempt))
                if records is None:
                    continue
                for idx, r in enumerate(records):
                    if r.get('id') == aircraft_id:
                        return path, records, idx

            # Check any remaining json files in directory
            for path in sorted(self.data_dir.glob("*.json")):
                if path.stem in KNOWN_SOURCES or path.name.startswith('.'):
                    continue
                records = None
                for attempt in range(5):
                    try:
                        text = path.read_text(encoding='utf-8')
                        records = json.loads(text) if text.strip() else []
                        break
                    except (PermissionError, OSError, json.JSONDecodeError):
                        if attempt == 4:
                            break
                        time.sleep(0.025 * (2 ** attempt))
                if records is None:
                    continue
                for idx, r in enumerate(records):
                    if r.get('id') == aircraft_id:
                        return path, records, idx

            return None

    def create(self, record_data: dict) -> dict:
        """Creates a new aircraft record, saves to disk atomically, and refreshes cache."""
        with self.lock:
            clean = validate_aircraft(record_data, is_create=True)
            aid = clean['id']

            # Check uniqueness across all JSON files
            if self.find_source_file(aid) is not None:
                raise AircraftDuplicateError(f"Aircraft with id '{aid}' already exists.")

            # Target file determination (geometry_trends.json by default)
            source_id = clean.get('source_id')
            if not source_id or source_id not in KNOWN_SOURCES:
                source_id = 'geometry_trends'
            clean['source_id'] = source_id

            # Provide safe standard defaults for optional metadata fields
            if 'family' not in clean or not clean['family']:
                clean['family'] = clean['model'].split()[0] if clean.get('model') else aid
            if 'source_locator' not in clean or not clean['source_locator']:
                clean['source_locator'] = 'BIPOL Studio User Input'
            if 'source_references' not in clean or not clean['source_references']:
                clean['source_references'] = 'User input via BIPOL Studio Database Editor'
            if 'empty_mass_definition' not in clean:
                clean['empty_mass_definition'] = 'OEW / operating empty weight'
            if 'year_basis' not in clean:
                clean['year_basis'] = 'certification'
            if 'variable_sweep' not in clean:
                clean['variable_sweep'] = False
            if 'year' not in clean:
                clean['year'] = None

            target_path = self.data_dir / f"{source_id}.json"
            if target_path.exists():
                records = []
                for attempt in range(5):
                    try:
                        text = target_path.read_text(encoding='utf-8')
                        records = json.loads(text) if text.strip() else []
                        break
                    except (PermissionError, OSError, json.JSONDecodeError):
                        if attempt == 4:
                            raise AircraftDatabaseError(f"Failed to read target aircraft database file {target_path.name}")
                        time.sleep(0.025 * (2 ** attempt))
            else:
                records = []

            records.append(clean)
            self._atomic_save(target_path, records)
            load_aircraft.cache_clear()

            # Return derived record from refreshed cache or derived(clean)
            result = self.get_by_id(aid)
            return result if result is not None else derived(clean)

    def update(self, aircraft_id: str, updates: dict) -> dict:
        """Updates an existing aircraft record, saves to disk atomically, and refreshes cache."""
        with self.lock:
            match = self.find_source_file(aircraft_id)
            if not match:
                raise AircraftNotFoundError(f"Aircraft with id '{aircraft_id}' not found.")

            path, records, idx = match
            existing = records[idx]

            # Merge updates while preserving the original immutable ID
            merged = {**existing, **updates, 'id': aircraft_id}
            clean = validate_aircraft(merged, is_create=False, existing=existing)

            records[idx] = clean
            self._atomic_save(path, records)
            load_aircraft.cache_clear()

            result = self.get_by_id(aircraft_id)
            return result if result is not None else derived(clean)

    def delete(self, aircraft_id: str) -> bool:
        """Deletes an aircraft record by ID from whichever file contains it and flushes cache."""
        with self.lock:
            match = self.find_source_file(aircraft_id)
            if not match:
                raise AircraftNotFoundError(f"Aircraft with id '{aircraft_id}' not found.")

            path, records, idx = match
            del records[idx]
            self._atomic_save(path, records)
            load_aircraft.cache_clear()
            return True

    def _atomic_save(self, path: Path, records: list) -> None:
        """Atomically writes JSON records to path using tempfile.mkstemp and os.replace."""
        temp_fd, temp_path = tempfile.mkstemp(
            prefix=f".{path.stem}-",
            suffix=".tmp",
            dir=path.parent
        )
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as stream:
                json.dump(records, stream, ensure_ascii=False, indent=2, allow_nan=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            for attempt in range(5):
                try:
                    os.replace(temp_path, path)
                    break
                except (PermissionError, OSError):
                    if attempt == 4:
                        raise
                    time.sleep(0.025 * (2 ** attempt))
        except Exception:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise


# Module-level default instance and helper functions
db = AircraftDatabase()


def get_aircraft_database() -> AircraftDatabase:
    """Returns the default AircraftDatabase singleton."""
    return db


def get_aircraft(aircraft_id: str) -> dict | None:
    return db.get_by_id(aircraft_id)


def create_aircraft(record_data: dict) -> dict:
    return db.create(record_data)


def update_aircraft(aircraft_id: str, updates: dict) -> dict:
    return db.update(aircraft_id, updates)


def delete_aircraft(aircraft_id: str) -> bool:
    return db.delete(aircraft_id)
