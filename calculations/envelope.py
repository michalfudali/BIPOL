"""
Moduł obwiedni obciążeń dopuszczalnych V-n (BIPOL I)
Obliczenia obwiedni manewrowej i podmuchowej według przepisów zdatności CS-23 / CS-25.
"""
import math
from calculations.atmosphere import G0, RHO0
from calculations.polish_law import resolve_category, limit_load_factors, envelope_speed_family, SUBCATEGORIES

def calculate_vn_envelope(m0: float, geom: dict, aero: dict, perf: dict, params: dict):
    """
    Parametry:
      - m0: masa startowa [kg]
      - geom: geometria skrzydła (S, b, MAC, AR)
      - aero: cz_max_clean, cx0
      - perf: prędkości vs_clean
      - params: kategoria samolotu (normal, utility, aerobatic, transport)
    """
    S = float(geom["wing"]["S"])
    mac = float(geom["wing"]["mac"])
    AR = float(geom["wing"]["AR"])
    W = m0 * G0
    ws = W / S
    
    vs_clean_ms = float(perf["speeds"]["vs_clean_kmh"]) / 3.6
    v_cr_ms = float(perf["speeds"]["v_cruise_kmh"]) / 3.6
    
    # 1. Określenie dopuszczalnych współczynników przeciążeń wg podstawy projektowej podkategorii
    #    (klasyfikacja Dz. U. 2025 poz. 1137 -> CS-25 / CS-23 / CS-VLA / CS-LSA / CS-22 / LTF-UL / STANAG 4671)
    category_key = resolve_category(params.get("category", "normal"))
    n_max, n_min, load_factor_ref = limit_load_factors(category_key, m0)
    category = envelope_speed_family(category_key)
    cz_max = float(aero["cz_max_clean"])
    cz_min = float(aero.get("cz_min_clean", -0.85))  # Współczynnik siły nośnej ujemnego przeciągnięcia
    
    # 2. Parametry podmuchów wg Danilecki "Konstruowanie samolotów" wzory (2.13)-(2.14) oraz CS-23.341
    # Pochodna współczynnika siły nośnej skończonego płata a_w = dCz/dalpha [1/rad] (wzór Helmbolda-Diedericha ze skosem)
    a_w = float(aero.get("a_w_rad", (2.0 * math.pi * AR) / (AR + 2.0 * ((AR + 4.0) / (AR + 2.0)))))
    
    # Cecha masowa samolotu mu_g = 2 * (m/S) / (rho * MAC * a_w) (Danilecki wzór 2.14 / CS-23.341)
    mu_g = (2.0 * (m0 / S)) / (RHO0 * mac * a_w)
    
    # Współczynnik łagodzenia podmuchu Kg wg Danilecki wzór (2.13) / CS-23.341(b)
    k_g = (0.88 * mu_g) / (5.3 + mu_g)
    
    # Prędkości obliczeniowe podmuchów wg CS-23.333(c) / Danilecki rozdz. 2:
    # U_b = 20.12 m/s (66 fps przy V_B), U_c = 15.24 m/s (50 fps przy V_C), U_d = 7.62 m/s (25 fps przy V_D)
    u_b = 20.12
    u_c = 15.24
    u_d = 7.62
    
    # 3. Prędkości charakterystyczne obwiedni wg CS-23.335 oraz CS-23.345
    # Prędkość manewrowa dodatnia VA = Vs1 * sqrt(n_max)
    v_a_ms = vs_clean_ms * math.sqrt(n_max)
    # Prędkość manewrowa ujemna VG = Vs1 * sqrt(|n_min| * (Cz_max / |Cz_min|))
    v_g_ms = vs_clean_ms * math.sqrt(abs(n_min) * (cz_max / abs(cz_min)))
    
    # Obliczeniowa prędkość przelotowa VC wg CS-23.335(a)
    # 1 lbf/ft² = 47.88026 N/m²; używamy siły ciężkości, nie masy.
    ws_psf = ws / 47.88026
    vc_Factor_kts = 36.0 if category in ("aerobatic", "acrobatic") else 33.0
    v_c_min_ms = (vc_Factor_kts * math.sqrt(max(1.0, ws_psf))) * 0.514444
    v_h_ms = float(perf["speeds"].get("v_max_sl_kmh", v_cr_ms * 3.6 * 1.12)) / 3.6
    # CS-23.335(a)(2): VC nie musi przekraczać 0.9 VH, ale musi być >= VA
    v_c_ms = max(v_cr_ms, v_a_ms * 1.02, min(v_c_min_ms, 0.9 * v_h_ms))
    
    # Prędkość maksymalnej intensywności podmuchów VB wg CS-23.335(d):
    # Punkt przecięcia linii przeciągnięcia dodatniego n = (V / Vs1)^2 z linią podmuchu U_de = 66 fps (20.12 m/s):
    # (1 / Vs1^2) * V_B^2 - ((0.5 * rho0 * a_w * Kg * U_b) / (W/S)) * V_B - 1 = 0
    a_quad = 1.0 / max(1.0, vs_clean_ms ** 2)
    b_quad = (0.5 * RHO0 * a_w * k_g * u_b) / ws
    v_b_intersect_ms = (b_quad + math.sqrt((b_quad ** 2) + 4.0 * a_quad)) / (2.0 * a_quad)
    v_b_ms = min(v_c_ms, max(v_a_ms * 0.85, v_b_intersect_ms))
    
    # Obliczeniowa prędkość nurkowania VD wg CS-23.335(b):
    # Stosunek VD / VC_min wg kategorii: 1.40 (normal), 1.50 (utility), 1.55 (aerobatic) oraz min 1.25 * VC
    vd_factor = 1.55 if category in ("aerobatic", "acrobatic") else (1.50 if category == "utility" else 1.40)
    v_d_ms = max(1.25 * v_c_ms, vd_factor * min(v_c_min_ms, v_c_ms))
    
    # Obliczeniowa prędkość z wypuszczonymi klapami VF wg CS-23.345(a):
    # VF = max(1.4 * Vs1, 1.8 * Vs0)
    vs_lnd_ms = float(perf["speeds"].get("vs_lnd_kmh", vs_clean_ms * 3.6 * 0.82)) / 3.6
    v_f_ms = max(1.4 * vs_clean_ms, 1.8 * vs_lnd_ms)
    
    # Współczynnik bezpieczeństwa konstrukcji nu = 1.5 wg CS-23.303 / Danilecki wzór (1.1)
    safety_factor_nu = 1.5
    n_ult_pos = round(n_max * safety_factor_nu, 2)
    n_ult_neg = round(n_min * safety_factor_nu, 2)
    
    # 4. Generowanie krzywych obwiedni manewrowej do wykresu
    # A. Krzywa przeciągnięcia dodatniego n = (V / Vs1)^2 od V=0 do VA
    stall_pos = []
    n_pts_stall = 18
    for i in range(n_pts_stall + 1):
        v = i * v_a_ms / n_pts_stall
        n = (0.5 * RHO0 * (v ** 2) * cz_max) / ws
        stall_pos.append({"v_kmh": round(v * 3.6, 1), "n": round(min(n, n_max), 2)})
        
    # B. Krzywa przeciągnięcia ujemnego od V=0 do VG
    stall_neg = []
    for i in range(n_pts_stall + 1):
        v = i * v_g_ms / n_pts_stall
        n = (0.5 * RHO0 * (v ** 2) * cz_min) / ws
        stall_neg.append({"v_kmh": round(v * 3.6, 1), "n": round(max(n, n_min), 2)})
        
    # C. Pełny wielokąt obwiedni manewrowej z paraboliczną granicą przeciągnięcia n(V) ~ V^2
    maneuver_polygon = (
        list(stall_pos)
        + [
            {"v_kmh": round(v_c_ms * 3.6, 1), "n": n_max},
            {"v_kmh": round(v_d_ms * 3.6, 1), "n": n_max},
            {"v_kmh": round(v_d_ms * 3.6, 1), "n": 0.0},
            {"v_kmh": round(v_c_ms * 3.6, 1), "n": n_min},
        ]
        + list(reversed(stall_neg))
    )
    
    # D. Linie podmuchów Pratta (Gust envelope): Delta_n = (0.5 * rho0 * V * a_w * K_g * U_de) / (W/S) (Danilecki wzory 2.10-2.13)
    delta_n_b = (0.5 * RHO0 * v_b_ms * a_w * k_g * u_b) / ws
    delta_n_c = (0.5 * RHO0 * v_c_ms * a_w * k_g * u_c) / ws
    delta_n_d = (0.5 * RHO0 * v_d_ms * a_w * k_g * u_d) / ws

    gust_pos = [
        {"v_kmh": 0.0, "n": 1.0},
        {"v_kmh": round(v_b_ms * 3.6, 1), "n": round(1.0 + delta_n_b, 2)},
        {"v_kmh": round(v_c_ms * 3.6, 1), "n": round(1.0 + delta_n_c, 2)},
        {"v_kmh": round(v_d_ms * 3.6, 1), "n": round(1.0 + delta_n_d, 2)}
    ]
    gust_neg = [
        {"v_kmh": 0.0, "n": 1.0},
        {"v_kmh": round(v_b_ms * 3.6, 1), "n": round(1.0 - delta_n_b, 2)},
        {"v_kmh": round(v_c_ms * 3.6, 1), "n": round(1.0 - delta_n_c, 2)},
        {"v_kmh": round(v_d_ms * 3.6, 1), "n": round(1.0 - delta_n_d, 2)}
    ]

    n_gust_max = round(max(1.0 + delta_n_b, 1.0 + delta_n_c, 1.0 + delta_n_d), 2)
    n_gust_min = round(min(1.0 - delta_n_b, 1.0 - delta_n_c, 1.0 - delta_n_d), 2)
    n_dimensioning_pos = round(max(n_max, n_gust_max), 2)
    n_dimensioning_neg = round(min(n_min, n_gust_min), 2)
    n_ult_pos = round(n_dimensioning_pos * safety_factor_nu, 2)
    n_ult_neg = round(n_dimensioning_neg * safety_factor_nu, 2)
        
    return {
        "limits": {
            "n_max": n_max,
            "n_min": n_min,
            "safety_factor_nu": safety_factor_nu,
            "n_ult_pos": n_ult_pos,
            "n_ult_neg": n_ult_neg,
            "n_gust_max": n_gust_max,
            "n_gust_min": n_gust_min,
            "n_dimensioning_pos": n_dimensioning_pos,
            "n_dimensioning_neg": n_dimensioning_neg,
            "category": category_key,
            "category_code": SUBCATEGORIES[category_key]["code"],
            "design_code": SUBCATEGORIES[category_key]["design_code"],
            "load_factor_reference": load_factor_ref
        },
        "speeds": {
            "v_s_kmh": round(vs_clean_ms * 3.6, 1),
            "v_s0_kmh": round(vs_lnd_ms * 3.6, 1),
            "v_a_kmh": round(v_a_ms * 3.6, 1),
            "v_b_kmh": round(v_b_ms * 3.6, 1),
            "v_g_kmh": round(v_g_ms * 3.6, 1),
            "v_c_kmh": round(v_c_ms * 3.6, 1),
            "v_d_kmh": round(v_d_ms * 3.6, 1),
            "v_f_kmh": round(v_f_ms * 3.6, 1)
        },
        "gust_factors": {
            "a_w": round(a_w, 3),
            "mu_g": round(mu_g, 2),
            "k_g": round(k_g, 3),
            "u_b_ms": u_b,
            "u_c_ms": u_c,
            "u_d_ms": u_d,
            "delta_n_b": round(delta_n_b, 3),
            "delta_n_c": round(delta_n_c, 3),
            "delta_n_d": round(delta_n_d, 3)
        },
        "stall_pos": stall_pos,
        "stall_neg": stall_neg,
        "maneuver_polygon": maneuver_polygon,
        "gust_pos": gust_pos,
        "gust_neg": gust_neg
    }

