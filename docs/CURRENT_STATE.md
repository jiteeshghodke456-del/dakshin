# Current state — night build 2026-11-21/22

## Update 4 (written ~09:50 IST 22 Nov) — model wired in, honesty sweep

- **Reproducibility rerun (Kaggle GPU, dakshin-prototype-train-gpu2)**: v1/v2
  died because Kaggle changed the dataset mount layout for new kernels
  (`/kaggle/input/datasets/<owner>/<slug>/`, legacy kernels keep the old
  path); v3 found the creds but died on a transient NSIDC HTTP 500 (no retry);
  v4 completed with the glob + retry fixes (both now in `make_notebook.py`,
  commit 0848d7e). Result: lead-1 held-out RMSE reproduces to 3e-5
  (0.04649 vs released 0.04646); leads 3–7 spread up to 0.012 (GPU
  nondeterminism); persistence beaten at every lead in every run. The CPU
  clone was on pace to hit Kaggle's 12 h wall mid-lead-1 and its output is
  discarded; its partial log agreed (best val 0.0434–0.0439).
- **The model is now in the product, everywhere it honestly can be**:
  `corrected_forecast.py --all` applies the released checkpoints to all 78
  cycles with full satellite history (`corrected_all.{npz,json}`); the site
  draws the AI edge on every one of those issued dates; the demo bridge
  console gained an "AI correction" panel fed only by release artifacts
  (`/api/model`, provenance kind *real*); the router comparison on corrected
  ice is wired (`CorrectedIceWorld`) but **gated**: no archived cycle has
  both a correction and a wave file yet, and the payload says so.
- **Season-long decision record** (new headline, with its caveat welded on):
  298 verifiable approach go/no-go decisions scored against the satellite on
  each target date — raw 287/298 (11 false "reachable"), corrected 298/298,
  **persistence also 298/298** (the station never flipped state inside a lead
  window all season). The record separates corrected from RAW, not from
  persistence. In `corrected_all.json["verification"]`.
- **Honesty fixes**: real_route.json now always reports
  `route_ends_km_from_station` (50.6 km) — the one-lattice-cell arrival rule
  (478ecd2) had silently turned "closed" into "open" while the track still
  ends 50.6 km out; site ribbon says so. The "full-resolution 1/12° router"
  overclaim is corrected everywhere: 1/12° **fields**, 0.55°×0.9° lattice.
  PROTOTYPE_RESULTS training-years typo fixed (2019–2020, not 2015–2020).
- Site: weekly USNIC berg fixes now follow the issued date (14 issues, bergs
  move), drift chains always true to the grid (×k schematic removed), day
  replay at 0.45 s. IEEE paper drafted+reviewed+revised, **local only** at
  `paper/` (gitignored) and `~/dakshin-paper.pdf` per the owner.
- Stale-history eval (post-update): a live-cycle AI edge on day−1 history is REJECTED by measurement — lead-1 RMSE 0.1076 vs raw 0.1022 (`dakshin/figures/stale_history_eval.json`). The AI layer lags the live cycle by one day, with the published number as the reason.
- Suite: 209 passed, 2 skipped. Frank capability list:
  `docs/WEAKNESS_ANALYSIS.md` §11 (2026-11-22 addendum).

## Overnight run update (written ~01:55 IST 22 Nov)

- Site: full-screen GIS viewer (Polar TEP shell), zoom/pan 1-8x with locked
  raster/vector sync, research-grade layers (full-res ice/thickness/drift,
  current streamlines, SST, wave direction, wind barbs, satellite-vs-model
  edges + innovation with QA hatching, 7-level bathymetry, day animation),
  IcySea-style berg day-dot chains, progressive disclosure, 16px type scale,
  roundel mark + first-visit intro, stale cycles badged, pipeline figures
  single-sourced. All pushed; Pages live.
- Source repo: grounding-aware berg v2 (26/88 held, 4.13 km/day), melt fixed
  to berg-relative speed, RealWorld serves real depth, currents/waves/SST
  int16-packed, NRT truth committed (rolls off NSIDC from 24 Nov), suite 197.
- Kaggle: **DONE.** GPU v8 completed 2026-11-21 22:51 UTC (v7 died on a
  pip numpy upgrade; pinned, commit d7b0d0f). Checkpoints committed with
  SHA256SUMS, Release `model-v0.1` published, hindcast + resolution study
  scored with the model (see docs/PROTOTYPE_RESULTS.md "Real-forecast
  hindcast (2026)"). The redundant CPU clone can be ignored.


If this session was cleared, read this file plus `docs/backlog.md` and
continue from "Next actions". Full task spec: the HANDOFF_TONIGHT text the
owner pasted (slices 1–11 + F1–F4); its hard rules still apply (real data
only; score once, report what comes out; push only to jiteeshghodke456-del).

## Done tonight (all committed and pushed to origin/main)

| Slice | What landed | Evidence |
|---|---|---|
| 1 (code) | `dakshin/model_io.py` checksum-verified loader + tests (skip until checkpoints) | `dakshin/test_model_io.py` |
| 2 (baselines) | NRT truth downloader (89 days), `build_channels_operational`, hindcast scorer. Raw CMEMS beats persistence at all leads | `dakshin/figures/realforecast_hindcast.json` |
| 4 | Currents in daily harvest + 82-day analysis backfill; CI run green | `data/cmems_cur_analysis/`, workflow run 44931056680 |
| 5 | RK2 berg forecast + USNIC validation: **persistence wins, giants are grounded**, measured 4.35 km/day error rate | `dakshin/figures/berg_hindcast.json` |
| 6 | Waves in harvest (daily max), ECMWF wind harvest (daily, CC BY 4.0), `RealWorld`, weather gate from real data (FAILs at 4.77 m waves on 2026-11-21), real route run: **Bharati approach: track ends 50.6 km short of the station** (arrival under the one-lattice-cell rule; the 25 km check says the approach is closed) | `dakshin/figures/real_route.json` |
| 7 | IBCSO v2 subset (CC-BY-4.0), min-depth block in both routers, chart gate never PASS without ENC | `data/bathymetry/`, agent commit ce236c7 |
| 8 | Hardened NMEA AIS decoder (pyais) + traffic gate bands | `dakshin/ais_feed.py` |
| F1 | Resolution study: RMSE blind to resolution (double penalty), IIEE shows 1° losing the edge, 1/12°≈1/4° | `docs/RESOLUTION_STUDY.md` |
| F3 | Coarse currents beat eddy-resolving on grounded bergs → grounding detection is the binding constraint | `dakshin/figures/berg_resolution.json` |

Test suite: 186 passed, 7 skipped (baseline at session start: 159; the 7
skips are model_io + pre-existing, they un-skip when checkpoints land).

## In flight

- **Slice 3 (AI ice into routing / site)**: unblocked now that checkpoints
  are in the repo. Next: apply the lead-matched correction to the latest
  archived cycle (`build_channels_operational` + `model_io`), compare the
  real route decision on raw vs corrected ice, surface the corrected field
  on the site as an AI layer.
- History of the Kaggle saga (for the study doc): the original 2026-08-31
  checkpoints were never in Kaggle's output store because the saved
  notebook's training cell was typed *markdown*; v6 fixed the cell type,
  v7 died importing numpy after pip half-upgraded it, v8 pinned numpy and
  completed. CMEMS credentials come from the private dataset
  `jiteeshghodke/cmems-creds` (CLI batch runs cannot read Kaggle Secrets).

## Progress since this file was written

- Rename DONE (package `dakshin`, hackathon docs under docs/archive-hackathon/).
- Slice 11 DONE: LICENSE (MIT), ATTRIBUTION.md, portable verify_claims
  (29/29 pass), TRUE_CLAIMS updated — the 8.6-day route claim is WITHDRAWN
  (route ends on land per IBCSO).
- F2 DONE: dakshin/readers/nemo.py (classic+CMIP names, curvilinear coords;
  untested on real NEMO output, says so). F4 DONE: models/iceberg/melt.py +
  scripts/berg_melt.py (labelled estimates; dakshin/figures/berg_melt.json).
- Site repo agent running: slice 10 layers + professional UI overhaul.
- Suite: 194 passed, 7 skipped.

## Owner's remaining end-of-build asks

1. **Study doc** written by Haiku and Sonnet subagents: exhaustive — project
   evolution stage by stage, research findings, innovations, architecture,
   file-by-file map, data flow, how to run every data operation, physics
   (WDE17 drift, double penalty, IIEE, POLARIS), papers used. The owner will
   feed it to another AI to study from, so density beats polish.
2. **README.md rewrite** for a physical-oceanography professor (NEMO/ANHA
   background): what this is, the honest results, data sources + licences,
   how to reproduce every number.

## Secrets (never commit)

Kaggle token + CMEMS login are cached in `~/.kaggle` / `~/.copernicusmarine`
in the sandbox; aisstream.io key at `~/.sih-secrets/aisstream.key`
(unused so far — shore AIS is empty in the Southern Ocean anyway).
