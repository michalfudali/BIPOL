"""Shared preliminary take-off model, from standstill to a 15 m obstacle."""
import math
from calculations.atmosphere import G0, RHO0


def takeoff_distance(ws, cz_max, cx0, k, engine, loading, eta=.82, eta_to=.65):
    """loading is P/W [W/N] for propellers or T/W [-] for jets.

    Constant mean acceleration, transition at n=1.15, ISA sea level.
    Return unavailable, never fictitious positive acceleration/climb, if power
    cannot overcome drag and rolling resistance. No regulatory field factors.
    """
    if engine == 'none':
        return dict(available=False, ground_roll_m=0., transition_m=0., climb_to_15m_m=0.,
                    air_distance_m=0., climb_angle_deg=0., distance_to_15m=0.,
                    note='Start samodzielny nie dotyczy statku bez napędu.')
    vs = math.sqrt(2 * ws / (RHO0 * cz_max))
    vlof, v2, vtr = 1.15 * vs, 1.2 * vs, 1.175 * vs
    vrms = vlof / math.sqrt(2)
    q = .5 * RHO0 * vrms**2
    phi = 1.6**2 / (1 + 1.6**2)
    thrust_roll = loading if engine == 'jet' else loading * eta_to / vrms
    net = thrust_roll - q / ws * (cx0 + phi * k * .25**2) - .03 * (1 - q / ws * .25)
    q2 = .5 * RHO0 * v2**2
    thrust_climb = loading if engine == 'jet' else loading * eta / v2
    gradient = thrust_climb - q2 / ws * (cx0 + k * (ws / q2)**2)
    ground = vlof**2 / (2 * G0 * net) if net > 0 else None
    if net <= 0 or gradient <= 0:
        return dict(available=False, ground_roll_m=ground, transition_m=None, climb_to_15m_m=None,
                    air_distance_m=None, climb_angle_deg=None, distance_to_15m=None,
                    note='Brak nadmiaru ciągu do rozbiegu lub wznoszenia nad przeszkodę 15 m.')
    gamma = math.asin(min(.35, gradient))
    radius = vtr**2 / (G0 * .15)
    height = radius * (1 - math.cos(gamma))
    if height >= 15:
        gamma = math.acos(max(0., 1 - 15 / radius))
        transition, climb = radius * math.sin(gamma), 0.
    else:
        transition = radius * math.sin(gamma)
        climb = (15 - height) / math.tan(gamma)
    return dict(available=True, ground_roll_m=ground, transition_m=transition,
                climb_to_15m_m=climb, air_distance_m=transition + climb,
                climb_angle_deg=math.degrees(gamma), distance_to_15m=ground + transition + climb,
                note='ISA, poziom morza, przeszkoda 15 m; odcinek naziemny i powietrzny, bez współczynników operacyjnych.')


def required_takeoff_loading(ws, cz_max, cx0, k, engine, distance, eta=.82, eta_to=.65):
    """Solve the same complete-distance model for the matching chart."""
    low, high = 0., 2. if engine == 'jet' else 200.
    def adequate(value):
        result = takeoff_distance(ws, cz_max, cx0, k, engine, value, eta, eta_to)
        return result['available'] and result['distance_to_15m'] <= distance
    if not adequate(high):
        return None
    for _ in range(45):
        middle = (low + high) / 2
        if adequate(middle):
            high = middle
        else:
            low = middle
    return high


def refine_takeoff_sizing(sizing, geom, aero, params, mass):
    """Use the actual flap polar after geometry; keep known engine power fixed."""
    target = params.get('takeoff_distance_m', 0)
    engine = params['engine_type']
    if not target or engine == 'none':
        return
    dp = sizing['design_point']
    def required(ws):
        return required_takeoff_loading(ws, aero['cz_max_to'], aero['cx0_to'], aero['k_to'],
                                        engine, target, params['prop_efficiency'], params['prop_eff_to'])
    requirement = required(mass * G0 / geom['wing']['S'])
    if requirement is None:
        raise ValueError('Zadana całkowita długość startu jest nieosiągalna w modelu. Zwiększ drogę startu lub zmniejsz obciążenie powierzchni.')
    sizing['curve_takeoff'] = [required(ws) for ws in sizing['ws_values']]
    sizing['takeoff_basis'] = '15m'
    if engine == 'jet':
        dp['tw'] = max(dp['tw'], requirement * 1.06)
        dp['thrust_kn'] = dp['tw'] * mass * G0 / 1000
    else:
        dp['required_power_kw'] = max(dp['required_power_kw'], requirement * mass * G0 / 1000 * 1.08)
        if params.get('power_input_mode') != 'fixed':
            dp['power_kw'] = dp['required_power_kw']
            dp['power_hp'] = dp['power_kw'] * 1000 / 735.5
            dp['pw'] = dp['power_kw'] * 1000 / (mass * G0)
            dp['pw_hp_kg'] = dp['power_hp'] / mass
