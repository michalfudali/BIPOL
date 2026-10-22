"""
Główny moduł integrujący obliczenia wstępnego projektowania samolotu BIPOL I
"""
from calculations.atmosphere import G0
from calculations.mass import calculate_mass_sizing
from calculations.sizing import calculate_matching_chart
from calculations.geometry import calculate_geometry
from calculations.aerodynamics import calculate_aerodynamics
from calculations.performance import calculate_performance
from calculations.envelope import calculate_vn_envelope
from calculations.balance import calculate_balance_and_stability
from calculations.bipol_projects import calculate_all_bipol_projects
from calculations.presets import AIRCRAFT_PRESETS
from calculations.polish_law import normalize_occupants, check_compliance
from calculations.validation import validate_parameters
from calculations.glide import calculate_glide_polar
from calculations.runway import refine_takeoff_sizing
from calculations.instructor import review_coursework
from calculations.official_topics import validate_topic_geometry
from calculations.constraints import resolve_and_lock_parameters, finalize_parameter_states, get_initial_constraint_suggestions, WING_PLANFORMS

def run_bipol_project(params: dict):
    """
    Wykonuje pełny ciąg obliczeniowy projektu BIPOL I (etapy P1 - P6).
    """
    # Normalizacja domeny: napęd odrzutowy nie występuje w konfiguracji ciągnącej w nosie kadłuba (GA tractor)
    params = validate_parameters(params)
    params, law_corrections = normalize_occupants(params)
    params["_law_corrections"] = law_corrections
    params, param_states, constraint_warnings = resolve_and_lock_parameters(params, params.get("locked_params", []))
    if params.get("engine_type") == "jet" and params.get("engine_location") in ("nose", "retractable", "none"):
        params["engine_location"] = "wing" if params.get("aircraft_type") == "jet_transport" else "rear"

    # Etap P1 i P2: Bilans masowy (szacowanie MTOW)
    mass_res = calculate_mass_sizing(params)
    m0 = mass_res["m0"]

    # Kategoria operacji UAS zależy od ryzyka operacji, a nie od progu masy 600 kg.
    
    # Etap P2: Dobór obciążenia powierzchni skrzydła i ciągu/mocy (Matching Chart)
    sizing_res = calculate_matching_chart(params, m0=m0)
    ws = sizing_res["design_point"]["ws"]
    
    # Etap P3: Wymiarowanie zespołów (skrzydło, kadłub, usterzenia, Schrenk)
    geom_res = calculate_geometry(m0, ws, params)
    validate_topic_geometry(params, geom_res)


    # Etap P4: Charakterystyki aerodynamiczne (biegunowe, doskonałość)
    aero_res = calculate_aerodynamics(geom_res, params, m0=m0)
    
    refine_takeoff_sizing(sizing_res, geom_res, aero_res, params, m0)
    finalize_parameter_states(params, param_states, mass_res, sizing_res, geom_res)

    # Etap P5: Osiągi samolotu (prędkości, wznoszenie, pułap, start, lądowanie)
    perf_res = calculate_performance(m0, geom_res, aero_res, sizing_res, params)
    perf_res["glide"] = calculate_glide_polar(m0, geom_res, aero_res, params["cruise_altitude_m"], params=params)
    
    # Etap P6: Obwiednia obciążeń dopuszczalnych V-n
    envelope_res = calculate_vn_envelope(m0, geom_res, aero_res, perf_res, params)
    
    # Etap P6: Wyważenie i stateczność statyczna
    balance_res = calculate_balance_and_stability(mass_res, geom_res, aero_res, params)
    
    # Ocena zgodności z wymaganiami taktyczno-technicznymi
    checks = []
    # 1. Zgodność z prędkością przeciągnięcia
    req_v_stall = float(params.get("v_stall_kmh", 100.0))
    act_v_stall = perf_res["speeds"]["vs_lnd_kmh"]
    checks.append({
        "parameter": "Prędkość przeciągnięcia z klapami Vs0",
        "required": f"≤ {req_v_stall} km/h",
        "actual": f"{act_v_stall} km/h",
        "passed": act_v_stall <= req_v_stall + 1.0,
        "note": "Warunek zdatności do lądowania na krótkich pasach"
    })
    
    # 2. Zgodność z prędkością wznoszenia
    req_climb = float(params.get("climb_rate_ms", 4.0))
    act_climb = perf_res["climb"]["wy_max_ms"]
    checks.append({
        "parameter": "Maksymalna prędkość wznoszenia wy_max",
        "required": f"≥ {req_climb} m/s",
        "actual": f"{act_climb} m/s",
        "passed": act_climb >= req_climb - 0.1,
        "note": "Bezpieczeństwo przy odejściu na drugi krąg i przewyższenie przeszkód"
    })
    
    # Full distances are not interchangeable with ground roll.
    if params['engine_type'] != 'none':
        req_to = params.get('takeoff_distance_m', 0)
        act_to = perf_res['takeoff']['distance_to_15m']
        checks.append(dict(parameter='Całkowita długość startu do 15 m',
            required=f'≤ {req_to:g} m' if req_to else 'Podaj założenie',
            actual=f'{act_to:g} m' if act_to is not None else 'Start nieosiągalny',
            passed=bool(req_to and act_to is not None and act_to <= req_to),
            note='Rozbieg + odcinek powietrzny do wysokości 15 m.'))
    req_lnd = params.get('landing_distance_m', 0)
    act_lnd = perf_res['landing']['distance_from_15m']
    checks.append(dict(parameter='Całkowita długość lądowania znad 15 m',
        required=f'≤ {req_lnd:g} m' if req_lnd else 'Podaj założenie', actual=f'{act_lnd:g} m',
        passed=bool(req_lnd and act_lnd <= req_lnd), note='Podejście + wyrównanie + dobieg do zatrzymania.'))

    # 4. Zapas stateczności statycznej w skrajnym tylnym położeniu ŚM
    act_sm = balance_res["stability"]["static_margin_aft_pct"]
    checks.append({
        "parameter": "Zapas stateczności statycznej Kn (tylne ŚM)",
        "required": "≥ 5.0% ŚDA",
        "actual": f"{act_sm}% ŚDA",
        "passed": act_sm >= 5.0,
        "note": "Kryterium stateczności podłużnej bez autopilota"
    })

    # Obliczenia dedykowane dla projektów semestralnych BIPOL I (P1 do P6)
    bipol_projects_res = calculate_all_bipol_projects(
        mass_res, sizing_res, geom_res, aero_res, perf_res, envelope_res, balance_res, params
    )

    # Zgodność z klasyfikacją statków powietrznych (Dz. U. 2025 poz. 1137, Tabele nr 1–3)
    law_res = check_compliance(params, mass_res, geom_res, perf_res)
    for c in law_res["checks"]:
        checks.append({
            "parameter": f"[{law_res['code']}] {c['name']}",
            "required": c["limit"],
            "actual": c["value"],
            "passed": c["ok"],
            "severity": c["severity"],
            "note": c["source"] + (" (zalecenie)" if c["severity"] == "warning" else "")
        })

    result = {
        "status": "success",
        "params": params,
        "mass": mass_res,
        "sizing": sizing_res,
        "geometry": geom_res,
        "aerodynamics": aero_res,
        "performance": perf_res,
        "envelope": envelope_res,
        "balance": balance_res,
        "compliance_checks": checks,
        "easa_compliance": law_res,
        "polish_law": law_res,
        "bipol_projects": bipol_projects_res,
        "constraints": {
            "parameter_states": param_states,
            "locked_keys": params.get("locked_params", []),
            "initial_suggestions": get_initial_constraint_suggestions(params.get("category", "cs23_level2"), params.get("aircraft_type", "piston_ga")),
            "available_planforms": WING_PLANFORMS,
            "warnings": constraint_warnings
        }
    }

    result["instructor_review"] = review_coursework(result)
    return result
