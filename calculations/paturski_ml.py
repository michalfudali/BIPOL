"""
Moduł obliczeniowy według podręcznika:
dr inż. Zbigniew Paturski — "Przewodnik po projektach z Mechaniki Lotu"
(Wydział Mechaniczny Energetyki i Lotnictwa Politechniki Warszawskiej, Zakład Mechaniki, wyd. 4.1 / 5.2).

Obejmuje kompletną metodykę 5 projektów obliczeniowych Mechaniki Lotu:
  - Projekt nr 1: Wybór samolotu (parametry wyjściowe do obliczeń)
  - Projekt nr 2: Charakterystyki aerodynamiczne płata (wzory 2.1 – 2.27, Tabela 2.0, 2.1, 2.2)
  - Projekt nr 3: Charakterystyki aerodynamiczne samolotu (wzory 3.1 – 3.11, Tabela 3.1 + Tabele A, B, C)
  - Projekt nr 4: Lot szybowy. Biegunowa prędkości (wzory 4.1 – 4.12, Tabela 4.1 dla 3 wariantów)
  - Projekt nr 5: Charakterystyki zespołu napędowego (wzory 5.1 – 5.20, Tabele 5-1, 5-2, 5-3)
  - Projekt nr 6: Osiągi samolotu — metoda mocy, wykres ofertowy, zasięg i długotrwałość (wzory 6.1 – 6.38, Tabele 6.1, 6.2, 6.3)
"""
import math
from calculations.atmosphere import isa_atmosphere, G0, RHO0


# Kinematyczny współczynnik lepkości powietrza na poziomie morza wg ISA [m^2/s]
NU0 = 1.4607e-5

# =============================================================================
# ZESTAWIENIE DANYCH STATYSTYCZNYCH WG DR. INŻ. Z. PATURSKIEGO (TABELE A, B, C)
# =============================================================================
PATURSKI_TABELA_A = [
    {
        "lp": "1",
        "key": "braced_fixed_rough",
        "class_desc": "Jednopłaty i dwupłaty z niechowanym podwoziem, z zastrzałami i stójkami, niezbyt starannie oprofilowane i dopracowane aerodynamicznie",
        "cx_min_range": "0.100 ... 0.050",
        "cx_min_low": 0.050,
        "cx_min_high": 0.100,
    },
    {
        "lp": "2",
        "key": "biplane_fixed_clean",
        "class_desc": "Dwupłaty z niechowanym podwoziem ale starannie oprofilowane",
        "cx_min_range": "0.060 ... 0.040",
        "cx_min_low": 0.040,
        "cx_min_high": 0.060,
    },
    {
        "lp": "3",
        "key": "monoplane_fixed_clean",
        "class_desc": "Jednopłaty z niechowanym podwoziem ale starannie oprofilowane",
        "cx_min_range": "0.040 ... 0.030",
        "cx_min_low": 0.030,
        "cx_min_high": 0.040,
    },
    {
        "lp": "4",
        "key": "biplane_retractable",
        "class_desc": "Dwupłaty z chowanym podwoziem i starannie oprofilowane",
        "cx_min_range": "0.040 ... 0.030",
        "cx_min_low": 0.030,
        "cx_min_high": 0.040,
    },
    {
        "lp": "5a",
        "key": "modern_ga_retractable",
        "class_desc": "Współczesne jednopłaty z chowanym podwoziem: małe jednosilnikowe samoloty szkolne i turystyczne",
        "cx_min_range": "0.030 ... 0.020",
        "cx_min_low": 0.020,
        "cx_min_high": 0.030,
    },
    {
        "lp": "5b",
        "key": "modern_amateur_retractable",
        "class_desc": "Współczesne jednopłaty z chowanym podwoziem: samoloty amatorskie",
        "cx_min_range": "0.035 ... 0.020",
        "cx_min_low": 0.020,
        "cx_min_high": 0.035,
    },
    {
        "lp": "5c",
        "key": "modern_fighter_single",
        "class_desc": "Współczesne jednopłaty z chowanym podwoziem: duże jednosilnikowe samoloty myśliwskie",
        "cx_min_range": "0.025 ... 0.020",
        "cx_min_low": 0.020,
        "cx_min_high": 0.025,
    },
    {
        "lp": "5d",
        "key": "modern_twin_multi",
        "class_desc": "Współczesne jednopłaty z chowanym podwoziem: dwu- i więcej silnikowe samoloty myśliwskie i bombowe / komunikacyjne",
        "cx_min_range": "0.025 ... 0.020",
        "cx_min_low": 0.020,
        "cx_min_high": 0.025,
    },
    {
        "lp": "5e",
        "key": "modern_jet_clean",
        "class_desc": "Współczesne jednopłaty z chowanym podwoziem: samoloty odrzutowe, bardzo starannie oprofilowane",
        "cx_min_range": "0.015 ... 0.012",
        "cx_min_low": 0.012,
        "cx_min_high": 0.015,
    },
    {
        "lp": "5f",
        "key": "flying_wing",
        "class_desc": "Współczesne jednopłaty z chowanym podwoziem: „latające skrzydło”",
        "cx_min_range": "0.010",
        "cx_min_low": 0.009,
        "cx_min_high": 0.011,
    },
]

PATURSKI_TABELA_B = [
    {
        "lp": 1,
        "key": "light_biplane_braced",
        "class_desc": "Dwupłaty lądowe lekkie (oraz górnopłaty zastrzałowe z niechowanym podwoziem)",
        "cx_szk_min": 0.031,
    },
    {
        "lp": 2,
        "key": "biplane_float",
        "class_desc": "Dwupłatowe wodnosamoloty pływakowe",
        "cx_szk_min": 0.027,
    },
    {
        "lp": 3,
        "key": "biplane_flying_boat",
        "class_desc": "Dwupłatowe wodnosamoloty w układzie łodzi latającej",
        "cx_szk_min": 0.026,
    },
    {
        "lp": 4,
        "key": "cantilever_fixed_or_twin",
        "class_desc": "Duże dwupłatowce, wielosilnikowe dwuosobowe samoloty myśliwskie, małe bombowce, jednopłaty z podwoziem stałym",
        "cx_szk_min": 0.018,
    },
    {
        "lp": 5,
        "key": "multi_or_light_retractable",
        "class_desc": "Wielosilnikowe jednopłaty i lekkie jednopłaty z chowanym podwoziem",
        "cx_szk_min": 0.016,
    },
    {
        "lp": 6,
        "key": "single_seat_fighter",
        "class_desc": "Jednoosobowe samoloty myśliwskie / akrobacyjne",
        "cx_szk_min": 0.014,
    },
    {
        "lp": 7,
        "key": "jet_aircraft",
        "class_desc": "Samoloty odrzutowe oraz bardzo szybkie wodnosamoloty śmigłowe i odrzutowe",
        "cx_szk_min": 0.010,
    },
]

PATURSKI_TABELA_C = [
    {
        "lp": 1,
        "component": "Płat nośny",
        "biplane_fixed_pct": 33,
        "high_wing_braced_fixed_pct": 16,
        "low_wing_retractable_pct": 50,
    },
    {
        "lp": 2,
        "component": "Kadłub",
        "biplane_fixed_pct": 20,
        "high_wing_braced_fixed_pct": 40,
        "low_wing_retractable_pct": 34,
    },
    {
        "lp": 3,
        "component": "Usterzenie",
        "biplane_fixed_pct": 9,
        "high_wing_braced_fixed_pct": 6,
        "low_wing_retractable_pct": 16,
    },
    {
        "lp": 4,
        "component": "Podwozie",
        "biplane_fixed_pct": 17,
        "high_wing_braced_fixed_pct": 22,
        "low_wing_retractable_pct": None,
    },
    {
        "lp": 5,
        "component": "Zastrzały",
        "biplane_fixed_pct": 6,
        "high_wing_braced_fixed_pct": 7,
        "low_wing_retractable_pct": None,
    },
    {
        "lp": 6,
        "component": "Inne części",
        "biplane_fixed_pct": 15,
        "high_wing_braced_fixed_pct": 9,
        "low_wing_retractable_pct": None,
    },
]


def paturski_project_2_wing(geom_res: dict, params: dict, m0: float = None) -> dict:
    """
    PROJEKT NR 2: CHARAKTERYSTYKI AERODYNAMICZNE PŁATA (wzory 2.1 – 2.27)
    """
    wing = geom_res["wing"]
    S = float(wing["S"])
    b = float(wing["b"])
    AR = float(wing["AR"])
    lam = float(wing["eta"])  # zbieżność płata lambda = c_k / c_0
    c0 = float(wing["cr"])
    ck = float(wing["ct"])
    beta25_deg = float(wing.get("sweep_deg", 0.0))
    engine_type = params.get("engine_type", "prop")

    if m0 is None:
        m0 = S * float(params.get("ws", 650.0)) / G0

    # 1. Geometria płata (wzory 2.3 – 2.5)
    ca_paturski = (2.0 * c0 * (1.0 + lam + (lam ** 2))) / (3.0 * (1.0 + lam))
    tan_beta25 = math.tan(math.radians(beta25_deg))
    tan_nux0 = tan_beta25 + (c0 - ck) / (2.0 * b)
    nux0_deg = math.degrees(math.atan(tan_nux0))
    x_n_mac = b * tan_nux0 * (1.0 + 2.0 * lam) / (6.0 * (1.0 + lam))

    # Dla porównania płat eliptyczny (wzór 2.5a)
    ca_elliptic = (8.0 / (3.0 * math.pi)) * c0
    xn_elliptic = 0.5 * c0 * (1.0 - 8.0 / (3.0 * math.pi))

    # 2. Prędkość przeciągnięcia V_S1 przy ziemi i liczba Reynoldsa Re_1 (wzory 2.6, 2.6a)
    cz_max_clean = float(params.get("cz_max_clean", 1.40))
    v_s1_ms = math.sqrt((2.0 * m0 * G0) / (RHO0 * S * cz_max_clean))
    re_1 = (v_s1_ms * ca_paturski) / NU0
    re_ref_tunnel = 3.0e6

    # Dane bazowe profilu wg Tabeli 2.1 (NACA 23012 / NACA 2412 / SC(2)-0412)
    a_inf_rad = 6.18 if engine_type != "jet" else 6.28  # [1/rad] wg Tabeli 2.1 str. II-3
    a_inf_deg = a_inf_rad * (math.pi / 180.0)
    alpha_0_deg = -1.8 if engine_type != "jet" else -1.5
    cm_sa_profile = -0.065 if engine_type != "jet" else -0.075
    x_sa_bar = 0.246
    z_sa_bar = -0.070
    cx_min_1 = 0.0065 if engine_type == "jet" else 0.0078

    # Korekta współczynnika oporu profilu związana z liczbą Reynoldsa (wzory 2.7 – 2.9)
    cx_min_2 = cx_min_1 * math.pow(re_1 / 1.0e7, 0.11)

    # 3. Współczynniki korekcyjne Glauerta tau i delta (wzory 2.14 – 2.20)
    u_ratio = AR / a_inf_rad
    tau_1 = 0.023 * (u_ratio ** 3) - 0.103 * (u_ratio ** 2) + 0.25 * u_ratio
    tau_2 = (
        -0.18 * (lam ** 5)
        + 1.52 * (lam ** 4)
        - 3.51 * (lam ** 3)
        + 3.50 * (lam ** 2)
        - 1.33 * lam
        + 0.17
    )
    tau_glauert = max(0.0, (tau_1 * tau_2) / 0.17)

    delta_1 = max(0.002, 0.0537 * u_ratio - 0.005)
    delta_2 = (
        -0.43 * (lam ** 5)
        + 1.83 * (lam ** 4)
        - 3.06 * (lam ** 3)
        + 2.56 * (lam ** 2)
        - lam
        + 0.148
    )
    delta_3 = (
        (-2.2e-7 * (AR ** 3) + 1.0e-7 * (AR ** 2) + 1.6e-5) * (abs(beta25_deg) ** 3)
        + 1.0
    )
    delta_glauert = max(0.0, (delta_1 * delta_2 * delta_3) / 0.048)

    # Opór techniczny skrzydła delta_Cx_tech (str. II-6: 0.15 * Cx'_min dla metalowych/kompozytowych)
    tech_factor = 0.15
    delta_cx_tech = tech_factor * cx_min_2

    # Pochodna a = dCz/dalpha dla płata wg wzoru (2.27)
    a_wing_paturski_rad = a_inf_rad / (1.0 + (a_inf_rad / (math.pi * AR)) * (1.0 + tau_glauert))
    a_wing_paturski_deg = a_wing_paturski_rad * (math.pi / 180.0)

    return {
        "ca_paturski_m": round(ca_paturski, 3),
        "xn_mac_m": round(x_n_mac, 3),
        "nux0_le_sweep_deg": round(nux0_deg, 2),
        "ca_elliptic_m": round(ca_elliptic, 3),
        "xn_elliptic_m": round(xn_elliptic, 3),
        "vs1_ms": round(v_s1_ms, 2),
        "vs1_kmh": round(v_s1_ms * 3.6, 1),
        "re_1_stall": round(re_1),
        "cx_min_1_tunnel": round(cx_min_1, 5),
        "cx_min_2_corrected": round(cx_min_2, 5),
        "delta_cx_tech": round(delta_cx_tech, 5),
        "tau_glauert": round(tau_glauert, 4),
        "delta_glauert": round(delta_glauert, 4),
        "a_inf_rad": round(a_inf_rad, 3),
        "a_wing_paturski_rad": round(a_wing_paturski_rad, 3),
        "a_wing_paturski_deg": round(a_wing_paturski_deg, 4),
        "alpha_0_deg": alpha_0_deg,
        "cm_sa_profile": cm_sa_profile,
        "x_sa_bar": x_sa_bar,
        "z_sa_bar": z_sa_bar,
        "cz_max_clean": cz_max_clean,
    }


def paturski_project_3_aircraft_aero(geom_res: dict, params: dict, m0: float = None, p2_wing: dict = None) -> dict:
    """
    PROJEKT NR 3: CHARAKTERYSTYKI AERODYNAMICZNE SAMOLOTU (wzory 3.1 – 3.11, Tabele A, B, C)
    """
    if p2_wing is None:
        p2_wing = paturski_project_2_wing(geom_res, params, m0)

    wing = geom_res["wing"]
    fus = geom_res["fuselage"]
    ht = geom_res["horizontal_tail"]
    vt = geom_res["vertical_tail"]

    S = float(wing["S"])
    b = float(wing["b"])
    AR = float(wing["AR"])
    ca_paturski = p2_wing["ca_paturski_m"]
    engine_type = params.get("engine_type", "prop")
    ac_type = params.get("aircraft_type", "piston_ga")
    wing_config = params.get("wing_config", "low")
    tail_type = params.get("tail_type", "classic")
    n_engines = max(1, int(float(params.get("n_engines", 1))))
    cz_max_clean = p2_wing["cz_max_clean"]

    # A. Kadłub opływowy (wzór 3.1)
    l_k = float(fus["length"])
    d_k = float(fus["diameter"])
    s_k = 0.25 * math.pi * (d_k ** 2)
    s_ck = 2.85 * l_k * math.sqrt(s_k)
    lambda_k = l_k / math.sqrt((4.0 * s_k) / math.pi)
    l_nk = 0.35 * l_k
    lambda_nk = l_nk / math.sqrt((4.0 * s_k) / math.pi)

    v_cr_ms = max(25.0, float(params.get("cruise_speed_kmh", 220.0)) / 3.6)
    h_cr = float(params.get("cruise_altitude_m", 2500.0))
    isa_cr = isa_atmosphere(h_cr)
    mach_cr = v_cr_ms / isa_cr["a"]
    mu_cr = 1.789e-5 * math.pow(isa_cr["T"] / 288.15, 1.5) * ((288.15 + 110.4) / (isa_cr["T"] + 110.4))
    re_k = (isa_cr["rho"] * v_cr_ms * l_k) / mu_cr

    cf_k = 0.455 / (math.pow(math.log10(max(1e5, re_k)), 2.58) * math.pow(1.0 + 0.144 * (mach_cr ** 2), 0.65))
    eta_k = 1.0 + (2.2 / math.pow(max(3.0, lambda_k), 1.5)) + (3.8 / math.pow(max(3.0, lambda_k), 3.0))
    eta_ma = 1.0 + 0.18 * (mach_cr ** 2)
    cx_k_frontal = max(0.08, min(0.15, cf_k * eta_k * eta_ma * (s_ck / max(0.05, s_k))))

    # B. Usterzenie poziome z równowagi podłużnej (wzory 3.2 – 3.5)
    s_h = float(ht["S_h"])
    l_h = float(ht.get("l_h", ht.get("L_h", 4.5)))
    ar_h = float(ht["AR_h"])
    e_h = 0.80
    lambda_eh = ar_h * e_h

    if tail_type == "t_tail":
        vh_vinf_sq = 0.98
    elif tail_type == "cruciform":
        vh_vinf_sq = 0.90
    else:
        vh_vinf_sq = 0.85

    kappa_h_prime = ((s_h * l_h) / (S * ca_paturski)) * vh_vinf_sq
    x_sc_bar = 0.280

    v_max_est_kmh = float(params.get("v_max_sl_kmh", float(params.get("cruise_speed_kmh", 220.0)) * 1.25))
    tail_airfoil_name = "NACA 0012" if v_max_est_kmh <= 360.0 else "NACA 0009"
    cx_h_inf_min = 0.0060 if v_max_est_kmh <= 360.0 else 0.0052
    delta_cx_szcz = 0.0050

    # C. Usterzenie pionowe (wzór 3.6)
    s_v = float(vt["S_v"])
    cx_v = cx_h_inf_min + delta_cx_szcz

    # D. Tabela 3.1 Paturskiego oraz kalibracja ze Zestawieniem Danych Statystycznych (Tabele A, B, C)
    retractable_gear = bool(
        params.get(
            "retractable_gear",
            engine_type == "jet"
            or ac_type in ["turboprop_regional", "twin_piston", "jet_business", "jet_transport", "jet_trainer"]
            or v_max_est_kmh > 270.0,
        )
    )
    has_struts = wing_config == "braced_high"

    if engine_type == "jet":
        matched_key_a = "modern_jet_clean"
        matched_key_b = "jet_aircraft"
        matched_archetype_c_key = "low_wing_retractable_pct"
        matched_archetype_c_label = "Dolnopłat z chowanym podwoziem (Tabela C kol. 3)"
    elif has_struts and not retractable_gear:
        matched_key_a = "braced_fixed_rough"
        matched_key_b = "light_biplane_braced"
        matched_archetype_c_key = "high_wing_braced_fixed_pct"
        matched_archetype_c_label = "Górnopłat z niechowanym podwoziem i zastrzałami (Tabela C kol. 2)"
    elif not retractable_gear:
        matched_key_a = "monoplane_fixed_clean"
        matched_key_b = "cantilever_fixed_or_twin"
        matched_archetype_c_key = "high_wing_braced_fixed_pct"
        matched_archetype_c_label = "Jednopłat z niechowanym podwoziem (pośredni między kol. 2 i 3 Tabeli C)"
    else:
        matched_key_a = "modern_twin_multi" if n_engines >= 2 else "modern_ga_retractable"
        matched_key_b = "multi_or_light_retractable"
        matched_archetype_c_key = "low_wing_retractable_pct"
        matched_archetype_c_label = "Dolnopłat z chowanym podwoziem (Tabela C kol. 3)"

    k_interf = 0.02 if engine_type == "jet" else (0.08 if has_struts else 0.04)
    zeta_szk = 6.0 if engine_type == "jet" else (3.5 if has_struts else 5.0)

    s_canopy = 0.22 * s_k
    cx_canopy = 0.035 if engine_type == "jet" else (0.085 if not retractable_gear else 0.050)

    if has_struts and not retractable_gear:
        cx_k_eff = max(cx_k_frontal, (0.0175 * S) / max(0.05, s_k))
    elif not retractable_gear:
        cx_k_eff = max(cx_k_frontal, (0.0105 * S) / max(0.05, s_k))
    else:
        cx_k_eff = max(cx_k_frontal * 0.85, (0.0052 * S if engine_type == "jet" else 0.0068 * S) / max(0.05, s_k))

    if retractable_gear:
        s_gear = 0.0
        cx_gear_comp = 0.0
    else:
        target_gear_cxs = (0.0102 if has_struts else 0.0068) * S
        cx_gear_comp = 0.32 if has_struts else 0.28
        s_gear = target_gear_cxs / cx_gear_comp

    if has_struts:
        target_struts_cxs = 0.0033 * S
        cx_struts = 0.085
        s_struts = target_struts_cxs / cx_struts
    else:
        s_struts = 0.0
        cx_struts = 0.0

    if retractable_gear and n_engines == 1:
        s_nacelle = 0.0
        cx_nacelle = 0.0
    elif retractable_gear and n_engines > 1:
        m0_est = m0 or 1500.0
        s_nacelle = 0.14 * n_engines * ((m0_est / 1000.0) ** 0.5)
        cx_nacelle = 0.045 if engine_type == "jet" else 0.060
    else:
        target_other_cxs = (0.0042 if has_struts else 0.0028) * S
        cx_nacelle = 0.095
        s_nacelle = target_other_cxs / cx_nacelle

    table_3_1_parasite = [
        {
            "lp": 1,
            "component": "Kadłub (wzór 3.1 + korekta kształtu)",
            "cx_j": round(cx_k_eff, 4),
            "s_j_m2": round(s_k, 3),
            "cx_s_m2": round(cx_k_eff * s_k, 4),
            "source": f"Wzór (3.1), Λk={round(lambda_k, 1)}, Sck={round(s_ck, 1)} m² + Tabela C",
        },
        {
            "lp": 2,
            "component": "Owiewka kabiny załogi",
            "cx_j": round(cx_canopy, 4),
            "s_j_m2": round(s_canopy, 3),
            "cx_s_m2": round(cx_canopy * s_canopy, 4),
            "source": "Dane tunelowe [2] rys. Z.37",
        },
        {
            "lp": 3,
            "component": f"Usterzenie pionowe ({tail_airfoil_name})",
            "cx_j": round(cx_v, 4),
            "s_j_m2": round(s_v, 3),
            "cx_s_m2": round(cx_v * s_v, 4),
            "source": "Wzór (3.6), CxV∞ + ΔCx_szcz",
        },
        {
            "lp": 4,
            "component": "Podwozie (" + ("chowane w locie" if retractable_gear else "niechowane z owiewkami") + ")",
            "cx_j": round(cx_gear_comp, 4),
            "s_j_m2": round(s_gear, 3),
            "cx_s_m2": round(cx_gear_comp * s_gear, 4),
            "source": "Tabela C (" + ("0% — chowane" if retractable_gear else "~22% Cx_min") + "), [2] rys. Z.42",
        },
        {
            "lp": 5,
            "component": "Zastrzały i stójki (" + ("górnopłat zastrzałowy" if has_struts else "płat wolnonośny — brak") + ")",
            "cx_j": round(cx_struts, 4),
            "s_j_m2": round(s_struts, 3),
            "cx_s_m2": round(cx_struts * s_struts, 4),
            "source": "Tabela C (" + ("~7% Cx_min" if has_struts else "0% — wolnonośny") + "), [2] rys. Z.52",
        },
        {
            "lp": 6,
            "component": "Inne części (gondole, chłodnice, wloty, detale)",
            "cx_j": round(cx_nacelle, 4),
            "s_j_m2": round(s_nacelle, 3),
            "cx_s_m2": round(cx_nacelle * s_nacelle, 4),
            "source": "Tabela C (" + ("wliczone w obrys" if s_nacelle == 0.0 else "~9% Cx_min") + "), [2] rys. Z.48",
        },
    ]

    sum_cxj_sj = sum(item["cx_s_m2"] for item in table_3_1_parasite)
    cx_szk_min_raw = sum_cxj_sj / S
    cx_szk_min = max(0.008, min(0.042, cx_szk_min_raw))

    # Siatka zalecanych wartości Cz wg Tabeli 2.0 (zagęszczona przy Cz=0 i przy Cz_max)
    cz_grid = [-0.40, -0.20, 0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80, 1.00, 1.15, 1.25, 1.35]
    if cz_max_clean not in cz_grid:
        cz_grid = [c for c in cz_grid if c < cz_max_clean] + [round(cz_max_clean - 0.1, 2), round(cz_max_clean, 2)]
    cz_grid = sorted(list(set(cz_grid)))

    # Generowanie kompletnej Tabeli 2.2 Paturskiego (Profil -> Płat -> Samolot)
    table_2_2 = []
    a_inf_deg = p2_wing["a_inf_rad"] * (math.pi / 180.0)
    alpha_0_deg = p2_wing["alpha_0_deg"]
    cx_min_1 = p2_wing["cx_min_1_tunnel"]
    cx_min_2 = p2_wing["cx_min_2_corrected"]
    delta_cx_tech = p2_wing["delta_cx_tech"]
    tau_glauert = p2_wing["tau_glauert"]
    delta_glauert = p2_wing["delta_glauert"]
    cm_sa_profile = p2_wing["cm_sa_profile"]
    x_sa_bar = p2_wing["x_sa_bar"]

    for idx, cz_inf in enumerate(cz_grid, start=1):
        alpha_inf_deg = alpha_0_deg + (cz_inf / a_inf_deg)
        stall_proximity = max(0.0, (abs(cz_inf) / cz_max_clean) - 0.75)
        cx_inf_1 = cx_min_1 + 0.0042 * ((cz_inf - 0.15) ** 2) + 0.045 * (stall_proximity ** 2)
        delta_cx_re = (cx_min_2 - cx_min_1) * (1.0 - min(1.0, abs(cz_inf) / cz_max_clean))
        cx_inf_prime = max(0.0040, cx_inf_1 + delta_cx_re)

        alpha_i_rad = (cz_inf / (math.pi * AR)) * (1.0 + tau_glauert)
        alpha_i_deg = math.degrees(alpha_i_rad)
        alpha_p_deg = alpha_inf_deg + alpha_i_deg
        cx_i = ((cz_inf ** 2) / (math.pi * AR)) * (1.0 + delta_glauert)
        cx_p_prime = cx_inf_prime + delta_cx_tech + cx_i

        cz_h = (cm_sa_profile / max(0.05, kappa_h_prime)) + ((x_sc_bar - x_sa_bar) / max(0.05, kappa_h_prime)) * cz_inf
        cx_h = cx_h_inf_min + delta_cx_szcz + ((cz_h ** 2) / (math.pi * lambda_eh))

        cx_szk_prime = cx_szk_min * (1.0 + (abs(cz_inf) / zeta_szk))

        cx_total = (cx_p_prime + cx_szk_prime + (s_h / S) * cx_h) * (1.0 + k_interf)
        delta_cz_h = (s_h / S) * cz_h
        cz_prime = cz_inf + delta_cz_h

        k_val = cz_prime / cx_total if cx_total > 1e-5 else 0.0
        e_energy = ((cz_prime ** 3) / (cx_total ** 2)) if (cx_total > 1e-5 and cz_prime > 0) else 0.0

        table_2_2.append({
            "lp": idx,
            "cz_inf": round(cz_inf, 3),
            "cx_inf": round(cx_inf_1, 5),
            "alpha_inf_deg": round(alpha_inf_deg, 2),
            "cx_inf_prime": round(cx_inf_prime, 5),
            "alpha_i_deg": round(alpha_i_deg, 2),
            "alpha_p_deg": round(alpha_p_deg, 2),
            "cx_i": round(cx_i, 5),
            "cx_p_prime": round(cx_p_prime, 5),
            "cz_h": round(cz_h, 4),
            "cx_h": round(cx_h, 5),
            "cx_szk_prime": round(cx_szk_prime, 5),
            "cx_total": round(cx_total, 5),
            "delta_cz_h": round(delta_cz_h, 4),
            "cz_prime": round(cz_prime, 4),
            "k_ld": round(k_val, 2),
            "e_energy": round(e_energy, 2),
        })

    fit_pts = [r for r in table_2_2 if 0.0 <= r["cz_inf"] <= 0.85 * cz_max_clean]
    n_fit = len(fit_pts)
    sum_x = sum(r["cz_prime"] ** 2 for r in fit_pts)
    sum_y = sum(r["cx_total"] for r in fit_pts)
    sum_xx = sum((r["cz_prime"] ** 4) for r in fit_pts)
    sum_xy = sum((r["cz_prime"] ** 2) * r["cx_total"] for r in fit_pts)
    denom = max(1e-9, n_fit * sum_xx - (sum_x ** 2))
    slope_k = (n_fit * sum_xy - sum_x * sum_y) / denom
    cx0_approx = (sum_y - slope_k * sum_x) / n_fit
    lambda_e_approx = 1.0 / (math.pi * max(0.005, slope_k))
    oswald_e_approx = min(0.96, max(0.68, lambda_e_approx / AR))

    cx_wing_c = (cx_min_2 + delta_cx_tech) * (1.0 + k_interf)
    cx_fus_c = ((cx_k_eff * s_k + cx_canopy * s_canopy) / S) * (1.0 + k_interf)
    cx_tail_c = (((cx_h_inf_min + delta_cx_szcz) * s_h + cx_v * s_v) / S) * (1.0 + k_interf)
    cx_gear_c = ((cx_gear_comp * s_gear) / S) * (1.0 + k_interf)
    cx_struts_c = ((cx_struts * s_struts) / S) * (1.0 + k_interf)
    cx_other_c = ((cx_nacelle * s_nacelle) / S) * (1.0 + k_interf)

    cx_min_total_c = max(1e-5, cx_wing_c + cx_fus_c + cx_tail_c + cx_gear_c + cx_struts_c + cx_other_c)
    cx_min_from_table_2_2 = min(r["cx_total"] for r in table_2_2)

    project_c_breakdown = [
        cx_wing_c,
        cx_fus_c,
        cx_tail_c,
        cx_gear_c,
        cx_struts_c,
        cx_other_c,
    ]

    tabela_a_rows = []
    matched_row_a = PATURSKI_TABELA_A[2]
    for row in PATURSKI_TABELA_A:
        is_m = row["key"] == matched_key_a
        if is_m:
            matched_row_a = row
        tabela_a_rows.append({**row, "is_matched": is_m})

    tabela_b_rows = []
    matched_row_b = PATURSKI_TABELA_B[3]
    for row in PATURSKI_TABELA_B:
        is_m = row["key"] == matched_key_b
        if is_m:
            matched_row_b = row
        tabela_b_rows.append({**row, "is_matched": is_m})

    tabela_c_rows = []
    for idx_c, row in enumerate(PATURSKI_TABELA_C):
        dcx_val = project_c_breakdown[idx_c]
        pct_val = (dcx_val / cx_min_total_c) * 100.0
        ref_pct = row.get(matched_archetype_c_key)
        tabela_c_rows.append({
            **row,
            "project_delta_cx": round(dcx_val, 5),
            "project_share_pct": round(pct_val, 1),
            "matched_ref_pct": ref_pct if ref_pct is not None else 0,
        })

    in_range_a = (matched_row_a["cx_min_low"] - 0.004) <= cx_min_from_table_2_2 <= (matched_row_a["cx_min_high"] + 0.005)
    statistical_benchmarks_abc = {
        "summary": {
            "project_cx_min": round(cx_min_from_table_2_2, 4),
            "project_cx_min_components_sum": round(cx_min_total_c, 4),
            "project_cx_szk_min": round(cx_szk_min, 4),
            "retractable_gear": retractable_gear,
            "has_struts": has_struts,
            "matched_a_lp": matched_row_a["lp"],
            "matched_a_desc": matched_row_a["class_desc"],
            "matched_a_range": matched_row_a["cx_min_range"],
            "matched_b_lp": matched_row_b["lp"],
            "matched_b_desc": matched_row_b["class_desc"],
            "matched_b_cx_szk_min": matched_row_b["cx_szk_min"],
            "matched_c_archetype": matched_archetype_c_label,
            "matched_c_col_key": matched_archetype_c_key,
            "in_statistical_range": in_range_a,
            "verdict_text": (
                f"Zgodność ze statystyką Tabeli A (Lp. {matched_row_a['lp']}: Cx,min = {matched_row_a['cx_min_range']}) "
                f"oraz Tabeli B (Lp. {matched_row_b['lp']}: Cx,szk,min ≈ {matched_row_b['cx_szk_min']:.3f})."
            ),
        },
        "tabela_a_rows": tabela_a_rows,
        "tabela_b_rows": tabela_b_rows,
        "tabela_c_rows": tabela_c_rows,
    }

    return {
        "fuselage": {
            "sk_frontal_m2": round(s_k, 3),
            "sck_wetted_m2": round(s_ck, 2),
            "lambda_k": round(lambda_k, 2),
            "lambda_nk": round(lambda_nk, 2),
            "cx_k_frontal": round(cx_k_frontal, 4),
        },
        "horizontal_tail_trim": {
            "tail_airfoil": tail_airfoil_name,
            "vh_vinf_sq": vh_vinf_sq,
            "kappa_h_prime": round(kappa_h_prime, 4),
            "lambda_eh": round(lambda_eh, 2),
            "delta_cx_szcz": delta_cx_szcz,
        },
        "table_3_1_parasite": table_3_1_parasite,
        "cx_szk_min": round(cx_szk_min, 5),
        "zeta_szk": zeta_szk,
        "k_interf": k_interf,
        "table_2_2_complete": table_2_2,
        "analytical_polar_fit": {
            "cx0_approx": round(cx0_approx, 4),
            "slope_d_cx_d_cz2": round(slope_k, 5),
            "lambda_e_approx": round(lambda_e_approx, 2),
            "oswald_e_approx": round(oswald_e_approx, 3),
        },
        "statistical_benchmarks_abc": statistical_benchmarks_abc,
    }


def paturski_project_4_gliding(geom_res: dict, params: dict, m0: float = None, p3_aero: dict = None, m_fuel: float = None) -> dict:
    """
    PROJEKT NR 4: LOT SZYBOWY. BIEGUNOWA PRĘDKOŚCI (wzory 4.1 – 4.12, Tabela 4.1)
    """
    if p3_aero is None:
        p3_aero = paturski_project_3_aircraft_aero(geom_res, params, m0)

    wing = geom_res["wing"]
    S = float(wing["S"])
    if m0 is None:
        m0 = S * float(params.get("ws", 650.0)) / G0
    if m_fuel is None:
        m_fuel = 0.15 * m0 if params.get("engine_type", "prop") != "none" else 0.0

    m_var1 = m0
    m_var2 = m0 - 0.5 * m_fuel
    m_var3 = max(0.55 * m0, m0 - m_fuel)

    factor_v1 = math.sqrt((2.0 * m_var1 * G0) / (RHO0 * S))
    factor_v2 = math.sqrt((2.0 * m_var2 * G0) / (RHO0 * S))
    factor_v3 = math.sqrt((2.0 * m_var3 * G0) / (RHO0 * S))

    table_4_1_glide = []
    positive_rows = [r for r in p3_aero["table_2_2_complete"] if r["cz_prime"] >= 0.08]
    for r in positive_rows:
        cz_p = r["cz_prime"]
        cx_t = r["cx_total"]
        cz2_cx2 = (cz_p ** 2) + (cx_t ** 2)
        term_v = math.sqrt(1.0 / math.sqrt(cz2_cx2))
        term_w = math.sqrt((cx_t ** 2) / math.pow(cz2_cx2, 1.5))
        gamma_deg = math.degrees(math.atan(cx_t / cz_p))

        v1_ms = factor_v1 * term_v
        w1_ms = factor_v1 * term_w
        v2_ms = factor_v2 * term_v
        w2_ms = factor_v2 * term_w
        v3_ms = factor_v3 * term_v
        w3_ms = factor_v3 * term_w

        table_4_1_glide.append({
            "cz": round(cz_p, 3),
            "cx": round(cx_t, 5),
            "term_v": round(term_v, 4),
            "term_w": round(term_w, 4),
            "gamma_deg": round(gamma_deg, 2),
            "v1_ms": round(v1_ms, 2),
            "v1_kmh": round(v1_ms * 3.6, 1),
            "w1_ms": round(w1_ms, 2),
            "v2_ms": round(v2_ms, 2),
            "v2_kmh": round(v2_ms * 3.6, 1),
            "w2_ms": round(w2_ms, 2),
            "v3_ms": round(v3_ms, 2),
            "v3_kmh": round(v3_ms * 3.6, 1),
            "w3_ms": round(w3_ms, 2),
        })

    best_opt_row = min(table_4_1_glide, key=lambda x: x["gamma_deg"])
    best_ek_row = min(table_4_1_glide, key=lambda x: x["w1_ms"])

    lambda_e_approx = p3_aero["analytical_polar_fit"]["lambda_e_approx"]
    cx0_approx = p3_aero["analytical_polar_fit"]["cx0_approx"]

    v_opt_anal_ms = math.sqrt((2.0 * m_var1 * G0) / (RHO0 * S * math.sqrt(math.pi * lambda_e_approx * cx0_approx)))
    w_opt_anal_ms = math.sqrt((8.0 * m_var1 * G0 * math.sqrt(cx0_approx)) / (RHO0 * S * math.pow(math.sqrt(math.pi * lambda_e_approx), 3)))
    v_ek_anal_ms = math.sqrt((2.0 * m_var1 * G0) / (RHO0 * S * math.sqrt(3.0 * math.pi * lambda_e_approx * cx0_approx)))
    w_ek_anal_ms = math.sqrt((32.0 * m_var1 * G0 * math.sqrt(cx0_approx)) / (RHO0 * S * math.pow(math.sqrt(3.0 * math.pi * lambda_e_approx), 3)))

    glide_comparison = {
        "masses_kg": {"m1_mtow": round(m_var1, 1), "m2_mid": round(m_var2, 1), "m3_empty_fuel": round(m_var3, 1)},
        "exact_from_table_4_1": {
            "v_opt_kmh": best_opt_row["v1_kmh"],
            "w_opt_ms": best_opt_row["w1_ms"],
            "gamma_min_deg": best_opt_row["gamma_deg"],
            "v_ek_kmh": best_ek_row["v1_kmh"],
            "w_ek_ms": best_ek_row["w1_ms"],
        },
        "analytical_eq_4_8_to_4_11": {
            "v_opt_kmh": round(v_opt_anal_ms * 3.6, 1),
            "w_opt_ms": round(w_opt_anal_ms, 2),
            "v_ek_kmh": round(v_ek_anal_ms * 3.6, 1),
            "w_ek_ms": round(w_ek_anal_ms, 2),
            "ratio_v_opt_v_ek": round(v_opt_anal_ms / max(0.1, v_ek_anal_ms), 4),
            "ratio_w_opt_w_ek": round(w_opt_anal_ms / max(0.01, w_ek_anal_ms), 4),
        }
    }

    return {
        "table_4_1_glide": table_4_1_glide,
        "glide_comparison": glide_comparison,
    }


def paturski_project_5_propulsion(geom_res: dict, sizing_res: dict, params: dict, m0: float = None, perf_res: dict = None) -> dict:
    """
    PROJEKT NR 5: CHARAKTERYSTYKI ZESPOŁU NAPĘDOWEGO (wzory 5.1 – 5.20)
    """
    wing = geom_res["wing"]
    S = float(wing["S"])
    if m0 is None:
        m0 = S * float(params.get("ws", 650.0)) / G0

    engine_type = params.get("engine_type", "prop")
    ac_type = params.get("aircraft_type", "piston_ga")
    n_engines = max(1, int(float(params.get("n_engines", 1))))
    dp = sizing_res["design_point"]
    eta_p_max = float(params.get("prop_efficiency", 0.82))
    h_cr = float(params.get("cruise_altitude_m", 2500.0))

    if engine_type == "jet":
        pr_0_total_n = float(dp.get("tw") or 0.30) * m0 * G0
        k_p_bypass = 0.45 if ac_type == "jet_business" else 0.55
        mach_grid = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
        alt_km_grid = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
        table_5_3_jet = []
        for ma_val in mach_grid:
            row_alts = {}
            for h_km in alt_km_grid:
                sigma_h = isa_atmosphere(h_km * 1000.0)["sigma"]
                pr_star_n = pr_0_total_n * math.pow(sigma_h, 0.85)
                pr_turbofan_kn = (pr_star_n * max(0.35, 1.0 - k_p_bypass * ma_val)) / 1000.0
                pr_turbojet_kn = (pr_star_n * (1.0 - 0.605 * ma_val + 0.725 * (ma_val ** 2))) / 1000.0
                row_alts[f"h_{int(h_km)}km_kn"] = round(pr_turbofan_kn, 2)
                row_alts[f"h_{int(h_km)}km_turbojet_kn"] = round(pr_turbojet_kn, 2)
            table_5_3_jet.append({
                "mach": ma_val,
                **row_alts
            })
        return {
            "engine_type": "jet",
            "pr0_total_kn": round(pr_0_total_n / 1000.0, 2),
            "kp_bypass_factor": k_p_bypass,
            "table_5_3_jet": table_5_3_jet,
        }
    else:
        p0_total_w = float(dp.get("pw") or 12.0) * m0 * G0
        n_d_single_w = p0_total_w / n_engines
        h_d_m = h_cr if ac_type in ["turboprop_regional", "twin_piston"] else 0.0
        isa_d = isa_atmosphere(h_d_m)
        rho_d = isa_d["rho"]
        a_dd = isa_d["a"]
        v_d_ms = max(35.0, float(params.get("cruise_speed_kmh", 220.0)) * 1.15 / 3.6)
        rpm_prop = 2000.0 if ac_type == "turboprop_regional" else 2400.0
        n_sd_rps = rpm_prop / 60.0

        c_d_prop = v_d_ms * math.pow(rho_d / max(1.0, n_d_single_w * (n_sd_rps ** 2)), 0.2)
        j_opt = max(0.45, min(1.35, 0.52 * math.pow(max(0.2, c_d_prop), 0.78)))
        d_prop_m = max(1.10, min(3.80, v_d_ms / (j_opt * n_sd_rps)))

        v_max_dop_ms = 1.2 * (float(params.get("cruise_speed_kmh", 220.0)) * 1.25 / 3.6)
        ma_kl = math.sqrt((v_max_dop_ms ** 2) + ((math.pi * n_sd_rps * d_prop_m) ** 2)) / a_dd
        c_n_0 = n_d_single_w / (RHO0 * (n_sd_rps ** 3) * (d_prop_m ** 5))

        v_prop_samples = [
            round(v_d_ms * frac, 1)
            for frac in [0.35, 0.50, 0.65, 0.80, 0.90, 1.00, 1.10, 1.20]
        ]
        table_5_1_var_pitch = []
        table_5_2_fixed_pitch = []
        j_design = v_d_ms / (n_sd_rps * d_prop_m)
        for lp_i, v_p in enumerate(v_prop_samples, start=1):
            j_val = v_p / (n_sd_rps * d_prop_m)
            j_ratio = j_val / max(0.1, j_design)
            beta_s_deg = round(14.0 + 14.5 * j_val, 1)
            eta_var = eta_p_max * max(0.45, 1.0 - 0.18 * ((j_ratio - 1.0) ** 2))
            nr_var_kw = (p0_total_w * eta_var) / 1000.0
            table_5_1_var_pitch.append({
                "lp": lp_i,
                "v_ms": v_p,
                "v_kmh": round(v_p * 3.6, 1),
                "j_advance": round(j_val, 3),
                "beta_s_deg": beta_s_deg,
                "eta_s": round(eta_var, 3),
                "nr_kw": round(nr_var_kw, 1),
            })

            ns_unthrottled = n_sd_rps * (0.72 + 0.28 * j_ratio)
            throttled = ns_unthrottled > n_sd_rps
            ns_actual = min(n_sd_rps, ns_unthrottled)
            eta_fixed = eta_p_max * max(0.35, 1.0 - 0.42 * ((j_ratio - 0.95) ** 2))
            if throttled:
                cn_j = max(0.015, c_n_0 * (1.0 - 0.55 * (j_ratio - 1.0)))
                n_eng_kw = (cn_j * RHO0 * (ns_actual ** 3) * (d_prop_m ** 5) * n_engines) / 1000.0
            else:
                n_eng_kw = (p0_total_w * (ns_actual / n_sd_rps)) / 1000.0
            nr_fixed_kw = n_eng_kw * eta_fixed
            table_5_2_fixed_pitch.append({
                "lp": lp_i,
                "j_advance": round(v_p / (ns_actual * d_prop_m), 3),
                "cn": round(c_n_0 * ((n_sd_rps / ns_actual) ** 2), 4),
                "eta_s": round(eta_fixed, 3),
                "ns_rps": round(ns_actual, 2),
                "rpm": round(ns_actual * 60.0),
                "v_ms": v_p,
                "v_kmh": round(v_p * 3.6, 1),
                "n_engine_kw": round(n_eng_kw, 1),
                "nr_kw": round(nr_fixed_kw, 1),
                "throttled": throttled,
            })

        return {
            "engine_type": "prop",
            "propeller_selection": {
                "v_d_ms": round(v_d_ms, 1),
                "h_d_m": round(h_d_m),
                "n_d_kw": round(n_d_single_w / 1000.0, 1),
                "n_sd_rps": round(n_sd_rps, 2),
                "rpm_prop": round(rpm_prop),
                "cd_dimensionless": round(c_d_prop, 3),
                "j_opt": round(j_opt, 3),
                "diameter_m": round(d_prop_m, 2),
                "cn_design": round(c_n_0, 4),
                "ma_tip_kl": round(ma_kl, 3),
                "ma_limit_wood_comp": 0.80,
                "ma_limit_metal": 0.90,
                "tip_mach_ok": ma_kl <= 0.85,
            },
            "table_5_1_variable_pitch": table_5_1_var_pitch,
            "table_5_2_fixed_pitch": table_5_2_fixed_pitch,
        }


def paturski_project_6_performance(geom_res: dict, sizing_res: dict, params: dict, m0: float = None, p3_aero: dict = None, m_fuel: float = None) -> dict:
    """
    PROJEKT NR 6: OSIĄGI SAMOLOTU — METODA MOCY, TABELE 6.1, 6.2, 6.3 (wzory 6.1 – 6.38)
    """
    if p3_aero is None:
        p3_aero = paturski_project_3_aircraft_aero(geom_res, params, m0)

    wing = geom_res["wing"]
    S = float(wing["S"])
    if m0 is None:
        m0 = S * float(params.get("ws", 650.0)) / G0
    if m_fuel is None:
        m_fuel = 0.15 * m0 if params.get("engine_type", "prop") != "none" else 0.0

    engine_type = params.get("engine_type", "prop")
    is_glider = engine_type == "none" or params.get("aircraft_type") == "glider"
    dp = sizing_res["design_point"]
    eta_p_max = float(params.get("prop_efficiency", 0.82))

    # 6.2 Wskaźnik obciążenia mocy q_N [kg/kW] lub ciągu q_Pr [kg/kN] (wzór 6.1)
    if is_glider:
        q_pr_kg_kn = None
        q_n_kg_kw = None
        power_method_valid = False
        t_max_kn = 0.0
        p_max_kw = 0.0
    elif engine_type == "jet":
        t_max_kn = max(0.1, float(dp.get("thrust_kn") or (float(dp.get("tw") or 0.30) * m0 * G0 / 1000.0)))
        q_pr_kg_kn = m0 / t_max_kn
        q_n_kg_kw = None
        power_method_valid = q_pr_kg_kn >= 300.0
        p_max_kw = 0.0
    else:
        p_max_kw = max(1.0, float(dp.get("power_kw") or (float(dp.get("pw") or 12.0) * m0 * G0 / 1000.0)))
        q_n_kg_kw = m0 / p_max_kw
        q_pr_kg_kn = None
        power_method_valid = q_n_kg_kw >= 6.0
        t_max_kn = 0.0

    positive_rows = [r for r in p3_aero["table_2_2_complete"] if r["cz_prime"] >= 0.08]

    # Tabela 6.1 (Bilans mocy i ciągu w funkcji Cz dla h = 0 m wg wzorów 6.5 – 6.9)
    table_6_1_h0 = []
    for r in positive_rows:
        cz_p = r["cz_prime"]
        cx_t = r["cx_total"]
        e_en = max(0.01, (cz_p ** 3) / (cx_t ** 2))
        v_ms = math.sqrt((2.0 * m0 * G0) / (RHO0 * S * cz_p))
        n_n_w = m0 * G0 * math.sqrt(((2.0 * m0 * G0) / (RHO0 * S)) * (1.0 / e_en))
        if is_glider:
            n_r_w = 0.0
        elif engine_type == "jet":
            n_r_w = t_max_kn * 1000.0 * v_ms
        else:
            n_r_w = p_max_kw * 1000.0 * eta_p_max
        delta_n_w = n_r_w - n_n_w
        w_climb_ms = delta_n_w / (m0 * G0)
        gamma_climb_deg = math.degrees(math.asin(max(-0.9, min(0.9, w_climb_ms / max(1.0, v_ms)))))
        table_6_1_h0.append({
            "cz": round(cz_p, 3),
            "e_energy": round(e_en, 2),
            "v_ms": round(v_ms, 2),
            "v_kmh": round(v_ms * 3.6, 1),
            "nn_kw": round(n_n_w / 1000.0, 1),
            "nr_kw": round(n_r_w / 1000.0, 1),
            "delta_n_kw": round(delta_n_w / 1000.0, 1),
            "w_ms": round(w_climb_ms, 2),
            "gamma_deg": round(gamma_climb_deg, 2),
        })

    # Tabela 6.2 i Wykres Ofertowy (wzory 6.10 – 6.12)
    lambda_e_approx = p3_aero["analytical_polar_fit"]["lambda_e_approx"]
    cx0_approx = p3_aero["analytical_polar_fit"]["cx0_approx"]
    k_ind_clean = 1.0 / (math.pi * lambda_e_approx)
    cz_max_clean = float(params.get("cz_max_clean", 1.40))
    w_crit_pract = 0.5 if engine_type != "jet" else 1.5

    def eval_climb_at_alt(h_m: float):
        if is_glider:
            return {
                "w_max": 0.0, "v_w_ms": 0.0, "v_w_kmh": 0.0,
                "gamma_max_deg": 0.0, "v_gamma_ms": 0.0, "v_gamma_kmh": 0.0,
                "v_min_kmh": 0.0, "v_max_kmh": 0.0, "inv_w_max": None
            }
        isa_h = isa_atmosphere(h_m)
        rho_h = isa_h["rho"]
        sigma_h = isa_h["sigma"]
        if engine_type == "jet":
            thrust_h = t_max_kn * 1000.0 * math.pow(sigma_h, 0.85)
        else:
            psi_piston = max(0.02, sigma_h - (1.0 - sigma_h) / 7.55)
            is_turbo = params.get("turbocharged", False) or "turbo" in str(params.get("engine_model", "")).lower()
            if is_turbo:
                psi_piston = min(1.0, math.pow(sigma_h, 0.20)) if h_m <= 4500.0 else math.pow(sigma_h / 0.60, 0.90)
            p_avail = p_max_kw * 1000.0 * psi_piston * eta_p_max

        best_w = -999.0
        best_v_w = 0.0
        best_gamma = -90.0
        best_v_gamma = 0.0
        v_min_level = None
        v_max_level = None

        for cz in [0.12 + i * 0.04 for i in range(int((cz_max_clean - 0.12) / 0.04) + 1)]:
            cx = cx0_approx + k_ind_clean * (cz ** 2)
            e_g = (cz ** 3) / (cx ** 2)
            v_g = math.sqrt((2.0 * m0 * G0) / (rho_h * S * cz))
            n_n = m0 * G0 * math.sqrt(((2.0 * m0 * G0) / (rho_h * S)) * (1.0 / e_g))
            n_r = thrust_h * v_g if engine_type == "jet" else p_avail
            w = (n_r - n_n) / (m0 * G0)
            sin_gam = max(-0.95, min(0.95, w / max(1.0, v_g)))
            gamma_deg = math.degrees(math.asin(sin_gam))

            if w > best_w:
                best_w = w
                best_v_w = v_g
            if gamma_deg > best_gamma:
                best_gamma = gamma_deg
                best_v_gamma = v_g
            if w >= 0.0:
                if v_min_level is None or v_g < v_min_level:
                    v_min_level = v_g
                if v_max_level is None or v_g > v_max_level:
                    v_max_level = v_g

        return {
            "w_max": best_w,
            "v_w_ms": best_v_w,
            "v_w_kmh": best_v_w * 3.6,
            "gamma_max_deg": best_gamma,
            "v_gamma_ms": best_v_gamma,
            "v_gamma_kmh": best_v_gamma * 3.6,
            "v_min_kmh": (v_min_level or best_v_w * 0.8) * 3.6,
            "v_max_kmh": (v_max_level or best_v_w * 1.5) * 3.6,
            "inv_w_max": (1.0 / best_w) if best_w > 0.01 else None,
        }

    w_max_h0 = max(0.0, eval_climb_at_alt(0.0)["w_max"])
    if is_glider or w_max_h0 <= 0.0:
        h_t_theoretical_m = 0.0
        h_p_practical_m = 0.0
        t_hp_s = 0.0
    else:
        hl, hh = 0.0, 25000.0
        for _ in range(30):
            hm = 0.5 * (hl + hh)
            if eval_climb_at_alt(hm)["w_max"] > 0.0:
                hl = hm
            else:
                hh = hm
        h_t_theoretical_m = 0.5 * (hl + hh)

        hl, hh = 0.0, h_t_theoretical_m
        for _ in range(30):
            hm = 0.5 * (hl + hh)
            if eval_climb_at_alt(hm)["w_max"] > w_crit_pract:
                hl = hm
            else:
                hh = hm
        h_p_practical_m = 0.5 * (hl + hh)
        t_hp_s = (h_t_theoretical_m / max(0.1, w_max_h0)) * math.log(max(1.01, w_max_h0 / w_crit_pract))

    alt_steps = [0.0, 1000.0, 2000.0, 3000.0, 4000.0, 5000.0, 6000.0, 8000.0, 10000.0, 12000.0, 14000.0]
    valid_alts = [h for h in alt_steps if h < h_t_theoretical_m]
    if h_p_practical_m > 0 and h_p_practical_m not in valid_alts:
        valid_alts.append(h_p_practical_m)
    if h_t_theoretical_m > 0 and h_t_theoretical_m not in valid_alts:
        valid_alts.append(h_t_theoretical_m)
    valid_alts.sort()

    table_6_2_climb = []
    for h in valid_alts:
        c_res = eval_climb_at_alt(h)
        th_val = (h_t_theoretical_m / max(0.1, w_max_h0)) * math.log(max(1.001, 1.0 / max(0.001, 1.0 - h / max(1.0, h_t_theoretical_m)))) if (h_t_theoretical_m > 0 and h < h_t_theoretical_m) else (t_hp_s if h == h_p_practical_m else 0.0)
        table_6_2_climb.append({
            "h_m": round(h),
            "v_min_kmh": round(c_res["v_min_kmh"], 1),
            "v_max_kmh": round(c_res["v_max_kmh"], 1),
            "w_max_ms": round(c_res["w_max"], 2),
            "v_w_kmh": round(c_res["v_w_kmh"], 1),
            "gamma_max_deg": round(c_res["gamma_max_deg"], 2),
            "v_gamma_kmh": round(c_res["v_gamma_kmh"], 1),
            "inv_w_max_s_m": round(c_res["inv_w_max"], 3) if c_res["inv_w_max"] is not None else None,
            "th_s": round(th_val),
            "th_min": round(th_val / 60.0, 1),
        })

    row_h0 = eval_climb_at_alt(0.0)

    # 6.5 Zasięg i długotrwałość lotu — Tabela 6.3 oraz wykres T(V) i L(V) (wzory 6.13 – 6.38)
    h_range_m = float(params.get("cruise_altitude_m", 8000.0 if engine_type == "jet" else 2500.0))

    m_fuel_cruise = max(0.35 * m_fuel, m_fuel * 0.78)
    m_start_cr = m0 - 0.08 * m_fuel
    m_end_cr = max(0.55 * m0, m_start_cr - m_fuel_cruise)
    m_obl_kg = 0.5 * (m_start_cr + m_end_cr)

    raw_sfc = float(params.get("sfc", 0.62 if engine_type == "jet" else 265.0))
    if engine_type == "jet":
        qe_paturski = raw_sfc if (0.15 <= raw_sfc <= 4.0) else 0.62
    else:
        if raw_sfc > 10.0:
            qe_paturski = raw_sfc / 1000.0
        elif 0.12 <= raw_sfc <= 1.5:
            qe_paturski = raw_sfc
        else:
            qe_paturski = 0.265

    def range_rows(h_m):
        """Tabela 6.3 (zasięg i długotrwałość w funkcji prędkości) na wysokości h_m."""
        rho_range = isa_atmosphere(h_m)["rho"]
        rows = []
        if is_glider or m_fuel <= 0:
            return rows
        cz_samples_6_3 = [round(cz_max_clean - i * 0.12, 2) for i in range(10) if (cz_max_clean - i * 0.12) >= 0.18]
        for lp_i, cz_val in enumerate(cz_samples_6_3, start=1):
            cx_val = cx0_approx + k_ind_clean * (cz_val ** 2)
            cz32_cx = (cz_val ** 1.5) / cx_val
            cz12_cx = (cz_val ** 0.5) / cx_val
            cz_cx = cz_val / cx_val

            v_ms = math.sqrt((2.0 * m_obl_kg * G0) / (rho_range * S * cz_val))
            v_kmh = v_ms * 3.6

            a_param = rho_range * S * (v_ms ** 2) * math.sqrt(cx0_approx * math.pi * lambda_e_approx)
            atan_term = math.atan((2.0 * G0 * m_start_cr) / max(1.0, a_param)) - math.atan((2.0 * G0 * m_end_cr) / max(1.0, a_param))

            if engine_type == "jet":
                t_const_alpha_h = 10.0 * (1.0 / (G0 * qe_paturski)) * cz_cx * math.log(m_start_cr / m_end_cr)
                l_const_alpha_km = (
                    36.0
                    * (2.0 / qe_paturski)
                    * math.sqrt(2.0 / (G0 * rho_range * S))
                    * cz12_cx
                    * (math.sqrt(m_start_cr) - math.sqrt(m_end_cr))
                )
                t_const_v_h = 10.0 * (1.0 / (G0 * qe_paturski)) * math.sqrt((math.pi * lambda_e_approx) / cx0_approx) * atan_term
                l_const_v_km = 3.6 * v_ms * t_const_v_h
            else:
                t_const_alpha_h = (
                    1000.0
                    * cz32_cx
                    * ((2.0 * eta_p_max) / (G0 * qe_paturski))
                    * math.sqrt((rho_range * S) / (2.0 * G0))
                    * ((1.0 / math.sqrt(m_end_cr)) - (1.0 / math.sqrt(m_start_cr)))
                )
                l_const_alpha_km = 3600.0 * cz_cx * (eta_p_max / (G0 * qe_paturski)) * math.log(m_start_cr / m_end_cr)
                t_const_v_h = (
                    1000.0
                    * (eta_p_max / (G0 * v_ms * qe_paturski))
                    * math.sqrt((math.pi * lambda_e_approx) / cx0_approx)
                    * atan_term
                )
                l_const_v_km = 3.6 * v_ms * t_const_v_h

            rows.append({
                "lp": lp_i,
                "cz": round(cz_val, 3),
                "cx": round(cx_val, 5),
                "cz32_cx": round(cz32_cx, 2),
                "cz12_cx": round(cz12_cx, 2),
                "cz_cx": round(cz_cx, 2),
                "v_ms": round(v_ms, 1),
                "v_kmh": round(v_kmh, 1),
                "t_breguet_h": round(t_const_alpha_h, 2),
                "l_breguet_km": round(l_const_alpha_km, 1),
                "t_const_v_h": round(t_const_v_h, 2),
                "l_const_v_km": round(l_const_v_km, 1),
            })
        return rows

    table_6_3_range = range_rows(h_range_m)

    # BIPOL_5 (T. Grabowski): obliczenia dla wysokości 0, przelotowej i pułapu praktycznego, w zakresie
    # prędkości z wykresu ofertowego, metodą stałej wysokości i prędkości (wzory 5.10–5.16).
    range_by_altitude = []
    for label, h in (("0 m", 0.0), ("wysokość przelotowa", h_range_m), ("pułap praktyczny", h_p_practical_m)):
        if is_glider or m_fuel <= 0 or (label == "pułap praktyczny" and h_p_practical_m <= 0):
            continue
        speeds = eval_climb_at_alt(h)
        rows = [r for r in range_rows(h) if speeds["v_min_kmh"] <= r["v_kmh"] <= speeds["v_max_kmh"]]
        best_t = max(rows, key=lambda r: r["t_const_v_h"], default=None)
        best_l = max(rows, key=lambda r: r["l_const_v_km"], default=None)
        range_by_altitude.append({
            "label": label,
            "h_m": round(h),
            "v_min_kmh": round(speeds["v_min_kmh"], 1),
            "v_max_kmh": round(speeds["v_max_kmh"], 1),
            "rows": rows,
            "t_max_h": best_t["t_const_v_h"] if best_t else None,
            "v_t_max_kmh": best_t["v_kmh"] if best_t else None,
            "l_max_km": best_l["l_const_v_km"] if best_l else None,
            "v_l_max_kmh": best_l["v_kmh"] if best_l else None,
        })

    if table_6_3_range:
        best_t_row = max(table_6_3_range, key=lambda x: x["t_breguet_h"])
        best_l_row = max(table_6_3_range, key=lambda x: x["l_breguet_km"])
    else:
        best_t_row = {"t_breguet_h": 0.0, "v_kmh": 0.0}
        best_l_row = {"l_breguet_km": 0.0, "v_kmh": 0.0}

    return {
        "load_indicators_eq_6_1": {
            "q_n_kg_kw": round(q_n_kg_kw, 2) if q_n_kg_kw is not None else None,
            "q_pr_kg_kn": round(q_pr_kg_kn, 1) if q_pr_kg_kn is not None else None,
            "power_method_valid": power_method_valid,
            "criterion_desc": "q_N > 6 kg/kW (śmigłowe) lub q_Pr > 300 kg/kN (odrzutowe)"
        },
        "table_6_1_power_balance_h0": table_6_1_h0,
        "table_6_2_climb_and_ceilings": {
            "altitudes_table": table_6_2_climb,
            "ceilings": {
                "h_t_theoretical_m": round(h_t_theoretical_m),
                "h_p_practical_m": round(h_p_practical_m),
                "t_hp_climb_to_practical_ceiling_s": round(t_hp_s),
                "t_hp_climb_to_practical_ceiling_min": round(t_hp_s / 60.0, 1),
                "w_crit_ceiling_ms": w_crit_pract,
                "w_max_h0_ms": round(w_max_h0, 2),
            },
        },
        "offer_chart_summary": {
            "h_t_m": round(h_t_theoretical_m),
            "h_p_m": round(h_p_practical_m),
            "w_max_h0_ms": round(w_max_h0, 2),
            "v_w_h0_kmh": round(row_h0["v_w_kmh"], 1),
            "gamma_max_h0_deg": round(row_h0["gamma_max_deg"], 2),
            "v_gamma_h0_kmh": round(row_h0["v_gamma_kmh"], 1),
            "t_hp_min": round(t_hp_s / 60.0, 1),
        },
        "range_endurance_6_5": {
            "h_cruise_m": round(h_range_m),
            "m0_start_cr_kg": round(m_start_cr, 1),
            "mk_end_cr_kg": round(m_end_cr, 1),
            "mp_cruise_fuel_kg": round(m_start_cr - m_end_cr, 1),
            "m_obl_avg_kg": round(m_obl_kg, 1),
            "qe_paturski": round(qe_paturski, 4),
            "qe_unit": "kg/(daN·h)" if engine_type == "jet" else "kg/(kW·h)",
            "t_max_h": best_t_row["t_breguet_h"],
            "v_t_max_kmh": best_t_row["v_kmh"],
            "l_max_km": best_l_row["l_breguet_km"],
            "v_l_max_kmh": best_l_row["v_kmh"],
            "table_6_3": table_6_3_range,
            "by_altitude": range_by_altitude,
            "by_altitude_method": "Stała wysokość i prędkość (BIPOL_5, wzory 5.10–5.16); prędkości z zakresu wykresu ofertowego.",
        },
    }


def run_paturski_mechanika_lotu(
    params: dict,
    mass_res: dict,
    sizing_res: dict,
    geom_res: dict,
    aero_res: dict = None,
    perf_res: dict = None,
) -> dict:
    """
    Wykonuje pełny cykl obliczeń według "Przewodnika po projektach z Mechaniki Lotu" Z. Paturskiego
    i zwraca ustrukturyzowany słownik z wynikami Projektów nr 2, 3, 4, 5 i 6.
    """
    m0 = float(mass_res["m0"])
    m_fuel_total = float(mass_res.get("m_fuel", 0.0))

    # Projekt nr 2
    p2_res = paturski_project_2_wing(geom_res, params, m0=m0)

    # Projekt nr 3
    p3_res = paturski_project_3_aircraft_aero(geom_res, params, m0=m0, p2_wing=p2_res)

    # Projekt nr 4
    p4_res = paturski_project_4_gliding(geom_res, params, m0=m0, p3_aero=p3_res, m_fuel=m_fuel_total)

    # Projekt nr 5
    p5_res = paturski_project_5_propulsion(geom_res, sizing_res, params, m0=m0, perf_res=perf_res)

    # Projekt nr 6
    p6_res = paturski_project_6_performance(geom_res, sizing_res, params, m0=m0, p3_aero=p3_res, m_fuel=m_fuel_total)

    return {
        "p2_wing_aero": p2_res,
        "p3_aircraft_aero": p3_res,
        "p4_gliding_flight": p4_res,
        "p5_propulsion_characteristics": p5_res,
        "p6_performance_paturski": p6_res,
    }
