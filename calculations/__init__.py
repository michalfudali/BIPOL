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

def run_bipol_project(params: dict):
    """
    Wykonuje pełny ciąg obliczeniowy projektu BIPOL I (etapy P1 - P6).
    """
    # Normalizacja domeny: napęd odrzutowy nie występuje w konfiguracji ciągnącej w nosie kadłuba (GA tractor)
    params = validate_parameters(params)
    if params.get("engine_type") == "jet" and params.get("engine_location") == "nose":
        params["engine_location"] = "wing" if params.get("aircraft_type") == "jet_transport" else "rear"

    # Klasyfikacja wg polskiego prawa (Dz. U. 2025 poz. 1137): spójność klasy UM/UL/A z liczbą osób na pokładzie
    params, law_corrections = normalize_occupants(params)
    params["_law_corrections"] = law_corrections

    # Etap P1 i P2: Bilans masowy (szacowanie MTOW)
    mass_res = calculate_mass_sizing(params)
    m0 = mass_res["m0"]

    # Kategoria operacji UAS zależy od ryzyka operacji, a nie od progu masy 600 kg.
    
    # Etap P2: Dobór obciążenia powierzchni skrzydła i ciągu/mocy (Matching Chart)
    sizing_res = calculate_matching_chart(params, m0=m0)
    ws = sizing_res["design_point"]["ws"]
    
    # Etap P3: Wymiarowanie zespołów (skrzydło, kadłub, usterzenia, Schrenk)
    geom_res = calculate_geometry(m0, ws, params)

    # Narzucona rozpiętość zmienia wydłużenie. Uzgodnij bilans masowy i napęd
    # z tą samą geometrią, z której następnie korzystają aerodynamika i osiągi.
    if params.get("wingspan_m") or params.get("span_limit"):
        for _ in range(80):
            span = params.get("wingspan_m") or params.get("span_limit")
            actual_ar = float(span) ** 2 * ws / (m0 * G0)
            if not 2 <= actual_ar <= 35:
                raise ValueError("Narzucona rozpiętość daje wydłużenie poza zakresem modelu 2–35. Zmień rozpiętość lub wymaganie VS0.")
            if abs(actual_ar - params["aspect_ratio"]) < 0.001:
                break
            params["aspect_ratio"] = actual_ar
            mass_res = calculate_mass_sizing(params)
            m0 = mass_res["m0"]
            sizing_res = calculate_matching_chart(params, m0=m0)
            ws = sizing_res["design_point"]["ws"]
            geom_res = calculate_geometry(m0, ws, params)
        else:
            raise ValueError("Nie uzyskano zgodności masy i narzuconej rozpiętości.")
    
    # Etap P4: Charakterystyki aerodynamiczne (biegunowe, doskonałość)
    aero_res = calculate_aerodynamics(geom_res, params)
    
    # Etap P5: Osiągi samolotu (prędkości, wznoszenie, pułap, start, lądowanie)
    perf_res = calculate_performance(m0, geom_res, aero_res, sizing_res, params)
    perf_res["glide"] = calculate_glide_polar(m0, geom_res, aero_res, params["cruise_altitude_m"])
    
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
    
    # 3. Zgodność z drogą rozbiegu
    req_to = float(params.get("takeoff_run_m", 500.0))
    act_to = perf_res["takeoff"]["ground_roll_m"]
    checks.append({
        "parameter": "Długość rozbiegu Sto",
        "required": f"≤ {req_to} m",
        "actual": f"{act_to} m",
        "passed": act_to <= req_to * 1.05,
        "note": "Wymóg operacyjny dla założonej klasy lotnisk"
    })
    
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

    return {
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
        "bipol_projects": bipol_projects_res
    }
