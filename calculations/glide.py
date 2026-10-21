# -*- coding: utf-8 -*-
"""
Lot szybowy i biegunowa prędkości opadania samolotu / szybowca.
Oparty na metodyce MEiL PW:
dr inż. Zbigniew Paturski — "Przewodnik po projektach z Mechaniki Lotu"
(Projekt nr 4: Lot szybowy. Biegunowa prędkości, wzory 4.1 – 4.12, Tabela 4.1 dla 3 wariantów masowych).
"""
import math
from calculations.atmosphere import G0, isa_atmosphere
from calculations.paturski_ml import paturski_project_4_gliding


def calculate_glide_polar(mass: float, geometry: dict, aero: dict, altitude_m: float = 0.0, params: dict = None):
    """
    Równowaga sił w locie ślizgowym (wzory 4.3 - 4.5):
      V = sqrt( 2*Q / (rho * S * sqrt(Cz^2 + Cx^2)) )
      w = V * Cx / sqrt(Cz^2 + Cx^2)
      K = Cz / Cx
    Wyznacza również Tabelę 4.1 dla 3 wariantów masowych oraz związki analityczne (wzory 4.8 - 4.12).
    """
    if params is None:
        params = {}
    p3 = aero.get("paturski_p3")
    p4 = paturski_project_4_gliding(geometry, params, m0=mass, p3_aero=p3)

    area = float(geometry["wing"]["S"])
    rho = isa_atmosphere(altitude_m)["rho"]
    cd0 = float(aero["cx0_clean"])
    k = float(aero["k_clean"])
    cl_max = float(aero["cz_max_clean"])

    cl_start = min(0.06, cl_max / 10.0)
    lift_coefficients = [cl_start + (cl_max - cl_start) * i / 160 for i in range(161)]
    lift_coefficients += [min(cl_max, math.sqrt(cd0 / k)), min(cl_max, math.sqrt(3.0 * cd0 / k))]
    points = []
    for cl in sorted(set(lift_coefficients)):
        cd = cd0 + k * cl * cl
        gamma = math.atan2(cd, cl)
        speed = math.sqrt(2.0 * mass * G0 / (rho * area * math.hypot(cl, cd)))
        points.append({
            # Round presentation in the UI, preserving force balance in the data.
            "cz": cl,
            "cx": cd,
            "v_ms": speed,
            "v_kmh": round(speed * 3.6, 1),
            "horizontal_ms": speed * math.cos(gamma),
            "sink_ms": speed * math.sin(gamma),
            "gamma_deg": math.degrees(gamma),
            "ld": cl / cd,
        })
    points.sort(key=lambda row: row["v_ms"])

    return {
        "altitude_m": altitude_m,
        "rho": rho,
        "model": "Równowaga dokładna Paturskiego (wzory 4.3–4.5): L=W·cos(γ), D=W·sin(γ).",
        "points": points,
        "best_glide": max(points, key=lambda row: row["ld"]),
        "minimum_sink": min(points, key=lambda row: row["sink_ms"]),
        "paturski_p4": p4,
        "table_4_1_glide": p4.get("table_4_1_glide", []),
        "glide_comparison": p4.get("glide_comparison", {})
    }
