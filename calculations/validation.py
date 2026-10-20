"""Wspólne wartości wejściowe i walidacja przed uruchomieniem obliczeń."""
import math

NUMERIC_LIMITS = {
    "n_pax": (0, 1000), "n_crew": (0, 20), "m_pax": (0, 500),
    "m_bag": (0, 500), "m_cargo": (0, 500000), "m_crew_person": (0, 500),
    "range_km": (0, 30000), "cruise_altitude_m": (0, 20000),
    "cruise_speed_kmh": (1, 1200), "v_stall_kmh": (1, 400),
    "takeoff_run_m": (1, 10000), "climb_rate_ms": (0, 100),
    "aspect_ratio": (2, 35), "taper_ratio": (0.1, 1),
    "sweep_quarter_deg": (-30, 60), "dihedral_deg": (-15, 20),
    "cx0": (0.001, 0.3), "oswald_e": (0.1, 1),
    "cz_max_clean": (0.1, 5), "cz_max_to": (0.1, 6), "cz_max_lnd": (0.1, 7),
    "prop_efficiency": (0.1, 1), "prop_eff_to": (0.1, 1),
    "ld_cruise": (1, 100), "sfc": (0.01, 1000), "loiter_time_min": (0, 1440),
    "wingspan_m": (0, 100), "span_limit": (0, 100),
    "v_h": (0.05, 2), "v_v": (0.005, 0.3), "ar_h": (1, 12), "ar_v": (0.5, 6),
    "tc_ratio": (0.04, 0.3), "delta_cx0_flaps_to": (0, 0.5),
    "delta_cx0_flaps_lnd": (0, 0.5), "delta_cx0_gear": (0, 0.5),
    "vmo_kcas": (1, 1000), "mmo": (0.01, 2),
}

DEFAULTS = {
    "aircraft_type": "piston_ga", "engine_type": "prop", "engine_location": "nose",
    "category": "cs23_level2", "n_pax": 4, "n_crew": 1, "m_pax": 80,
    "m_bag": 0, "m_cargo": 0, "m_crew_person": 90,
    "range_km": 1200, "cruise_altitude_m": 3000, "cruise_speed_kmh": 250,
    "v_stall_kmh": 100, "takeoff_run_m": 500, "climb_rate_ms": 4,
    "aspect_ratio": 8, "taper_ratio": 0.55, "oswald_e": 0.8, "cx0": 0.025,
    "cz_max_clean": 1.45, "cz_max_to": 1.8, "cz_max_lnd": 2.2,
    "prop_efficiency": 0.82, "prop_eff_to": 0.65,
}


def validate_parameters(data):
    if not isinstance(data, dict):
        raise ValueError("Parametry projektu muszą być obiektem JSON.")
    p = {**DEFAULTS, **data}
    if data.get("aircraft_type") == "uav" and "m_cargo" not in data:
        p["m_cargo"] = 80
    if data.get("aircraft_type") in ("jet_business", "jet_transport") and "engine_type" not in data:
        p["engine_type"] = "jet"
    for key, (lower, upper) in NUMERIC_LIMITS.items():
        if key not in p:
            continue
        value = p[key]
        try:
            number = float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Pole {key}: podaj liczbę.") from None
        if isinstance(value, bool) or not math.isfinite(number) or not lower <= number <= upper:
            raise ValueError(f"Pole {key}: wymagana skończona liczba od {lower} do {upper}.")
        if key in ("n_pax", "n_crew") and not number.is_integer():
            raise ValueError(f"Pole {key}: liczba osób musi być całkowita.")
        p[key] = number
    if p["aircraft_type"] not in ("piston_ga", "turboprop_regional", "jet_business", "jet_transport", "uav"):
        raise ValueError("Nieznana klasa konstrukcyjna samolotu.")
    if p["engine_type"] not in ("prop", "jet"):
        raise ValueError("Nieznany rodzaj napędu.")
    if p["v_stall_kmh"] >= p["cruise_speed_kmh"]:
        raise ValueError("Prędkość przelotowa musi być większa od prędkości przeciągnięcia VS0.")
    if p["cz_max_to"] < p["cz_max_clean"] or p["cz_max_lnd"] < p["cz_max_to"]:
        raise ValueError("Wymagane Cz max: konfiguracja gładka ≤ startowa ≤ lądowania.")
    return p
