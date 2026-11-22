#!/usr/bin/env python3
"""Slice 6 check: route on REAL forecast data and evaluate the weather gate.

    python scripts/real_route_run.py [cycle YYYY-MM-DD]

Runs the unmodified sim Router (Dijkstra, arrival-time costs, land + IBCSO
depth blocking) with RealWorld — real GLO12 ice, real CMEMS waves, real ECMWF
wind — for one archived cycle, on the corridor segment the data covers
(south of 55S; there is no wave/wind harvest north of the box). Writes
dakshin/figures/real_route.json with worst_hs/worst wind taken from real files
and the weather gate's state.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "dakshin"))

from gates import weather_gate  # noqa: E402
from real_world import RealWorld  # noqa: E402
from sim.router import Router, VesselModel  # noqa: E402

OUT = ROOT / "dakshin" / "figures" / "real_route.json"
NPZ = ROOT / "dakshin" / "figures" / "corrected_forecast.npz"
NPZ_JSON = ROOT / "dakshin" / "figures" / "corrected_forecast.json"
START = (-55.5, 45.0)      # corridor entry, on the Cape Town-Bharati line
BHARATI = (-69.4, 76.2)


class CorrectedIceWorld:
    """RealWorld with the U-Net correction added to SIC: delta = corrected -
    raw from corrected_forecast.npz, applied by nearest 25 km NSIDC cell at
    the nearest available lead. The correction stays at its native 25 km;
    everything else passes through unchanged."""

    def __init__(self, world, npz_path):
        from pyproj import Transformer
        from scipy.spatial import cKDTree
        self.w = world
        z = np.load(npz_path)
        self._tr = Transformer.from_crs("EPSG:4326", "EPSG:3412", always_xy=True)
        px, py = self._tr.transform(z["lon"].ravel(), z["lat"].ravel())
        self._tree = cKDTree(np.column_stack([px, py]))
        self._leads = sorted(int(k.rsplit("lead", 1)[1]) for k in z.files
                             if k.startswith("corrected_lead"))
        self._delta = {L: (z[f"corrected_lead{L}"] - z[f"raw_lead{L}"]).ravel()
                       for L in self._leads}

    def sample(self, lat, lon, t):
        out = dict(self.w.sample(lat, lon, t))
        tt = float(np.min(t)) if np.ndim(t) else float(t)
        L = min(self._leads, key=lambda k: abs(k - tt))
        px, py = self._tr.transform(np.asarray(lon, float).ravel(),
                                    np.asarray(lat, float).ravel())
        _, idx = self._tree.query(np.column_stack([px, py]))
        d = self._delta[L][idx].reshape(np.shape(out["sic"]))
        out["sic"] = np.clip(np.where(np.isfinite(d), out["sic"] + d,
                                      out["sic"]), 0.0, 1.0)
        return out

    def __getattr__(self, name):
        return getattr(self.w, name)


def solve_with_fallback(world):
    """Route to Bharati; when the approach is sealed, route to the closest
    reachable cell instead and report that distance."""
    router = Router(world, VesselModel(),
                    lat_min=-70.6, lat_max=-55.0, lon_min=13.0, lon_max=79.5)
    result = router.solve(START, BHARATI, depart_t=0.0, objective="time")
    approach_closed = result is None
    closest_km = None
    if approach_closed:
        # The goal is sealed off by over-limit ice (real late-spring fast
        # ice). Route instead to the closest cell the ship can actually
        # reach, and say so — that is the bridge-useful answer.
        LO, LA = np.meshgrid(router.lons, router.lats)
        s0 = world.sample(LA, LO, 0.0)
        passable = (~router.land) & (s0["sic"] <= router.vessel.ice_limit) \
            & ~(np.isfinite(router.depth) & (router.depth < router.vessel.min_depth_m))
        d2goal = np.hypot((LA - BHARATI[0]) * 111.0,
                          (LO - BHARATI[1]) * 111.0 * np.cos(np.radians(BHARATI[0])))
        d2goal[~passable] = np.inf
        j, i = np.unravel_index(np.argmin(d2goal), d2goal.shape)
        closest_km = float(d2goal[j, i])
        result = router.solve(START, (float(router.lats[j]), float(router.lons[i])),
                              depart_t=0.0, objective="time")
    return result, approach_closed, closest_km


def main() -> int:
    cycle = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 \
        else dt.date(2026, 11, 21)
    world = RealWorld(cycle)
    result, approach_closed, closest_km = solve_with_fallback(world)
    if result is None:
        payload = {"cycle": str(cycle), "route": None,
                   "reason": "no route under the ice limit on this cycle"}
        OUT.write_text(json.dumps(payload, indent=2) + "\n")
        print("no route found"); return 1

    # wind along the track at arrival times, from the real IFS file
    worst_wind = None
    winds = []
    for leg in result["legs"]:
        s = world.sample(leg["lat"], leg["lon"], leg["hours"] / 24.0)
        w = s.get("wind_ms")
        if w is not None and np.isfinite(w):
            winds.append(float(w))
    if winds:
        worst_wind = max(winds)

    gate = weather_gate(worst_hs_m=result["worst_hs"], worst_wind_ms=worst_wind)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "cycle": str(cycle),
        "start": START, "goal": BHARATI,
        "segment_note": "corridor segment south of 55S — the harvest box; "
                        "no real wave/wind data exists north of it",
        "approach_closed_at_ice_limit": approach_closed,
        "closest_approach_km": round(closest_km, 1) if closest_km is not None else None,
        "eta_days": result["days"],
        "worst_ice": result["worst_sic"],
        "worst_hs_m": result["worst_hs"],
        "worst_wind_ms": round(worst_wind, 1) if worst_wind is not None else None,
        "weather_gate": {"state": gate.state.name, "reason": gate.reason,
                         "unassessed": gate.unassessed},
        "n_legs": len(result["legs"]),
    }

    # Where the track actually ends relative to the station. Since the
    # one-lattice-cell arrival rule (router commit 478ecd2), solve() succeeds
    # once the ship is within one 0.55 x 0.9 deg diagonal of a station ashore,
    # so "a route exists" no longer means "the ship reaches the station".
    end = result["legs"][-1]
    payload["route_ends_km_from_station"] = round(float(np.hypot(
        (end["lat"] - BHARATI[0]) * 111.0,
        (end["lon"] - BHARATI[1]) * 111.0 * np.cos(np.radians(BHARATI[0])))), 1)
    payload["lattice_note"] = (
        "router lattice is 0.55 x 0.9 deg over native 1/12 deg fields; it "
        "cannot resolve the final ~50 km to the station — the 25 km "
        "reachability check (corrected_forecast.json) covers the approach")

    # Same router on U-Net-corrected ice, on the newest cycle that has a
    # correction: the comparison a reviewer asks for ("does the AI move the
    # route?"). Labelled with its own cycle, which may trail the payload's.
    if NPZ.exists() and NPZ_JSON.exists():
        c_cycle = json.loads(NPZ_JSON.read_text())["cycle"]
        c_world = world if c_cycle == str(cycle) \
            else RealWorld(dt.date.fromisoformat(c_cycle))
        if getattr(c_world, "_hs", None) is None:
            payload["corrected_ice_check"] = {
                "skipped": f"newest corrected cycle ({c_cycle}) has no archived "
                           "wave file and the router needs waves; the check "
                           "runs on the first cycle that has both"}
            c_world = None

        def brief(res, closed, closest):
            e = res["legs"][-1] if res else None
            return {
                "arrived_within_lattice_rule": res is not None and not closed,
                "closest_approach_km": round(closest, 1) if closest is not None else None,
                "eta_days": res["days"] if res else None,
                "worst_ice": res["worst_sic"] if res else None,
                "route_ends_km_from_station": None if e is None else round(float(np.hypot(
                    (e["lat"] - BHARATI[0]) * 111.0,
                    (e["lon"] - BHARATI[1]) * 111.0 * np.cos(np.radians(BHARATI[0])))), 1),
            }

        if c_world is not None:
            payload["corrected_ice_check"] = {
                "cycle": c_cycle,
                "raw": brief(*solve_with_fallback(c_world)),
                "corrected": brief(*solve_with_fallback(CorrectedIceWorld(c_world, NPZ))),
                "note": "U-Net delta added at its native 25 km (nearest cell, "
                        "nearest lead); same vessel, depth and land blocking",
            }

    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
