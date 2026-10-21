"""
Moduł wyboru obciążenia powierzchni skrzydła (W/S) i obciążenia ciągu (T/W) lub mocy (P/W)
Matching Chart / Diagram doboru parametrów płatowca i napędu wg BIPOL I
"""
import math
from calculations.atmosphere import isa_atmosphere, G0, RHO0

def calculate_matching_chart(params: dict, m0: float = None):
    """
    Parametry wejściowe:
      - engine_type: 'jet' lub 'prop'
      - v_stall_kmh: prędkość przeciągnięcia / podejścia [km/h] (np. 110 km/h)
      - takeoff_run_m: wymagana droga rozbiegu [m] (np. 450 m)
      - climb_rate_ms: wymagana prędkość wznoszenia przy ziemi [m/s] (np. 6.0 m/s)
      - cruise_speed_kmh: prędkość przelotowa [km/h]
      - cruise_altitude_m: wysokość przelotu [m]
      - aspect_ratio: wydłużenie skrzydła Lambda (np. 8.5)
      - oswald_e: współczynnik Oswalda e (np. 0.8)
      - cx0: współczynnik oporu szkodliwego cx0 (np. 0.024)
      - cz_max_clean: cz_max profilu gładkiego (np. 1.5)
      - cz_max_to: cz_max z klapami do startu (np. 1.8)
      - cz_max_lnd: cz_max z klapami do lądowania (np. 2.2)
      - prop_efficiency: sprawność śmigła (np. 0.82)
      - prop_eff_to: sprawność śmigła na rozbiegu (np. 0.65)
    """
    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = "none" if ac_type == "glider" else params.get("engine_type", "prop")
    v_stall_kmh = float(params.get("v_stall_kmh", 100.0))
    v_stall_ms = v_stall_kmh / 3.6
    
    s_to_req = float(params.get("takeoff_run_m", 500.0))
    wy_req = float(params.get("climb_rate_ms", 5.0))
    
    v_cr_kmh = float(params.get("cruise_speed_kmh", 240.0))
    v_cr_ms = v_cr_kmh / 3.6
    h_cr = float(params.get("cruise_altitude_m", 3000.0))
    
    AR = float(params.get("aspect_ratio", 8.0))
    e = float(params.get("oswald_e", 0.80))
    cx0_base = float(params.get("cx0", 0.025))
    wing_config = params.get("wing_config", "low")
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")

    cx0 = cx0_base
    if wing_config == "braced_high":
        cx0 += 0.0020
    if flap_type == "junkers":
        cx0 += 0.0025
    if slat_type == "fixed_slot":
        cx0 += 0.0030
    
    cz_max_to = float(params.get("cz_max_to", 1.8))
    cz_max_lnd = float(params.get("cz_max_lnd", 2.2))
    
    eta_p = float(params.get("prop_efficiency", 0.82))
    eta_to = float(params.get("prop_eff_to", 0.65))
    
    # Warunki atmosferyczne na przelocie
    isa_cr = isa_atmosphere(h_cr)
    rho_cr = isa_cr["rho"]
    sigma_cr = isa_cr["sigma"]
    
    # 1. Ograniczenie prędkości przeciągnięcia w konfiguracji do lądowania (Stall speed limit)
    # W/S <= 0.5 * rho0 * Vs0^2 * Cz_max_lnd
    ws_stall_max = 0.5 * RHO0 * (v_stall_ms ** 2) * cz_max_lnd
    fixed_area = float(params.get('wing_area_m2') or 0)
    ws_design = (float(m0) * G0 / fixed_area if fixed_area and m0 is not None
                 else round(0.95 * ws_stall_max, 1))
    
    # Tworzymy wektor punktów W/S od 200 N/m^2 do 1.15 * ws_stall_max
    ws_min = min(200.0, 0.25 * ws_stall_max)
    ws_max = max(ws_stall_max * 1.15, 800.0)
    ws_min = min(ws_min, ws_design * .7)
    ws_max = max(ws_max, ws_design * 1.15)
    steps = 40
    ws_values = [ws_min + i * (ws_max - ws_min) / steps for i in range(steps + 1)]
    
    # Wykresy ograniczeń
    curve_takeoff = []
    curve_climb = []
    curve_cruise = []
    
    # Współczynnik oporu indukowanego k w biegunowej: Cx = Cx0 + k * Cz^2
    k_ind = 1.0 / (math.pi * AR * e)
    
    # Współczynnik tarcia kół o nawierzchnię podczas rozbiegu
    mu_ground = 0.04
    
    for ws in ws_values:
        if engine_type == "none":
            curve_takeoff.append(0.0)
            curve_climb.append(0.0)
            curve_cruise.append(0.0)
            continue

        # --- A. Rozbieg (Takeoff) ---
        s_eff = max(30.0, s_to_req)
        tw_to = (1.21 * ws) / (G0 * RHO0 * cz_max_to * s_eff) + mu_ground
        
        if engine_type == "none":
            curve_takeoff.append(0.0)
        elif engine_type == "jet":
            curve_takeoff.append(round(tw_to, 4))
        else:
            # Prędkość oderwania V_LOF = 1.12 * V_stall_to
            v_to = 1.12 * math.sqrt(max(1.0, 2.0 * ws / (RHO0 * cz_max_to)))
            pw_to = (tw_to * v_to) / eta_to
            curve_takeoff.append(round(pw_to, 2))
            
        # --- B. Wznoszenie przy ziemi (Climb rate wg BIPOL_1_wzory.pdf) ---
        if engine_type == "none":
            curve_climb.append(0.0)
        elif engine_type == "jet":
            # Dla odrzutowca (T approx const): max(wy) przy Cz_opt = sqrt(Cx0 / k) -> K_max
            cz_climb = math.sqrt(cx0 / k_ind)
            ld_climb = cz_climb / (2.0 * cx0)
            v_y = math.sqrt(2.0 * ws / (RHO0 * cz_climb))
            tw_climb = (wy_req / v_y) + (1.0 / ld_climb)
            curve_climb.append(round(tw_climb, 4))
        else:
            # Dla śmigłowego (P_rozp approx const): max(wy) przy min mocy wymaganej -> Cz_ekon = sqrt(3 * Cx0 / k)
            cz_climb = math.sqrt(3.0 * cx0 / k_ind)
            cx_climb = 4.0 * cx0
            ld_climb = cz_climb / cx_climb
            v_y = math.sqrt(2.0 * ws / (RHO0 * cz_climb))
            pw_climb = (wy_req + (v_y / ld_climb)) / eta_p
            curve_climb.append(round(pw_climb, 2))
            
        # --- C. Przelot (Cruise) ---
        q_cr = 0.5 * rho_cr * (v_cr_ms ** 2)
        cz_cr = ws / q_cr
        cx_cr = cx0 + k_ind * (cz_cr ** 2)
        
        tw_cr_alt = cx_cr / cz_cr
        engine_lapse = math.pow(sigma_cr, 0.80)
        tw_cr_sl = tw_cr_alt / engine_lapse
        
        if engine_type == "none":
            curve_cruise.append(0.0)
        elif engine_type == "jet":
            curve_cruise.append(round(tw_cr_sl, 4))
        else:
            power_lapse = math.pow(sigma_cr, 0.85)
            pw_cr_sl = (tw_cr_alt * v_cr_ms) / (eta_p * power_lapse)
            curve_cruise.append(round(pw_cr_sl, 2))

    # Dobór punktu projektowego (Design Point):
    # Wybieramy W/S równe 95% ws_stall_max (rezerwa na prędkość przeciągnięcia Vs0)
    # A prescribed area sets W/S. VS0 remains an upper-bound requirement.
    
    # Obliczamy wartości w punkcie ws_design:
    s_eff = max(30.0, s_to_req)
    tw_to_design = (1.21 * ws_design) / (G0 * RHO0 * cz_max_to * s_eff) + mu_ground
    
    q_cr = 0.5 * rho_cr * (v_cr_ms ** 2)
    cz_cr = ws_design / q_cr
    cx_cr = cx0 + k_ind * (cz_cr ** 2)
    tw_cr_sl_design = (cx_cr / cz_cr) / math.pow(sigma_cr, 0.80)
    
    if engine_type == "none":
        tw_design = None
        pw_design = None
    elif engine_type == "jet":
        cz_climb = math.sqrt(cx0 / k_ind)
        ld_climb = cz_climb / (2.0 * cx0)
        v_y = math.sqrt(2.0 * ws_design / (RHO0 * cz_climb))
        tw_climb_design = (wy_req / v_y) + (1.0 / ld_climb)
        
        tw_required = max(tw_to_design, tw_climb_design, tw_cr_sl_design) * 1.06 # 6% margines projektowy
        tw_design = round(tw_required, 3)
        pw_design = None
    else:
        v_to = 1.12 * math.sqrt(max(1.0, 2.0 * ws_design / (RHO0 * cz_max_to)))
        pw_to_design = (tw_to_design * v_to) / eta_to
        
        cz_climb = math.sqrt(3.0 * cx0 / k_ind)
        cx_climb = 4.0 * cx0
        ld_climb = cz_climb / cx_climb
        v_y = math.sqrt(2.0 * ws_design / (RHO0 * cz_climb))
        pw_climb_design = (wy_req + (v_y / ld_climb)) / eta_p
        
        pw_cr_sl_design = ((cx_cr / cz_cr) * v_cr_ms) / (eta_p * math.pow(sigma_cr, 0.85))
        
        pw_required = max(pw_to_design, pw_climb_design, pw_cr_sl_design) * 1.08 # 8% margines projektowy
        pw_design = round(pw_required, 2)
        tw_design = None

    # Teoretyczne minimum T/W dla warunku rzeczywistych rozwiązań wznoszenia (Galiński & Grabowski wzór 18)
    # (T/W)_min >= G + 2 * sqrt(Cx0 / (pi * AR * e)) = G + 1 / K_max
    k_max_val = 0.5 * math.sqrt((math.pi * AR * e) / cx0)
    v_ref_climb = math.sqrt(2.0 * ws_design / (RHO0 * math.sqrt(cx0 / k_ind)))
    grad_g = wy_req / v_ref_climb
    tw_min_climb_bipol18 = grad_g + (1.0 / k_max_val)

    w_newtons = (float(m0) * G0) if m0 is not None else None
    power_kw = round((pw_design * w_newtons) / 1000.0, 1) if (pw_design and w_newtons) else None
    power_hp = round((pw_design * w_newtons) / 735.5, 1) if (pw_design and w_newtons) else None
    thrust_kn = round((tw_design * w_newtons) / 1000.0, 2) if (tw_design and w_newtons) else None
    required_power_kw = power_kw
    if engine_type == 'prop' and 'engine_power_kw' in params.get('locked_params', []):
        power_kw = float(params['engine_power_kw'])
        power_hp = power_kw * 1000 / 735.5
        pw_design = power_kw * 1000 / w_newtons

    return {
        "engine_type": engine_type,
        "ws_values": [round(x, 1) for x in ws_values],
        "ws_stall_max": round(ws_stall_max, 1),
        "curve_takeoff": curve_takeoff,
        "curve_climb": curve_climb,
        "curve_cruise": curve_cruise,
        "design_point": {
            "ws": ws_design,
            "ws_N_m2": ws_design,
            "tw": tw_design,
            "pw": pw_design, # W/N
            "pw_hp_kg": round(pw_design * G0 / 735.5, 3) if pw_design else None, # KM/kg
            "power_kw": power_kw,
            "required_power_kw": required_power_kw,
            "power_hp": power_hp,
            "thrust_kn": thrust_kn,
            "tw_min_climb_bipol18": round(tw_min_climb_bipol18, 4)
        }
    }
