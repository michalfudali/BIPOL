"""Traceable analytical checks from Galiński & Grabowski, BIPOL_1_wzory.

These idealized, steady, subsonic results supplement the performance solver.
They are not measured aircraft performance or certification evidence.
"""
import math
from calculations.atmosphere import G0, isa_atmosphere


def preliminary_insights(params, mass, geometry, aero):
    rho = isa_atmosphere(params['cruise_altitude_m'])['rho']
    weight = mass['m0'] * G0
    area = geometry['wing']['S']
    cd0, k = aero['cx0_clean'], aero['k_clean']
    cl_ld = math.sqrt(cd0 / k)
    ld_max = 1 / (2 * math.sqrt(cd0 * k))
    operating_points = []
    for key, label, cl, formula in (
        ('max_ld', 'Największa doskonałość / zasięg śmigłowy', cl_ld, 'Cz = √(Cx₀/k), Kmax = 1/(2√(Cx₀k))'),
        ('jet_range', 'Największy zasięg odrzutowy', cl_ld / math.sqrt(3), 'Cz = √(Cx₀/(3k))'),
        ('prop_endurance', 'Najdłuższy lot śmigłowy / minimum mocy', cl_ld * math.sqrt(3), 'Cz = √(3Cx₀/k)'),
    ):
        cd = cd0 + k * cl * cl
        operating_points.append({'key': key, 'label': label, 'cl': cl, 'cd': cd, 'ld': cl/cd,
            'v_tas_kmh': math.sqrt(2*weight/(rho*area*cl))*3.6,
            'below_stall_limit': cl <= aero['cz_max_clean'], 'formula': formula})
    v = params['cruise_speed_kmh']/3.6
    ws = weight/area
    q = .5*rho*v*v
    n45 = math.sqrt(2)
    return {'source': 'BIPOL_1_wzory.pdf, s. 1–9; BIPOL_1.pdf, s. 2–6',
        'altitude_m': params['cruise_altitude_m'], 'rho': rho, 'operating_points': operating_points,
        'k_max': ld_max, 'cx0_from_kmax': 1/(4*k*ld_max*ld_max),
        'wetted_aspect_ratio': geometry['wing']['AR'] / geometry['wetted_area']['swet_over_s'],
        'climb': {'gradient_required': params.get('climb_rate_ms', 0)/v,
            'tw_lower_bound': params.get('climb_rate_ms', 0)/v + 1/ld_max,
            'formula': 'T/W ≥ G + 1/Kmax; G = w/V (przy stałej TAS)'},
        'turn_45': {'load_factor': n45, 'radius_m': v*v/G0, 'rate_deg_s': math.degrees(G0/v),
            'cl_required': n45*ws/q, 'stall_limited_n': q*aero['cz_max_clean']/ws,
            'tw_required': q*cd0/ws + k*n45*n45*ws/q,
            'tw_lower_bound': n45/ld_max,
            'formula': 'n = 1/cosφ; r = V²/[g√(n²−1)]; T/W = qCx₀/(W/S) + k·n²·(W/S)/q'},
        'limitations': 'Biegunowa paraboliczna, stałe zużycie jednostkowe i sprawność napędu, lot ustalony. Prędkości TAS dla masy startowej i wysokości przelotowej. Cz powyżej Czmax oznacza nieosiągalny punkt. Warunek ciągu w zakręcie nie uwzględnia ograniczeń konstrukcji ani dostępnej mocy. Swet służy do kontroli szkicu, bez wymyślonej interpolacji wykresu Raymera.'}
