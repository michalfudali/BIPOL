"""
Moduł charakterystyk aerodynamicznych samolotu (BIPOL I)
Wyznaczanie biegunowych aerodynamicznych w konfiguracji gładkiej, startowej i do lądowania,
metody sumowania oporów komponentów (Component Buildup Method: Cf * FF * Q * Swet/S wg Raymera/Torenbeeka),
doskonałości aerodynamicznej K(Cz) oraz parametrów optymalnych.
"""
import math
from calculations.atmosphere import isa_atmosphere

def calculate_aerodynamics(geom: dict, params: dict):
    """
    Parametry:
      - AR: wydłużenie skrzydła
      - oswald_e: współczynnik Oswalda dla konfiguracji gładkiej (np. 0.82)
      - cx0_clean: współczynnik oporu szkodliwego czystego płatowca (np. 0.024)
      - delta_cx0_flaps_to: przyrost oporu od klap startowych (np. 0.015)
      - delta_cx0_flaps_lnd: przyrost oporu od klap do lądowania (np. 0.055)
      - delta_cx0_gear: przyrost oporu od wypuszczonego podwozia (np. 0.020)
      - cz_max_clean: max Cz w konfiguracji gładkiej (np. 1.45)
      - cz_max_to: max Cz w konfiguracji startowej (np. 1.85)
      - cz_max_lnd: max Cz w konfiguracji do lądowania (np. 2.25)
    """
    S = float(geom["wing"]["S"])
    AR = float(geom["wing"]["AR"])
    mac = float(geom["wing"]["mac"])
    sweep_deg = float(geom["wing"].get("sweep_deg", 0.0))
    tc_wing = float(geom["wing"].get("tc_ratio", 0.12))
    e_clean = float(params.get("oswald_e", 0.82))
    cx0_base = float(params.get("cx0", 0.024))

    wing_config = params.get("wing_config", "low")
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")

    cx0_clean = cx0_base
    if wing_config == "braced_high":
        cx0_clean += 0.0020
    if flap_type == "junkers":
        cx0_clean += 0.0025
    if slat_type == "fixed_slot":
        cx0_clean += 0.0030

    # =========================================================================
    # METODA SUMOWANIA OPORÓW KOMPONENTÓW (COMPONENT BUILDUP - RAYMER / TORENBEEK)
    # Cx0_i = Cf_i * FF_i * Q_i * (Swet_i / S_ref)
    # =========================================================================
    h_cr = float(params.get("cruise_altitude_m", 2500.0))
    v_cr_ms = max(20.0, float(params.get("cruise_speed_kmh", 220.0)) / 3.6)
    isa_cr = isa_atmosphere(h_cr)
    rho_cr = isa_cr["rho"]
    T_cr = isa_cr["T"]
    a_cr = isa_cr["a"]
    mach_cr = v_cr_ms / a_cr
    # Lepkość dynamiczna powietrza wg wzoru Sutherlanda [Pa*s]
    mu_cr = 1.789e-5 * math.pow(T_cr / 288.15, 1.5) * ((288.15 + 110.4) / (T_cr + 110.4))
    k_rough = 1.0e-5  # Chropowatość ekwiwalentna powierzchni lakierowanej / duralowej [m]

    def calc_cf(length_m: float, k_lam: float):
        re_actual = max(1e5, (rho_cr * v_cr_ms * max(0.2, length_m)) / mu_cr)
        re_cutoff = 38.21 * math.pow(max(0.2, length_m) / k_rough, 1.053)
        re_eff = min(re_actual, re_cutoff)
        cf_lam = 1.328 / math.sqrt(re_actual)
        cf_turb = 0.455 / (math.pow(math.log10(re_eff), 2.58) * math.pow(1.0 + 0.144 * (mach_cr ** 2), 0.65))
        cf_total = k_lam * cf_lam + (1.0 - k_lam) * cf_turb
        return round(re_actual), round(cf_total, 5)

    # Współczynnik kształtu dla powierzchni nośnych (Raymer eq. 12.30 / Hoerner)
    sweep_rad = math.radians(sweep_deg)
    xc_m = 0.30  # Położenie max grubości profilu NACA 23012
    comp_corr = max(1.0, 1.34 * math.pow(max(0.18, mach_cr), 0.18) * math.pow(math.cos(sweep_rad), 0.28))
    ff_wing = (1.0 + (0.6 / xc_m) * tc_wing + 100.0 * (tc_wing ** 4)) * comp_corr
    tc_tail = 0.09
    ff_tail = (1.0 + (0.6 / 0.30) * tc_tail + 100.0 * (tc_tail ** 4)) * comp_corr

    # Współczynnik kształtu kadłuba (Raymer eq. 12.31: FF = 1 + 60/f^3 + f/400)
    f_fus = max(3.0, float(geom["fuselage"]["fineness"]))
    ff_fus = 1.0 + (60.0 / (f_fus ** 3)) + (f_fus / 400.0)

    # Powierzchnie omywane i obliczenia składowych
    swet_wing = float(geom["wing"].get("S_wet", 2.0 * S * 0.88))
    swet_fus = float(geom["fuselage"].get("S_wet", math.pi * geom["fuselage"]["diameter"] * geom["fuselage"]["length"] * 0.78))
    swet_ht = float(geom["horizontal_tail"].get("S_wet", 2.0 * geom["horizontal_tail"]["S_h"] * 1.02))
    swet_vt = float(geom["vertical_tail"].get("S_wet", 2.0 * geom["vertical_tail"]["S_v"] * 1.02))

    re_wing, cf_wing = calc_cf(mac, 0.25)
    re_fus, cf_fus = calc_cf(geom["fuselage"]["length"], 0.10)
    re_ht, cf_ht = calc_cf(geom["horizontal_tail"]["mac_h"], 0.20)
    re_vt, cf_vt = calc_cf(geom["vertical_tail"]["mac_v"], 0.20)

    q_wing = 1.00 if wing_config in ["high", "mid"] else (1.08 if wing_config == "braced_high" else 1.02)
    q_fus = 1.00
    q_tail = 1.04

    cx0_wing_raw = cf_wing * ff_wing * q_wing * (swet_wing / S)
    cx0_fus_raw = cf_fus * ff_fus * q_fus * (swet_fus / S)
    cx0_ht_raw = cf_ht * ff_tail * q_tail * (swet_ht / S)
    cx0_vt_raw = cf_vt * ff_tail * q_tail * (swet_vt / S)
    cx0_tail_raw = cx0_ht_raw + cx0_vt_raw

    ac_type = params.get("aircraft_type", "piston_ga")
    cx0_gear_misc_raw = 0.0045 if ac_type == "piston_ga" else 0.0020
    if wing_config == "braced_high":
        cx0_gear_misc_raw += 0.0020
    cx0_leak_raw = 0.06 * (cx0_wing_raw + cx0_fus_raw + cx0_tail_raw + cx0_gear_misc_raw)
    cx0_buildup_total = cx0_wing_raw + cx0_fus_raw + cx0_tail_raw + cx0_gear_misc_raw + cx0_leak_raw

    # Skalowanie składowych do docelowego cx0_clean przy zachowaniu fizycznych proporcji metody Component Buildup
    scale_f = cx0_clean / max(1e-4, cx0_buildup_total)
    component_drag_buildup = [
        {
            "component": "Płat nośny (tarcie + kształt FF)",
            "re": re_wing,
            "cf": cf_wing,
            "ff": round(ff_wing, 3),
            "q": q_wing,
            "swet_m2": round(swet_wing, 2),
            "cx0_i": round(cx0_wing_raw * scale_f, 4),
            "share_pct": round((cx0_wing_raw / cx0_buildup_total) * 100.0, 1)
        },
        {
            "component": "Kadłub (opływ + smukłość f=" + str(round(f_fus, 1)) + ")",
            "re": re_fus,
            "cf": cf_fus,
            "ff": round(ff_fus, 3),
            "q": q_fus,
            "swet_m2": round(swet_fus, 2),
            "cx0_i": round(cx0_fus_raw * scale_f, 4),
            "share_pct": round((cx0_fus_raw / cx0_buildup_total) * 100.0, 1)
        },
        {
            "component": "Usterzenie poziome i pionowe (UP + UV)",
            "re": re_ht,
            "cf": cf_ht,
            "ff": round(ff_tail, 3),
            "q": q_tail,
            "swet_m2": round(swet_ht + swet_vt, 2),
            "cx0_i": round(cx0_tail_raw * scale_f, 4),
            "share_pct": round((cx0_tail_raw / cx0_buildup_total) * 100.0, 1)
        },
        {
            "component": "Podwozie / Gondole / Zastrzały (Cx_misc)",
            "re": None,
            "cf": None,
            "ff": None,
            "q": 1.25,
            "swet_m2": None,
            "cx0_i": round(cx0_gear_misc_raw * scale_f, 4),
            "share_pct": round((cx0_gear_misc_raw / cx0_buildup_total) * 100.0, 1)
        },
        {
            "component": "Chłodnice, wloty i nieszczelności (L&P 6%)",
            "re": None,
            "cf": None,
            "ff": None,
            "q": 1.00,
            "swet_m2": None,
            "cx0_i": round(cx0_leak_raw * scale_f, 4),
            "share_pct": round((cx0_leak_raw / cx0_buildup_total) * 100.0, 1)
        }
    ]
    
    # Przyrosty dla konfiguracji startowej
    delta_cx0_to = float(params.get("delta_cx0_flaps_to", 0.015))
    e_to = e_clean * 0.94
    cz_max_to = float(params.get("cz_max_to", 1.85))
    
    # Przyrosty dla lądowania
    delta_cx0_lnd = float(params.get("delta_cx0_flaps_lnd", 0.050))
    delta_cx0_gear = float(params.get("delta_cx0_gear", 0.018))
    e_lnd = e_clean * 0.88
    cz_max_lnd = float(params.get("cz_max_lnd", 2.25))
    cz_max_clean = float(params.get("cz_max_clean", 1.45))
    
    # Współczynniki oporu indukowanego k = 1 / (pi * AR * e) (Wzór 6 BIPOL_1_wzory.pdf)
    k_clean = 1.0 / (math.pi * AR * e_clean)
    k_to = 1.0 / (math.pi * AR * e_to)
    k_lnd = 1.0 / (math.pi * AR * e_lnd)
    
    cx0_to = cx0_clean + delta_cx0_to
    cx0_lnd = cx0_clean + delta_cx0_lnd + delta_cx0_gear
    
    # 1. Punkt optymalny (K_max - max zasięg śmigłowych wg wzoru 7, 8 i 20 BIPOL_1_wzory.pdf)
    cz_opt = math.sqrt(cx0_clean / k_clean)
    cx_opt = 2.0 * cx0_clean
    k_max = cz_opt / cx_opt
    
    # 2. Punkt ekonomiczny (min moc wymagana / max długotrwałość śmigłowych / min opadanie)
    cz_econ = math.sqrt(3.0 * cx0_clean / k_clean)
    cx_econ = 4.0 * cx0_clean
    k_econ = cz_econ / cx_econ

    # 3. Punkt maksymalnego zasięgu odrzutowca: max(Cz^(1/2)/Cx) wg wzorów (27) i (28) BIPOL_1_wzory.pdf
    cz_jet_range = math.sqrt(cx0_clean / (3.0 * k_clean))
    cx_jet_range = (4.0 / 3.0) * cx0_clean
    k_jet_range = cz_jet_range / cx_jet_range

    # 4. Pochodna współczynnika siły nośnej skrzydła skończonego a_w = dCz/dalpha [1/rad] i [1/deg]
    # Wg wzoru Helmbolda-Diedericha (Danilecki wz. 2.13-2.14) oraz wzorów Glauerta-Paturskiego (2.14)-(2.20) i (2.27)
    cos_sweep = math.cos(sweep_rad)
    a_w_rad = (2.0 * math.pi * AR) / (2.0 + math.sqrt(4.0 + (AR / max(0.2, cos_sweep)) ** 2))
    a_w_deg = a_w_rad * (math.pi / 180.0)

    lam_taper = float(geom["wing"].get("eta", 0.6))
    a_inf_rad = 6.18 if params.get("engine_type", "prop") != "jet" else 6.28
    u_gl = AR / a_inf_rad
    tau_1 = 0.023 * (u_gl ** 3) - 0.103 * (u_gl ** 2) + 0.25 * u_gl
    tau_2 = -0.18 * (lam_taper ** 5) + 1.52 * (lam_taper ** 4) - 3.51 * (lam_taper ** 3) + 3.50 * (lam_taper ** 2) - 1.33 * lam_taper + 0.17
    tau_glauert = max(0.0, (tau_1 * tau_2) / 0.17)

    delta_1 = max(0.002, 0.0537 * u_gl - 0.005)
    delta_2 = -0.43 * (lam_taper ** 5) + 1.83 * (lam_taper ** 4) - 3.06 * (lam_taper ** 3) + 2.56 * (lam_taper ** 2) - lam_taper + 0.148
    delta_3 = (-2.2e-7 * (AR ** 3) + 1.0e-7 * (AR ** 2) + 1.6e-5) * (abs(sweep_deg) ** 3) + 1.0
    delta_glauert = max(0.0, (delta_1 * delta_2 * delta_3) / 0.048)

    a_w_paturski_rad = a_inf_rad / (1.0 + (a_inf_rad / (math.pi * AR)) * (1.0 + tau_glauert))
    a_w_paturski_deg = a_w_paturski_rad * (math.pi / 180.0)
    e_energy_max = (cz_econ ** 3) / (cx_econ ** 2)
    
    # Generowanie punktów biegunowej do wykresu Cz vs Cx, K(Cz) i funkcji energetycznej E(Cz) = Cz^3/Cx^2
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
        "cx0_buildup_theoretical": round(cx0_buildup_total, 4),
        "component_drag_buildup": component_drag_buildup,
        "cx0_to": round(cx0_to, 4),
        "cx0_lnd": round(cx0_lnd, 4),
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
        "polar_points": polar_points
    }
