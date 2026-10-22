"""Validated, locally sourced corrections to reference aircraft records.

The downloaded catalogues remain immutable. Corrections contain only measured
input fields; dependent quantities are recomputed by ``trends.derived``.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from threading import RLock


CORRECTIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "aircraft" / "local_corrections.json"
_LOCK = RLock()


def _number(key, label, unit, minimum, maximum, group, *, integer=False, nullable=True):
    return {"key": key, "label": label, "unit": unit, "min": minimum, "max": maximum,
            "type": "integer" if integer else "number", "group": group, "nullable": nullable}


def _choice(key, label, group):
    return {"key": key, "label": label, "unit": "", "min": None, "max": None,
            "type": "select", "group": group, "nullable": True,
            "options": [
                {"value": "", "label": "Brak informacji"},
                {"value": "15m", "label": "Całkowita odległość do/z 15 m"},
                {"value": "50ft", "label": "Całkowita odległość do/z 50 ft"},
                {"value": "field_length", "label": "Długość pola startowego/lądowania"},
                {"value": "ground_roll", "label": "Tylko rozbieg/dobieg"},
                {"value": "unknown", "label": "Nieokreślona podstawa pomiaru"},
            ]}


EDITABLE_FIELDS = [
    _number("m0", "Masa startowa MTOW", "kg", 0.1, 1_000_000, "Masy", nullable=False),
    _number("me", "Masa pusta OEW", "kg", 0.1, 1_000_000, "Masy"),
    _number("s", "Powierzchnia skrzydła", "m²", 0.01, 2_000, "Geometria"),
    _number("b", "Rozpiętość skrzydła", "m", 0.01, 200, "Geometria"),
    _number("h_tail_area", "Powierzchnia usterzenia poziomego", "m²", 0.001, 1_000, "Geometria"),
    _number("v_tail_area", "Powierzchnia usterzenia pionowego", "m²", 0.001, 1_000, "Geometria"),
    _number("prop_diameter_m", "Średnica śmigła", "m", 0.01, 20, "Geometria"),
    _number("year", "Rok certyfikacji", "", 1900, 2100, "Identyfikacja", integer=True),
    _number("n_engines", "Liczba silników", "", 0, 8, "Napęd", integer=True),
    _number("p_kw", "Łączna moc silników", "kW", 0.001, 200_000, "Napęd"),
    _number("t_kn", "Łączny ciąg silników", "kN", 0.001, 10_000, "Napęd"),
    _number("v_cruise_kmh", "Prędkość przelotowa", "km/h", 1, 2_000, "Osiągi"),
    _number("cruise_mach", "Liczba Macha przelotu", "Ma", 0.001, 2, "Osiągi"),
    _number("v_max", "Prędkość maksymalna", "km/h", 1, 2_000, "Osiągi"),
    _number("mmo", "Graniczna liczba Macha", "Ma", 0.001, 2, "Osiągi"),
    _number("range_km", "Zasięg katalogowy", "km", 1, 50_000, "Osiągi"),
    _number("climb_rate_ms", "Prędkość wznoszenia", "m/s", 0.001, 150, "Osiągi"),
    _number("ld_max", "Doskonałość maksymalna", "", 1, 200, "Osiągi"),
    _number("w_z_min_ms", "Minimalne opadanie", "m/s", 0.001, 50, "Osiągi"),
    _number("takeoff_m", "Droga startu ze źródła", "m", 0, 20_000, "Start i lądowanie"),
    _choice("takeoff_basis", "Podstawa pomiaru startu", "Start i lądowanie"),
    _number("landing_m", "Droga lądowania ze źródła", "m", 0, 20_000, "Start i lądowanie"),
    _choice("landing_basis", "Podstawa pomiaru lądowania", "Start i lądowanie"),
    _number("v_h", "Współczynnik usterzenia poziomego V_H", "", 0.001, 2, "Sterowanie"),
    _number("aileron_span_fraction", "Udział rozpiętości lotek", "", 0.001, 1, "Sterowanie"),
    _number("aileron_chord_ratio", "Względna cięciwa lotki", "", 0.001, 1, "Sterowanie"),
    _number("elevator_chord_ratio", "Względna cięciwa steru wysokości", "", 0.001, 1, "Sterowanie"),
    _number("rudder_chord_ratio", "Względna cięciwa steru kierunku", "", 0.001, 1, "Sterowanie"),
    _number("dihedral_deg", "Kąt wzniosu skrzydła", "°", -15, 20, "Geometria"),
]
_FIELD_BY_KEY = {field["key"]: field for field in EDITABLE_FIELDS}
_FULL_DISTANCE_BASES = {"15m", "50ft", "field_length"}


def validate_aircraft_override(base_record: dict, changes: dict, source: str) -> dict:
    """Return a normalized correction for an existing reference aircraft."""
    if not isinstance(base_record, dict) or not isinstance(base_record.get("id"), str):
        raise ValueError("Poprawka wymaga istniejącego rekordu samolotu.")
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Podaj co najmniej jeden zmieniany parametr samolotu.")
    if not isinstance(source, str) or not 5 <= len(source.strip()) <= 2000:
        raise ValueError("Podaj źródło poprawki (5–2000 znaków): dokument, strona lub URL i warunki pomiaru.")

    clean = {}
    for key, value in changes.items():
        spec = _FIELD_BY_KEY.get(key)
        if spec is None:
            raise ValueError(f"Nie można edytować pola {key}; pochodne i identyfikatory są wyliczane lub stałe.")
        if value is None or (spec["type"] == "select" and value == ""):
            if not spec["nullable"]:
                raise ValueError(f"Pole {key} jest wymagane i nie może być puste.")
            clean[key] = None
            continue
        if spec["type"] == "select":
            if not isinstance(value, str) or value not in {item["value"] for item in spec["options"]}:
                raise ValueError(f"Pole {key}: wybierz poprawną podstawę pomiaru.")
            clean[key] = value
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Pole {key}: podaj skończoną liczbę lub wyczyść pole.")
        if not spec["min"] <= value <= spec["max"]:
            raise ValueError(f"Pole {key}: wymagany zakres {spec['min']}–{spec['max']} {spec['unit']}.")
        if spec["type"] == "integer" and not float(value).is_integer():
            raise ValueError(f"Pole {key}: wymagana liczba całkowita.")
        clean[key] = int(value) if spec["type"] == "integer" else float(value)

    effective = {**base_record, **clean}
    if effective.get("me") is not None and effective["me"] >= effective["m0"]:
        raise ValueError("Masa pusta OEW musi być mniejsza od MTOW.")
    engine = effective.get("engine_type")
    if engine == "jet" and effective.get("p_kw") is not None:
        raise ValueError("Odrzutowiec ma ciąg w kN; nie wpisuj mocy śmigłowej w kW.")
    if engine == "prop" and effective.get("t_kn") is not None:
        raise ValueError("Samolot śmigłowy ma moc w kW; nie wpisuj ciągu odrzutowego w kN.")
    if engine == "none" and any(effective.get(key) is not None for key in ("p_kw", "t_kn")):
        raise ValueError("Konstrukcja bez napędu nie może mieć mocy ani ciągu.")
    engines = effective.get("n_engines")
    if engines is not None and ((engine == "none" and engines != 0) or
                                (engine in ("prop", "jet") and engines == 0)):
        raise ValueError("Liczba silników jest niespójna z rodzajem napędu.")
    for distance in ("takeoff", "landing"):
        value_key, basis_key = f"{distance}_m", f"{distance}_basis"
        value, basis = effective.get(value_key), effective.get(basis_key)
        if value_key in clean and value is not None and basis_key not in clean:
            raise ValueError(f"Zmieniając {value_key}, podaj także {basis_key}; rozbieg i długość całkowita to różne dane.")
        if basis_key in clean and basis is not None and value is None:
            raise ValueError(f"Pole {basis_key} wymaga zmierzonej odległości {value_key}.")
        if (value_key in clean or basis_key in clean) and basis in _FULL_DISTANCE_BASES and value == 0:
            raise ValueError(f"Pełna odległość {value_key} musi być dodatnia.")
    return {"id": base_record["id"], "changes": clean, "source": source.strip()}


def apply_aircraft_override(base_record: dict, override: dict | None) -> dict:
    """Apply a correction to raw data and recompute all dependent metrics."""
    from calculations.trends import derived

    if not override:
        return derived(base_record)
    if not isinstance(override, dict) or override.get("id") != base_record.get("id"):
        raise ValueError("Identyfikator poprawki nie zgadza się z samolotem.")
    clean = validate_aircraft_override(base_record, override.get("changes"), override.get("source"))
    row = {**base_record, **clean["changes"]}
    original_source = base_record.get("source_references") or ""
    row["source_references"] = f"{original_source}; Poprawka użytkownika: {clean['source']}".lstrip("; ")
    row = derived(row)
    row["correction_fields"] = list(clean["changes"])
    row["correction_source"] = clean["source"]
    return row


def read_aircraft_corrections() -> dict:
    """Read the local correction file without touching the upstream snapshots."""
    with _LOCK:
        if not CORRECTIONS_PATH.exists():
            return {}
        try:
            content = json.loads(CORRECTIONS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("Nie można odczytać lokalnych poprawek bazy samolotów.") from error
        if not isinstance(content, dict) or content.get("schema") != 1 or not isinstance(content.get("corrections"), dict):
            raise ValueError("Nieprawidłowy format lokalnych poprawek bazy samolotów.")
        return content["corrections"]


def _write_aircraft_corrections(corrections: dict) -> None:
    CORRECTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        descriptor, temporary = tempfile.mkstemp(prefix=".aircraft-corrections-", suffix=".json",
                                               dir=CORRECTIONS_PATH.parent)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump({"schema": 1, "corrections": corrections}, stream, ensure_ascii=False,
                      indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, CORRECTIONS_PATH)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)


def save_aircraft_correction(correction: dict) -> None:
    """Atomically replace one aircraft correction, keeping all other edits."""
    with _LOCK:
        corrections = read_aircraft_corrections()
        corrections[correction["id"]] = correction
        _write_aircraft_corrections(corrections)


def delete_aircraft_correction(aircraft_id: str) -> None:
    with _LOCK:
        corrections = read_aircraft_corrections()
        if aircraft_id in corrections:
            del corrections[aircraft_id]
            _write_aircraft_corrections(corrections)
