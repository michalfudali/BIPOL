"""
Moduł wyważenia samolotu i stateczności statycznej podłużnej (BIPOL I)
Wyznaczanie położenia środka masy w różnych konfiguracjach załadowania,
przeliczenie na % ŚDA (MAC), wyznaczenie punktu neutralnego oraz zapasu stateczności.
"""
import math

def calculate_balance_and_stability(m_sizing: dict, geom: dict, aero: dict, params: dict):
    """
    Parametry:
      - m_sizing: wyniki bilansu mas (m0, m_empty, m_fuel, m_payload, m_crew, breakdown)
      - geom: geometria płatowca (L_fus, mac, x_le_mac, S, S_h, l_h)
      - aero: aerodynamika
      - params: konfiguracja układu (układ silników itp.)
    """
    l_f = float(geom["fuselage"]["length"])
    d_f = float(geom["fuselage"]["diameter"])
    S = float(geom["wing"]["S"])
    AR = float(geom["wing"]["AR"])
    mac = float(geom["wing"]["mac"])
    x_le_mac_offset = float(geom["wing"]["x_le_mac"])
    
    # Dobór podłużnego położenia skrzydła na kadłubie (x_lemac) metodą wyważenia grup masowych (wg Raymer / Torenbeek / BIPOL):
    # Zespoły związane z kadłubem: kadłub, usterzenie, instalacje oraz napęd (jeśli w dziobie lub z tyłu kadłuba).
    # Zespoły związane ze skrzydłem: płat, podwozie główne oraz gondole silnikowe (jeśli na skrzydle).
    engine_loc = params.get("engine_location", "nose") # 'nose', 'wing', 'rear'
    bd = m_sizing["breakdown"]
    m_empty = max(1.0, m_sizing["m_empty"])
    m_crew = m_sizing["m_crew"]
    m_fuel = m_sizing["m_fuel"]
    m_payload = m_sizing["m_payload"]

    x_fus = 0.44 * l_f
    x_tail = 0.91 * l_f
    x_sys = 0.40 * l_f

    if engine_loc == "nose":
        x_prop_fixed = 0.10 * l_f
        target_oew_mac = 0.25
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            bd["m_propulsion"] * x_prop_fixed
        )
        m_wing_group = bd["m_wing"] + bd["m_gear"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45) * mac
    elif engine_loc == "rear":
        x_prop_fixed = 0.76 * l_f
        target_oew_mac = 0.27
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys +
            bd["m_propulsion"] * x_prop_fixed
        )
        m_wing_group = bd["m_wing"] + bd["m_gear"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45) * mac
    else: # wing
        target_oew_mac = 0.25
        mom_fus_fixed = (
            bd["m_fuselage"] * x_fus +
            bd["m_tail"] * x_tail +
            bd["m_systems"] * x_sys
        )
        m_wing_group = bd["m_wing"] + bd["m_gear"] + bd["m_propulsion"]
        mom_wing_offset = (bd["m_wing"] * 0.38 + bd["m_gear"] * 0.45 - bd["m_propulsion"] * 0.15) * mac

    denom_m = max(1.0, m_empty - m_wing_group)
    x_lemac = (mom_fus_fixed + mom_wing_offset - target_oew_mac * mac * m_empty) / denom_m
    x_lemac = max(0.28 * l_f, min(0.56 * l_f, x_lemac))
    x_le_wing = x_lemac - x_le_mac_offset

    if engine_loc == "nose":
        x_prop = 0.10 * l_f
    elif engine_loc == "rear":
        x_prop = 0.76 * l_f
    else:
        x_prop = x_lemac - 0.15 * mac
        
    x_arms = {
        "fuselage": round(x_fus, 2),
        "wing": round(x_lemac + 0.38 * mac, 2),
        "tail": round(x_tail, 2),
        "propulsion": round(x_prop, 2),
        "gear": round(x_lemac + 0.45 * mac, 2),
        "systems": round(x_sys, 2),
        "crew": round(x_lemac - 0.18 * mac, 2),
        "pax_front": round(x_lemac + 0.12 * mac, 2),
        "pax_rear": round(x_lemac + 0.48 * mac, 2),
        "baggage": round(x_lemac + 0.75 * mac, 2),
        "fuel": round(x_lemac + 0.32 * mac, 2)
    }
    
    # 1. Moment masy pustej (OEW)
    mom_empty = (
        bd["m_fuselage"] * x_arms["fuselage"] +
        bd["m_wing"] * x_arms["wing"] +
        bd["m_tail"] * x_arms["tail"] +
        bd["m_propulsion"] * x_arms["propulsion"] +
        bd["m_gear"] * x_arms["gear"] +
        bd["m_systems"] * x_arms["systems"]
    )
    x_cg_empty = mom_empty / max(1.0, m_empty)
    
    # 2. Stan: Samolot pusty + załoga
    unmanned = bool(m_sizing.get("unmanned", False)) or params.get("aircraft_type") == "uav"
    m_crew_state = m_empty + m_crew
    mom_crew_state = mom_empty + m_crew * x_arms["crew"]
    x_cg_crew = mom_crew_state / max(1.0, m_crew_state)
    
    # 3. Stan: Bez paliwa (ZFW = Empty + Crew + Payload)
    if unmanned:
        # UAV: wyposażenie zadaniowe (głowica optoelektroniczna w dziobie/pod kadłubem + awionika misji w okolicy ŚM)
        x_arms["payload_sensor"] = round(x_lemac - 0.35 * mac, 2)
        x_arms["payload_bay"] = round(x_lemac + 0.20 * mac, 2)
        mom_zfw = mom_crew_state + (m_payload * 0.60) * x_arms["payload_sensor"] + (m_payload * 0.40) * x_arms["payload_bay"]
    else:
        m_pax = m_payload * 0.80
        m_bag = m_payload * 0.20
        mom_zfw = mom_crew_state + (m_pax * 0.45) * x_arms["pax_front"] + (m_pax * 0.55) * x_arms["pax_rear"] + m_bag * x_arms["baggage"]
    m_zfw = m_crew_state + m_payload
    x_cg_zfw = mom_zfw / max(1.0, m_zfw)
    
    # 4. Stan: Pełna masa startowa (MTOW = ZFW + Fuel)
    mom_mtow = mom_zfw + m_fuel * x_arms["fuel"]
    m_mtow = m_zfw + m_fuel
    x_cg_mtow = mom_mtow / max(1.0, m_mtow)
    
    # 5. Stan: Lądowanie z rezerwą paliwa (MLW: 15% paliwa)
    m_fuel_res = 0.15 * m_fuel
    mom_mlw = mom_zfw + m_fuel_res * x_arms["fuel"]
    m_mlw = m_zfw + m_fuel_res
    x_cg_mlw = mom_mlw / max(1.0, m_mlw)
    
    # Funkcja pomocnicza: przeliczenie na % ŚDA (MAC)
    def to_percent_mac(x):
        return round(((x - x_lemac) / mac) * 100.0, 1)
        
    loading_states = [
        {"name": "Masa pusta (OEW)", "mass_kg": round(m_empty, 1), "xcg_m": round(x_cg_empty, 3), "xcg_mac_pct": to_percent_mac(x_cg_empty)},
    ]
    if not unmanned:
        loading_states.append({"name": "Pusty + załoga", "mass_kg": round(m_crew_state, 1), "xcg_m": round(x_cg_crew, 3), "xcg_mac_pct": to_percent_mac(x_cg_crew)})
    else:
        # UAV: pusty + pełne paliwo bez wyposażenia zadaniowego (lot techniczny / przebazowanie)
        m_ferry = m_empty + m_fuel
        x_cg_ferry = (mom_empty + m_fuel * x_arms["fuel"]) / max(1.0, m_ferry)
        loading_states.append({"name": "Pusty + paliwo, bez wyposażenia zadaniowego", "mass_kg": round(m_ferry, 1), "xcg_m": round(x_cg_ferry, 3), "xcg_mac_pct": to_percent_mac(x_cg_ferry)})
    loading_states += [
        {"name": "Masa bez paliwa (ZFW)" if not unmanned else "Pusty + wyposażenie zadaniowe (ZFW)", "mass_kg": round(m_zfw, 1), "xcg_m": round(x_cg_zfw, 3), "xcg_mac_pct": to_percent_mac(x_cg_zfw)},
        {"name": "Masa lądowania (MLW)", "mass_kg": round(m_mlw, 1), "xcg_m": round(x_cg_mlw, 3), "xcg_mac_pct": to_percent_mac(x_cg_mlw)},
        {"name": "Masa startowa (MTOW)", "mass_kg": round(m_mtow, 1), "xcg_m": round(x_cg_mtow, 3), "xcg_mac_pct": to_percent_mac(x_cg_mtow)},
    ]
    
    # Zakres zmienności położenia środka ciężkości
    all_pct = [s["xcg_mac_pct"] for s in loading_states]
    cg_forward_limit = min(all_pct)
    cg_aft_limit = max(all_pct)
    
    # 6. Punkt neutralny płatowca (Neutral Point x_N) wg równania stateczności podłużnej (Mechanika Lotu I - Projekt 6):
    # x_N/MAC = x_ac_wbn + eta_H * V_H * (a_H / a_W) * (1 - d_epsilon / d_alpha)
    vh = float(geom["horizontal_tail"]["vh_coeff"])
    ar_h = float(geom["horizontal_tail"]["AR_h"])
    a_w = (2.0 * math.pi * AR) / (AR + 2.0)
    a_h = (2.0 * math.pi * ar_h) / (ar_h + 2.0)
    de_da = min(0.55, (2.0 * a_w) / (math.pi * AR))  # Gradient odchylenia strug za skrzydłem d_epsilon/d_alpha
    eta_h_eff = 0.72  # Współczynnik spiętrzenia i interferencji na usterzeniu poziomym (z wolnym/trymowanym sterem)

    # Destabilizujący wpływ kadłuba oraz gondoli/śmigła wg wzoru Munka-Multhoppa: Delta x_ac_fus + Delta x_ac_nac
    engine_type = params.get("engine_type", "prop")
    delta_xac_fus = min(0.11, max(0.055, (0.35 * (d_f ** 2) * l_f) / (S * mac * a_w)))
    if engine_type == "none":
        delta_xac_prop = 0.0
    elif engine_type == "jet":
        delta_xac_prop = 0.015 if engine_loc == "wing" else 0.008
    else:
        delta_xac_prop = 0.030 if engine_loc in ["nose", "wing"] else 0.010
    x_ac_wbn_pct = (0.25 - delta_xac_fus - delta_xac_prop) * 100.0
    delta_xn_tail_pct = (eta_h_eff * vh * (a_h / a_w) * (1.0 - de_da)) * 100.0

    neutral_point_pct = round(x_ac_wbn_pct + delta_xn_tail_pct, 1)
    neutral_point_m = round(x_lemac + (neutral_point_pct / 100.0) * mac, 3)
    
    # Zapas stateczności statycznej (Static Margin K_n = (x_N - x_CG)/MAC)
    static_margin_forward = round(neutral_point_pct - cg_forward_limit, 1)
    static_margin_aft = round(neutral_point_pct - cg_aft_limit, 1)
    
    is_stable = static_margin_aft >= 5.0
    
    return {
        "x_le_wing_m": round(x_le_wing, 3),
        "x_lemac_m": round(x_lemac, 3),
        "arms": x_arms,
        "loading_states": loading_states,
        "cg_range": {
            "forward_pct": cg_forward_limit,
            "aft_pct": cg_aft_limit,
            "delta_pct": round(cg_aft_limit - cg_forward_limit, 1)
        },
        "neutral_point": {
            "x_n_m": neutral_point_m,
            "x_n_mac_pct": neutral_point_pct
        },
        "stability": {
            "static_margin_forward_pct": static_margin_forward,
            "static_margin_aft_pct": static_margin_aft,
            "is_stable": is_stable,
            "evaluation": "Stateczny statycznie (zapas 5-20% ŚDA)" if is_stable else "Uwaga: mały zapas stateczności w tylnym położeniu ŚM!"
        }
    }
