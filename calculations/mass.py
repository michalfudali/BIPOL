"""
Moduł analizy masowej i wstępnego bilansu mas samolotu (BIPOL I)
Wstępne oszacowanie masy startowej MTOW (m0), masy pustej (me), masy paliwa (mf)
oraz szczegółowy rozkład mas składowych według zaleceń ZSiS MEiL PW / E. Torenbeek / J. Roskam.

Zgodność 100% z BIPOL_1.pdf (s. 3–6) i wytycznymi prowadzącego:
- Metoda proporcji (dla samolotów niezrzucających ładunku w locie) wg wzorów (4)–(5).
- Metoda iteracyjna (dla samolotów zrzucających ładunek lub z misją zadaniową) wg 12 kroków.
- Wznoszenie i rozpędzanie wg Corke'a (Rys. 3) z uwzględnieniem liczby Macha i pułapu.
- Zasilanie równania masowego współczynnikami A, C i K_vs z analizy trendów.
"""
import math
from calculations.atmosphere import isa_atmosphere, G0
from calculations.polish_law import is_unmanned, resolve_category, SUBCATEGORIES
from calculations.instructor import CRUISE_LD_FACTOR, MIN_MASS_ITERATIONS


def corke_climb_fuel_fraction(engine_type: str, h_cr_m: float, v_cr_ms: float) -> float:
    """
    Wznoszenie i rozpędzanie wg Corke'a (BIPOL_1, s. 4–5, Rys. 3).
    Spadek masy zależy od przyrostu liczby Macha pomiędzy pułapem początkowym
    a końcowym oraz od pułapu przelotowego.
    """
    a_sl = 340.29
    isa = isa_atmosphere(h_cr_m)
    t_cr = isa["T"]
    a_cr = math.sqrt(1.4 * 287.05 * t_cr)
    ma_cr = v_cr_ms / max(1.0, a_cr)
    v_start = min(v_cr_ms, max(30.0, 0.75 * v_cr_ms))
    ma_start = v_start / a_sl
    delta_ma = max(0.0, ma_cr - ma_start)
    if engine_type == "jet":
        ff = 0.985 - 0.020 * delta_ma - 0.0000015 * h_cr_m
        return max(0.940, min(0.985, ff))
    else:
        ff = 0.995 - 0.015 * delta_ma - 0.0000012 * h_cr_m
        return max(0.965, min(0.995, ff))


def calculate_mass_sizing(params: dict):
    """
    Parametry wejściowe w słowniku params:
      - aircraft_type: 'piston_ga', 'turboprop_regional', 'jet_business', 'jet_transport', 'uav', 'glider', 'motoglider'
      - mass_method: 'auto' | 'proportion' | 'iterative' (domyślnie 'auto', 'iterative' przy zrzucie ładunku)
      - payload_drop_kg: masa ładunku zrzucanego w trakcie misji [kg] (dla metody iteracyjnej)
      - outbound_range_km, return_range_km: zasięg dolotu do celu i powrotu [km]
      - n_pax, m_pax, m_bag, m_cargo, n_crew, m_crew_person
      - range_km, cruise_altitude_m, cruise_speed_kmh
      - aspect_ratio, oswald_e, cx0, mission_ld_factor
      - engine_type, sfc, prop_efficiency, loiter_time_min, loiter_speed_kmh
      - empty_mass_fraction, empty_mass_trend_A, empty_mass_trend_C, variable_sweep (K_vs)
    """
    ac_type = params.get("aircraft_type", "piston_ga")
    n_pax = int(params.get("n_pax", 4))
    m_pax = float(params.get("m_pax", 80.0))
    m_bag = float(params.get("m_bag", 0.0))
    m_cargo = float(params.get("m_cargo", 0.0))
    n_crew = int(params.get("n_crew", 1 if n_pax <= 4 else 2))
    m_crew_person = float(params.get("m_crew_person", 90.0))

    range_m = float(params.get("range_km", 1200.0)) * 1000.0
    h_cr = float(params.get("cruise_altitude_m", 3000.0))
    v_cr_ms = max(15.0, float(params.get("cruise_speed_kmh", 250.0)) / 3.6)
    engine_type = params.get("engine_type", "prop")
    loiter_min = float(params.get("loiter_time_min", 45.0))
    eta_p = float(params.get("prop_efficiency", 0.82))

    # Sprzężenie doskonałości przelotowej z geometrią i aerodynamiką (BIPOL_1_wzory.pdf, wzory 8 i 28)
    AR = float(params.get("aspect_ratio", 8.0))
    oswald_e = float(params.get("oswald_e", 0.80))
    cx0_base = float(params.get("cx0", 0.025))
    wing_config = params.get("wing_config", "low")
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")

    cx0_eff = cx0_base
    if wing_config == "braced_high":
        cx0_eff += 0.0020
    if flap_type == "junkers":
        cx0_eff += 0.0025
    if slat_type == "fixed_slot":
        cx0_eff += 0.0030

    k_max_theo = 0.5 * math.sqrt((math.pi * AR * oswald_e) / max(0.008, cx0_eff))
    # Lecture note IMG20261021122751: K_cr = 0.94 Kmax (wskazówka prowadzącego, zastępuje 0.8 z PDF)
    ld_cr = k_max_theo * float(params.get('mission_ld_factor', CRUISE_LD_FACTOR))

    # 1. Masa płatna (Payload) i załoga
    unmanned = is_unmanned(params)
    if unmanned:
        n_crew = 0
        n_pax = 0
    m_payload = n_pax * (m_pax + m_bag) + m_cargo
    m_crew = n_crew * m_crew_person
    if m_payload + m_crew <= 0.0:
        raise ValueError("Do wyznaczenia MTOW podaj dodatnią masę załogi lub ładunku.")

    # 2. Wyznaczenie ułamków zużycia paliwa (Fuel Fractions)
    if ac_type == "glider" or engine_type == "none":
        ff_warmup = 1.0
        ff_takeoff = 1.0
        ff_climb = 1.0
        ff_cruise = 1.0
        ff_task = 1.0
        ff_descent = 1.0
        ff_loiter = 1.0
        ff_landing = 1.0
        m_ff = 1.0
        fuel_fraction = 0.0
        c_t_sec = 0.0
        c_p = 0.0
        f_trapped = 1.0
    else:
        # Faza 1: Rozruch i kołowanie
        ff_warmup = 0.992 if engine_type == "prop" else 0.975

        # Faza 2: Start (BIPOL_1, s. 4: 0.970 <= ff <= 0.975)
        ff_takeoff = 0.995 if engine_type == "prop" else 0.985
        ff_landing = 0.995
        if params.get('mission_phase_model', 'galinski') == 'galinski':
            # Rozruch i start jako jeden etap bez podwójnego naliczania paliwa
            ff_warmup, ff_takeoff, ff_landing = 1.0, 0.975, 0.975

        # Faza 3: Wznoszenie (BIPOL_1, s. 4–5: Corke Rys. 3)
        if params.get('climb_model') == 'corke' or params.get('mission_phase_model') == 'corke':
            ff_climb = corke_climb_fuel_fraction(engine_type, h_cr, v_cr_ms)
        else:
            ff_climb = 0.988 if engine_type == "prop" else 0.978

        # Faza 4: Przelot obliczeniowy (Breguet)
        raw_sfc = float(params.get("sfc", 0.62 if engine_type == "jet" else 265.0))
        if engine_type == "jet":
            sfc_h = raw_sfc if 0.15 <= raw_sfc <= 4.0 else 0.62
            c_t_sec = sfc_h / 3600.0
            c_p = 0.0
            ff_cruise = math.exp(- (range_m * c_t_sec) / (v_cr_ms * ld_cr))
        else:
            if 0.12 <= raw_sfc <= 1.5:
                sfc_g_kwh = raw_sfc * 1000.0
            elif raw_sfc >= 80.0:
                sfc_g_kwh = raw_sfc
            else:
                sfc_g_kwh = 265.0
            c_p = (sfc_g_kwh * 1e-3) / (1000.0 * 3600.0)  # [kg / (W*s)]
            c_t_sec = 0.0
            ff_cruise = math.exp(- (range_m * c_p * G0) / (eta_p * ld_cr))

        # Faza zadaniowa na maksymalnym ciągu/mocy (BIPOL_1, s. 5)
        t_task_min = float(params.get('t_max_thrust_min') or params.get('task_time_min') or 0.0)
        if t_task_min > 0.0:
            t_task_s = t_task_min * 60.0
            if engine_type == "jet":
                ff_task = max(0.70, 1.0 - (c_t_sec * 1.15 * 0.22 * t_task_s))
            else:
                ff_task = max(0.70, 1.0 - (c_p * 150000.0 * t_task_s / (1600.0 * G0)))
        else:
            ff_task = 1.0

        # Faza 5: Zniżanie
        ff_descent = 0.992

        # Faza 6: Krążenie / patrol (BIPOL_1, s. 6)
        t_loiter_sec = loiter_min * 60.0
        loiter_speed_kmh = float(params.get('loiter_speed_kmh', 0.0))
        v_loiter_ms = (loiter_speed_kmh / 3.6) if loiter_speed_kmh > 0.0 else (v_cr_ms * 0.72)

        if engine_type == "jet":
            ld_loiter = max(ld_cr, k_max_theo)
            ff_loiter = math.exp(- (t_loiter_sec * c_t_sec) / ld_loiter)
        else:
            ld_loiter = 0.866 * k_max_theo
            ff_loiter = math.exp(- (t_loiter_sec * v_loiter_ms * c_p * G0) / (eta_p * ld_loiter))

        # Całkowity współczynnik misji M_ff
        m_ff = ff_warmup * ff_takeoff * ff_climb * ff_cruise * ff_task * ff_descent * ff_loiter * ff_landing

        # BIPOL_1, eq. 4: rezerwa paliwa i paliwo nieużywalne
        f_trapped = float(params.get('fuel_reserve_factor', 1.06))
        fuel_fraction = f_trapped * (1.0 - m_ff)
        if fuel_fraction >= 0.62:
            raise ValueError("Brak wykonalnego bilansu masy dla tej misji: wymagany udział paliwa jest zbyt duży.")

    # 3. Model masy pustej m_empty / m_0 = A * m_0^C * K_vs (BIPOL_1, równanie 1)
    stats_coeff = {
        "glider":              {"A": 0.82, "C": -0.05, "guess": 420.0},
        "motoglider":          {"A": 0.86, "C": -0.05, "guess": 650.0},
        "piston_ga":           {"A": 0.92, "C": -0.06, "guess": 1100.0},
        "turboprop_regional":  {"A": 0.96, "C": -0.05, "guess": 12000.0},
        "jet_business":        {"A": 1.02, "C": -0.06, "guess": 6500.0},
        "jet_transport":       {"A": 0.95, "C": -0.05, "guess": 45000.0},
        "uav":                 {"A": 0.82, "C": -0.04, "guess": 650.0}
    }
    coeff = stats_coeff.get(ac_type, stats_coeff["piston_ga"])
    A_coeff = coeff["A"]
    C_coeff = coeff["C"]

    category = resolve_category(params.get("category", "normal"))
    load_basis = SUBCATEGORIES[category]["load_basis"]
    struct_mod = 1.0
    if wing_config == "braced_high":
        struct_mod *= 0.972
    if load_basis == "cs23_aerobatic":
        struct_mod *= 1.045
    elif load_basis in ("cs23_utility", "cs22_utility"):
        struct_mod *= 1.018
    if AR > 9.0:
        struct_mod *= (1.0 + 0.006 * (AR - 9.0))
    if flap_type in ["fowler", "double_slotted"]:
        struct_mod *= 1.012

    # BIPOL_1, s. 4: równanie (1) z analizy trendów wstawia się do równania (5).
    trend_A, trend_C = params.get('empty_mass_trend_A'), params.get('empty_mass_trend_C')
    trend_model = trend_A is not None and trend_C is not None
    k_vs = 1.04 if params.get('variable_sweep', False) else 1.0

    def empty_share(mass):
        if trend_model:
            return float(trend_A) * max(mass, 1e-9) ** float(trend_C) * k_vs
        if params.get('empty_mass_fraction') is not None:
            return float(params['empty_mass_fraction'])
        return min(max(A_coeff * max(50.0, mass) ** C_coeff * struct_mod, 0.38), 0.74)

    useful_mass = m_payload + m_crew

    # =========================================================================
    # METODA PROPORCJI (BIPOL_1, s. 4, wzory 4–5)
    # =========================================================================
    low_p, high_p = 0.0, max(coeff["guess"], useful_mass * 2)
    while high_p * (1.0 - fuel_fraction - empty_share(high_p)) < useful_mass:
        high_p *= 2
        if high_p > 1e9:
            if trend_model:
                raise ValueError(
                    f"Równanie (1) z analizy trendów (A = {float(trend_A):.4g}, C = {float(trend_C):.4g}) nie daje ".replace('.', ',') +
                    "rozwiązania równania (5) dla tej misji: udział masy pustej rośnie z masą zbyt szybko. "
                    "Sprawdź dobór próby (oczekiwane C < 0) albo wróć do korelacji klasy.")
            raise ValueError("Nie uzyskano wykonalnego bilansu masy dla zadanej misji.")
    history_prop = []
    m0_prop = (low_p + high_p) / 2
    empty_fraction_prop = empty_share(m0_prop)
    for i in range(100):
        m0_prop = (low_p + high_p) / 2
        empty_fraction_prop = empty_share(m0_prop)
        residual = m0_prop * (1.0 - fuel_fraction - empty_fraction_prop) - useful_mass
        history_prop.append({"iter": i + 1, "m0": round(m0_prop, 1),
                             "empty_fraction": round(empty_fraction_prop, 4), "diff": round(abs(residual), 6)})
        if i + 1 >= MIN_MASS_ITERATIONS and abs(residual) < 0.001:
            break
        if residual > 0:
            high_p = m0_prop
        else:
            low_p = m0_prop

    m_empty_prop = empty_fraction_prop * m0_prop
    m_fuel_prop = fuel_fraction * m0_prop

    # =========================================================================
    # METODA ITERACYJNA (BIPOL_1, s. 4, 12 kroków)
    # =========================================================================
    m_drop = float(params.get('payload_drop_kg', 0.0))
    if m_drop <= 0.0 and (params.get('mission_has_drop', False) or (params.get('mass_method') == 'iterative' and params.get('m_cargo', 0) > 0)):
        m_drop = float(params.get('m_cargo', 0.0))
    m_drop = max(0.0, min(m_payload, m_drop))
    m_payload_remaining = m_payload - m_drop

    r_out = float(params.get('outbound_range_km', 0.0)) * 1000.0 or (0.5 * range_m)
    r_ret = float(params.get('return_range_km', 0.0)) * 1000.0 or (0.5 * range_m)

    if ac_type == "glider" or engine_type == "none":
        ff_cr_out = 1.0
        ff_cr_ret = 1.0
    elif engine_type == "jet":
        ff_cr_out = math.exp(- (r_out * c_t_sec) / (v_cr_ms * ld_cr))
        ff_cr_ret = math.exp(- (r_ret * c_t_sec) / (v_cr_ms * ld_cr))
    else:
        ff_cr_out = math.exp(- (r_out * c_p * G0) / (eta_p * ld_cr))
        ff_cr_ret = math.exp(- (r_ret * c_p * G0) / (eta_p * ld_cr))

    history_iter = []
    m0_curr = m0_prop
    prev_m0 = None
    prev_diff = None
    m1 = m2 = m3 = m3_burn = m4 = m5 = m6 = m7 = 0.0
    m_e_calc = 0.0
    m_e_trend = 0.0
    m_fuel_burned = 0.0
    m_fuel_res = 0.0

    for step in range(1, 60):
        # 1) Start mass m0
        # 2) Post-takeoff
        m1 = m0_curr * ff_warmup * ff_takeoff
        # 3) Post-climb
        m2 = m1 * ff_climb
        # 4) Post-outbound
        m3 = m2 * ff_cr_out
        # 5) Post-task & Drop
        m3_burn = m3 * ff_task
        m4 = max(m_payload_remaining + m_crew + 1.0, m3_burn - m_drop)
        # 6) Post-return
        m5 = m4 * ff_cr_ret
        # 7) Post-loiter
        m6 = m5 * ff_loiter
        # 8) Post-landing
        m7 = m6 * ff_landing

        # 9) Masa pustego z bilansu misji
        m_fuel_burned = (m0_curr - m1) + (m1 - m2) + (m2 - m3) + (m3 - m3_burn) + (m4 - m5) + (m5 - m6) + (m6 - m7)
        m_fuel_res = (f_trapped - 1.0) * m_fuel_burned
        m_e_calc = max(10.0, m7 - m_payload_remaining - m_crew - m_fuel_res)

        # 10) Realistyczna masa pustego z równania trendu (1)
        m_e_trend = empty_share(m0_curr) * m0_curr

        # 11) Różnica mas
        diff_me = m_e_calc - m_e_trend
        diff_rel = abs(diff_me) / max(1.0, m_e_trend)

        history_iter.append({
            "iter": step,
            "m0": round(m0_curr, 1),
            "m_empty_calc": round(m_e_calc, 1),
            "m_empty_trend": round(m_e_trend, 1),
            "diff": round(abs(diff_me), 4),
            "diff_rel": round(diff_rel, 6),
            "empty_fraction": round(m_e_calc / m0_curr, 4)
        })

        if step >= MIN_MASS_ITERATIONS and diff_rel < 0.001:
            break

        # 12) Przyspieszenie iteracji: interpolacja liniowa z dwóch ostatnich iteracji (BIPOL_1 s. 4)
        if prev_m0 is not None and prev_diff is not None and abs(diff_me - prev_diff) > 1e-6:
            m0_next = m0_curr - diff_me * (m0_curr - prev_m0) / (diff_me - prev_diff)
        else:
            deriv_approx = max(0.08, 1.0 - empty_share(m0_curr) - fuel_fraction)
            m0_next = m0_curr - diff_me / deriv_approx

        prev_m0 = m0_curr
        prev_diff = diff_me
        m0_curr = max(useful_mass * 1.15, min(m0_next, m0_curr * 2.2))

    m0_iter = m0_curr
    m_empty_iter = m_e_calc
    m_fuel_iter = m_fuel_burned + m_fuel_res

    # Wybór metody wiodącej
    user_method = params.get('mass_method', 'auto')
    if user_method == 'iterative':
        use_iterative = True
    elif user_method == 'proportion':
        use_iterative = False
    else:
        # 'auto': metoda iteracyjna dla misji ze zrzutem ładunku
        use_iterative = (m_drop > 0.0)

    if use_iterative:
        m0 = m0_iter
        m_empty = m_empty_iter
        m_fuel = m_fuel_iter
        empty_fraction = m_empty / m0
        fuel_fraction = m_fuel / m0
        history = history_iter
        method_name = 'iterative'
    else:
        m0 = m0_prop
        m_empty = m_empty_prop
        m_fuel = m_fuel_prop
        empty_fraction = empty_fraction_prop
        fuel_fraction = m_fuel_prop / m0
        history = history_prop
        method_name = 'proportion'

    # Podział masowy według Torenbeeka / BIPOL
    breakdown_shares = {
        "piston_ga": {
            "wing": 0.28, "fuselage": 0.24, "tail": 0.05, "gear": 0.12, 
            "propulsion": 0.21, "systems": 0.10
        },
        "turboprop_regional": {
            "wing": 0.25, "fuselage": 0.23, "tail": 0.06, "gear": 0.11,
            "propulsion": 0.22, "systems": 0.13
        },
        "jet_business": {
            "wing": 0.26, "fuselage": 0.24, "tail": 0.06, "gear": 0.10,
            "propulsion": 0.19, "systems": 0.15
        },
        "jet_transport": {
            "wing": 0.27, "fuselage": 0.25, "tail": 0.05, "gear": 0.11,
            "propulsion": 0.18, "systems": 0.14
        },
        "uav": {
            "wing": 0.30, "fuselage": 0.22, "tail": 0.06, "gear": 0.08,
            "propulsion": 0.20, "systems": 0.14
        }
    }
    shares = dict(breakdown_shares.get(ac_type, breakdown_shares["piston_ga"]))
    if ac_type == "glider" or engine_type == "none":
        remaining = 1.0 - shares["propulsion"]
        shares = {key: (0.0 if key == "propulsion" else value / remaining) for key, value in shares.items()}
    if wing_config == "braced_high":
        shares["wing"] = round(shares["wing"] * 0.89, 3)
        shares["fuselage"] = round(1.0 - (shares["wing"] + shares["tail"] + shares["gear"] + shares["propulsion"] + shares["systems"]), 3)

    mass_components = {
        "m_wing": round(m_empty * shares["wing"], 1),
        "m_fuselage": round(m_empty * shares["fuselage"], 1),
        "m_tail": round(m_empty * shares["tail"], 1),
        "m_gear": round(m_empty * shares["gear"], 1),
        "m_propulsion": round(m_empty * shares["propulsion"], 1),
        "m_systems": round(m_empty * shares["systems"], 1),
    }

    # Masa bez paliwa (Zero Fuel Weight)
    m_zfw = m_empty + m_payload + m_crew

    # Passenger/cargo/fuel trade at fixed MTOW (notatka prowadzącego IMG...122735)
    payload_range = []
    if engine_type != 'none' and ac_type != 'glider' and n_pax:
        other_phases = ff_warmup * ff_takeoff * ff_climb * ff_descent * ff_loiter * ff_landing
        range_scale = (v_cr_ms / c_t_sec if engine_type == 'jet' else eta_p / (c_p * G0)) * ld_cr
        for passengers in sorted({n_pax, max(0, n_pax - 1), n_pax // 2, 0}, reverse=True):
            payload = passengers * (m_pax + m_bag) + m_cargo
            fuel = m0 - m_empty - m_crew - payload
            cruise_fraction = (1 - fuel / (m0 * f_trapped)) / other_phases
            available_range = (-range_scale * math.log(cruise_fraction) / 1000
                               if 0 < cruise_fraction <= 1 else None)
            payload_range.append({'passengers': passengers, 'payload_kg': round(payload, 1),
                                  'fuel_kg': round(fuel, 1), 'range_km': round(available_range, 1) if available_range is not None else None})

    # Podsumowanie obu metod
    sizing_methods = {
        "proportion": {
            "method": "proportion",
            "name": "Metoda proporcji (BIPOL_1 s. 4, wzory 4–5)",
            "m0": round(m0_prop, 1),
            "m_empty": round(m_empty_prop, 1),
            "m_fuel": round(m_fuel_prop, 1),
            "empty_fraction": round(m_empty_prop / m0_prop, 4),
            "fuel_fraction": round(m_fuel_prop / m0_prop, 4),
            "total_mff": round(m_ff, 5),
            "iterations": history_prop,
            "residual": history_prop[-1]["diff"] if history_prop else 0.0
        },
        "iterative": {
            "method": "iterative",
            "name": "Metoda iteracyjna (BIPOL_1 s. 4, 12 kroków)",
            "m0": round(m0_iter, 1),
            "m_empty": round(m_empty_iter, 1),
            "m_fuel": round(m_fuel_iter, 1),
            "m_drop": round(m_drop, 1),
            "empty_fraction": round(m_empty_iter / m0_iter, 4),
            "fuel_fraction": round(m_fuel_iter / m0_iter, 4),
            "iterations": history_iter,
            "residual_relative": history_iter[-1]["diff_rel"] if history_iter else 0.0,
            "phases": {
                "m0": round(m0_iter, 1),
                "m1_takeoff": round(m1, 1),
                "m2_climb": round(m2, 1),
                "m3_outbound": round(m3, 1),
                "m3_post_task": round(m3_burn, 1),
                "m4_post_drop": round(m4, 1),
                "m5_return": round(m5, 1),
                "m6_loiter": round(m6, 1),
                "m7_landing": round(m7, 1)
            }
        }
    }

    return {
        "m0": round(m0, 1),
        "m_empty": round(m_empty, 1),
        "m_fuel": round(m_fuel, 1),
        "m_payload": round(m_payload, 1),
        "m_crew": round(m_crew, 1),
        "n_crew": n_crew,
        "n_pax": n_pax,
        "unmanned": unmanned,
        "m_zfw": round(m_zfw, 1),
        "empty_fraction": round(empty_fraction, 4),
        "empty_mass_model": ('bipol1_trend' if trend_model else
                             'fixed_fraction' if params.get('empty_mass_fraction') is not None else 'class_correlation'),
        "empty_mass_trend": {"A": float(trend_A), "C": float(trend_C), "k_vs": k_vs} if trend_model else None,
        "fuel_fraction": round(fuel_fraction, 4),
        "payload_fraction": round(m_payload / m0, 4),
        "ld_cruise_used": round(ld_cr, 2),
        "primary_method": method_name,
        "payload_drop_kg": round(m_drop, 1),
        "payload_remaining_kg": round(m_payload_remaining, 1),
        "sizing_methods": sizing_methods,
        "mission_assumptions": {
            "method": method_name,
            "phase_model": params.get('mission_phase_model', 'galinski'),
            "reserve_factor": float(params.get('fuel_reserve_factor', 1.06)),
            "ld_factor": float(params.get('mission_ld_factor', CRUISE_LD_FACTOR)),
            "k_max_preliminary": k_max_theo,
            "mass_residual_relative": abs(m0 - m_empty - m_fuel - m_payload - m_crew) / m0,
            "source": "BIPOL_1.pdf, s. 4–6; wytyczne prowadzącego, IMG20261021122751.jpg (K=0,94 Kmax)",
            "note": "Metoda proporcji dla misji bez zrzutu ładunku (wzory 4–5); metoda iteracyjna dla misji ze zrzutem ładunku (12 kroków).",
        },
        "fuel_fractions_detail": {
            "warmup": ff_warmup,
            "takeoff": ff_takeoff,
            "climb": ff_climb,
            "cruise": ff_cruise,
            "task": ff_task,
            "descent": ff_descent,
            "loiter": ff_loiter,
            "landing": ff_landing,
            "total_mff": m_ff
        },
        "breakdown": mass_components,
        "iterations": history,
        "payload_range": payload_range
    }
