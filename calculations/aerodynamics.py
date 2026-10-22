# -*- coding: utf-8 -*-
"""
Moduł charakterystyk aerodynamicznych samolotu (BIPOL I).
Oparty w pierwszej kolejności na oficjalnej metodyce MEiL PW:
dr inż. Zbigniew Paturski — "Przewodnik po projektach z Mechaniki Lotu"
(Projekt nr 2: Płat, Projekt nr 3: Samolot).

Wyznacza:
- Geometrię i charakterystyki płata (ca, xN, Vs1, Re1, Glauert tau, delta, a_w)
- Opory komponentów samolotu (wzory 3.1 - 3.10, Tabela 3.1)
- Biegunową analityczną Cx = Cx0 + Cz^2 / (pi * Lambda * e) (wzór 3.11)
- Porównanie z zestawieniem statystycznym dr. Paturskiego (Tabele A, B, C)
- Punkty optymalne K_max, K_econ, E_max oraz konfiguracje ze skrzydełkami, klapami i podwoziem
"""
import math
from calculations.atmosphere import isa_atmosphere, G0, RHO0
from calculations.paturski_ml import paturski_project_2_wing, paturski_project_3_aircraft_aero


def calculate_aerodynamics(geom: dict, params: dict, m0: float = None):
    """
    Główna funkcja obliczeniowa aerodynamiki — uruchamia w pierwszej kolejności
    metodykę Paturskiego (Projekt nr 2 i Projekt nr 3).
    """
    wing = geom["wing"]
    S = float(wing["S"])
    AR = float(wing["AR"])
    mac = float(wing["mac"])
    sweep_deg = float(wing.get("sweep_deg", 0.0))
    tc_wing = float(wing.get("tc_ratio", 0.12))
    sweep_rad = math.radians(sweep_deg)

    # 1. METODYKA PATURSKIEGO JAKO PIERWSZA I NADRZĘDNA
    p2 = paturski_project_2_wing(geom, params, m0=m0)
    p3 = paturski_project_3_aircraft_aero(geom, params, m0=m0, p2_wing=p2)

    fit = p3["analytical_polar_fit"]
    cx0_clean = fit["cx0_approx"]
    oswald_e = fit["oswald_e_approx"]
    lambda_e = fit["lambda_e_approx"]
    k_clean = fit.get("k_ind_approx") or fit.get("slope_d_cx_d_cz2") or (1.0 / (math.pi * lambda_e))

    a_w_paturski_rad = p2["a_wing_paturski_rad"]
    a_w_paturski_deg = p2["a_wing_paturski_deg"]
    tau_glauert = p2["tau_glauert"]
    delta_glauert = p2["delta_glauert"]
    a_w_rad = a_w_paturski_rad
    a_w_deg = a_w_paturski_deg

    cz_max_clean = float(p2.get("cz_max_clean") or params.get("cz_max_clean", 1.40))

    # 2. Mechanizacja skrzydła (klapy i sloty) wg założeń BIPOL I / Paturskiego
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")
    wing_config = params.get("wing_config", "low")

    flap_deltas = {
        "plain": {"delta_cz_to": 0.30, "delta_cz_lnd": 0.60, "delta_cx0_to": 0.010, "delta_cx0_lnd": 0.035, "e_to": 0.74, "e_lnd": 0.68},
        "single_slotted": {"delta_cz_to": 0.40, "delta_cz_lnd": 0.85, "delta_cx0_to": 0.012, "delta_cx0_lnd": 0.045, "e_to": 0.76, "e_lnd": 0.70},
        "fowler": {"delta_cz_to": 0.55, "delta_cz_lnd": 1.15, "delta_cx0_to": 0.015, "delta_cx0_lnd": 0.055, "e_to": 0.78, "e_lnd": 0.72},
        "double_slotted": {"delta_cz_to": 0.50, "delta_cz_lnd": 1.05, "delta_cx0_to": 0.018, "delta_cx0_lnd": 0.065, "e_to": 0.75, "e_lnd": 0.68},
        "junkers": {"delta_cz_to": 0.45, "delta_cz_lnd": 0.90, "delta_cx0_to": 0.020, "delta_cx0_lnd": 0.060, "e_to": 0.72, "e_lnd": 0.66},
        "none": {"delta_cz_to": 0.00, "delta_cz_lnd": 0.00, "delta_cx0_to": 0.000, "delta_cx0_lnd": 0.000, "e_to": oswald_e, "e_lnd": oswald_e}
    }
    fd = flap_deltas.get(flap_type, flap_deltas["single_slotted"])

    delta_cz_slat = 0.0
    delta_cx_slat = 0.0
    if slat_type in ("auto_slat", "slats_auto"):
        delta_cz_slat = 0.35
        delta_cx_slat = 0.008
    elif slat_type == "fixed_slot":
        delta_cz_slat = 0.30
        delta_cx_slat = 0.012

    cz_max_to = round(cz_max_clean + fd["delta_cz_to"] + delta_cz_slat * 0.5, 2)
    cz_max_lnd = round(cz_max_clean + fd["delta_cz_lnd"] + delta_cz_slat, 2)

    delta_cx0_to = fd["delta_cx0_to"] + delta_cx_slat * 0.5
    delta_cx0_lnd = fd["delta_cx0_lnd"] + delta_cx_slat

    ac_type = params.get("aircraft_type", "piston_ga")
    is_retractable = bool(params.get("retractable_gear", True if ac_type not in ["piston_ga", "ultralight", "glider"] else False))
    delta_cx0_gear = 0.018 if (is_retractable and ac_type != "glider") else 0.000

    e_to = min(oswald_e, fd["e_to"])
    e_lnd = min(oswald_e, fd["e_lnd"])
    k_to = 1.0 / (math.pi * AR * e_to)
    k_lnd = 1.0 / (math.pi * AR * e_lnd)

    cx0_to = cx0_clean + delta_cx0_to
    cx0_lnd = cx0_clean + delta_cx0_lnd + delta_cx0_gear

    # 3. Punkty optymalne biegunowej Paturskiego (wzory 20, 27-28 i Projekt nr 4 wzory 4.8-4.12)
    cz_opt = math.sqrt(cx0_clean / k_clean)
    cx_opt = 2.0 * cx0_clean
    k_max = cz_opt / cx_opt

    cz_econ = math.sqrt(3.0 * cx0_clean / k_clean)
    cx_econ = 4.0 * cx0_clean
    k_econ = cz_econ / cx_econ

    cz_jet_range = math.sqrt(cx0_clean / (3.0 * k_clean))
    cx_jet_range = (4.0 / 3.0) * cx0_clean
    k_jet_range = cz_jet_range / cx_jet_range
    e_energy_max = (cz_econ ** 3) / (cx_econ ** 2)

    # 4. Zestawienie składowych oporu Component Drag Buildup z Tabeli 3.1 dr. Paturskiego
    # Mapujemy wiersze Tabeli 3.1 na format komponentów
    h_cr = float(params.get("cruise_altitude_m", 2500.0))
    v_cr_ms = max(20.0, float(params.get("cruise_speed_kmh", 220.0)) / 3.6)
    isa_cr = isa_atmosphere(h_cr)
    rho_cr = isa_cr["rho"]
    mu_cr = 1.789e-5 * math.pow(isa_cr["T"] / 288.15, 1.5) * ((288.15 + 110.4) / (isa_cr["T"] + 110.4))

    re_wing = round((rho_cr * v_cr_ms * mac) / mu_cr)
    cf_wing = round(p2["cx_min_2_corrected"], 5)
    ff_wing = round(1.0 + 2.0 * tc_wing + 60.0 * (tc_wing ** 4), 3)

    l_fus = float(geom["fuselage"]["length"])
    re_fus = round((rho_cr * v_cr_ms * l_fus) / mu_cr)
    f_fus = max(3.0, float(geom["fuselage"]["fineness"]))
    ff_fus = round(1.0 + 60.0 / (f_fus ** 3) + f_fus / 400.0, 3)

    swet_wing = float(geom["wing"].get("S_wet", 2.0 * S * 0.88))
    swet_fus = float(geom["fuselage"].get("S_wet", math.pi * geom["fuselage"]["diameter"] * l_fus * 0.78))
    swet_ht = float(geom["horizontal_tail"].get("S_wet", 2.0 * geom["horizontal_tail"]["S_h"] * 1.02))
    swet_vt = float(geom["vertical_tail"].get("S_wet", 2.0 * geom["vertical_tail"]["S_v"] * 1.02))

    component_drag_buildup = []
    for row in p3["table_3_1_parasite"]:
        comp_name = row["component"]
        cx0_i = row.get("cx_delta", round(row.get("cx_s_m2", 0.0) / max(0.1, S), 4))
        share = row.get("share_pct", round((cx0_i / max(1e-4, cx0_clean)) * 100.0, 1))

        if "Płat" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = re_wing, cf_wing, ff_wing, 1.0, swet_wing
        elif "Kadłub" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = re_fus, 0.0035, ff_fus, 1.0, swet_fus
        elif "poziome" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = round(re_wing * 0.6), 0.0040, 1.15, 1.04, swet_ht
        elif "pionowe" in comp_name:
            c_re, c_cf, c_ff, c_q, c_swet = round(re_wing * 0.5), 0.0040, 1.15, 1.04, swet_vt
        else:
            c_re, c_cf, c_ff, c_q, c_swet = 0, 0.0, 1.0, 1.0, round(row.get("s_j_m2", 0.0), 2)

        component_drag_buildup.append({
            "component": comp_name,
            "re": c_re,
            "cf": c_cf,
            "ff": c_ff,
            "q": c_q,
            "swet_m2": round(c_swet, 2),
            "cx0_i": round(cx0_i, 4),
            "share_pct": round(share, 1),
            "source": row.get("source", "Paturski Tabela 3.1")
        })

    # 5. Generowanie punktów biegunowej (Tabela 2.2 Paturskiego z rozszerzeniem na klapy)
    polar_points = []
    n_pts = 40
    for i in range(n_pts + 1):
        cz = -0.2 + i * (cz_max_lnd - (-0.2)) / n_pts

        # Konfiguracja gładka
        if cz <= cz_max_clean:
            cx_c = cx0_clean + k_clean * (cz ** 2)
            ld_c = cz / cx_c if abs(cx_c) > 1e-4 else 0.0
            e_en_c = ((cz ** 3) / (cx_c ** 2)) if (abs(cx_c) > 1e-4 and cz > 0) else 0.0
        else:
            cx_c = None
            ld_c = None
            e_en_c = None

        # Konfiguracja startowa
        if cz <= cz_max_to:
            cx_t = cx0_to + k_to * (cz ** 2)
            ld_t = cz / cx_t if abs(cx_t) > 1e-4 else 0.0
        else:
            cx_t = None
            ld_t = None

        # Konfiguracja lądowania
        cx_l = cx0_lnd + k_lnd * (cz ** 2)
        ld_l = cz / cx_l if abs(cx_l) > 1e-4 else 0.0

        polar_points.append({
            "cz": round(cz, 3),
            "cx_clean": round(cx_c, 4) if cx_c is not None else None,
            "ld_clean": round(ld_c, 2) if ld_c is not None else None,
            "e_energy_clean": round(e_en_c, 1) if e_en_c is not None else None,
            "cx_to": round(cx_t, 4) if cx_t is not None else None,
            "cx_lnd": round(cx_l, 4) if cx_l is not None else None
        })

    return {
        "k_clean": round(k_clean, 5),
        "cx0_clean": round(cx0_clean, 4),
        "cx0_buildup_theoretical": round(cx0_clean, 4),
        "component_drag_buildup": component_drag_buildup,
        "oswald_e": round(oswald_e, 3),
        "lambda_e": round(lambda_e, 2),
        "cx0_to": round(cx0_to, 4),
        "cx0_lnd": round(cx0_lnd, 4),
        "k_to": round(k_to, 5),
        "k_lnd": round(k_lnd, 5),
        "k_max": round(k_max, 2),
        "k_econ": round(k_econ, 2),
        "e_energy_max": round(e_energy_max, 1),
        "k_jet_range": round(k_jet_range, 2),
        "cz_opt": round(cz_opt, 3),
        "cx_opt": round(cx_opt, 4),
        "cz_econ": round(cz_econ, 3),
        "cx_econ": round(cx_econ, 4),
        "cz_jet_range": round(cz_jet_range, 3),
        "cx_jet_range": round(cx_jet_range, 4),
        "a_w_rad": round(a_w_rad, 4),
        "a_w_deg": round(a_w_deg, 4),
        "a_w_paturski_rad": round(a_w_paturski_rad, 4),
        "a_w_paturski_deg": round(a_w_paturski_deg, 4),
        "tau_glauert": round(tau_glauert, 4),
        "delta_glauert": round(delta_glauert, 4),
        "cz_max_clean": cz_max_clean,
        "cz_max_to": cz_max_to,
        "cz_max_lnd": cz_max_lnd,
        "polar_points": polar_points,
        "control_surfaces": geom.get("control_surfaces", {}),
        "paturski_p2": p2,
        "paturski_p3": p3,
        "table_2_2_complete": p3.get("table_2_2_complete", []),
        "statistical_comparison": p3.get("statistical_benchmarks_abc", {})
    }
