"""
Moduł geometrii płatowca i rozkładu Schrenka (BIPOL I)
Wymiarowanie skrzydła, Średniej Cięciwy Aerodynamicznej (ŚDA / MAC),
usterzeń metodą współczynników objętościowych (VH, VV), kadłuba
oraz wyznaczanie rozkładu obciążenia wzdłuż rozpiętości metodą Schrenka.
"""
import math
from calculations.atmosphere import G0

def calculate_geometry(m0: float, ws: float, params: dict):
    """
    Parametry wejściowe:
      - m0: masa startowa [kg]
      - ws: wybrane obciążenie powierzchni W/S [N/m^2]
      - aspect_ratio: wydłużenie skrzydła Lambda (np. 8.0)
      - taper_ratio: zbieżność skrzydła eta = ct / cr (np. 0.55)
      - sweep_quarter_deg: skos w 25% cięciwy [deg] (np. 0 - 25)
      - dihedral_deg: wznos skrzydła Gamma [deg] (np. 3.0)
      - n_pax: liczba pasażerów
      - ac_type: typ samolotu
      - v_h: współczynnik objętości usterzenia poziomego V_H (np. 0.70)
      - v_v: współczynnik objętości usterzenia pionowego V_V (np. 0.05)
      - ar_h: wydłużenie usterzenia poziomego (np. 4.0)
      - ar_v: wydłużenie usterzenia pionowego (np. 1.5)
    """
    AR = float(params.get("aspect_ratio", 8.0))
    eta = float(params.get("taper_ratio", 0.55))
    sweep_deg = float(params.get("sweep_quarter_deg", 0.0))
    dihedral_deg = float(params.get("dihedral_deg", 3.0))
    n_pax = int(params.get("n_pax", 4))
    ac_type = params.get("aircraft_type", "piston_ga")
    
    # 1. Geometria skrzydła
    weight_n = m0 * G0
    S = weight_n / ws
    eta = max(0.1, min(1.0, float(params.get("taper_ratio", 0.55))))
    AR = max(2.0, min(35.0, float(params.get("aspect_ratio", 8.0))))

    req_span = params.get("wingspan_m") or params.get("span_limit")
    try:
        req_span_val = float(req_span) if req_span is not None else 0.0
    except (ValueError, TypeError):
        req_span_val = 0.0

    if req_span_val > 0.5:
        b = req_span_val
        AR = (b ** 2) / S
    else:
        b = max(1.0, math.sqrt(S * AR))

    wing_config = params.get("wing_config", "low") # 'low', 'high', 'mid'
    
    # Cięciwa przykadłubowa i końcowa (dla skrzydła trapezowego)
    # S = (cr + ct)/2 * b = cr * (1 + eta)/2 * b
    cr = (2.0 * S) / (b * (1.0 + eta))
    ct = eta * cr
    
    # Średnia Cięciwa Aerodynamiczna (ŚDA / MAC)
    mac = (2.0 / 3.0) * cr * ((1.0 + eta + eta**2) / (1.0 + eta))
    
    # Położenie ŚDA wzdłuż rozpiętości (od płaszczyzny symetrii)
    y_mac = (b / 6.0) * ((1.0 + 2.0 * eta) / (1.0 + eta))
    
    # Położenie krawędzi natarcia ŚDA wzdłuż osi X względem krawędzi natarcia w nasadzie
    sweep_rad = math.radians(sweep_deg)
    # Skos krawędzi natarcia chi_0: tg(chi_0) = tg(chi_25) + (cr - ct)/(2 * b) ...
    tan_chi0 = math.tan(sweep_rad) + (cr * (1.0 - eta)) / (2.0 * b)
    x_le_mac = y_mac * tan_chi0
    
    # 2. Geometria kadłuba (wstępne oszacowanie z liczby pasażerów i rozpiętości)
    if ac_type in ["piston_ga", "uav"]:
        fuselage_len = max(5.5, 0.72 * b)
        fuselage_diam = 1.25 if n_pax <= 4 else 1.50
    elif ac_type == "turboprop_regional":
        fuselage_len = max(18.0, 0.85 * b)
        fuselage_diam = 2.40
    elif ac_type == "jet_business":
        fuselage_len = max(14.0, 0.88 * b)
        fuselage_diam = 1.90
    else: # jet_transport
        fuselage_len = max(28.0, 0.95 * b)
        fuselage_diam = 3.60
        
    fuselage_fineness = fuselage_len / fuselage_diam
    
    # 3. Geometria usterzenia poziomego (UP) metodą współczynnika objętościowego VH
    # V_H = (S_H * L_H) / (S * MAC) (wg Usterzenie_wymiary.pdf str. 2-7 / T. Corke)
    engine_loc = params.get("engine_location", "nose")
    if engine_loc == "nose":
        lh_ratio = 0.58
        lv_ratio = 0.55
    elif engine_loc == "rear":
        lh_ratio = 0.47
        lv_ratio = 0.45
    else: # wing
        lh_ratio = 0.53
        lv_ratio = 0.50

    vh_coeff = float(params.get("v_h", 0.70))
    l_h = lh_ratio * fuselage_len # Ramię usterzenia poziomego od 0.25 ŚDA płata do 0.25 ŚDA usterzenia
    S_h = (vh_coeff * S * mac) / l_h
    ar_h = float(params.get("ar_h", 4.0))
    eta_h = 0.60
    b_h = math.sqrt(S_h * ar_h)
    cr_h = (2.0 * S_h) / (b_h * (1.0 + eta_h))
    ct_h = eta_h * cr_h
    mac_h = (2.0 / 3.0) * cr_h * ((1.0 + eta_h + eta_h**2) / (1.0 + eta_h))
    
    # 4. Geometria usterzenia pionowego (UV) metodą współczynnika objętościowego VV
    # V_V = (S_V * L_V) / (S * b)
    vv_coeff = float(params.get("v_v", 0.050))
    l_v = lv_ratio * fuselage_len # Ramię usterzenia pionowego
    S_v = (vv_coeff * S * b) / l_v
    ar_v = float(params.get("ar_v", 1.6))
    eta_v = 0.65
    h_v = math.sqrt(S_v * ar_v) # Wysokość usterzenia pionowego
    cr_v = (2.0 * S_v) / (h_v * (1.0 + eta_v))
    ct_v = eta_v * cr_v
    mac_v = (2.0 / 3.0) * cr_v * ((1.0 + eta_v + eta_v**2) / (1.0 + eta_v))
    
    # 5. Podwozie (Wheelbase & Track)
    gear_wheelbase = round(0.38 * fuselage_len, 2) # Baza podwozia
    gear_track = round(0.24 * b, 2)               # Rozstaw kół podwozia głównego
    
    # 6. Rozkład obciążenia Schrenka wzdłuż półrozpiętości y w [0, b/2]
    # c_geom(y) = cr * (1 - (1 - eta) * y / (b/2))
    # c_ellip(y) = (4 * S) / (pi * b) * sqrt(1 - (y / (b/2))^2)
    # c_schrenk(y) = (c_geom + c_ellip) / 2
    n_points = 25
    half_span = b / 2.0
    schrenk_data = []
    
    c_ellip_root = (4.0 * S) / (math.pi * b)
    
    for i in range(n_points + 1):
        y = (i / n_points) * half_span
        eta_span = y / half_span # y / (b/2) od 0 do 1
        
        # Cięciwa trapezowa
        c_geom = cr * (1.0 - (1.0 - eta) * eta_span)
        
        # Cięciwa eliptyczna
        arg = max(0.0, 1.0 - (eta_span ** 2))
        c_ellip = c_ellip_root * math.sqrt(arg)
        
        # Rozkład Schrenka (średnia arytmetyczna wg Danilecki wzór 7.1)
        c_schrenk = 0.5 * (c_geom + c_ellip)
        
        # Współczynnik siły nośnej profilu przy Cz_płata = 1.0 (Danilecki wzór 7.2)
        # cz1(y) = 0.5 * (1 + c_ellip / c_geom)
        cz_local_norm = 0.5 * (1.0 + (c_ellip / max(0.001, c_geom)))
        
        schrenk_data.append({
            "y": round(y, 2),
            "eta_span": round(eta_span, 3),
            "c_geom": round(c_geom, 3),
            "c_ellip": round(c_ellip, 3),
            "c_schrenk": round(c_schrenk, 3),
            "cz_local_norm": round(cz_local_norm, 3)
        })

    # Wyznaczenie przekroju krytycznego skrzydła wg metody Schrenka (maksimum cz_local_norm)
    crit_pt = max(schrenk_data[:-1], key=lambda pt: pt["cz_local_norm"])
    max_cz1_schrenk = crit_pt["cz_local_norm"]
    stall_eta_span = crit_pt["eta_span"]
    stall_y_m = crit_pt["y"]

    # Powierzchnie omywane poszczególnych zespołów płatowca (Raymer rozdz. 12.5 / Torenbeek)
    tc_wing = float(params.get("tc_ratio", 0.12))
    tc_tail = 0.09
    s_exposed = max(0.75 * S, S - cr * fuselage_diam)
    s_wet_wing = 2.0 * s_exposed * (1.0 + 0.25 * tc_wing)
    s_wet_fus = math.pi * fuselage_diam * fuselage_len * math.pow(max(0.5, 1.0 - 2.0 / fuselage_fineness), 2.0 / 3.0) * (1.0 + 1.0 / (fuselage_fineness ** 2))
    s_wet_htail = 2.0 * S_h * (1.0 + 0.25 * tc_tail)
    s_wet_vtail = 2.0 * S_v * (1.0 + 0.25 * tc_tail)
    s_wet_total = s_wet_wing + s_wet_fus + s_wet_htail + s_wet_vtail

    return {
        "wing": {
            "S": round(S, 2),
            "S_exposed": round(s_exposed, 2),
            "S_wet": round(s_wet_wing, 2),
            "b": round(b, 2),
            "AR": round(AR, 2),
            "eta": round(eta, 3),
            "cr": round(cr, 3),
            "ct": round(ct, 3),
            "mac": round(mac, 3),
            "y_mac": round(y_mac, 2),
            "x_le_mac": round(x_le_mac, 2),
            "sweep_deg": sweep_deg,
            "dihedral_deg": dihedral_deg,
            "wing_config": wing_config,
            "tc_ratio": tc_wing
        },
        "fuselage": {
            "length": round(fuselage_len, 2),
            "diameter": round(fuselage_diam, 2),
            "fineness": round(fuselage_fineness, 2),
            "S_wet": round(s_wet_fus, 2)
        },
        "horizontal_tail": {
            "S_h": round(S_h, 2),
            "S_wet": round(s_wet_htail, 2),
            "b_h": round(b_h, 2),
            "AR_h": round(ar_h, 2),
            "cr_h": round(cr_h, 3),
            "ct_h": round(ct_h, 3),
            "mac_h": round(mac_h, 3),
            "l_h": round(l_h, 2),
            "vh_coeff": vh_coeff
        },
        "vertical_tail": {
            "S_v": round(S_v, 2),
            "S_wet": round(s_wet_vtail, 2),
            "h_v": round(h_v, 2),
            "AR_v": round(ar_v, 2),
            "cr_v": round(cr_v, 3),
            "ct_v": round(ct_v, 3),
            "mac_v": round(mac_v, 3),
            "l_v": round(l_v, 2),
            "vv_coeff": vv_coeff
        },
        "gear": {
            "wheelbase": gear_wheelbase,
            "track": gear_track
        },
        "wetted_area": {
            "total_m2": round(s_wet_total, 2),
            "swet_over_s": round(s_wet_total / S, 2)
        },
        "schrenk": schrenk_data,
        "schrenk_Pinpoint": {
            "max_cz1": round(max_cz1_schrenk, 3),
            "stall_eta_span": round(stall_eta_span, 3),
            "stall_y_m": round(stall_y_m, 2)
        }
    }
