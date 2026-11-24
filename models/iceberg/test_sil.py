"""Tests for the sea-ice locking rule of Marson et al. (2024).

The numbers pinned here are the paper's defaults (A_s = 0.90, A_t = 0.86,
P* = 20,000, P_t = 0.8 P_s, 15 % floor) worked by hand, so a change to any of
them, or to the corrected ramp sign, fails a test.

    python -m pytest models/iceberg/test_sil.py -q
"""
import itertools
import math

import pytest

import sil
from sil import C_SI, P_STAR, RHO_SI, locking_force_per_width, ramp, sil_velocity

FREE = (0.05, -0.02)     # berg velocity without sea ice, m/s
ICE = (-0.20, 0.10)      # sea-ice velocity, m/s


def test_defaults_are_the_published_values():
    assert (sil.RHO_SI, sil.C_SI, sil.P_STAR) == (916.7, 0.9, 20_000.0)
    assert (sil.A_S, sil.A_GAP, sil.PT_FACTOR, sil.A_FLOOR) == (0.90, 0.04, 0.8, 0.15)


def test_thin_ice_cover_has_no_effect():
    for conc in (0.0, 0.10, 0.15):                  # the floor itself is "no effect"
        assert sil_velocity(*FREE, conc, 2.0, *ICE) == (*FREE, 0.0)


def test_full_cover_of_very_thick_ice_locks_the_berg_to_the_ice():
    u, v, lam = sil_velocity(*FREE, 1.0, 10.0, *ICE)
    assert lam == 1.0
    assert (u, v) == ICE


def test_lambda_is_always_between_0_and_1():
    concs = [0.0, 0.15, 0.16, 0.5, 0.86, 0.87, 0.88, 0.9, 0.95, 1.0, 1.02]
    thicks = [0.0, 0.01, 0.3, 1.0, 5.0]
    speeds = [-3.0, -0.2, 0.0, 0.2, 3.0]
    for conc, thick, u_si, v_si in itertools.product(concs, thicks, speeds, speeds):
        u, v, lam = sil_velocity(*FREE, conc, thick, u_si, v_si)
        assert 0.0 <= lam <= 1.0
        # the result always lies between the two velocities
        assert min(FREE[0], u_si) - 1e-12 <= u <= max(FREE[0], u_si) + 1e-12
        assert min(FREE[1], v_si) - 1e-12 <= v <= max(FREE[1], v_si) + 1e-12


def test_ramp_is_monotonic_and_uses_the_corrected_sign():
    values = [ramp(0.80 + 0.001 * i, 0.86, 0.90) for i in range(160)]
    assert values == sorted(values)
    assert values[0] == 0.0 and values[-1] == 1.0
    # printed Eq. 5 has (v_t - v_s) underneath and would give -0.5 here
    assert ramp(0.88, 0.86, 0.90) == pytest.approx(0.5)
    assert ramp(0.86, 0.86, 0.90) == 0.0 and ramp(0.90, 0.86, 0.90) == 1.0


def test_lambda_rises_with_concentration_through_the_transition():
    lams = [sil_velocity(*FREE, 0.84 + 0.005 * i, 1.0, *ICE)[2] for i in range(17)]
    assert lams == sorted(lams)
    assert lams[0] == 0.0 and lams[-1] == 1.0
    u, v, lam = sil_velocity(*FREE, 0.88, 1.0, *ICE)   # half-way in concentration
    assert lam == pytest.approx(0.5)
    assert (u, v) == pytest.approx((-0.075, 0.04))


def test_missing_sea_ice_has_no_effect():
    good = [0.95, 1.0, *ICE]
    for i in range(4):
        args = list(good)
        args[i] = math.nan
        assert sil_velocity(*FREE, *args) == (*FREE, 0.0)


def test_ice_too_weak_for_the_drag_does_not_lock():
    # A = 0.95 puts the concentration ramp at 1, so lambda is the strength ramp.
    conc, thick = 0.95, 1.0
    strength = P_STAR * thick * math.exp(-20.0 * (1.0 - conc))

    def ice_speed_for(p_s):       # berg at rest, ice moving east at this speed
        return math.sqrt(p_s / (0.5 * RHO_SI * C_SI * thick))

    # strength = 0.9 P_s sits half-way between P_t = 0.8 P_s and P_s
    half = sil_velocity(0.0, 0.0, conc, thick, ice_speed_for(strength / 0.9), 0.0)
    assert half[2] == pytest.approx(0.5)
    # strength = 0.5 P_s is below P_t: the ice breaks, the berg is free
    assert sil_velocity(0.0, 0.0, conc, thick, ice_speed_for(strength / 0.5), 0.0)[2] == 0.0
    # zero-thickness ice has no strength at all
    assert sil_velocity(*FREE, 1.0, 0.0, *ICE) == (*FREE, 0.0)


def test_overrides_move_the_thresholds():
    assert sil_velocity(*FREE, 0.92, 1.0, *ICE)[2] == 1.0
    assert sil_velocity(*FREE, 0.92, 1.0, *ICE, a_s=0.95)[2] == pytest.approx(0.25)
    # the floor only bites when raised above the ramp: at the floor is "no effect"
    assert sil_velocity(*FREE, 0.92, 1.0, *ICE, a_floor=0.92) == (*FREE, 0.0)
    assert sil_velocity(*FREE, 0.93, 1.0, *ICE, a_floor=0.92)[2] == 1.0
    # halving P* halves the strength: 0.9 P_s becomes 0.45 P_s, below P_t
    conc, thick = 0.95, 1.0
    speed = math.sqrt(P_STAR * thick * math.exp(-1.0) / 0.9 / (0.5 * RHO_SI * C_SI * thick))
    assert sil_velocity(0.0, 0.0, conc, thick, speed, 0.0, p_star=P_STAR / 2)[2] == 0.0
    assert sil_velocity(0.0, 0.0, conc, thick, speed, 0.0, pt_factor=0.5)[2] == pytest.approx(0.8)


# --- P_s as the paper defines it: |F_c + F_p + F_o| / W (its Eq. 3) ----------

GIANT = dict(lat_deg=-66.0, length_m=30_000.0, width_m=20_000.0)


def test_locking_force_is_zero_when_ice_and_current_agree():
    assert locking_force_per_width(0.1, -0.05, 0.1, -0.05, **GIANT) == 0.0


def test_locking_force_matches_a_hand_calculation():
    # ice 0.1 m/s faster than the current, eastward, 30 x 20 km x 250 m berg
    f = 2 * 7.2921e-5 * math.sin(math.radians(66.0))
    rotation = 850.0 * 30_000.0 * 250.0 * f * 0.1                      # M f dV / W
    drag = 0.5 * 0.9 * 850.0 * (2 / math.pi) * 50_000.0 * 250.0 * 0.01 / 20_000.0
    expected = math.hypot(rotation, drag)
    assert rotation == pytest.approx(84_935, rel=1e-3) and drag == pytest.approx(1_522, rel=1e-3)
    assert locking_force_per_width(0.15, 0.0, 0.05, 0.0, **GIANT) == pytest.approx(expected)
    # only the velocity difference matters, not its direction
    assert locking_force_per_width(0.05, 0.1, 0.05, 0.0, **GIANT) == pytest.approx(expected)


def test_locking_force_grows_with_berg_length_and_speed_difference():
    base = locking_force_per_width(0.15, 0.0, 0.05, 0.0, **GIANT)
    longer = locking_force_per_width(0.15, 0.0, 0.05, 0.0, lat_deg=-66.0,
                                     length_m=60_000.0, width_m=20_000.0)
    faster = locking_force_per_width(0.25, 0.0, 0.05, 0.0, **GIANT)
    assert longer == pytest.approx(2 * base, rel=1e-3)
    assert faster == pytest.approx(2 * base, rel=1e-3)


def test_given_p_s_decides_locking_instead_of_the_drag_form():
    # full cover, 1 m ice: strength P = 20,000 N/m
    args = (*FREE, 1.0, 1.0, *ICE)
    assert sil_velocity(*args)[2] == 1.0                     # drag form: locks
    assert sil_velocity(*args, p_s=19_000.0)[2] == 1.0       # P above P_s
    assert sil_velocity(*args, p_s=22_222.2)[2] == pytest.approx(0.5, abs=1e-3)
    assert sil_velocity(*args, p_s=30_000.0) == (*FREE, 0.0)  # P below 0.8 P_s


def test_a_giant_berg_needs_stronger_ice_than_a_small_one():
    # same ice, same 0.1 m/s difference: 1.5 m of full pack holds a 200 m berg
    # and cannot hold a 30 km one
    small = locking_force_per_width(0.15, 0.0, 0.05, 0.0, lat_deg=-66.0,
                                    length_m=200.0, width_m=150.0)
    giant = locking_force_per_width(0.15, 0.0, 0.05, 0.0, **GIANT)
    strength = P_STAR * 1.5
    assert small < 0.8 * strength < strength < 0.8 * giant
    assert sil_velocity(0.05, 0.0, 1.0, 1.5, 0.15, 0.0, p_s=small)[2] == 1.0
    assert sil_velocity(0.05, 0.0, 1.0, 1.5, 0.15, 0.0, p_s=giant)[2] == 0.0
