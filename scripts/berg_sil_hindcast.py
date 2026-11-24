#!/usr/bin/env python3
"""Test the sea-ice locking (SIL) rule of Marson et al. (2024) on the iceberg
hindcast.

    Marson, J. M., Myers, P. G., Garbo, A., Copland, L., & Mueller, D. (2024).
    Sea ice-driven iceberg drift in Baffin Bay. JGR Oceans, 129, e2023JC020697.
    https://doi.org/10.1029/2023JC020697

Scores the same weekly USNIC fix-to-fix segments as scripts/berg_hindcast.py
in four variants:

    v1  WDE17 on analysis currents, zero wind
    v2  v1 + grounding (assumed keel against IBCSO bathymetry)
    v3  v1 + sea-ice locking
    v4  v2 + sea-ice locking

Sea ice is day 0 of each archived CMEMS cycle (dakshin.berg_forecast.IceField).
SIL runs at the paper's default parameters. The sensitivity grid at the end is
reported as sensitivity only; no parameter is chosen from it.

Before scoring anything new, the script checks that v1 and v2 reproduce the
committed dakshin/figures/berg_hindcast.json row for row.

Writes dakshin/figures/berg_sil_hindcast.json. Scored once, reported as it
comes out.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "dakshin"))
sys.path.insert(0, str(ROOT / "models" / "iceberg"))

import sil  # noqa: E402
from berg_forecast import (ASSUMED_DRAUGHT_M, STATUS_OK, BathymetryGrid,  # noqa: E402
                           IceField)
from berg_hindcast import OUT as COMMITTED_HINDCAST  # noqa: E402
from berg_hindcast import fix_series, load_field, run_segments  # noqa: E402

OUT = ROOT / "dakshin" / "figures" / "berg_sil_hindcast.json"
MOVING_KM = 3.0   # same split as berg_hindcast.py: USNIC fixes resolve ~0.01 deg
SENS_A_S = (0.85, 0.90, 0.95)
SENS_P_STAR = (10_000.0, 20_000.0, 40_000.0)


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "median": None, "mean": None}
    return {"n": len(values), "median": round(float(np.median(values)), 2),
            "mean": round(float(np.mean(values)), 2)}


def summarise(segments: list[dict]) -> dict:
    """Error in km/day over every segment. A held berg predicts no further
    motion, so its error is the distance from where it was held."""
    moving = [s for s in segments if s["persistence_km"] > MOVING_KM]
    still = [s for s in segments if s["persistence_km"] <= MOVING_KM]
    out = {"n_held": sum(s["status"] != STATUS_OK for s in segments)}
    for label, rows in (("all", segments), ("moving", moving), ("still", still)):
        out[label] = stats([s["error_km_per_day"] for s in rows])
    return out


def sil_diagnostics(segments: list[dict]) -> dict:
    hours = sum(s["sil"]["hours"] for s in segments)
    locking = sum(s["sil"]["hours_locking"] for s in segments)
    full = sum(s["sil"]["hours_fully_locked"] for s in segments)
    missing = sum(s["sil"]["hours_no_ice_data"] for s in segments)
    frac = lambda n: round(n / hours, 4) if hours else None  # noqa: E731
    return {
        "berg_hours": hours,
        "hours_no_ice_data": missing,
        "fraction_hours_no_ice_data": frac(missing),
        "fraction_hours_lambda_gt_0": frac(locking),
        "fraction_hours_lambda_eq_1": frac(full),
        "mean_lambda": frac(sum(s["sil"]["lambda_sum"] for s in segments)),
        "segments_with_any_locking": sum(s["sil"]["hours_locking"] > 0 for s in segments),
        "segments_with_no_ice_data_at_all": sum(
            s["sil"]["hours"] > 0 and s["sil"]["hours_no_ice_data"] == s["sil"]["hours"]
            for s in segments),
    }


def ice_at_observed_positions(segments: list[dict], ice: IceField) -> dict:
    """Sea ice at each berg's OBSERVED start position, noon of every day of the
    segment. For a still berg that is where it really sat all week."""
    start = {(name, str(d0)): (lat0, lon0)
             for name, series in fix_series().items()
             for (d0, lat0, lon0, _, _) in series}
    out = {}
    for label, keep in (("still", lambda s: s["persistence_km"] <= MOVING_KM),
                        ("moving", lambda s: s["persistence_km"] > MOVING_KM)):
        speeds, concs, samples = [], [], 0
        for s in filter(keep, segments):
            lat0, lon0 = start[(s["berg"], s["from"])]
            d0 = dt.date.fromisoformat(s["from"])
            for i in range(s["days"] + 1):
                day = d0 + dt.timedelta(days=i)
                a, h, u, v = ice.sample(lon0, lat0, dt.datetime(day.year, day.month, day.day, 12))
                samples += 1
                if all(np.isfinite(x) for x in (a, h, u, v)):
                    speeds.append(float(np.hypot(u, v)))
                    concs.append(float(a))
        out[label] = {
            "samples": samples,
            "samples_with_ice_data": len(speeds),
            "mean_ice_speed_m_per_s": round(float(np.mean(speeds)), 4) if speeds else None,
            "mean_ice_speed_km_per_day": round(float(np.mean(speeds)) * 86.4, 2) if speeds else None,
            "mean_concentration": round(float(np.mean(concs)), 3) if concs else None,
            "fraction_samples_conc_ge_0p90": round(float(np.mean(np.array(concs) >= 0.90)), 3) if concs else None,
        }
    return out


def check_reproduces(label: str, mine: list[dict], committed: list[dict]) -> None:
    key = lambda s: (s["berg"], s["from"], s["to"], s["status"],  # noqa: E731
                     s["error_km"], s["persistence_km"])
    if [key(s) for s in mine] != [key(s) for s in committed]:
        raise SystemExit(f"{label} does not reproduce {COMMITTED_HINDCAST.name}; "
                         "the inputs changed since it was written. Re-run "
                         "scripts/berg_hindcast.py first, then this script.")


def main() -> int:
    field_ = load_field()
    bathy = BathymetryGrid()
    ice = IceField.from_archive()
    ice_days = [dt.date.fromtimestamp(t * 86400.0) for t in ice.t]
    for day, src in sorted(ice.substituted.items()):
        print(f"sea ice: {day} is stale or missing, using {src}")

    runs = {
        "v1_wde17": dict(),
        "v2_grounding": dict(bathymetry=bathy),
        "v3_sil": dict(ice_field=ice),
        "v4_grounding_sil": dict(bathymetry=bathy, ice_field=ice),
    }
    results = {name: run_segments(field_, verbose=False, **kw) for name, kw in runs.items()}

    committed = json.loads(COMMITTED_HINDCAST.read_text())
    check_reproduces("v1", results["v1_wde17"], committed["segments"])
    check_reproduces("v2", results["v2_grounding"], committed["v2_grounding"]["segments"])

    base = results["v1_wde17"]
    n_moving = sum(s["persistence_km"] > MOVING_KM for s in base)
    persistence = {
        "all": stats([s["persistence_km_per_day"] for s in base]),
        "moving": stats([s["persistence_km_per_day"] for s in base if s["persistence_km"] > MOVING_KM]),
        "still": stats([s["persistence_km_per_day"] for s in base if s["persistence_km"] <= MOVING_KM]),
    }
    descriptions = {
        "v1_wde17": "WDE17 on CMEMS analysis surface currents, zero wind",
        "v2_grounding": f"v1 + grounding (assumed keel {ASSUMED_DRAUGHT_M:.0f} m on IBCSO)",
        "v3_sil": "v1 + sea-ice locking, paper defaults",
        "v4_grounding_sil": "v2 + sea-ice locking, paper defaults",
    }
    variants = {}
    for name, segments in results.items():
        variants[name] = {"description": descriptions[name], **summarise(segments)}
        if "ice_field" in runs[name]:
            variants[name]["sil"] = sil_diagnostics(segments)

    # Sensitivity: reported, never used to pick the headline.
    sensitivity = []
    for a_s in SENS_A_S:
        for p_star in SENS_P_STAR:
            segs = run_segments(field_, ice_field=ice, verbose=False,
                                sil_params={"a_s": a_s, "p_star": p_star})
            summary, diag = summarise(segs), sil_diagnostics(segs)
            if (a_s, p_star) == (sil.A_S, sil.P_STAR):
                assert summary == summarise(results["v3_sil"]), "default run must equal v3"
            sensitivity.append({
                "a_s": a_s, "p_star": p_star,
                "is_paper_default": (a_s, p_star) == (sil.A_S, sil.P_STAR),
                "all": summary["all"], "moving": summary["moving"], "still": summary["still"],
                "fraction_hours_lambda_gt_0": diag["fraction_hours_lambda_gt_0"],
                "fraction_hours_lambda_eq_1": diag["fraction_hours_lambda_eq_1"],
            })

    rows = []
    for i, s in enumerate(base):
        row = {k: s[k] for k in ("berg", "from", "to", "days", "persistence_km",
                                 "persistence_km_per_day")}
        row["moving"] = s["persistence_km"] > MOVING_KM
        for name, segments in results.items():
            row[name] = {"status": segments[i]["status"],
                         "error_km_per_day": segments[i]["error_km_per_day"]}
            if "sil" in segments[i]:
                row[name]["sil"] = segments[i]["sil"]
        rows.append(row)

    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "rule": "Sea-ice locking, Marson et al. (2024), JGR Oceans 129, "
                "e2023JC020697, https://doi.org/10.1029/2023JC020697",
        "parameters": {"A_s": sil.A_S, "A_t": round(sil.A_S - sil.A_GAP, 2),
                       "P_star": sil.P_STAR, "P_t_over_P_s": sil.PT_FACTOR,
                       "concentration_floor": sil.A_FLOOR,
                       "rho_si": sil.RHO_SI, "c_si": sil.C_SI,
                       "note": "paper defaults, not tuned on this data"},
        "differences_from_paper": [
            "berg dynamics are WDE17 (closed form), not NEMO-ICB",
            "zero wind",
            "surface currents only (no keel-depth average)",
            "daily sea-ice fields (day 0 of each CMEMS cycle), not model time steps",
            "ramp denominator is (v_s - v_t); the printed Eq. 5 has (v_t - v_s)",
            "P_s uses the no-sea-ice velocity V_sumF where NEMO-ICB uses the berg velocity",
            "an unlocked berg feels no sea-ice drag (WDE17 has no such term)",
        ],
        "caveats": [
            "USNIC positions are accurate to only a few km",
            "weekly fixes: no track between them, no beacons",
            "keel draught and berg thickness are assumed, USNIC publishes neither",
        ],
        "sea_ice": {
            "source": "CMEMS GLO12 day 0 of each archived cycle "
                      "(data/cmems_forecast_archive)",
            "days": f"{ice_days[0]}..{ice_days[-1]}",
            "stale_days_filled_from_nearest_good_day": {
                str(d): str(src) for d, src in sorted(ice.substituted.items())},
        },
        "currents": committed["currents"],
        "n_segments": len(base),
        "split": {"moving_km_threshold": MOVING_KM, "moving": n_moving,
                  "still": len(base) - n_moving},
        "reproduces_committed_berg_hindcast": {"v1": True, "v2": True},
        "persistence_km_per_day": persistence,
        "variants_error_km_per_day": variants,
        "ice_at_observed_berg_positions": ice_at_observed_positions(base, ice),
        "sensitivity": {
            "note": "v3 re-run on a grid; shown as sensitivity only. The headline "
                    "is the paper-default run. No parameter was chosen from this.",
            "runs": sensitivity,
        },
        "segments": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"\n{len(base)} segments: {n_moving} moving (> {MOVING_KM:.0f} km), "
          f"{len(base) - n_moving} still. Error in km/day, median (mean).")
    print(f"{'variant':20s} {'held':>4s} {'all':>13s} {'moving':>13s} {'still':>13s}")
    cell = lambda st: f"{st['median']:5.2f} ({st['mean']:5.2f})"  # noqa: E731
    print(f"{'persistence':20s} {'':>4s} {cell(persistence['all']):>13s} "
          f"{cell(persistence['moving']):>13s} {cell(persistence['still']):>13s}")
    for name, v in variants.items():
        print(f"{name:20s} {v['n_held']:4d} {cell(v['all']):>13s} "
              f"{cell(v['moving']):>13s} {cell(v['still']):>13s}")
    for name in ("v3_sil", "v4_grounding_sil"):
        d = variants[name]["sil"]
        print(f"{name}: {d['berg_hours']} berg-hours, lambda>0 in "
              f"{100 * d['fraction_hours_lambda_gt_0']:.1f}%, lambda=1 in "
              f"{100 * d['fraction_hours_lambda_eq_1']:.1f}%, no ice data in "
              f"{100 * d['fraction_hours_no_ice_data']:.1f}%, "
              f"{d['segments_with_any_locking']} segments with any locking")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
