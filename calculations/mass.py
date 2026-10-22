"""
Moduł analizy masowej i wstępnego bilansu mas samolotu (BIPOL I)
Wstępne oszacowanie masy startowej MTOW (m0), masy pustej (me), masy paliwa (mf)
oraz szczegółowy rozkład mas składowych według zaleceń ZSiS MEiL PW / E. Torenbeek / J. Roskam.
"""
import math
from calculations.atmosphere import isa_atmosphere, G0
from calculations.polish_law import is_unmanned, resolve_category, SUBCATEGORIES
from calculations.instructor import CRUISE_LD_FACTOR, MIN_MASS_ITERATIONS

def calculate_mass_sizing(params: dict):
    """
    Parametry wejściowe w słowniku params:
      - aircraft_type: 'piston_ga', 'turboprop_regional', 'jet_business', 'jet_transport', 'uav'
      - n_pax: liczba pasażerów
      - m_pax: masa jednego pasażera [kg] (domyślnie 80 kg)
      - m_bag: masa bagażu na pasażera [kg] (domyślnie 20 kg)
      - m_cargo: dodatkowa masa ładunku cargo [kg]
      - n_crew: liczba członków załogi (domyślnie 2)
      - m_crew_person: masa członka załogi z torbą [kg] (domyślnie 90 kg)
      - range_km: zasięg obliczeniowy [km]
      - cruise_altitude_m: wysokość przelotowa [m]
      - cruise_speed_kmh: prędkość przelotowa [km/h]
      - ld_cruise: doskonałość przelotowa L/D (K) [-]
      - engine_type: 'jet' lub 'prop'
      - sfc: jednostkowe zużycie paliwa:
            dla odrzutowych: c_j w [1/h] lub [g/(kN*s)] -> np. 0.6 1/h
            dla śmigłowych: c_p w [g/(kW*h)] -> np. 280 g/(kW*h) lub [kg/(W*s)]
      - prop_efficiency: sprawność śmigła eta_p (dla 'prop', domyślnie 0.82)
      - loiter_time_min: czas rezerwy / krążenia [min] (domyślnie 45 min)
    """
    ac_type = params.get("aircraft_type", "piston_ga")
    n_pax = int(params.get("n_pax", 4))
    m_pax = float(params.get("m_pax", 80.0))
    # Jeżeli m_bag nie zostało przekazane osobno (w formularzu m_pax oznacza masę pasażera z bagażem = 100 kg), domyślnie 0.0
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

    # Sprzężenie doskonałości przelotowej z geometrią i aerodynamiką (wg BIPOL_1_wzory.pdf wzór 8 i 28)
    AR = float(params.get("aspect_ratio", 8.0))
    oswald_e = float(params.get("oswald_e", 0.80))
    cx0_base = float(params.get("cx0", 0.025))
    wing_config = params.get("wing_config", "low")
    flap_type = params.get("flap_type", "single_slotted")
    slat_type = params.get("slat_type", "none")

    # Ewentualne kary oporu szkodliwego w przelocie od zastrzałów, klap Junkersa lub stałych slotów
    cx0_eff = cx0_base
    if wing_config == "braced_high":
        cx0_eff += 0.0020
    if flap_type == "junkers":
        cx0_eff += 0.0025
    if slat_type == "fixed_slot":
        cx0_eff += 0.0030

    k_max_theo = 0.5 * math.sqrt((math.pi * AR * oswald_e) / max(0.008, cx0_eff))
    if "aspect_ratio" in params and "cx0" in params:
        # Lecture note IMG20261021122751: K_cr = 0.94 Kmax, superseding 0.8 in the PDF.
        ld_cr = k_max_theo * float(params.get('mission_ld_factor', CRUISE_LD_FACTOR))
    else:
        ld_cr = float(params.get("ld_cruise", 12.0))
    
    # 1. Masa płatna (Payload) i załoga
    # Bezzałogowy statek powietrzny (klasa UM wg Dz. U. 2025 poz. 1137): 0 osób na pokładzie,
    # masa płatna = wyposażenie zadaniowe (głowica, sensory, łącze danych).
    unmanned = is_unmanned(params)
    if unmanned:
        n_crew = 0
        n_pax = 0
    m_payload = n_pax * (m_pax + m_bag) + m_cargo
    m_crew = n_crew * m_crew_person
    if m_payload + m_crew <= 0.0:
        raise ValueError("Do wyznaczenia MTOW podaj dodatnią masę załogi lub ładunku.")
    
    # 2. Wyznaczenie ułamka zużycia paliwa (Fuel Fractions)
    if ac_type == "glider" or engine_type == "none":
        ff_warmup = 1.0
        ff_takeoff = 1.0
        ff_climb = 1.0
        ff_cruise = 1.0
        ff_descent = 1.0
        ff_loiter = 1.0
        ff_landing = 1.0
        m_ff = 1.0
        fuel_fraction = 0.0
    else:
        # Etap 1: Rozruch i kołowanie (Warm-up & Taxi)
        ff_warmup = 0.992 if engine_type == "prop" else 0.975
        
        # Etap 2: Start (Takeoff)
        ff_takeoff = 0.995 if engine_type == "prop" else 0.985
        
        # Etap 3: Wznoszenie (Climb)
        ff_climb = 0.988 if engine_type == "prop" else 0.978
        ff_landing = 0.995
        if params.get('mission_phase_model', 'galinski') == 'galinski':
            # BIPOL_1, pp. 4–6: 0.970–0.975 for start and landing.
            # Treat start/taxi as one phase so it is not counted twice.
            ff_warmup, ff_takeoff, ff_landing = 1.0, 0.975, 0.975
        
        # Etap 4: Przelot obliczeniowy (Cruise wg wzoru Bregueta)
        raw_sfc = float(params.get("sfc", 0.62 if engine_type == "jet" else 265.0))
        if engine_type == "jet":
            # Zabezpieczenie na wypadek pozostawienia sfc śmigłowego (np. 265 g/kWh) po zmianie napędu na 'jet'
            sfc_h = raw_sfc if 0.15 <= raw_sfc <= 4.0 else 0.62
            c_t_sec = sfc_h / 3600.0
            ff_cruise = math.exp(- (range_m * c_t_sec) / (v_cr_ms * ld_cr))
        else:
            # Silnik śmigłowy (tłokowy lub turbośmigłowy): sfc w [g/(kW*h)] (lub przeliczenie z kg/(kW*h) jeśli w przedziale 0.12..1.5)
            if 0.12 <= raw_sfc <= 1.5:
                sfc_g_kwh = raw_sfc * 1000.0
            elif raw_sfc >= 80.0:
                sfc_g_kwh = raw_sfc
            else:
                sfc_g_kwh = 265.0
            c_p = (sfc_g_kwh * 1e-3) / (1000.0 * 3600.0) # [kg / (W*s)]
            ff_cruise = math.exp(- (range_m * c_p * G0) / (eta_p * ld_cr))
            
        # Etap 5: Zniżanie (Descent)
        ff_descent = 0.992
        
        # Etap 6: Krążenie / Rezerwa nawigacyjna (Loiter)
        t_loiter_sec = loiter_min * 60.0
        if engine_type == "jet":
            # Krążenie odrzutowca przy doskonałości maksymalnej K_max
            ld_loiter = max(ld_cr, k_max_theo)
            ff_loiter = math.exp(- (t_loiter_sec * c_t_sec) / ld_loiter)
        else:
            # Krążenie samolotu śmigłowego na prędkości ekonomicznej V_ekon (Cz_ekon = sqrt(3)*Cz_opt, K_ekon = 0.866*K_max)
            ld_loiter = 0.866 * k_max_theo
            v_loiter_ms = v_cr_ms * 0.72
            ff_loiter = math.exp(- (t_loiter_sec * v_loiter_ms * c_p * G0) / (eta_p * ld_loiter))
            
        # Całkowity współczynnik misji M_ff
        m_ff = ff_warmup * ff_takeoff * ff_climb * ff_cruise * ff_descent * ff_loiter * ff_landing
        
        # BIPOL_1, eq. 4: reserve + unusable fuel, distinct from explicit loiter.
        f_trapped = float(params.get('fuel_reserve_factor', 1.06))
        fuel_fraction = f_trapped * (1.0 - m_ff)
        if fuel_fraction >= 0.62:
            raise ValueError("Brak wykonalnego bilansu masy dla tej misji: wymagany udział paliwa jest zbyt duży.")
    
    # 3. Parametry korelacji statystycznej dla masy pustej: m_empty / m_0 = A * m_0^C
    # wg Roskama / Raymera / ZSiS MEiL PW dla różnych kategorii
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

    # Modyfikatory konstrukcyjne masy pustej wg monografii prof. C. Galińskiego
    category = resolve_category(params.get("category", "normal"))
    load_basis = SUBCATEGORIES[category]["load_basis"]
    struct_mod = 1.0
    if wing_config == "braced_high":
        struct_mod *= 0.972  # Zastrzały odciążają dźwigar i zmniejszają masę skrzydła o ~10-12%
    if load_basis == "cs23_aerobatic":
        struct_mod *= 1.045  # Współczynnik n_max = +6.0 wymaga wzmocnienia struktury
    elif load_basis in ("cs23_utility", "cs22_utility"):
        struct_mod *= 1.018  # n_max = +4.4 (CS-23 Utility) / +5.3 (CS-22)
    if AR > 9.0:
        struct_mod *= (1.0 + 0.006 * (AR - 9.0)) # Wzrost masy dźwigara przy dużym wydłużeniu
    if flap_type in ["fowler", "double_slotted"]:
        struct_mod *= 1.012  # Wózki szynowe i mechanizm klap Fowlera / dwuszczelinowych
    
    # 4. Pętla iteracyjna dla m_0 (MTOW)
    def empty_share(mass):
        return min(max(A_coeff * max(50.0, mass) ** C_coeff * struct_mod, 0.38), 0.74)

    useful_mass = m_payload + m_crew
    low, high = 0.0, max(coeff["guess"], useful_mass * 2)
    while high * (1 - fuel_fraction - empty_share(high)) < useful_mass:
        high *= 2
        if high > 1e9:
            raise ValueError("Nie uzyskano wykonalnego bilansu masy dla zadanej misji.")
    history = []
    for i in range(100):
        m0 = (low + high) / 2
        empty_fraction = empty_share(m0)
        residual = m0 * (1 - fuel_fraction - empty_fraction) - useful_mass
        history.append({"iter": i + 1, "m0": round(m0, 1),
                        "empty_fraction": round(empty_fraction, 4), "diff": round(abs(residual), 6)})
        if i + 1 >= MIN_MASS_ITERATIONS and abs(residual) < 0.001:
            break
        if residual > 0:
            high = m0
        else:
            low = m0

    m_empty = empty_fraction * m0
    m_fuel = fuel_fraction * m0
    
    # 5. Szczegółowy podział masowy według Torenbeeka / BIPOL
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
        # Brak zespołu napędowego; zachowaj względne proporcje pozostałych
        # grup zamiast przypisywać szybowcowi fikcyjną masę silnika.
        remaining = 1.0 - shares["propulsion"]
        shares = {key: (0.0 if key == "propulsion" else value / remaining) for key, value in shares.items()}
    if wing_config == "braced_high":
        # Redukcja udziału masy skrzydła na rzecz kadłuba/okuć w górnopłacie zastrzałowym
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

    # Passenger/cargo/fuel trade at fixed MTOW (lecture note IMG...122735).
    # This is a mass-limited envelope; tank volume is not known at this stage.
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
        "fuel_fraction": round(fuel_fraction, 4),
        "payload_fraction": round(m_payload / m0, 4),
        "ld_cruise_used": round(ld_cr, 2),
        "mission_assumptions": {
            "phase_model": params.get('mission_phase_model', 'galinski'),
            "reserve_factor": float(params.get('fuel_reserve_factor', 1.06)),
            "ld_factor": float(params.get('mission_ld_factor', CRUISE_LD_FACTOR)),
            "k_max_preliminary": k_max_theo,
            "mass_residual_relative": abs(m0 - m_empty - m_fuel - m_payload - m_crew) / m0,
            "source": "BIPOL_1.pdf, s. 4–6; wytyczne prowadzącego, IMG20261021122751.jpg (K=0,94 Kmax)",
            "note": "Metoda proporcji: bez zrzutu ładunku. Start/wznoszenie/zniżanie/lądowanie są przybliżeniami. Krążenie jest oddzielną fazą; współczynnik 1,06 dodaje rezerwę i paliwo nieużywalne.",
        },
        "fuel_fractions_detail": {
            "warmup": round(ff_warmup, 4),
            "takeoff": round(ff_takeoff, 4),
            "climb": round(ff_climb, 4),
            "cruise": round(ff_cruise, 4),
            "descent": round(ff_descent, 4),
            "loiter": round(ff_loiter, 4),
            "landing": round(ff_landing, 4),
            "total_mff": round(m_ff, 4)
        },
        "breakdown": mass_components,
        "iterations": history,
        "payload_range": payload_range
    }
