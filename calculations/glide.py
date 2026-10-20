"""Lot szybowy z równowagi obu składowych siły, jak w projekcie z ZIP-a."""
import math

from calculations.atmosphere import G0, isa_atmosphere


def calculate_glide_polar(mass, geometry, aero, altitude_m=0.0):
    """L = W cos(gamma), D = W sin(gamma), prędkość rzeczywista TAS.

    Biegunowa paraboliczna, brak ciągu i oporu trymowania. Próbkowanie po Cz
    omija niejednoznaczne rozwiązywanie równowagi na zadanej prędkości.
    """
    area = geometry["wing"]["S"]
    rho = isa_atmosphere(altitude_m)["rho"]
    cd0, k, cl_max = aero["cx0_clean"], aero["k_clean"], aero["cz_max_clean"]
    cl_start = min(0.06, cl_max / 10)
    lift_coefficients = [cl_start + (cl_max - cl_start) * i / 160 for i in range(161)]
    lift_coefficients += [min(cl_max, math.sqrt(cd0 / k)), min(cl_max, math.sqrt(3 * cd0 / k))]
    points = []
    for cl in sorted(set(lift_coefficients)):
        cd = cd0 + k * cl * cl
        gamma = math.atan2(cd, cl)
        speed = math.sqrt(2 * mass * G0 / (rho * area * math.hypot(cl, cd)))
        points.append({
            "cz": cl, "cx": cd, "v_ms": speed, "v_kmh": speed * 3.6,
            "horizontal_ms": speed * math.cos(gamma),
            "sink_ms": speed * math.sin(gamma), "gamma_deg": math.degrees(gamma),
            "ld": cl / cd,
        })
    points.sort(key=lambda row: row["v_ms"])
    return {
        "altitude_m": altitude_m,
        "rho": rho,
        "model": "Równowaga dokładna L=W·cos(γ), D=W·sin(γ); bez oporu trymowania i ciągu.",
        "points": points,
        "best_glide": max(points, key=lambda row: row["ld"]),
        "minimum_sink": min(points, key=lambda row: row["sink_ms"]),
    }
