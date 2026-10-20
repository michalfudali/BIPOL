"""
Moduł osiągów samolotu (BIPOL I)
Obliczenia prędkości charakterystycznych (Vs, Vc, Vmax), prędkości wznoszenia wy(V),
pułapu praktycznego i statycznego, dróg startu i lądowania.
"""
import math
from calculations.atmosphere import isa_atmosphere, G0, RHO0

def calculate_performance(m0: float, geom: dict, aero: dict, sizing: dict, params: dict):
    """
    Parametry:
      - m0: masa startowa MTOW [kg]
      - geom: słownik geometrii
      - aero: słownik aerodynamiki
      - sizing: wyniki doboru napędu
      - params: parametry misji i napędu
    """
    S = float(geom["wing"]["S"])
    AR = float(geom["wing"]["AR"])
    W = m0 * G0
    ws = W / S
    
    engine_type = params.get("engine_type", "prop")
    cz_max_clean = float(aero["cz_max_clean"])
    cz_max_to = float(aero["cz_max_to"])
    cz_max_lnd = float(aero["cz_max_lnd"])
    cx0 = float(aero["cx0_clean"])
    k_clean = float(aero["k_clean"])
    
    # 1. Prędkości przeciągnięcia na poziomie morza [m/s] i [km/h]
    vs_clean_ms = math.sqrt(2.0 * ws / (RHO0 * cz_max_clean))
    vs_to_ms = math.sqrt(2.0 * ws / (RHO0 * cz_max_to))
    vs_lnd_ms = math.sqrt(2.0 * ws / (RHO0 * cz_max_lnd))
    
    # 2. Ciąg / Moc dostępna na poziomie morza
    dp = sizing["design_point"]
    eta_p = float(params.get("prop_efficiency", 0.82))
    if engine_type == "none" or params.get("aircraft_type") == "glider":
        T0_avail = 0.0
        P0_avail = 0.0
    elif engine_type == "jet":
        T0_avail = dp["tw"] * W # Ciąg startowy [N]
        P0_avail = None
    else:
        P0_avail = dp["pw"] * W # Moc startowa [W]
        T0_avail = None

    def eval_wy_at_alt(v_ms: float, h_m: float = 0.0):
        isa = isa_atmosphere(h_m)
        rho = isa["rho"]
        sigma = isa["sigma"]
        q = 0.5 * rho * (v_ms ** 2)
        cz = ws / max(1.0, q)
        cx = cx0 + k_clean * (cz ** 2)
        drag = q * S * cx
        if engine_type == "none" or params.get("aircraft_type") == "glider":
            power_excess = - drag * v_ms
        elif engine_type == "jet":
            thrust = T0_avail * math.pow(sigma, 0.80)
            power_excess = (thrust - drag) * v_ms
        else:
            p_avail = P0_avail * eta_p * math.pow(sigma, 0.85)
            power_excess = p_avail - drag * v_ms
        return power_excess / W

    # 3. Analityczna prędkość optymalnego wznoszenia V_wy_max na poziomie morza (H = 0)
    if engine_type == "jet":
        # Maksimum nadmiaru mocy (T0 - D(V))*V: 3*Cx0*q^2 - (T0/S)*q - k*(W/S)^2 = 0
        ts = T0_avail / S
        q_wy = (ts + math.sqrt((ts ** 2) + 12.0 * cx0 * k_clean * (ws ** 2))) / (6.0 * cx0)
        v_wy_opt = max(vs_clean_ms * 1.05, math.sqrt((2.0 * q_wy) / RHO0))
    else:
        # Minimum mocy wymaganej D(V)*V przy Cz_ekon = sqrt(3*Cx0/k)
        cz_econ = math.sqrt((3.0 * cx0) / k_clean)
        cz_wy = min(cz_max_clean * 0.92, cz_econ)
        v_wy_opt = math.sqrt((2.0 * ws) / (RHO0 * cz_wy))

    wy_max = eval_wy_at_alt(v_wy_opt, 0.0)
    v_wy_max = v_wy_opt

    # 4. Dokładna prędkość maksymalna na poziomie morza V_max_SL
    if engine_type == "none" or params.get("aircraft_type") == "glider":
        # Szybowiec bez napędu: prędkość maksymalna to V_NE (dopuszczalna wg obwiedni V-n, min 220 km/h)
        v_max_sl_ms = max(float(params.get("cruise_speed_kmh", 120.0)) * 1.5 / 3.6, 60.0)
    else:
        v_low = v_wy_opt
        v_high = 380.0
        for _ in range(40):
            v_mid = 0.5 * (v_low + v_high)
            if eval_wy_at_alt(v_mid, 0.0) > 0.0:
                v_low = v_mid
            else:
                v_high = v_mid
        v_max_sl_ms = 0.5 * (v_low + v_high)

    # 5. Krzywa wznoszenia wy(V) na poziomie morza od 1.02*Vs_clean do V_max_SL (gdzie wy = 0)
    v_start = vs_clean_ms * 1.02
    v_end = max(v_start * 1.3, v_max_sl_ms)
    n_v = 28
    v_samples = [v_start + i * (v_end - v_start) / n_v for i in range(n_v + 1)]
    if v_start < v_wy_opt < v_end:
        v_samples.append(v_wy_opt)
    v_samples = sorted(v_samples)

    climb_curve = []
    for v in v_samples:
        wy_val = eval_wy_at_alt(v, 0.0)
        if wy_val > wy_max:
            wy_max = wy_val
            v_wy_max = v
        climb_curve.append({
            "v_kmh": round(v * 3.6, 1),
            "wy_ms": round(wy_val, 2)
        })
        
    # 6. Prędkość przelotowa i liczba Macha
    v_cr_req_kmh = float(params.get("cruise_speed_kmh", 250.0))
    v_cr_req_ms = v_cr_req_kmh / 3.6
    h_cr = float(params.get("cruise_altitude_m", 3000.0))
    isa_cr = isa_atmosphere(h_cr)
    mach_cr = v_cr_req_ms / isa_cr["a"]
    
    # 7. Pułap praktyczny (H_prakt, gdzie wy_max(H) = 0.5 m/s) wyznaczany w atmosferze wzorcowej ISA
    def max_wy_at_h(h_m: float):
        isa_h = isa_atmosphere(h_m)
        sigma = isa_h["sigma"]
        rho_h = isa_h["rho"]
        vs_h = math.sqrt((2.0 * ws) / (rho_h * cz_max_clean))
        if engine_type == "jet":
            ts_h = (T0_avail * math.pow(sigma, 0.80)) / S
            q_wy_h = (ts_h + math.sqrt((ts_h ** 2) + 12.0 * cx0 * k_clean * (ws ** 2))) / (6.0 * cx0)
            v_opt_h = max(vs_h * 1.05, math.sqrt((2.0 * q_wy_h) / rho_h))
        else:
            v_opt_h = v_wy_max / math.sqrt(sigma)
        return eval_wy_at_alt(v_opt_h, h_m)

    def ceiling_for(required_climb):
        h_low, h_high = 0.0, 20000.0
        if max_wy_at_h(0.0) <= required_climb:
            return 0.0
        if max_wy_at_h(h_high) >= required_climb:
            return h_high
        for _ in range(30):
            h_mid = 0.5 * (h_low + h_high)
            if max_wy_at_h(h_mid) > required_climb:
                h_low = h_mid
            else:
                h_high = h_mid
        return round(0.5 * (h_low + h_high), -1)

    h_pract = ceiling_for(0.5)
    h_absolute = ceiling_for(0.0)
    
    # 8. Długość startu i lądowania nad przeszkodę H = 15 m (50 ft) wg Fiszdon / Filcek / Raymer
    b_span = float(geom["wing"]["b"])
    wing_cfg = geom["wing"].get("wing_config", "low")
    h_wing = 0.11 * b_span if wing_cfg == "low" else (0.16 * b_span if wing_cfg == "mid" else 0.22 * b_span)
    # Współczynnik wpływu ziemi McCormicka (Ground Effect) na opór indukowany
    phi_ge = ((16.0 * h_wing / b_span) ** 2) / (1.0 + ((16.0 * h_wing / b_span) ** 2))

    mu_to = 0.04  # Nawierzchnia betonowa / asfaltowa
    cz_to = aero["cz_max_to"]
    cx0_to = aero["cx0_to"]
    k_to = 1.0 / (math.pi * AR * (float(params.get("oswald_e", 0.80)) * 0.94))

    v_lof_ms = 1.12 * vs_to_ms
    v_2_ms = 1.20 * vs_to_ms
    v_rms_to = v_lof_ms / math.sqrt(2.0)  # Prędkość średniokwadratowa rozbiegu ~ 0.792 Vs_TO
    q_rms_to = 0.5 * RHO0 * (v_rms_to ** 2)

    if engine_type == "none" or params.get("aircraft_type") == "glider":
        tw_rms = 0.0
        tw_v2 = 0.0
        s_g_to = 0.0
        s_tr_to = 0.0
        s_climb_to = 0.0
        s_air_to = 0.0
        gamma_to_rad = 0.0
        s_to_15 = 0.0
    elif engine_type == "jet":
        tw_rms = (dp.get("tw") or 0.0) * 0.94
        tw_v2 = (dp.get("tw") or 0.0) * 0.90
        cz_roll = min(0.65, mu_to / max(0.01, 2.0 * phi_ge * k_to))
        cx_roll = cx0_to + phi_ge * k_to * (cz_roll ** 2)
        a_mean_to = G0 * max(0.06, tw_rms - mu_to - (q_rms_to / ws) * (cx_roll - mu_to * cz_roll))
        s_g_to = (v_lof_ms ** 2) / (2.0 * a_mean_to)
        q_v2 = 0.5 * RHO0 * (v_2_ms ** 2)
        cz_v2 = ws / max(1.0, q_v2)
        cx_v2 = cx0_to + k_to * (cz_v2 ** 2)
        sin_gamma_to = max(0.04, min(0.35, tw_v2 - (cx_v2 / max(0.1, cz_v2))))
        gamma_to_rad = math.asin(sin_gamma_to)
        n_tr = 1.18
        r_tr = (v_lof_ms ** 2) / (G0 * (n_tr - 1.0))
        h_tr = r_tr * (1.0 - math.cos(gamma_to_rad))
        if h_tr < 15.0:
            s_tr_to = r_tr * math.sin(gamma_to_rad)
            s_climb_to = (15.0 - h_tr) / math.tan(gamma_to_rad)
        else:
            s_tr_to = math.sqrt(max(1.0, 2.0 * r_tr * 15.0 - 225.0))
            s_climb_to = 0.0
        s_air_to = s_tr_to + s_climb_to
        s_to_15 = s_g_to + s_air_to
    else:
        pw_ratio = dp.get("pw") or 0.0
        eta_to = float(params.get("prop_eff_to", 0.65))
        tw_rms = (pw_ratio * eta_to) / max(12.0, v_rms_to)
        tw_v2 = (pw_ratio * (eta_to + 0.06)) / max(15.0, v_2_ms)
        cz_roll = min(0.65, mu_to / max(0.01, 2.0 * phi_ge * k_to))
        cx_roll = cx0_to + phi_ge * k_to * (cz_roll ** 2)
        a_mean_to = G0 * max(0.06, tw_rms - mu_to - (q_rms_to / ws) * (cx_roll - mu_to * cz_roll))
        s_g_to = (v_lof_ms ** 2) / (2.0 * a_mean_to)
        q_v2 = 0.5 * RHO0 * (v_2_ms ** 2)
        cz_v2 = ws / max(1.0, q_v2)
        cx_v2 = cx0_to + k_to * (cz_v2 ** 2)
        sin_gamma_to = max(0.04, min(0.35, tw_v2 - (cx_v2 / max(0.1, cz_v2))))
        gamma_to_rad = math.asin(sin_gamma_to)
        n_tr = 1.18
        r_tr = (v_lof_ms ** 2) / (G0 * (n_tr - 1.0))
        h_tr = r_tr * (1.0 - math.cos(gamma_to_rad))
        if h_tr < 15.0:
            s_tr_to = r_tr * math.sin(gamma_to_rad)
            s_climb_to = (15.0 - h_tr) / math.tan(gamma_to_rad)
        else:
            s_tr_to = math.sqrt(max(1.0, 2.0 * r_tr * 15.0 - 225.0))
            s_climb_to = 0.0
        s_air_to = s_tr_to + s_climb_to
        s_to_15 = s_g_to + s_air_to

    # Lądowanie znad przeszkody H = 15 m oraz dobieg naziemny (Fiszdon / Raymer)
    v_app_ms = 1.30 * vs_lnd_ms
    v_td_ms = 1.15 * vs_lnd_ms
    cx0_lnd = aero["cx0_lnd"]
    gamma_app_rad = math.radians(3.5)
    r_flare = (v_app_ms ** 2) / (G0 * 0.15)
    h_flare = r_flare * (1.0 - math.cos(gamma_app_rad))
    s_air_lnd = max(20.0, (15.0 - min(12.0, h_flare)) / math.tan(gamma_app_rad) + r_flare * math.sin(gamma_app_rad))

    # Dobieg: swobodne toczenie (reakcja 1.5 s) + hamowanie zasadnicze (mu_ham = 0.40 + opór aerodynamiczny)
    s_free_lnd = 1.5 * v_td_ms
    mu_brake = 0.40
    v_rms_lnd = v_td_ms / math.sqrt(2.0)
    q_rms_lnd = 0.5 * RHO0 * (v_rms_lnd ** 2)
    cz_lnd_roll = 0.20
    cx_lnd_roll = cx0_lnd + phi_ge * k_to * (cz_lnd_roll ** 2)
    a_mean_brake = G0 * (mu_brake + (q_rms_lnd / ws) * max(0.0, cx_lnd_roll - mu_brake * cz_lnd_roll))
    s_brake_lnd = (v_td_ms ** 2) / (2.0 * a_mean_brake)
    s_g_lnd = s_free_lnd + s_brake_lnd
    s_lnd_15 = s_air_lnd + s_g_lnd

    # 9. Parametry zakrętu ustalonego (wg BIPOL_1_wzory.pdf wzory 30-52)
    v_turn_ms = max(vs_clean_ms * 1.45, min(v_cr_req_ms, v_max_sl_ms * 0.85))
    q_turn = 0.5 * RHO0 * (v_turn_ms ** 2)
    n_aero_max = (q_turn * cz_max_clean) / ws
    if engine_type == "none" or params.get("aircraft_type") == "glider":
        # Szybowiec w krążeniu termicznym: typowy kąt przechylenia 45° (n = 1.41)
        n_sustained = min(n_aero_max, 1.414)
    else:
        t_avail_turn = T0_avail if engine_type == "jet" else (P0_avail * eta_p) / v_turn_ms
        n_thrust_sq = ((t_avail_turn / W) * q_turn - (q_turn ** 2) * cx0 / ws) / (k_clean * ws)
        n_sustained = min(n_aero_max, math.sqrt(max(1.05, n_thrust_sq)))
    
    # Kąt przechylenia phi = arccos(1/n) (wzór 31)
    cos_phi = min(1.0, 1.0 / max(1.0, n_sustained))
    bank_angle_deg = math.degrees(math.acos(cos_phi))
    
    # Promień zakrętu r_min = V^2 / (g * sqrt(n^2 - 1)) (wzór 34)
    n_factor = math.sqrt(max(0.01, (n_sustained ** 2) - 1.0))
    r_min_turn_m = (v_turn_ms ** 2) / (G0 * n_factor)
    
    # Prędkość kątowa zakrętu dpsi/dt = g * sqrt(n^2 - 1) / V (wzory 36 i 52)
    psi_dot_rad_s = (G0 * n_factor) / v_turn_ms
    psi_dot_deg_s = math.degrees(psi_dot_rad_s)
    t_turn_360_s = (2.0 * math.pi) / max(0.01, psi_dot_rad_s)
    
    return {
        "speeds": {
            "vs_clean_kmh": round(vs_clean_ms * 3.6, 1),
            "vs_to_kmh": round(vs_to_ms * 3.6, 1),
            "vs_lnd_kmh": round(vs_lnd_ms * 3.6, 1),
            "v_lof_kmh": round(v_lof_ms * 3.6, 1),
            "v_2_kmh": round(v_2_ms * 3.6, 1),
            "v_app_kmh": round(v_app_ms * 3.6, 1),
            "v_td_kmh": round(v_td_ms * 3.6, 1),
            "v_cruise_kmh": round(v_cr_req_kmh, 1),
            "v_max_sl_kmh": round(v_max_sl_ms * 3.6, 1),
            "mach_cruise": round(mach_cr, 3)
        },
        "climb": {
            "wy_max_ms": round(wy_max, 2),
            "v_wy_max_kmh": round(v_wy_max * 3.6, 1),
            "climb_curve": climb_curve
        },
        "ceiling": {
            "service_ceiling_m": int(h_pract),
            "service_ceiling_ft": int(h_pract * 3.28084),
            "absolute_ceiling_m": int(h_absolute),
            "model_upper_limit_m": 20000
        },
        "takeoff": {
            "ground_roll_m": round(s_g_to, 1),
            "transition_m": round(s_tr_to, 1),
            "climb_to_15m_m": round(s_climb_to, 1),
            "air_distance_m": round(s_air_to, 1),
            "climb_angle_deg": round(math.degrees(gamma_to_rad), 1),
            "distance_to_15m": round(s_to_15, 1)
        },
        "landing": {
            "air_approach_m": round(s_air_lnd, 1),
            "free_roll_m": round(s_free_lnd, 1),
            "braking_roll_m": round(s_brake_lnd, 1),
            "ground_roll_m": round(s_g_lnd, 1),
            "distance_from_15m": round(s_lnd_15, 1)
        },
        "turn": {
            "n_sustained": round(n_sustained, 2),
            "bank_angle_deg": round(bank_angle_deg, 1),
            "r_min_m": round(r_min_turn_m, 1),
            "psi_dot_deg_s": round(psi_dot_deg_s, 2),
            "t_360_s": round(t_turn_360_s, 1),
            "v_turn_kmh": round(v_turn_ms * 3.6, 1)
        }
    }
