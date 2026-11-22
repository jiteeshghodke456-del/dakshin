#!/usr/bin/env python3
"""Does a one-day-stale satellite history cost the correction its skill?

    python scripts/stale_history_eval.py

The live forecast cycle can never have a fresh day-0 satellite file (NSIDC
NRT publishes ~1 day late), so an AI edge for the live cycle must run on
history ending at day-1 — outside the training assumption. This measures
what that staleness costs, on the archive, scored once:

  fresh: history obs[t-0 .. t-6]   (the hindcast's setting)
  stale: history obs[t-1 .. t-7]   (the live-cycle reality)

Same cycles, same mask, same checkpoints, same scoring conventions as
scripts/realforecast_hindcast.py. Writes
dakshin/figures/stale_history_eval.json.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "dakshin"))
sys.path.insert(0, str(ROOT / "scripts"))

from features import N_HISTORY, build_channels_operational, iiee_km2  # noqa: E402
from grid import GlorysToNsidcRegridder, nsidc_lonlat  # noqa: E402
from realforecast_hindcast import NRT_DIR, clean_cycles, load_nrt  # noqa: E402

OUT = ROOT / "dakshin" / "figures" / "stale_history_eval.json"
LEADS = (1, 3, 5, 7)
BOX = {"lat_min": -78.0, "lat_max": -55.0, "lon_min": 0.0, "lon_max": 80.0}


def main() -> int:
    import torch
    from model_io import load_checkpoint

    cycles = clean_cycles()
    obs = load_nrt()
    template = xr.open_dataset(next(iter(NRT_DIR.glob("sic_pss25_*.nc"))))
    first = next(iter(cycles.values()))
    rg = GlorysToNsidcRegridder(template, first["latitude"].values,
                                first["longitude"].values)
    lon, lat = nsidc_lonlat(template)
    box = ((lat >= BOX["lat_min"]) & (lat <= BOX["lat_max"])
           & (lon >= BOX["lon_min"]) & (lon <= BOX["lon_max"]))
    models = {lead: load_checkpoint(lead) for lead in LEADS}

    results = {}
    for lead in LEADS:
        acc = {"se": {k: 0.0 for k in ("cmems", "fresh", "stale")},
               "iiee": {k: [] for k in ("cmems", "fresh", "stale")},
               "cnt": 0.0}
        n = 0
        for day, ds in sorted(cycles.items()):
            target = day + dt.timedelta(days=lead)
            fresh_days = [day - dt.timedelta(days=k) for k in range(N_HISTORY)]
            stale_days = [day - dt.timedelta(days=k + 1) for k in range(N_HISTORY)]
            need = set(fresh_days) | set(stale_days) | {target}
            if any(d not in obs for d in need):
                continue
            fc = rg(ds["siconc"].isel(time=lead).values.astype(np.float32))
            an = rg(ds["siconc"].isel(time=0).values.astype(np.float32))
            truth = obs[target]
            truth_f = np.nan_to_num(truth, nan=0.0)
            mask = np.isfinite(truth) & box & np.isfinite(fc)
            if mask.sum() == 0:
                continue
            preds = {}
            for name, hdays in (("fresh", fresh_days), ("stale", stale_days)):
                x, _ = build_channels_operational(
                    fc, an, np.stack([obs[d] for d in hdays]),
                    int(target.strftime("%Y%m%d")))
                with torch.no_grad():
                    delta = models[lead](torch.from_numpy(x))[0, 0].numpy()
                preds[name] = np.clip(x[0, 0] + delta, 0.0, 1.0)
                if name == "fresh":
                    preds["cmems"] = x[0, 0]
            for name, p in preds.items():
                acc["se"][name] += float((((p - truth_f) ** 2) * mask).sum())
                acc["iiee"][name].append(iiee_km2(p, truth_f, mask))
            acc["cnt"] += float(mask.sum())
            n += 1
        results[f"lead_{lead}"] = {
            "n_cycles": n,
            "rmse": {k: round((v / acc["cnt"]) ** 0.5, 5)
                     for k, v in acc["se"].items()},
            "iiee_km2_mean": {k: round(float(np.mean(v)), 0)
                              for k, v in acc["iiee"].items()},
        }
        r = results[f"lead_{lead}"]
        print(f"lead {lead} (n={n}): rmse fresh {r['rmse']['fresh']} "
              f"stale {r['rmse']['stale']} cmems {r['rmse']['cmems']} | "
              f"iiee fresh {r['iiee_km2_mean']['fresh']:.0f} "
              f"stale {r['iiee_km2_mean']['stale']:.0f} "
              f"cmems {r['iiee_km2_mean']['cmems']:.0f}")

    OUT.write_text(json.dumps({
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "question": "cost of running the correction with satellite history "
                    "ending at day-1 instead of day-0 (the live-cycle reality)",
        "scoring": "identical to realforecast_hindcast.py (pooled RMSE, "
                   "IIEE at 15%), cycles restricted to those where both "
                   "history windows and the target observation exist",
        "leads": results,
    }, indent=2) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
