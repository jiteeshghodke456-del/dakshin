#!/usr/bin/env python3
"""Slice 3: apply the trained correction to the latest real forecast cycle
and ask the only question that matters for the route: does the AI change
the Bharati-approach decision?

    python scripts/corrected_forecast.py [cycle YYYY-MM-DD | --all]

Reuses the hindcast scorer's machinery (same regridder, same channels, same
checkpoints) on the newest archived cycle with a full 7-day satellite
history. The corrected field lives on the model's native 25 km NSIDC grid —
it is a correction to the forecast, not a higher-resolution product.

Writes dakshin/figures/corrected_forecast.npz (raw + corrected fields per
lead, with grid lat/lon, for the site's AI layer) and
dakshin/figures/corrected_forecast.json (the approach-decision summary).

--all additionally runs every usable cycle and writes
dakshin/figures/corrected_all.npz (corrected fields only, uint8 sic*200
with 255 = no data, keys c<YYYYMMDD>_l<lead>) and corrected_all.json
(per-cycle approach decisions), for the site to draw the AI edge on every
issued date.
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

from features import build_channels_operational, N_HISTORY  # noqa: E402
from grid import GlorysToNsidcRegridder, nsidc_lonlat  # noqa: E402
from realforecast_hindcast import NRT_DIR, clean_cycles, load_nrt  # noqa: E402

OUT_NPZ = ROOT / "dakshin" / "figures" / "corrected_forecast.npz"
OUT_JSON = ROOT / "dakshin" / "figures" / "corrected_forecast.json"
LEADS = (1, 3, 5, 7)
BHARATI = (-69.4, 76.2)
ICE_LIMIT = 0.80              # VesselModel default; a test pins this


def reachable(sic: np.ndarray, d2_station_km: np.ndarray) -> bool:
    """Is any cell near the station 4-connected to distant open water
    through cells at or under the ice limit? This is the router's notion of
    'approach open', not a min over a circle that mixes in unreachable
    water.  shortcut: ignores depth blocking; upgrade to Router if the
    two ever disagree on a real cycle."""
    from scipy.ndimage import label
    passable = np.isfinite(sic) & (sic <= ICE_LIMIT)
    lab, _ = label(passable)
    near = lab[(d2_station_km <= 50.0) & passable]
    far = lab[(d2_station_km >= 400.0) & passable]
    return bool(near.size and far.size
                and np.intersect1d(near, far).size)


def correct_cycle(day, ds, obs, rg, d2, models):
    """Raw and corrected fields plus the per-lead decision for one cycle."""
    import torch
    history = np.stack([obs[day - dt.timedelta(days=k)]
                        for k in range(N_HISTORY)])
    an = rg(ds["siconc"].isel(time=0).values.astype(np.float32))
    fields, summary = {}, {}
    for lead in LEADS:
        target = day + dt.timedelta(days=lead)
        fc = rg(ds["siconc"].isel(time=lead).values.astype(np.float32))
        x, _ = build_channels_operational(fc, an, history,
                                          int(target.strftime("%Y%m%d")))
        with torch.no_grad():
            delta = models[lead](torch.from_numpy(x))[0, 0].numpy()
        corrected = np.where(np.isfinite(fc),
                             np.clip(fc + delta, 0.0, 1.0), np.nan)
        fields[f"raw_lead{lead}"] = fc
        fields[f"corrected_lead{lead}"] = corrected
        summary[f"lead_{lead}"] = {
            "target": str(target),
            "station_reachable": {
                "raw": reachable(fc, d2),
                "corrected": reachable(corrected, d2),
            },
            "mean_abs_correction": round(float(
                np.nanmean(np.abs(corrected - fc))), 4),
        }
    return fields, summary


def main() -> int:
    from model_io import load_checkpoint

    cycles = clean_cycles()
    obs = load_nrt()
    run_all = len(sys.argv) > 1 and sys.argv[1] == "--all"
    want = (dt.date.fromisoformat(sys.argv[1])
            if len(sys.argv) > 1 and not run_all else None)
    usable = [d for d in sorted(cycles) if all(
        d - dt.timedelta(days=k) in obs for k in range(N_HISTORY))]
    if want is not None:
        usable = [d for d in usable if d == want]
    if not usable:
        print("no cycle with a full 7-day satellite history")
        return 1
    day = usable[-1]
    ds = cycles[day]

    template = xr.open_dataset(next(iter(NRT_DIR.glob("sic_pss25_*.nc"))))
    rg = GlorysToNsidcRegridder(template, ds["latitude"].values,
                                ds["longitude"].values)
    lon, lat = nsidc_lonlat(template)
    d2 = np.hypot((lat - BHARATI[0]) * 111.0,
                  (lon - BHARATI[1]) * 111.0 * np.cos(np.radians(BHARATI[0])))
    models = {lead: load_checkpoint(lead) for lead in LEADS}

    if run_all:
        packed, decisions = {}, {}
        tally = {"raw": 0, "corrected": 0, "persistence": 0, "n": 0}
        for d in usable:
            flds, summ = correct_cycle(d, cycles[d], obs, rg, d2, models)
            leads_out = {}
            for lead in LEADS:
                c = flds[f"corrected_lead{lead}"]
                packed[f"c{d.strftime('%Y%m%d')}_l{lead}"] = np.where(
                    np.isfinite(c), np.round(c * 200), 255).astype(np.uint8)
                row = dict(summ[f"lead_{lead}"]["station_reachable"])
                tgt = d + dt.timedelta(days=lead)
                if tgt in obs:   # verify against the satellite ON the target date
                    truth = reachable(obs[tgt], d2)
                    row["satellite_target"] = truth
                    tally["n"] += 1
                    tally["raw"] += row["raw"] == truth
                    tally["corrected"] += row["corrected"] == truth
                    tally["persistence"] += reachable(obs[d], d2) == truth
                leads_out[f"lead_{lead}"] = row
            decisions[str(d)] = {
                "satellite_day0_reachable": reachable(obs[d], d2),
                "leads": leads_out,
            }
            print(f"{d}: done")
        all_npz = OUT_NPZ.with_name("corrected_all.npz")
        all_json = OUT_JSON.with_name("corrected_all.json")
        np.savez_compressed(all_npz, **packed)
        all_json.write_text(json.dumps({
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "encoding": "uint8 sic*200, 255 = no data; keys c<YYYYMMDD>_l<lead>",
            "ice_limit": ICE_LIMIT,
            "verification": {
                "note": "lead-decisions scored against the satellite field on "
                        "the target date (not day 0); decisions whose target "
                        "is beyond the archive are uncounted",
                "n_decisions": tally["n"],
                "raw_correct": tally["raw"],
                "corrected_correct": tally["corrected"],
                "persistence_correct": tally["persistence"],
                "caveat": "the station's state never flipped inside a lead "
                          "window this season, so persistence scores perfectly "
                          "too: this record separates the corrected field from "
                          "the RAW forecast, not from persistence",
            },
            "cycles": decisions,
        }, indent=2) + "\n")
        print(f"wrote {all_json} and {all_npz} "
              f"({all_npz.stat().st_size/1e6:.1f} MB, {len(usable)} cycles); "
              f"decision verification raw {tally['raw']}/{tally['n']} "
              f"corrected {tally['corrected']}/{tally['n']}")

    fields, summary = correct_cycle(day, ds, obs, rg, d2, models)
    for lead in LEADS:
        s = summary[f"lead_{lead}"]["station_reachable"]
        print(f"lead {lead} ({summary[f'lead_{lead}']['target']}): station "
              f"reachable raw {s['raw']} corrected {s['corrected']} "
              f"(limit {ICE_LIMIT})")

    agree = all(v["station_reachable"]["raw"] == v["station_reachable"]["corrected"]
                for v in summary.values())
    sat = reachable(obs[day], d2)
    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "cycle": str(day),
        "grid": "NSIDC 25 km polar stereographic (model-native); the "
                "correction does not add resolution",
        "question": "is any cell within 50 km of Bharati 4-connected to open "
                    "water 400+ km out through cells at or under the limit "
                    "(depth blocking not applied here)",
        "ice_limit": ICE_LIMIT,
        "satellite_day0_reachable": sat,
        "ai_changed_reachability": not agree,
        "leads": summary,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n")
    np.savez_compressed(OUT_NPZ, lat=lat, lon=lon, **fields)
    print(f"wrote {OUT_JSON} and {OUT_NPZ} "
          f"({OUT_NPZ.stat().st_size/1e6:.1f} MB); "
          f"satellite day-0 reachable: {sat}, AI changed reachability: {not agree}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
