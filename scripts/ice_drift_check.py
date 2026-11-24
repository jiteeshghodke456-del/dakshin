#!/usr/bin/env python3
"""Is the CMEMS sea-ice velocity we lock icebergs to (docs/SIL_EXPERIMENT.md)
right? Compare it with observed ice drift.

Observation: EUMETSAT OSI SAF Global Low Resolution Sea Ice Drift, OSI-405-d
(doi:10.15770/EUM_SAF_OSI_NRT_2007, CC BY 4.0). Satellite-tracked 48-hour ice
displacements on a 62.5 km grid, one file per day.

Model: usi/vsi from day 0 of each archived CMEMS GLO12 cycle, the same
IceField the locking experiment uses.

For every observed vector inside the corridor box (0-80E, 55-78S), the model
velocity is sampled at the vector's start point and averaged over the same 48
hours (every 6 h, trapezoid). This is a fixed-point average, not a tracked
parcel; 48 h of drift is small next to the 62.5 km observation grid.

    python scripts/ice_drift_check.py --fetch   # download + extract the box
    python scripts/ice_drift_check.py           # compare, write the JSON

--fetch writes data/osisaf_drift/osisaf_sh_drift_box.csv (committed, so the
comparison reruns offline). Raw files go to data/osisaf_drift/raw/ (ignored).
Writes dakshin/figures/ice_drift_check.json.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "dakshin"))
sys.path.insert(0, str(ROOT / "models" / "iceberg"))

from berg_forecast import IceField, great_circle_km, known_stale_dates  # noqa: E402

THREDDS = "https://thredds.met.no/thredds"
CATALOG = THREDDS + "/catalog/osisaf/met.no/ice/drift_lr/merged/{y}/{m:02d}/catalog.html"
FILE = THREDDS + "/fileServer/osisaf/met.no/ice/drift_lr/merged/{y}/{m:02d}/{name}"
NAME = re.compile(r"ice_drift_sh_polstere-625_multi-oi_(\d{8})1200-(\d{8})1200\.nc")
DRIFT_DIR = ROOT / "data" / "osisaf_drift"
BOX_CSV = DRIFT_DIR / "osisaf_sh_drift_box.csv"
OUT = ROOT / "dakshin" / "figures" / "ice_drift_check.json"
BOX = {"lon": (0.0, 80.0), "lat": (-78.0, -55.0)}
NOMINAL = 30                      # status_flag: nominal_quality
ACCEPTED = (20, 21, 22, 30)       # + smaller pattern, corrected, interpolated
KM_PER_DEG = 111.195
NEAR_BERG_KM = 200.0
FIELDS = ["start", "end", "lat0", "lon0", "lat1", "lon1", "hours", "flag", "uncert_km"]


def fetch(first: dt.date, last: dt.date) -> None:
    """Download every 48 h product starting in [first, last]; keep box vectors."""
    import xarray as xr
    raw = DRIFT_DIR / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows = []
    months = sorted({(d.year, d.month) for d in (first, last)}
                    | {(first.year, m) for m in range(first.month, last.month + 1)})
    for y, m in months:
        page = urllib.request.urlopen(CATALOG.format(y=y, m=m), timeout=60).read().decode()
        for name in sorted({mt.group(0) for mt in NAME.finditer(page)}):
            start = dt.datetime.strptime(NAME.match(name).group(1), "%Y%m%d").date()
            if not first <= start <= last:
                continue
            path = raw / name
            if not path.exists():
                urllib.request.urlretrieve(FILE.format(y=y, m=m, name=name), path)
            with xr.open_dataset(path) as ds:
                lat, lon = ds["lat"].values, ds["lon"].values
                flag = ds["status_flag"].values[0]
                keep = (np.isin(flag, ACCEPTED)
                        & (lon >= BOX["lon"][0]) & (lon <= BOX["lon"][1])
                        & (lat >= BOX["lat"][0]) & (lat <= BOX["lat"][1]))
                hours = 48.0 + (ds["dt1"].values[0] - ds["dt0"].values[0]) / 3600.0
                end = start + dt.timedelta(days=2)
                for i, j in zip(*np.nonzero(keep)):
                    rows.append([start, end, f"{lat[i, j]:.4f}", f"{lon[i, j]:.4f}",
                                 f"{ds['lat1'].values[0, i, j]:.4f}",
                                 f"{ds['lon1'].values[0, i, j]:.4f}",
                                 f"{hours[i, j]:.3f}", int(flag[i, j]),
                                 f"{ds['uncert_dX_and_dY'].values[0, i, j]:.3f}"])
    with BOX_CSV.open("w", newline="") as fh:
        csv.writer(fh).writerows([FIELDS, *rows])
    print(f"wrote {BOX_CSV}: {len(rows)} vectors")


def berg_points() -> list[tuple[float, float]]:
    """Start positions of the hindcast segments (the bergs SIL was tested on)."""
    from berg_hindcast import BOX as HBOX, fix_series
    return sorted({(lat, lon) for series in fix_series().values()
                   for (_, lat, lon, _, _) in series
                   if HBOX["lon"][0] <= lon <= HBOX["lon"][1]
                   and HBOX["lat"][0] <= lat <= HBOX["lat"][1]})


def describe(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    ou, ov = np.array([r["obs_u"] for r in rows]), np.array([r["obs_v"] for r in rows])
    mu, mv = np.array([r["mod_u"] for r in rows]), np.array([r["mod_v"] for r in rows])
    o_speed, m_speed = np.hypot(ou, ov), np.hypot(mu, mv)
    r2 = lambda x: round(float(x), 2)  # noqa: E731
    return {
        "n": len(rows),
        "observed_speed_km_per_day": {"mean": r2(o_speed.mean()), "median": r2(np.median(o_speed))},
        "model_speed_km_per_day": {"mean": r2(m_speed.mean()), "median": r2(np.median(m_speed))},
        "model_over_observed_mean_speed": r2(m_speed.mean() / o_speed.mean()),
        "share_of_vectors_where_model_is_faster": r2(np.mean(m_speed > o_speed)),
        "vector_difference_km_per_day": {
            "mean": r2(np.hypot(mu - ou, mv - ov).mean()),
            "rmse": r2(np.sqrt(np.mean((mu - ou) ** 2 + (mv - ov) ** 2)))},
        "correlation": {"east": r2(np.corrcoef(ou, mu)[0, 1]), "north": r2(np.corrcoef(ov, mv)[0, 1])},
        "observation_uncertainty_km_per_day_1sd_per_component": r2(
            np.mean([r["uncert"] for r in rows])),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="download and extract, then stop")
    ap.add_argument("--first", default="2026-08-31")
    ap.add_argument("--last", default="2026-11-21")
    args = ap.parse_args()
    if args.fetch:
        fetch(dt.date.fromisoformat(args.first), dt.date.fromisoformat(args.last))
        return 0

    ice = IceField.from_archive()
    stale = known_stale_dates()
    lo = dt.date.fromtimestamp(ice.t[0] * 86400.0)
    hi = dt.date.fromtimestamp(ice.t[-1] * 86400.0)
    bergs = berg_points()
    rows, skipped_stale, no_model = [], 0, 0
    with BOX_CSV.open() as fh:
        for r in csv.DictReader(fh):
            start = dt.date.fromisoformat(r["start"])
            days = [start + dt.timedelta(days=i) for i in range(3)]
            if days[0] < lo or days[-1] > hi:
                continue
            if any(d in stale for d in days):
                skipped_stale += 1
                continue
            lat0, lon0, lat1, lon1 = (float(r[k]) for k in ("lat0", "lon0", "lat1", "lon1"))
            per_day = 24.0 / float(r["hours"])
            obs_u = (lon1 - lon0) * KM_PER_DEG * np.cos(np.radians((lat0 + lat1) / 2)) * per_day
            obs_v = (lat1 - lat0) * KM_PER_DEG * per_day
            t0 = dt.datetime(start.year, start.month, start.day, 12)
            samples = np.array([ice.sample(lon0, lat0, t0 + dt.timedelta(hours=6 * k))
                                for k in range(9)])            # (A, h, u, v)
            if not np.isfinite(samples).all():
                no_model += 1
                continue
            mean = np.trapezoid(samples, axis=0) / 8.0
            rows.append({
                "start": r["start"], "month": start.month, "flag": int(r["flag"]),
                "conc": float(mean[0]), "uncert": float(r["uncert_km"]) * per_day,
                "obs_u": float(obs_u), "obs_v": float(obs_v),
                "mod_u": float(mean[2]) * 86.4, "mod_v": float(mean[3]) * 86.4,
                "near_berg": min(great_circle_km(lat0, lon0, b[0], b[1]) for b in bergs)
                             <= NEAR_BERG_KM,
            })

    nominal = [r for r in rows if r["flag"] == NOMINAL]
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "observation": "EUMETSAT OSI SAF Global Low Resolution Sea Ice Drift OSI-405-d, "
                       "Southern Hemisphere, 62.5 km, 48 h displacements, "
                       "doi:10.15770/EUM_SAF_OSI_NRT_2007, CC BY 4.0",
        "model": "CMEMS GLO12 usi/vsi, day 0 of each archived cycle, sampled at the "
                 "vector start point and averaged over the same 48 h",
        "box": BOX,
        "period": f"{min(r['start'] for r in rows)}..{max(r['start'] for r in rows)} (window starts)",
        "caveats": [
            "fixed-point 48 h mean of the model, not a tracked parcel",
            "observations are 62.5 km averages; the model grid is 1/12 degree",
            "no observed vectors close to the coast or the ice edge (product flag)",
            "windows touching a stale CMEMS day are dropped",
        ],
        "vectors_dropped_for_stale_cmems_day": skipped_stale,
        "vectors_dropped_no_model_ice": no_model,
        "headline_nominal_quality": describe(nominal),
        "all_accepted_flags": describe(rows),
        "nominal_where_model_conc_ge_0p90": describe([r for r in nominal if r["conc"] >= 0.90]),
        "nominal_where_model_conc_lt_0p90": describe([r for r in nominal if r["conc"] < 0.90]),
        f"nominal_within_{NEAR_BERG_KM:.0f}km_of_a_hindcast_berg": describe(
            [r for r in nominal if r["near_berg"]]),
        "nominal_by_month": {str(m): describe([r for r in nominal if r["month"] == m])
                             for m in sorted({r["month"] for r in nominal})},
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    for key in ("headline_nominal_quality", "nominal_where_model_conc_ge_0p90",
                f"nominal_within_{NEAR_BERG_KM:.0f}km_of_a_hindcast_berg"):
        d = payload[key]
        if d["n"]:
            print(f"{key}: n={d['n']} observed {d['observed_speed_km_per_day']['mean']} "
                  f"model {d['model_speed_km_per_day']['mean']} km/day "
                  f"(ratio {d['model_over_observed_mean_speed']}), "
                  f"corr E {d['correlation']['east']} N {d['correlation']['north']}")
        else:
            print(f"{key}: no vectors")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
