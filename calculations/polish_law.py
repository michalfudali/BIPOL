"""
Klasyfikacja statków powietrznych wg polskiego prawa lotniczego.

Podstawa prawna:
  Obwieszczenie Ministra Infrastruktury z dnia 6 sierpnia 2025 r. w sprawie ogłoszenia jednolitego
  tekstu rozporządzenia Ministra Infrastruktury w sprawie klasyfikacji statków powietrznych
  (Dz. U. 2025 poz. 1137) – Tabela nr 1 (klasy, kategorie, podkategorie, ograniczenia MTOM),
  Tabela nr 2 (warunki kategorii K1–K6), Tabela nr 3 (podkategorie UL kategorii K4 i K6).

Podstawy projektowe obciążeń (przyjęte dla danej podkategorii – rozporządzenie nie określa
współczynników przeciążeń, wynikają one z przepisów budowy właściwych dla podkategorii):
  CS-25.337, CS-23.337 (Amdt 4: normal / utility / aerobatic / commuter), CS-VLA.337,
  CS-LSA (ASTM F2245), CS-22.337, LTF-UL (urządzenia latające UL), STANAG 4671 USAR.337 (UAV).
"""

KT_TO_KMH = 1.852
LB_PER_KG = 2.20462
AVGAS_DENSITY_KG_L = 0.72
JETA1_DENSITY_KG_L = 0.80
LAW_REF = "Dz. U. 2025 poz. 1137"

# Kategorie zdatności wg Tabeli nr 2
K_CATEGORIES = {
    "K1": "K1. Podstawowa (certyfikat typu EASA / UE 2018/1139)",
    "K2": "K2. Konwencyjna (krajowy certyfikat typu, poza UE 2018/1139)",
    "K3": "K3. Specjalna (bez certyfikatu typu, m.in. amatorska do 4 miejsc)",
    "K4": "K4. Kwalifikowana (lista typów zatwierdzonych UL)",
    "K5": "K5. Niekwalifikowana (bez dokumentów zdatności, cele sportowe/rekreacyjne)",
    "K6A": "K6A. Amatorska (≥ 51 % pracy wykonane przez amatora)",
    "K6E": "K6E. Eksperymentalna",
    "K6H": "K6H. Historyczna",
    "K6R": "K6R. Replika",
}

# Rejestr podkategorii.  Klucze 'normal', 'utility', 'aerobatic', 'commuter', 'transport'
# pozostają aliasami (zgodność wsteczna z zapisanymi projektami).
SUBCATEGORIES = {
    "a1_transport": {
        "code": "A1", "class": "A", "class_name": "A. Samolot",
        "name": "A1. Transportowy duży", "mtom_min": 8618.0, "mtom_max": None,
        "k_allowed": ["K1", "K2", "K3"], "unmanned": False,
        "occupants_max": None, "pax_max": None, "crew_min": 2,
        "load_basis": "cs25", "design_code": "CS-25",
        "occupant_mass_kg": 77.0,
    },
    "a2_commuter": {
        "code": "A2", "class": "A", "class_name": "A. Samolot",
        "name": "A2. Transportu lokalnego (commuter)", "mtom_min": None, "mtom_max": 8618.0,
        "k_allowed": ["K1", "K2", "K3"], "unmanned": False,
        "occupants_max": None, "pax_max": 19, "crew_min": 1,
        "load_basis": "cs23_commuter", "design_code": "CS-23 Commuter",
        "occupant_mass_kg": 77.0,
    },
    "a3_normal": {
        "code": "A3.1", "class": "A", "class_name": "A. Samolot",
        "name": "A3.1. Lekki – Normalna", "mtom_min": None, "mtom_max": 5700.0,
        "k_allowed": ["K1", "K2", "K3"], "unmanned": False,
        "occupants_max": None, "pax_max": 9, "crew_min": 1,
        "load_basis": "cs23_normal", "design_code": "CS-23 Normal",
        "occupant_mass_kg": 77.0,
    },
    "a3_utility": {
        "code": "A3.2", "class": "A", "class_name": "A. Samolot",
        "name": "A3.2. Lekki – Użytkowa", "mtom_min": None, "mtom_max": 5700.0,
        "k_allowed": ["K1", "K2", "K3"], "unmanned": False,
        "occupants_max": None, "pax_max": 9, "crew_min": 1,
        "load_basis": "cs23_utility", "design_code": "CS-23 Utility",
        "occupant_mass_kg": 86.0,
    },
    "a3_aerobatic": {
        "code": "A3.3", "class": "A", "class_name": "A. Samolot",
        "name": "A3.3. Lekki – Akrobacyjna", "mtom_min": None, "mtom_max": 5700.0,
        "k_allowed": ["K1", "K2", "K3"], "unmanned": False,
        "occupants_max": None, "pax_max": 9, "crew_min": 1,
        "load_basis": "cs23_aerobatic", "design_code": "CS-23 Aerobatic",
        "occupant_mass_kg": 86.0,
    },
    "a4_vla": {
        "code": "A4", "class": "A", "class_name": "A. Samolot",
        "name": "A4. Bardzo lekki (VLA)", "mtom_min": None, "mtom_max": 750.0,
        "k_allowed": ["K1", "K2"], "unmanned": False,
        "occupants_max": 2, "pax_max": 1, "crew_min": 1,
        "vs0_max_kmh": 45.0 * KT_TO_KMH, "piston_only": True, "single_engine": True,
        "load_basis": "cs_vla", "design_code": "CS-VLA",
        "occupant_mass_kg": 86.0,
    },
    "a5_lsa": {
        "code": "A5", "class": "A", "class_name": "A. Samolot",
        "name": "A5. Lekki sportowy (LSA)", "mtom_min": None, "mtom_max": 600.0,
        "mtom_max_water": 650.0,
        "k_allowed": ["K1", "K2"], "unmanned": False,
        "occupants_max": 2, "pax_max": 1, "crew_min": 1,
        "vs0_max_kmh": 45.0 * KT_TO_KMH, "piston_only": True, "single_engine": True,
        "load_basis": "cs_lsa", "design_code": "CS-LSA (ASTM F2245)",
        "occupant_mass_kg": 86.0,
    },
    "mg_utility": {
        "code": "MG1", "class": "MG", "class_name": "MG. Motoszybowiec",
        "name": "MG1. Motoszybowiec – Użytkowa", "mtom_min": None, "mtom_max": 850.0,
        "k_allowed": ["K1", "K2"], "unmanned": False,
        "occupants_max": 2, "pax_max": 1, "crew_min": 1, "w_b2_max": 3.0,
        "load_basis": "cs22_utility", "design_code": "CS-22",
        "occupant_mass_kg": 80.0,
    },
    "ul_a": {
        "code": "UL-A", "class": "UL", "class_name": "UL. Urządzenie latające",
        "name": "UL-A. Ultralekki samolot", "mtom_min": None, "mtom_max": 600.0,
        "mtom_max_water": 650.0,
        "k_allowed": ["K4", "K6A", "K6E", "K6H", "K6R"], "unmanned": False,
        "occupants_max": 2, "pax_max": 1, "crew_min": 1,
        "vs0_max_kmh": 45.0 * KT_TO_KMH,
        "load_basis": "ltf_ul", "design_code": "LTF-UL / wymagania ULC dla UL",
        "occupant_mass_kg": 77.0,
    },
    "ul_mg": {
        "code": "UL-MG", "class": "UL", "class_name": "UL. Urządzenie latające",
        "name": "UL-MG. Ultralekki motoszybowiec", "mtom_min": None, "mtom_max": 600.0,
        "k_allowed": ["K4", "K6A", "K6E", "K6H", "K6R"], "unmanned": False,
        "occupants_max": 2, "pax_max": 1, "crew_min": 1,
        "load_basis": "cs22_utility", "design_code": "CS-22 (przyjęte dla UL-MG)",
        "occupant_mass_kg": 77.0,
    },
    "ul_115": {
        "code": "UL-115", "class": "UL", "class_name": "UL. Urządzenie latające",
        "name": "UL-115. Jednoosobowe z napędem", "mtom_min": None, "mtom_max": None,
        "k_allowed": ["K5"], "unmanned": False,
        "occupants_max": 1, "pax_max": 0, "crew_min": 1, "crew_max": 1,
        "empty_mass_max": 115.0, "fuel_volume_max_l": 20.0,
        "vmax_kmh": 102.0, "empty_wing_loading_max": 10.0,
        "load_basis": "ltf_ul", "design_code": "LTF-UL (przyjęte dla UL-115)",
        "occupant_mass_kg": 77.0,
    },
    "um_heavy": {
        "code": "UMW", "class": "UM", "class_name": "UM. Bezzałogowy statek powietrzny",
        "name": "UMW. Bezzałogowy ciężki", "mtom_min": 600.0, "mtom_max": None,
        "k_allowed": ["K1"], "unmanned": True,
        "occupants_max": 0, "pax_max": 0, "crew_min": 0, "crew_max": 0,
        "load_basis": "stanag4671", "design_code": "STANAG 4671 (USAR) / UE 2019/945",
        "occupant_mass_kg": 0.0,
    },
    "um_light": {
        "code": "UML", "class": "UM", "class_name": "UM. Bezzałogowy statek powietrzny",
        "name": "UML. Bezzałogowy lekki", "mtom_min": None, "mtom_max": 600.0,
        "k_allowed": ["K1"], "unmanned": True,
        "occupants_max": 0, "pax_max": 0, "crew_min": 0, "crew_max": 0,
        "load_basis": "stanag4671", "design_code": "STANAG 4671 (USAR) / UE 2019/945",
        "occupant_mass_kg": 0.0,
    },
}

CATEGORY_ALIASES = {
    "normal": "a3_normal",
    "utility": "a3_utility",
    "aerobatic": "a3_aerobatic",
    "acrobatic": "a3_aerobatic",
    "commuter": "a2_commuter",
    "transport": "a1_transport",
    "vla": "a4_vla",
    "lsa": "a5_lsa",
    "uav": "um_light",
}

# Klasy konstrukcyjne (rodzaj napędu / statystyka mas) dopuszczalne w danej podkategorii
AIRCRAFT_TYPE_ALLOWED = {
    "a1_transport": ["jet_transport", "turboprop_regional", "jet_business"],
    "a2_commuter": ["turboprop_regional", "jet_business", "piston_ga"],
    "a3_normal": ["piston_ga", "turboprop_regional", "jet_business"],
    "a3_utility": ["piston_ga", "turboprop_regional"],
    "a3_aerobatic": ["piston_ga", "turboprop_regional"],
    "a4_vla": ["piston_ga"],
    "a5_lsa": ["piston_ga"],
    "mg_utility": ["piston_ga"],
    "ul_a": ["piston_ga"],
    "ul_mg": ["piston_ga"],
    "ul_115": ["piston_ga"],
    "um_heavy": ["uav"],
    "um_light": ["uav"],
}


def resolve_category(category) -> str:
    """Zwraca klucz podkategorii z rejestru (z obsługą aliasów i wartości historycznych)."""
    cat = str(category or "a3_normal").strip().lower()
    cat = CATEGORY_ALIASES.get(cat, cat)
    return cat if cat in SUBCATEGORIES else "a3_normal"


def is_unmanned(params: dict) -> bool:
    """Bezzałogowy statek powietrzny (klasa UM) – zero osób na pokładzie."""
    if params.get("aircraft_type") == "uav":
        return True
    return SUBCATEGORIES[resolve_category(params.get("category"))]["unmanned"]


def default_category_for(aircraft_type: str) -> str:
    return {
        "uav": "um_light",
        "jet_transport": "a1_transport",
        "turboprop_regional": "a2_commuter",
        "jet_business": "a3_normal",
    }.get(aircraft_type, "a3_normal")


def normalize_occupants(params: dict):
    """
    Wymusza zgodność liczby osób na pokładzie z klasą/podkategorią (Tabela nr 1 i 3).
    Zwraca (nowe_params, lista_korekt).
    """
    p = dict(params)
    notes = []
    ac_type = p.get("aircraft_type", "piston_ga")
    cat_key = resolve_category(p.get("category"))

    # Spójność klasa konstrukcyjna <-> klasa UM
    if ac_type == "uav" and not SUBCATEGORIES[cat_key]["unmanned"]:
        notes.append(f"Klasa konstrukcyjna UAV wymaga klasy UM ({LAW_REF}, Tabela nr 1) – "
                     f"podkategorię '{SUBCATEGORIES[cat_key]['code']}' zastąpiono podkategorią klasy UM.")
        cat_key = "um_light"
        p["_um_auto"] = True
    elif SUBCATEGORIES[cat_key]["unmanned"] and ac_type != "uav":
        notes.append("Wybrano podkategorię klasy UM – klasę konstrukcyjną ustawiono na UAV.")
        ac_type = "uav"
    p["aircraft_type"] = ac_type
    p["category"] = cat_key
    sub = SUBCATEGORIES[cat_key]

    n_crew = int(float(p.get("n_crew", 1) or 0))
    n_pax = int(float(p.get("n_pax", 0) or 0))

    if sub["unmanned"]:
        if n_crew or n_pax:
            notes.append(f"Bezzałogowy statek powietrzny (klasa UM): usunięto {n_crew} os. załogi "
                         f"i {n_pax} pasażerów – na pokładzie 0 osób.")
        n_crew, n_pax = 0, 0
        p["m_pax"] = 0.0
        m_cargo = float(p.get("m_cargo", 0.0) or 0.0)
        if m_cargo <= 0.0:
            p["m_cargo"] = 80.0
            notes.append("UAV bez ładunku użytecznego – przyjęto 80 kg wyposażenia zadaniowego "
                         "(głowica optoelektroniczna, łącze danych, sensory).")
    else:
        crew_min = sub.get("crew_min", 1)
        if n_crew < crew_min:
            notes.append(f"Statek załogowy podkategorii {sub['code']} wymaga min. {crew_min} pilota(ów) – skorygowano.")
            n_crew = crew_min
        crew_max = sub.get("crew_max")
        if crew_max is not None and n_crew > crew_max:
            notes.append(f"Podkategoria {sub['code']} jest jednoosobowa – liczbę załogi ograniczono do {crew_max}.")
            n_crew = crew_max
        occ_max = sub.get("occupants_max")
        if occ_max is not None and n_crew + n_pax > occ_max:
            new_pax = max(0, occ_max - n_crew)
            notes.append(f"Podkategoria {sub['code']} dopuszcza max {occ_max} miejsc(a) – "
                         f"liczbę pasażerów zmniejszono z {n_pax} do {new_pax}.")
            n_pax = new_pax
        # Masa projektowa pilota UL nie mniejsza niż 77 kg (przypisy 5 i 6 do Tabeli nr 1)
        if sub["class"] == "UL":
            m_crew_person = float(p.get("m_crew_person", 90.0) or 90.0)
            if m_crew_person < 77.0:
                p["m_crew_person"] = 77.0
                notes.append("Masa projektowa pilota UL podniesiona do 77 kg (przypis 5/6 do Tabeli nr 1).")

    p["n_crew"] = n_crew
    p["n_pax"] = n_pax
    return p, notes


def limit_load_factors(category, m0: float):
    """Dopuszczalne (eksploatacyjne) współczynniki przeciążeń manewrowych n+ / n- wg podstawy projektowej."""
    sub = SUBCATEGORIES[resolve_category(category)]
    basis = sub["load_basis"]
    w_lb = max(1.0, m0) * LB_PER_KG
    n_formula = 2.1 + 24000.0 / (w_lb + 10000.0)

    if basis == "cs25":
        n_pos = min(3.8, max(2.5, n_formula)); n_neg = -1.0
        ref = "CS-25.337: n+ = 2,1 + 24000/(W+10000) ∈ [2,5; 3,8], n- = -1,0"
    elif basis in ("cs23_normal", "cs23_commuter"):
        n_pos = min(3.8, n_formula); n_neg = -0.4 * n_pos
        ref = "CS-23.337(a)(1): n+ = 2,1 + 24000/(W+10000) ≤ 3,8 [W w lb], n- = -0,4·n+"
    elif basis == "cs23_utility":
        n_pos = 4.4; n_neg = -0.4 * n_pos
        ref = "CS-23.337(a)(2): n+ = 4,4, n- = -0,4·n+"
    elif basis == "cs23_aerobatic":
        n_pos = 6.0; n_neg = -0.5 * n_pos
        ref = "CS-23.337(a)(3): n+ = 6,0, n- = -0,5·n+"
    elif basis == "cs_vla":
        n_pos = 3.8; n_neg = -1.5
        ref = "CS-VLA.337: n+ ≥ 3,8, n- ≥ -1,5"
    elif basis == "cs_lsa":
        n_pos = 4.0; n_neg = -2.0
        ref = "CS-LSA / ASTM F2245: n+ ≥ 4,0, n- ≥ -2,0"
    elif basis == "cs22_utility":
        n_pos = 5.3; n_neg = -2.65
        ref = "CS-22.337 (Utility): n1 = +5,3 przy VA, n4 = -2,65 przy VA"
    elif basis == "ltf_ul":
        n_pos = 4.0; n_neg = -2.0
        ref = "LTF-UL §337: n+ = +4,0, n- = -2,0 (przyjęta podstawa projektowa UL)"
    elif basis == "stanag4671":
        w_kg = max(1.0, m0)
        n_pos = min(3.8, 2.1 + 10900.0 / (w_kg + 4536.0)); n_neg = -0.4 * n_pos
        ref = "STANAG 4671 USAR.337: n+ = 2,1 + 10900/(W+4536) ≤ 3,8 [W w kg], n- = -0,4·n+"
    else:
        n_pos = min(3.8, n_formula); n_neg = -0.4 * n_pos
        ref = "CS-23.337 (normal)"
    return round(n_pos, 2), round(n_neg, 2), ref


def envelope_speed_family(category) -> str:
    """Rodzina współczynników VC/VD wg CS-23.335: 'aerobatic', 'utility' lub 'normal'."""
    basis = SUBCATEGORIES[resolve_category(category)]["load_basis"]
    if basis == "cs23_aerobatic":
        return "aerobatic"
    if basis in ("cs23_utility", "cs22_utility"):
        return "utility"
    if basis == "cs25":
        return "transport"
    return "normal"


def suggest_subcategory(m0: float, n_crew: int, n_pax: int, unmanned: bool, engine_type: str) -> str:
    if unmanned:
        return "um_heavy" if m0 > 600.0 else "um_light"
    if m0 > 8618.0:
        return "a1_transport"
    if m0 > 5700.0:
        return "a2_commuter"
    if (n_crew + n_pax) <= 2 and engine_type == "prop":
        if m0 <= 600.0:
            return "ul_a"
        if m0 <= 750.0:
            return "a4_vla"
    return "a3_normal"


def _chk(name, limit, value, ok, source, severity="error"):
    return {"name": name, "limit": limit, "value": value, "ok": bool(ok),
            "severity": "ok" if ok else severity, "source": source}


def check_compliance(params: dict, mass_res: dict, geom_res: dict = None, perf_res: dict = None) -> dict:
    """Weryfikacja zgodności projektu z ograniczeniami podkategorii (Dz. U. 2025 poz. 1137)."""
    cat_key = resolve_category(params.get("category"))
    sub = SUBCATEGORIES[cat_key]
    ac_type = params.get("aircraft_type", "piston_ga")
    engine_type = params.get("engine_type", "prop")
    k_cat = str(params.get("airworthiness_k") or sub["k_allowed"][0]).upper()
    seaplane = bool(params.get("seaplane", False))

    m0 = float(mass_res.get("m0", 0.0))
    m_empty = float(mass_res.get("m_empty", 0.0))
    m_fuel = float(mass_res.get("m_fuel", 0.0))
    n_crew = int(float(params.get("n_crew", 0) or 0))
    n_pax = int(float(params.get("n_pax", 0) or 0))
    occupants = n_crew + n_pax
    S = float((geom_res or {}).get("wing", {}).get("S", 0.0) or 0.0)
    b = float((geom_res or {}).get("wing", {}).get("span", (geom_res or {}).get("wing", {}).get("b", 0.0)) or 0.0)
    speeds = (perf_res or {}).get("speeds", {})
    vs0 = float(speeds.get("vs_lnd_kmh", params.get("v_stall_kmh", 0.0)) or 0.0)
    vmax = float(speeds.get("v_max_sl_kmh", 0.0) or 0.0)

    tab1 = f"{LAW_REF}, Tabela nr 1"
    tab2 = f"{LAW_REF}, Tabela nr 2"
    tab3 = f"{LAW_REF}, Tabela nr 3"
    checks = []

    # Kategoria K
    checks.append(_chk("Kategoria zdatności dopuszczalna dla podkategorii",
                       " / ".join(sub["k_allowed"]), k_cat, k_cat in sub["k_allowed"], tab1))

    # Klasa konstrukcyjna
    allowed_types = AIRCRAFT_TYPE_ALLOWED.get(cat_key, [])
    checks.append(_chk("Klasa konstrukcyjna / napęd zgodny z podkategorią",
                       ", ".join(allowed_types), ac_type, ac_type in allowed_types,
                       f"{tab1}; {sub['design_code']}", "warning"))

    # MTOM
    mtom_max = sub.get("mtom_max_water") if (seaplane and sub.get("mtom_max_water")) else sub.get("mtom_max")
    if mtom_max is not None:
        checks.append(_chk("Maksymalna masa startowa MTOM", f"≤ {mtom_max:.0f} kg", f"{m0:.1f} kg",
                           m0 <= mtom_max, tab3 if sub["class"] == "UL" else tab1))
    if sub.get("mtom_min") is not None:
        checks.append(_chk("Maksymalna masa startowa MTOM", f"> {sub['mtom_min']:.0f} kg", f"{m0:.1f} kg",
                           m0 > sub["mtom_min"], tab1,
                           "error" if sub["class"] == "UM" else "warning"))
    if cat_key == "mg_utility" and k_cat == "K3" and m0 <= 600.0:
        checks.append(_chk("Motoszybowiec K3 – MTOM", "> 600 kg (inaczej UL-MG)", f"{m0:.1f} kg", False, tab1))

    # Osoby na pokładzie
    if sub["unmanned"]:
        checks.append(_chk("Osoby na pokładzie (bezzałogowy statek powietrzny)", "0 os.",
                           f"{occupants} os.", occupants == 0, tab1))
    else:
        checks.append(_chk("Pilot na pokładzie (statek załogowy)", f"≥ {sub.get('crew_min', 1)} os.",
                           f"{n_crew} os.", n_crew >= sub.get("crew_min", 1), tab2))
        if sub.get("occupants_max") is not None:
            checks.append(_chk("Liczba miejsc", f"≤ {sub['occupants_max']}", f"{occupants}",
                               occupants <= sub["occupants_max"],
                               tab3 if sub["class"] == "UL" else f"{tab1}; {sub['design_code']}"))
        if sub.get("pax_max") is not None and sub.get("occupants_max") is None:
            checks.append(_chk("Liczba miejsc pasażerskich (bez pilotów)", f"≤ {sub['pax_max']}", f"{n_pax}",
                               n_pax <= sub["pax_max"], f"{sub['design_code']} §23.1", "warning"))
        if k_cat == "K3" and sub["class"] == "A":
            checks.append(_chk("Samolot K3 konstrukcji amatorskiej – liczba miejsc", "≤ 4", f"{occupants}",
                               occupants <= 4, tab2, "warning"))

    # VS0
    if sub.get("vs0_max_kmh"):
        vs0_lim = sub["vs0_max_kmh"]
        src = tab3 if sub["class"] == "UL" else sub["design_code"]
        if cat_key == "ul_a":
            light_lim = 520.0 if seaplane else 475.0
            if m0 <= light_lim:
                vs0_lim = 35.0 * KT_TO_KMH
                src = f"{tab3}, przypis {'3' if seaplane else '1'}"
        checks.append(_chk("Prędkość przeciągnięcia w konfiguracji do lądowania VS0 (CAS)",
                           f"≤ {vs0_lim:.1f} km/h ({vs0_lim / KT_TO_KMH:.0f} kt)", f"{vs0:.1f} km/h",
                           vs0 <= vs0_lim + 0.05, src))

    if sub.get("piston_only"):
        checks.append(_chk("Napęd: pojedynczy silnik nieturbinowy ze śmigłem", "tłokowy, śmigłowy",
                           f"{ac_type} / {engine_type}", ac_type == "piston_ga" and engine_type == "prop",
                           sub["design_code"]))

    if cat_key == "a2_commuter" and engine_type == "jet":
        checks.append(_chk("Commuter wg CS-23 Amdt 4 – napęd śmigłowy wielosilnikowy", "śmigłowy",
                           "odrzutowy", False, "CS-23 Amdt 4 §23.1(a)(2) (CS-23 Amdt 5: poziom 4)", "warning"))

    if sub.get("w_b2_max") and b > 0:
        wb2 = m0 / (b * b)
        checks.append(_chk("Współczynnik m/b² motoszybowca", f"≤ {sub['w_b2_max']:.1f} kg/m²",
                           f"{wb2:.2f} kg/m²", wb2 <= sub["w_b2_max"], "CS-22.1"))

    # UL-115 – Tabela nr 1 przypis 6 i Tabela nr 2 (K5 pkt 2.5)
    if cat_key == "ul_115":
        checks.append(_chk("Masa własna (bez pilota, wyposażenia ≤ 11 kg i paliwa)", "≤ 115 kg",
                           f"{m_empty:.1f} kg", m_empty <= 115.0, f"{tab1}, przypis 6"))
        rho_f = JETA1_DENSITY_KG_L if engine_type == "jet" else AVGAS_DENSITY_KG_L
        v_fuel = m_fuel / rho_f
        checks.append(_chk("Pojemność zbiorników paliwa", "≤ 20 l", f"{v_fuel:.1f} l", v_fuel <= 20.0,
                           f"{tab2}, K5 pkt 2 ppkt 5 lit. a"))
        if vmax > 0:
            checks.append(_chk("Prędkość lotu poziomego na pełnej mocy (CAS)", "≤ 102 km/h", f"{vmax:.1f} km/h",
                               vmax <= 102.0, f"{tab2}, K5 pkt 2 ppkt 5 lit. b"))
        if S > 0:
            wl = m_empty / S
            checks.append(_chk("Obciążenie powierzchni nośnej pustego UL (bez pilota i paliwa)", "≤ 10 kg/m²",
                               f"{wl:.2f} kg/m²", wl <= 10.0, f"{tab2}, K5 pkt 2 ppkt 5 lit. c"))

    errors = [c for c in checks if c["severity"] == "error"]
    warnings = [c for c in checks if c["severity"] == "warning"]
    suggested = suggest_subcategory(m0, n_crew, n_pax, sub["unmanned"], engine_type)
    n_pos, n_neg, n_ref = limit_load_factors(cat_key, m0)

    return {
        "legal_basis": f"Rozporządzenie Ministra Infrastruktury w sprawie klasyfikacji statków powietrznych ({LAW_REF})",
        "category_key": cat_key,
        "class": sub["class_name"],
        "subcategory": sub["name"],
        "code": sub["code"],
        "airworthiness_k": k_cat,
        "airworthiness_k_name": K_CATEGORIES.get(k_cat, k_cat),
        "k_allowed": sub["k_allowed"],
        "design_code": sub["design_code"],
        "unmanned": sub["unmanned"],
        "load_factors": {"n_pos": n_pos, "n_neg": n_neg, "reference": n_ref},
        "checks": checks,
        "compliant": len(errors) == 0,
        "n_errors": len(errors),
        "n_warnings": len(warnings),
        "suggested_category": suggested,
        "suggested_name": SUBCATEGORIES[suggested]["name"],
        "corrections": list(params.get("_law_corrections", [])),
    }


def catalog_for_frontend() -> dict:
    """Rejestr podkategorii udostępniany frontendowi (/api/aircraft-classification)."""
    out = {}
    for key, s in SUBCATEGORIES.items():
        n_pos, n_neg, ref = limit_load_factors(key, 600.0 if s["class"] != "A" else 1200.0)
        out[key] = {
            "code": s["code"], "class": s["class"], "class_name": s["class_name"], "name": s["name"],
            "mtom_min": s.get("mtom_min"), "mtom_max": s.get("mtom_max"),
            "k_allowed": s["k_allowed"], "unmanned": s["unmanned"],
            "occupants_max": s.get("occupants_max"), "crew_min": s.get("crew_min"),
            "crew_max": s.get("crew_max"), "design_code": s["design_code"],
            "aircraft_types": AIRCRAFT_TYPE_ALLOWED.get(key, []),
            "n_pos_typ": n_pos, "n_neg_typ": n_neg, "load_ref": ref,
        }
    return {"subcategories": out, "k_categories": K_CATEGORIES, "aliases": CATEGORY_ALIASES, "legal_basis": LAW_REF}
