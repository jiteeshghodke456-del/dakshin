"""Sea-ice locking (SIL) of icebergs, after Marson et al. (2024).

    Marson, J. M., Myers, P. G., Garbo, A., Copland, L., & Mueller, D. (2024).
    Sea ice-driven iceberg drift in Baffin Bay. JGR Oceans, 129, e2023JC020697.
    https://doi.org/10.1029/2023JC020697

In dense, strong pack ice an iceberg stops moving through the ice and moves
with it. The paper blends the two velocities (its Eq. 7):

    V = (1 - lambda) * V_sumF + lambda * V_si,   lambda = alpha_A * alpha_P

where V_sumF is the berg velocity from every other force and V_si is the
sea-ice velocity. alpha_A ramps from 0 to 1 as concentration A goes from
A_t = A_s - 0.04 to A_s = 0.90. alpha_P ramps as the ice strength
P = P* h exp(-20 (1 - A)) (Eq. 4) goes from P_t = 0.8 P_s to P_s. Below
A = 0.15 sea ice has no effect at all.

**P_s, the strength the ice needs.** The paper computes it locally as "the
force (by unit of length) required for sea ice to resist (without breaking)
all the other forces imposed on the iceberg": the magnitude of its Eq. 3,

    F_si = -(F_c + F_p + F_r + F_a + F_o),

divided by the berg width. `locking_force_per_width` is that rule on the
forces WDE17 has (Coriolis, pressure gradient, water drag), and it is passed
to `sil_velocity` as `p_s`. Because the force grows with berg mass, a giant
berg needs far stronger ice than a small one.

Without `p_s`, `sil_velocity` falls back to the sea-ice drag form of Eq. 2
per unit width, 1/2 rho_si c_si h |V_si - V_sumF|^2. That is NOT the paper's
P_s. It is what the first hindcast run used, from a mis-transcribed brief,
and it is kept so that run stays reproducible. It is so small at real ice
speeds that the strength test never binds: locking then depends on
concentration alone.

Other things that differ from the paper, on purpose:

1. **The ramp denominator.** Eq. 5 is printed as (v - v_t) / (v_t - v_s),
   which is negative across the whole transition. This module uses
   (v - v_t) / (v_s - v_t), the form that goes from 0 to 1.
2. **Where the forces are evaluated.** NEMO-ICB steps the berg's momentum.
   Our drift is a closed form, so `locking_force_per_width` asks what the ice
   must supply to hold the berg at the ice velocity.
3. **The unlocked case.** In the paper an unlocked berg (lambda = 0) can
   still feel sea-ice drag when A > 0.15. Our V_sumF (Wagner-Dell-Eisenman
   2017) has no sea-ice drag term, so here unlocked means plain WDE17.

Defaults are the paper's. They are not tuned on our data.
"""
from __future__ import annotations

import math

try:                       # imported as models.iceberg.sil
    from .drift import C_W, RHO_I, coriolis_abs
except ImportError:        # imported as a top-level module (tests, scripts)
    from drift import C_W, RHO_I, coriolis_abs

RHO_SI = 916.7      # sea-ice density, kg/m^3 (paper, Eq. 2)
C_SI = 0.9          # sea-ice drag coefficient (paper, Eq. 2)
P_STAR = 20_000.0   # ice strength constant, N/m^2 (paper, Eq. 4)
A_S = 0.90          # concentration at which locking is complete
A_GAP = 0.04        # A_t = A_s - A_GAP
PT_FACTOR = 0.8     # P_t = PT_FACTOR * P_s
A_FLOOR = 0.15      # at or below this concentration sea ice does nothing
ASSUMED_THICKNESS_M = 250.0   # berg thickness; USNIC publishes none (as melt.py)


def ramp(v: float, v_t: float, v_s: float) -> float:
    """0 below v_t, 1 above v_s, linear in between (Eq. 5, sign corrected)."""
    if v < v_t:
        return 0.0
    if v > v_s:
        return 1.0
    if v_s <= v_t:
        # thresholds coincide and v sits on them: only reachable with zero
        # strength against zero drag, which cannot hold a berg
        return 0.0
    return (v - v_t) / (v_s - v_t)


def locking_force_per_width(u_si: float, v_si: float, u_w: float, v_w: float,
                            lat_deg: float, length_m: float, width_m: float,
                            thickness_m: float = ASSUMED_THICKNESS_M) -> float:
    """P_s of the paper: |F_c + F_p + F_o| / W in N/m, for a berg held at the
    sea-ice velocity in a current (u_w, v_w), with no wind.

    Forces as in WDE17, on a berg of mass M = rho_i L W H:
      Coriolis + pressure gradient   M f k x (V_w - V_si)       (F_p is the
                                     geostrophic form WDE17 uses)
      water drag                     1/2 rho_w C_w A_w |dV| dV, with
                                     A_w = (rho_i / rho_w) (2 / pi) (L + W) H
    The two are perpendicular, so their magnitudes add in quadrature. Air drag
    is zero at zero wind in WDE17's approximation and there is no wave term.
    """
    dv = math.hypot(u_si - u_w, v_si - v_w)
    mass_per_width = RHO_I * length_m * thickness_m                  # M / W
    rotation = mass_per_width * float(coriolis_abs(lat_deg)) * dv
    drag = (0.5 * C_W * RHO_I * (2.0 / math.pi) * (length_m + width_m)
            * thickness_m * dv * dv / width_m)                       # rho_w cancels
    return math.hypot(rotation, drag)


def sil_velocity(u_f: float, v_f: float, conc: float, thick: float,
                 u_si: float, v_si: float, *,
                 a_s: float = A_S, p_star: float = P_STAR,
                 pt_factor: float = PT_FACTOR,
                 a_floor: float = A_FLOOR,
                 p_s: float | None = None) -> tuple[float, float, float]:
    """Blend the no-sea-ice berg velocity (u_f, v_f) with the ice velocity.

    `p_s` is the strength threshold in N/m, normally from
    `locking_force_per_width`. Left out, the sea-ice drag form is used (see
    the module docstring: that is not the paper's rule).

    Returns (u, v, lambda). Missing sea ice (any NaN), concentration at or
    below `a_floor`, or ice with no thickness leave the velocity untouched
    with lambda = 0.
    """
    if (not all(math.isfinite(x) for x in (conc, thick, u_si, v_si))
            or conc <= a_floor or thick <= 0.0):
        return u_f, v_f, 0.0
    strength = p_star * thick * math.exp(-20.0 * (1.0 - conc))
    if p_s is None:
        p_s = 0.5 * RHO_SI * C_SI * thick * ((u_si - u_f) ** 2 + (v_si - v_f) ** 2)
    lam = (ramp(conc, a_s - A_GAP, a_s)
           * ramp(strength, pt_factor * p_s, p_s))
    return ((1.0 - lam) * u_f + lam * u_si,
            (1.0 - lam) * v_f + lam * v_si, lam)
