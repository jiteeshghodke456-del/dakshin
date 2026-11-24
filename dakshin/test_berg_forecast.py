"""Slice 5 checks from the handoff: stationary in still water, ~8.64 km/day in
a 0.1 m/s current, and a hard stop at the coast. Synthetic fields test the
integrator's plumbing only — validation against real USNIC positions lives in
scripts/berg_hindcast.py on real analysis currents."""
import datetime as dt

import numpy as np
import pytest

from berg_forecast import (STATUS_GROUNDED, STATUS_OK, CurrentField,
                           forecast_track, great_circle_km)

START = dt.datetime(2026, 9, 2, 0, 0)
GIANT = dict(length_m=30_000.0, width_m=20_000.0)


def uniform_field(u=0.0, v=0.0, nan_east_of=None):
    lat = np.arange(-70.0, -59.9, 0.5)
    lon = np.arange(0.0, 40.1, 0.5)
    nd = 12
    uu = np.full((nd, len(lat), len(lon)), u, np.float32)
    vv = np.full((nd, len(lat), len(lon)), v, np.float32)
    if nan_east_of is not None:
        uu[:, :, lon >= nan_east_of] = np.nan
    t0 = np.datetime64(START.date()).astype("datetime64[s]").astype(float) / 86400.0
    return CurrentField(uu, vv, lat, lon, t0 + np.arange(nd) + 0.5)


def test_still_water_berg_stays_put():
    tr = forecast_track("T", -65.0, 20.0, field_=uniform_field(), start=START,
                        days=5, **GIANT)
    assert tr.status == STATUS_OK
    assert great_circle_km(tr.lats[0], tr.lons[0], tr.lats[-1], tr.lons[-1]) < 1e-6


def test_uniform_eastward_current_advects_8_64_km_per_day():
    tr = forecast_track("T", -65.0, 20.0, field_=uniform_field(u=0.1),
                        start=START, days=1, **GIANT)
    assert tr.status == STATUS_OK
    d = great_circle_km(tr.lats[0], tr.lons[0], tr.lats[-1], tr.lons[-1])
    assert abs(d - 8.64) < 0.2          # 0.1 m/s * 86400 s = 8.64 km
    assert tr.lons[-1] > tr.lons[0]     # moved east
    assert abs(tr.lats[-1] - tr.lats[0]) < 0.02


def test_coastal_berg_stops_with_grounded_flag():
    # eastward current pushing straight into a NaN (land/unknown) region
    tr = forecast_track("T", -65.0, 29.0, field_=uniform_field(u=0.5, nan_east_of=30.0),
                        start=START, days=9, **GIANT)
    assert tr.status == STATUS_GROUNDED
    assert tr.lons[-1] < 30.5           # never crossed into the unknown
    assert len(tr.times) > 1            # it did move before stopping


def test_grounding_holds_berg_on_shallow_bank():
    # v2 behaviour: a keel-deep bank under the berg means it must not advect,
    # however strong the current. Uses the real committed bathymetry.
    import numpy as np
    from berg_forecast import ASSUMED_DRAUGHT_M, BathymetryGrid

    bathy = BathymetryGrid()
    # find a real cell in the test field's area shallower than the keel
    lat_sel = (bathy.lat >= -70) & (bathy.lat <= -60)
    lon_sel = (bathy.lon >= 0) & (bathy.lon <= 40)
    depth = -bathy.elev[np.ix_(lat_sel, lon_sel)]
    cand = np.argwhere((depth > 0) & (depth < ASSUMED_DRAUGHT_M))
    assert len(cand), "no keel-deep bank in the test window — adjust window"
    i, j = cand[0]
    la = bathy.lat[lat_sel][i]
    lo = bathy.lon[lon_sel][j]
    tr = forecast_track("T", float(la), float(lo), field_=uniform_field(u=0.5),
                        start=START, days=5, bathymetry=bathy, **GIANT)
    assert tr.status == STATUS_GROUNDED
    assert len(tr.lats) == 1          # never moved

    # same berg, no bathymetry: v1 behaviour unchanged
    tr1 = forecast_track("T", float(la), float(lo), field_=uniform_field(u=0.5),
                         start=START, days=1, **GIANT)
    assert len(tr1.lats) > 1


def test_wind_forcing_R_is_small_for_giants():
    tr = forecast_track("T", -65.0, 20.0, field_=uniform_field(u=0.1),
                        start=START, days=1, **GIANT)
    assert tr.wind_forcing_R is not None and tr.wind_forcing_R < 0.1


# --- sea-ice locking (Marson et al. 2024), wired in behind ice_field ---------

def sheared_field():
    """Currents that vary in latitude, longitude and time, so every part of
    the integrator (both RK2 stages, space and time interpolation) matters."""
    lat = np.arange(-70.0, -59.9, 0.5)
    lon = np.arange(0.0, 40.1, 0.5)
    nd = 6
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    u = np.stack([0.10 + 0.01 * (la + 65.0) + 0.005 * d for d in range(nd)]).astype(np.float32)
    v = np.stack([0.03 * np.sin(np.radians(lo * 9.0)) - 0.004 * d for d in range(nd)]).astype(np.float32)
    t0 = np.datetime64(START.date()).astype("datetime64[s]").astype(float) / 86400.0
    return CurrentField(u, v, lat, lon, t0 + np.arange(nd) + 0.5)


def uniform_ice(conc, thick=1.5, u=0.0, v=0.0):
    from berg_forecast import IceField
    f = sheared_field()
    shape = f.u.shape
    return IceField(np.full(shape, conc, np.float32), np.full(shape, thick, np.float32),
                    np.full(shape, u, np.float32), np.full(shape, v, np.float32),
                    f.lat, f.lon, f.t)


def sheared_track(**kwargs):
    return forecast_track("T", -65.2, 20.3, field_=sheared_field(), start=START,
                          days=3, **GIANT, **kwargs)


def test_without_ice_field_the_track_is_byte_identical_to_before_sil():
    # Pinned from commit dae93a8, the last one before sea-ice locking existed.
    import hashlib
    import struct
    tr = sheared_track()
    blob = struct.pack(f"<{2 * len(tr.lats)}d", *tr.lats, *tr.lons)
    assert len(tr.lats) == 73
    assert (tr.lats[-1], tr.lons[-1]) == (-65.21607267915715, 20.873384155439098)
    assert hashlib.sha256(blob).hexdigest() == (
        "f7259aa354968629e073db81e37874ccf8b58d12bd365369c50936c0ae38c0a8")
    assert tr.wind_forcing_R == 0.0646612222213936
    assert tr.sil_lambda == [] and tr.ice_missing_steps == 0


def test_open_water_ice_field_changes_nothing_but_records_lambda_zero():
    free, iced = sheared_track(), sheared_track(ice_field=uniform_ice(0.10))
    assert (iced.lats, iced.lons) == (free.lats, free.lons)
    assert iced.sil_lambda == [0.0] * 72 and iced.ice_missing_steps == 0


def test_full_thick_pack_carries_the_berg_with_the_ice_not_the_current():
    # ice drifts due north at 0.1 m/s while the current pushes east
    tr = sheared_track(ice_field=uniform_ice(1.0, thick=3.0, v=0.1))
    assert tr.sil_lambda == [1.0] * 72
    assert tr.lons[-1] == tr.lons[0]                       # no eastward motion
    north_km = great_circle_km(tr.lats[0], tr.lons[0], tr.lats[-1], tr.lons[-1])
    assert abs(north_km - 3 * 8.64) < 0.05 and tr.lats[-1] > tr.lats[0]


def test_half_locked_berg_moves_at_the_blend_of_both_velocities():
    free = sheared_track()
    half = sheared_track(ice_field=uniform_ice(0.88))      # still ice, lambda 0.5
    assert half.sil_lambda == pytest.approx([0.5] * 72)
    d_free = great_circle_km(free.lats[0], free.lons[0], free.lats[-1], free.lons[-1])
    d_half = great_circle_km(half.lats[0], half.lons[0], half.lats[-1], half.lons[-1])
    assert 0.45 * d_free < d_half < 0.55 * d_free


def test_missing_ice_data_uses_plain_drift_and_is_counted():
    tr = sheared_track(ice_field=uniform_ice(np.nan))
    free = sheared_track()
    assert (tr.lats, tr.lons) == (free.lats, free.lons)
    assert tr.sil_lambda == [0.0] * 72 and tr.ice_missing_steps == 72


def test_sil_params_reach_the_rule():
    tr = sheared_track(ice_field=uniform_ice(0.88), sil_params={"a_s": 0.95})
    assert tr.sil_lambda == [0.0] * 72                     # A_t is now 0.91


def test_locking_is_applied_in_the_first_rk2_stage_too():
    # Ice velocity grows eastward. A locked berg has no eastward motion, so the
    # midpoint stays on its meridian and one step moves it north at exactly the
    # ice speed there. If stage 1 used the unlocked current instead, the
    # midpoint would slide east and pick up a different ice speed.
    from berg_forecast import M_PER_DEG, IceField
    f = sheared_field()
    v_si = np.broadcast_to(0.01 * f.lon, f.u.shape).astype(np.float32)
    ice = IceField(np.ones(f.u.shape, np.float32), np.full(f.u.shape, 3.0, np.float32),
                   np.zeros(f.u.shape, np.float32), v_si, f.lat, f.lon, f.t)
    tr = forecast_track("T", -65.2, 20.3, field_=f, start=START, days=1 / 24,
                        ice_field=ice, **GIANT)
    v_here = ice.sample(20.3, -65.2, START)[3]
    assert tr.lons[-1] == 20.3
    assert tr.lats[-1] == pytest.approx(-65.2 + v_here * 3600.0 / M_PER_DEG, abs=1e-10)


def test_recorded_lambda_is_the_midpoint_stage_of_each_hour():
    # Still ice whose concentration climbs from 0.86 to 0.90 over one day, so
    # lambda climbs from 0 to 1 and the value at each step's midpoint is known.
    from berg_forecast import IceField
    f = sheared_field()
    conc = np.full(f.u.shape, 0.90, np.float32)
    conc[0] = 0.86
    zeros = np.zeros(f.u.shape, np.float32)
    ice = IceField(conc, np.full(f.u.shape, 2.0, np.float32), zeros, zeros,
                   f.lat, f.lon, f.t)
    noon = START + dt.timedelta(hours=12)        # the first day centre
    tr = forecast_track("T", -65.2, 20.3, field_=f, start=noon, days=1,
                        ice_field=ice, **GIANT)
    assert tr.sil_lambda == pytest.approx([(n + 0.5) / 24 for n in range(24)], abs=1e-5)


def test_force_rule_locks_a_small_berg_but_not_a_giant_in_the_same_ice():
    # 1.5 m of full pack drifting north while the current runs east. The
    # paper's strength threshold scales with berg mass: this ice can hold a
    # 200 m berg at its own velocity and cannot hold a 30 km one.
    ice = uniform_ice(1.0, thick=1.5, v=0.1)
    rule = {"strength_rule": "forces"}
    giant = sheared_track(ice_field=ice, sil_params=rule)
    assert giant.sil_lambda == [0.0] * 72
    assert (giant.lats, giant.lons) == (sheared_track().lats, sheared_track().lons)

    small = forecast_track("T", -65.2, 20.3, 200.0, 150.0, sheared_field(), START, 3,
                           ice_field=ice, sil_params=rule)
    assert small.sil_lambda == [1.0] * 72 and small.lons[-1] == small.lons[0]
    # the first run's drag form locks the giant too: it ignores berg size
    assert sheared_track(ice_field=ice).sil_lambda == [1.0] * 72


def test_unknown_strength_rule_is_rejected():
    with pytest.raises(ValueError, match="strength_rule"):
        sheared_track(ice_field=uniform_ice(1.0), sil_params={"strength_rule": "typo"})
