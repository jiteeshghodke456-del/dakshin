# Dakshin: architecture and data flow

Study document. First written 2026-11-21 against HEAD `44e3efa`; updated 2026-11-22 against HEAD `779cf83` (`git log -1 --format='%h %ad'` gives `779cf83 Sun Nov 22 05:12:19 2026 +0000`), branch `main`; other study documents and `docs/backlog.md` were being edited in the working tree by another process, and everything here describes committed files. Everything below describes committed code and files; the grounding check in `dakshin/berg_forecast.py` that was an uncommitted working-tree edit in the first version is now committed (commit `a274a64`, section 5d). Every number below is taken from a file in the repository, whose path is given beside it, or was measured while writing this document, in which case it says "measured here" and gives the command. Where something is pending or unknown the text says so. Nothing here is invented to fill a gap.

Conventions. Paths are relative to the repository root. "Committed" means tracked by git; "gitignored" means present on the author's disk but not in the repository and therefore to be re-fetched (see section 9). The first version marked every place a U-Net result would sit with "training re-run in progress"; the checkpoints now exist and every such place carries the real result (section 11).

Contents: 1 what the system is; 2 component map; 3 file-by-file tables; 4 the grid story; 5 the data pipelines (a to e); 6 the nine gates; 7 two routing engines; 8 what is real and what is synthetic; 9 data on disk, committed or not; 10 data operations (commands); 11 state of the model and the open items.

---

## 1. What the system is, in one page

Dakshin is an advisory decision aid for Antarctic resupply voyages. The scoped case (ADR-001, `docs/DECISIONS.md`) is one corridor (Cape Town to Bharati/Maitri), one season (austral summer) and one chartered vessel (MV Vasiliy Golovnin, IMO 8723426). It does not steer the ship, it does not warn about growlers or bergy bits, and it does not quote fuel (`docs/TRUE_CLAIMS.md` section 4).

It has four technical parts.

1. A data layer: harvested ocean-model forecasts (CMEMS GLO12 ice, currents, waves), ECMWF 10 m wind, NSIDC passive-microwave sea-ice concentration (the "truth"), USNIC iceberg positions and IBCSO v2 bathymetry. Quality control on the satellite product is a first-class step (`dakshin/ice_quality.py`).
2. A sea-ice model: a small residual U-Net that corrects the CMEMS ice-concentration forecast toward satellite observations (`models/sic_correction/unet.py`). It is trained: four checkpoints (leads 1, 3, 5, 7 days) are committed in `models/sic_correction/checkpoints/`, SHA-256 pinned, published as GitHub release `model-v0.1`, and scored against real operational forecasts (section 5c). It has no role on the live forecast cycle, because that needs a day-0 satellite file that does not exist yet (section 5c, `dakshin/figures/stale_history_eval.json`).
3. An iceberg model: the Wagner, Dell and Eisenman (2017) closed-form drift law driven by CMEMS surface currents, integrated with a midpoint (RK2) scheme, validated against later USNIC fixes, plus a melt estimate (`models/iceberg/`, `dakshin/berg_forecast.py`).
4. A decision layer: a time-dependent Dijkstra router (`dakshin/sim/router.py`) fed by a `RealWorld` object (`dakshin/real_world.py`), and nine decision gates whose worst state sets a "route health" (`dakshin/gates.py`, `dakshin/decision.py`). Unknown evidence is never treated as a pass.

The methodological stance, visible everywhere in the code and the docs, is that the repository reports what a test returns, including when it goes against the project. Four numbers have been withdrawn or restated in the record (17.4-day transit, 8.6-day transit, a figure caption, a defence of the reanalysis background); they are listed in `docs/TRUE_CLAIMS.md` section 3. `README.md` "Withdrawn claims" lists six, adding the +27% over persistence (best of 30 epochs chosen on the reported set) and the 12 km/day iceberg uncertainty growth.

---

## 2. Component map

| Location | What lives there |
|---|---|
| `dakshin/` | The core package. Satellite-data quality control (`ice_quality.py`), grid and regridding (`grid.py`), feature construction and scoring metrics (`features.py`), checkpoint loading (`model_io.py`), the real-data world for the router (`real_world.py`), iceberg forecasting (`berg_forecast.py`), AIS decoding (`ais_feed.py`), decision objects and gates (`decision.py`, `gates.py`, `workflow.py`), POLARIS band calculation (`polaris.py`), protected areas, coastline, and the September-prototype routing experiments that run on PolarRoute (`make_route_figure.py`, `ice_meshes.py`, `route_regret.py`, `alternatives.py`, `destination_window.py`). |
| `dakshin/readers/` | `nemo.py`: reader for native NEMO output (grid_T/U/V and ice files), mapping classic and CMIP-style variable names to one set of fields on curvilinear `nav_lon`/`nav_lat`. Never run on real NEMO output (its own docstring says so). |
| `dakshin/sim/` | A deterministic, seeded, synthetic Southern Ocean world (`world.py`, `fields.py`, `ice.py`, `bergs.py`, `noise.py`) used by the bridge console demo, plus the `Router` and `VesselModel` (`router.py`) that are also used on real data, plus real-data helpers (`bathymetry.py`, `geo_mask.py`). See section 8. |
| `dakshin/demo/` | FastAPI app and static front end. Serves the real, already computed artifacts under `dakshin/figures/` and the bridge console. The console declares its environment as synthetic (`dakshin/demo/test_bridge_ui.py` asserts the page contains "SYNTHETIC ENVIRONMENT"). |
| `dakshin/kaggle/` | `make_notebook.py` generates `isih_train.ipynb`, the self-contained Kaggle training notebook, by embedding `unet.py`, `grid.py` and `features.py` from the repository so the two cannot drift. `README.md` and `kernel-metadata.json` (commit `779cf83`) record the batch-run recipe: the credentials-cell swap, the push command and the failure modes already hit. |
| `dakshin/figures/` | Committed result files: the JSONs quoted in this document plus figures. |
| `dakshin/data/` | Gitignored. Holds the 1,096 daily NSIDC G02202 v6 files (2018-01-01 to 2020-12-31) used for training truth and for the QA audit. |
| `models/sic_correction/` | `unet.py` and `checkpoints/`: four trained prototype checkpoints `isih_prototype_lead{1,3,5,7}.pt` (7,763,017 bytes each), `SHA256SUMS`, the training run's skill table `isih_skill_by_lead.csv`, and two training-run figures (`isih_skill_curve.png`, `demo_comparison.png`). All committed; also published as release `model-v0.1` (4 `.pt` plus `SHA256SUMS`, published 2026-11-21 23:16 UTC, read here with `gh release view model-v0.1 --repo jiteeshghodke456-del/dakshin`). `sha256sum -c SHA256SUMS` passes on all four (measured here). |
| `models/iceberg/` | `drift.py` (WDE17), `melt.py` (three melt terms), `catalogue.py` (USNIC loader and archive fetcher), `regime_report.py` and its JSON (which drift regime the real catalogue sits in). |
| `scripts/` | Harvesters, back-fills, and the experiment scripts that write `dakshin/figures/*.json`. |
| `data/` | Harvested archives: `cmems_forecast_archive/` (committed), `cmems_cur_analysis/` (committed), `ecmwf_wind/` (two files committed, the 00z and 12z runs of 2026-11-21), `icebergs/` (committed), `bathymetry/` (corridor subset committed), `nsidc_nrt/` (committed since `a6fdc83`, 89 daily files plus `MANIFEST.sha256`, because the server window of about three months starts dropping the oldest days from 24 November (`a6fdc83`) and they cannot then be re-fetched). |
| `.github/workflows/cmems-harvest.yml` | The only workflow file and the only scheduled job. Since `a274a64` it also runs the ECMWF wind harvest on every slot and the weekly USNIC list on Fridays (both `continue-on-error`), and commits `data/ecmwf_wind` and `data/icebergs/archive` with the CMEMS archive. |
| `docs/` | Design record. `ML_ARCHITECTURE.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `TRUE_CLAIMS.md`, `PROTOTYPE_RESULTS.md`, `RESOLUTION_STUDY.md`, `CURRENT_STATE.md`, `backlog.md`. `docs/study/` is this study pack. |

Test suites sit beside the code (`dakshin/test_*.py`, `dakshin/sim/test_sim.py`, `dakshin/demo/test_*.py`, `dakshin/readers/test_nemo.py`, `models/iceberg/test_*.py`). Measured here (2026-11-22, `/home/agent/.venvs/sih-work/bin/python -m pytest -q` from the repository root, tree at `0cda289`): 209 passed, 2 skipped, 54 s (a second run: 48 s); at `779cf83` with only documentation edits uncommitted, the same 209 passed, 2 skipped in 27 s. The two skips are `dakshin/demo/test_bridge_ui.py:41` (playwright not installed) and `dakshin/test_protected_areas.py:32` (Antarctic Treaty shapefile absent, fetch with `dakshin/download_protected_areas.py`); the checkpoint-dependent tests in `dakshin/test_model_io.py` now run. The first version of this document measured 195 passed, 7 skipped on a mid-edit working tree; re-run before quoting a count.

A top-level `requirements.txt` now exists (commit `df7f39e`): unpinned names, Python 3.12 stated as verified, `torch` noted as CPU-sufficient for inference (numpy, scipy, pandas, xarray, netCDF4, h5netcdf, h5py, pyproj, torch, matplotlib, fastapi, uvicorn, pydantic, httpx, pyshp, pytest, copernicusmarine, ecmwf-opendata, cfgrib, pyais). There is still no `pyproject.toml`; `dakshin/demo/requirements.txt` remains the only list with pinned versions (`ATTRIBUTION.md` lists the dependency licences).

---

## 3. File-by-file tables

Writers/readers are given as paths. "lib" means imported by others and does no I/O of its own.

### 3.1 `dakshin/`

| File | What it does | Key functions | Reads / writes |
|---|---|---|---|
| `ice_quality.py` | QA for NSIDC CDR: sets land-spillover and no-input cells to NaN, reports the QA bit breakdown, detects a "hard zero next to heavy ice" without needing flags | `load_sic`, `load_stdev`, `qa_breakdown`, `hard_zero_next_to_ice`; QA bit constants | reads CDR NetCDF (`cdr_seaice_conc`, `cdr_seaice_conc_qa_flag`, `cdr_seaice_conc_stdev`); used by hindcast, route meshes, audit |
| `grid.py` | NSIDC EPSG:3412 geometry and the regridder from a lat/lon source (1-D axes or 2-D curvilinear) onto the NSIDC grid by mean of source points per target cell | `nsidc_lonlat`, `GlorysToNsidcRegridder` (`__call__`, `coverage`) | lib; used by the Kaggle notebook, hindcast, NEMO path |
| `features.py` | Builds the 12 input channels for training (`build_channels`) and for the operational hindcast (`build_channels_operational`); RMSE; IIEE; the baseline suite | `build_channels`, `build_channels_operational`, `iiee_km2`, `rmse`, `evaluate_baselines` | lib |
| `model_io.py` | Loads a lead's checkpoint after a SHA-256 check against `models/sic_correction/checkpoints/SHA256SUMS`; refuses unverified weights | `checkpoint_path`, `verify_checksum`, `load_checkpoint`; config `in_channels=12, base_filters=32, depth=3` | reads `models/sic_correction/checkpoints/isih_prototype_lead{1,3,5,7}.pt` (present; the two tests in `dakshin/test_model_io.py` run) |
| `real_world.py` | Real-data counterpart of the synthetic `World` with the same `sample(lat, lon, t)` contract; one archived forecast cycle supplies ice, waves, wind; also returns real seabed depth as `depth_m` (since `e724417`) so the chart gate is not UNKNOWN on real data | `RealWorld.sample` | reads `data/cmems_forecast_archive/cmems_siconc_<cycle>.nc`, `cmems_wav_<cycle>.nc`, `data/ecmwf_wind/ecmwf_wind_<cycle>_00z.nc`, `data/bathymetry/ibcso_v2_corridor_0p05.nc` |
| `berg_forecast.py` | Daily-current field object and RK2 berg integrator with hourly steps; stops a berg at a NaN current and marks it "grounded or unknown". v2 (commit `a274a64`): with a `BathymetryGrid` argument, a berg whose assumed keel (`ASSUMED_DRAUGHT_M` = 0.83 x 250 m = 207.5 m) reaches the IBCSO/GEBCO seabed is held as grounded at its start or where the track first touches such a cell; without it the behaviour is the original v1 | `CurrentField` (`from_files`, `sample`), `BathymetryGrid`, `Track`, `forecast_track`, `great_circle_km` | reads CMEMS `uo`/`vo` files and `data/bathymetry/ibcso_v2_corridor_0p05.nc`; used by `scripts/berg_hindcast.py`, `berg_resolution.py`, `berg_melt.py`, `berg_tracks.py` |
| `ais_feed.py` | NMEA 0183 AIS decoder (pyais) from UDP or file; latest position per MMSI; sentinels (lat 91, lon 181, 102.3 kn, 360 deg) rejected; fragment buffer bounded | `AISFeed.feed_sentence`, `feed_file`, `listen_udp` | no persistent I/O; feeds `traffic_gate` |
| `decision.py` | Data model of the decision layer: gate states, route health, evidence, decision, approval | `GateState`, `Health`, `GateResult`, `health_from_gates`, `Decision`, `gate_digest` | lib |
| `gates.py` | The nine gate evaluators and `evaluate_all` | `capability_gate`, `chart_gate`, `ice_gate`, `weather_gate`, `traffic_gate`, `logistics_gate`, `communications_gate`, `contingency_gate`, `execution_gate`, `evaluate_all`, `coverage_summary` | lib; called by `dakshin/demo/decision_service.py`, `scripts/real_route_run.py` |
| `workflow.py` | The passage workflow (mission, route plan, review, approve, re-plan) as a state machine | `Workflow`, `Mission`, `Voyage`, `Stage` | lib |
| `polaris.py` | IMO POLARIS (MSC.1/Circ.1519, Table 1.3) risk index computed as a band across candidate ice-class rows, never as one number | `rio_exact`, `rio_single_stage`, `band`, `along`, `tier`, `speed_limit_kn` | lib |
| `protected_areas.py`, `download_protected_areas.py` | ASPA (permit required) versus ASMA (management plan) treated as different constraint types; Treaty Secretariat shapefile (EPSG:3031) to a small committed extract | `load_areas`, `station_context`, `build_extract` | writes `dakshin/figures/protected_areas.json` |
| `coastline.py` | Natural Earth coastline simplified to a committed extract so the running app needs no GIS stack | `build`, `rdp`, `clip_polygon` | writes `dakshin/figures/coastline.json` |
| `download_nsidc.py` | Fetches NSIDC G02202 v6 south daily files for a year range, 6 workers by default | `list_year_files`, `download_one` | writes `dakshin/data/nsidc_sic/` (gitignored) |
| `build_dataset.py` | Builds per-year `.npz` of paired (GLORYS12 background, NSIDC truth, mask, dates); not what the Kaggle notebook uses (the notebook builds the pairs in memory) | `build_year`, `fetch_glorys_year` | writes `.npz` per year |
| `audit_ice_quality.py` | Audits all 1,096 CDR days for spillover, no-input and hard-zero cells, and for the 17 x 17 cell box around Bharati and Maitri | `station_windows` | writes `dakshin/figures/ice_quality_audit.json` |
| `ice_meshes.py` | One cached PolarRoute vessel-performance mesh per day; defines the `GOLOVNIN` config dict | `vessel_mesh_for`, `CellLookup` | needs PolarRoute env; caches under `dakshin/data/vessel_meshes/` |
| `make_route_figure.py`, `plot_route.py` | One PolarRoute route (Cape Town to Bharati, 2019-12-01) and its figure | `nsidc_to_dataframe`, `build_mesh`, `route` | write `dakshin/figures/mesh.json`, `routes.json`, `waypoints.csv`, `sic_points.csv`, `route_map.png` |
| `route_regret.py` | Static plan versus daily re-plan, replayed through observed ice | `plan_route`, `replay`, `sail_daily_replan` | writes `dakshin/figures/route_regret.json`; PolarRoute env |
| `alternatives.py` | Alternative corridors and a two-vessel comparison | `corridors`, `two_vessel_comparison` | writes `alternatives.json`, `vessel_comparison.json` |
| `destination_window.py` | Is the destination cell passable on each day | `main` | writes `dakshin/figures/destination_window.json` |
| `mlflow_backfill.py` | Republishes the numbers in `docs/PROTOTYPE_RESULTS.md` as MLflow runs (it computes nothing) | `backfill` | local MLflow store (gitignored) |
| `test_*.py` | Unit and behavioural tests | | read real files; docstring in `dakshin/demo/test_data.py`: "No fixtures, no synthetic data" |

### 3.2 `dakshin/sim/`, `dakshin/readers/`, `dakshin/demo/`

| File | What it does | Notes |
|---|---|---|
| `sim/router.py` | `VesselModel` (speed and per-distance fuel derating) and `Router` (Dijkstra, 8-connected, arrival-time costs, 6-hour condition slots, land and depth blocking, one-lattice-cell arrival rule since `478ecd2`, `_goal_nodes`) | The only router that has a time dimension; used on real data via `RealWorld`. The lattice is 0.55 x 0.9 degrees laid over 1/12 degree fields: it is not a 1/12 degree router |
| `sim/world.py` | Assembles `World`: pressure, wind, ice, SST, waves, visibility, bergs, traffic, warnings, from one seed (default 20261207) | Synthetic state; real physics relationships (wind as pressure gradient, waves damped by ice) |
| `sim/fields.py`, `ice.py`, `noise.py`, `hashing.py` | Seeded Fourier noise, atmosphere, ocean, ice-edge model | "Real physics, synthetic initial conditions" (`sim/fields.py` docstring) |
| `sim/bergs.py` | Berg population advected with the tested WDE17 function | Synthetic positions; both catalogue-sized and smaller bergs |
| `sim/bathymetry.py` | Real IBCSO v2 / GEBCO_2020 depth lookup; each 0.05 degree box holds the shallowest source value within it and its eight neighbours (about 5 km buffer, commit `24317da`); NaN outside coverage | Reads `data/bathymetry/ibcso_v2_corridor_0p05.nc` |
| `sim/geo_mask.py` | One land test (even-odd ray casting over the committed coastline rings) | Reads `dakshin/figures/coastline.json` |
| `readers/nemo.py` | `NemoReader(*paths)`: `.field(name)` for `ice_concentration`, `u_current`, `v_current`, `sst`, `ice_thickness`; `.lon`, `.lat` 2-D; `.available()` | Alias lists for classic (`vozocrtx`, `vomecrty`, `votemper`, `ileadfra`, `soicecov`) and CMIP-style (`uo`, `vo`, `thetao`, `tos`, `siconc`) names |
| `demo/app.py` | FastAPI: `/api/summary`, `/api/route`, `/api/cells`, `/api/day/{d}`, `/api/decision`, `/api/workflow`, `/api/alternatives`, `/api/model` (404 when the checkpoints are absent), `/bridge`, others | Startup refuses to run if any day in the window lacks a satellite file |
| `demo/data.py`, `decision_service.py`, `voyage.py`, `workflow_service.py`, `bridge_api.py` | Loaders for real artifacts; builds a `Decision` from files; voyage state; bridge console API. `data.model_card()` (commit `0c3b9ef`) assembles the model card for `/api/model` from published artifacts only: `SHA256SUMS` (12-character hashes, sizes), the training run's `isih_skill_by_lead.csv`, `release: model-v0.1`, and `corrected_all.json["verification"]`; nothing is recomputed. The bridge console's "AI correction" panel (`dakshin/demo/static/bridge.js`) renders it with provenance kind `real` (`provenance.js`); `test_model_card_is_real_artifacts` in `dakshin/demo/test_app.py` pins it | `decision_service.build` calls `evaluate_all` with `live_sensors=False` and no weather, traffic or wave inputs, so in the demo those gates are UNKNOWN. Real weather is evaluated only in `scripts/real_route_run.py` |

### 3.3 `models/`

| File | What it does |
|---|---|
| `sic_correction/unet.py` | `SICCorrectionUNet(in_channels, base_filters, depth)`: 3-level U-Net with 2 x (3x3 conv, batch-norm, ReLU) blocks, max-pool down, transposed-conv up, skip concatenation, 1x1 head initialised to zero; replicate-pads input to a multiple of 2^depth and crops back; `apply_correction` = clip(base + delta, 0, 1); `count_parameters` |
| `iceberg/drift.py` | WDE17: `GAMMA`, `coriolis_abs`, `harmonic_length`, `lambda_param`, `alpha`, `beta` (both in cancellation-free form), `iceberg_velocity`, `deflection_angle_deg`, `relative_wind_forcing` (R), `critical_length_m` |
| `iceberg/melt.py` | `basal_melt_m_per_day`, `buoyant_convection_m_per_day`, `wave_erosion_m_per_day`, `freshwater_m3_per_day` |
| `iceberg/catalogue.py` | `load_usnic` (SI units, BOM-safe, swaps axes if needed, rejects non-southern latitudes), `fetch_usnic`, `fetch_usnic_archive`, `summarise` |
| `iceberg/regime_report.py` | R across a declared envelope of winds (5, 10, 20, 30 m/s) and currents (0.05, 0.1, 0.3 m/s) for the real catalogue; writes `models/iceberg/regime_report.json` |

### 3.4 `scripts/`

| Script | Purpose | Writes |
|---|---|---|
| `harvest_cmems.sh` | Daily CMEMS cycle harvest (ice, currents, waves, and since `a274a64` surface temperature), stale-cycle rule, compression. Currents, waves and SST are fetched after the ice cycle is accepted, never fail the harvest, and exist only for cycles from 2026-11-21 on | `data/cmems_forecast_archive/cmems_{siconc,cur,wav,sst}_<cycle>.nc`, `data/cmems_harvest.log` |
| `compress_netcdf.py`, `reduce_wav_daily.py` | int16 packing / deflate (the pack table now also covers `uo`, `vo` at +-3 m/s, `VHM0_dmax` at 25 m and `thetao` at 50 degC, commit `2ffa6b2`); 3-hourly waves to daily max | in place |
| `harvest_ecmwf_wind.py` | Latest 00z/12z IFS 10 m wind, steps 0 to 240 h every 6 h, cropped to the box | `data/ecmwf_wind/ecmwf_wind_<date>_<hh>z.nc` |
| `harvest_usnic.sh` | Weekly USNIC CSV, named by the newest "Last Update" | `data/icebergs/archive/AntarcticIcebergs_<yyyymmdd>.csv` |
| `download_nsidc_nrt.py` | NSIDC G10016 v4 NRT daily files and a SHA-256 manifest | `data/nsidc_nrt/` (committed since `a6fdc83`; the script's own docstring still says "gitignored") |
| `backfill_cur_analysis.py` | One-off daily analysis currents backfill | `data/cmems_cur_analysis/cmems_cur_analysis_<date>.nc` |
| `subset_bathymetry.py` | IBCSO v2 south of 50 S plus GEBCO_2020 north of it, box-max onto a 0.05 degree grid | `data/bathymetry/ibcso_v2_corridor_0p05.nc` |
| `score_cmems_archive.py` | Persistence versus CMEMS using the model's own later day-0 as truth; flatters CMEMS, a baseline not a skill claim | stdout |
| `realforecast_hindcast.py` | The honest test (section 5c); with the model unless `--no-model` | `dakshin/figures/realforecast_hindcast.json` |
| `resolution_study.py` | F1, coarsening study; with the model unless `--no-model` | `resolution_study.json`, `resolution_study.png` |
| `corrected_forecast.py` | Applies the four checkpoints to archived cycles with a full 7-day satellite history and asks the approach question on the 25 km grid (`reachable`: is any cell within 50 km of Bharati 4-connected, through cells at or under 0.80, to cells 400 km or more away; `scipy.ndimage.label`, depth blocking not applied). Default: the newest such cycle (raw and corrected fields per lead). `--all`: every such cycle, with each lead's decision verified against the satellite field on the target date (section 5c) | `dakshin/figures/corrected_forecast.{npz,json}` (single cycle), `corrected_all.{npz,json}` (`--all`; fields packed as uint8 sic x 200, 255 = no data, keys `c<YYYYMMDD>_l<lead>`) |
| `stale_history_eval.py` | Scores the model with satellite history ending at day-1 (`stale`) against day-0 (`fresh`), same cycles, mask and scoring as the hindcast (section 5c) | `dakshin/figures/stale_history_eval.json` |
| `berg_hindcast.py`, `berg_resolution.py`, `berg_melt.py`, `berg_tracks.py` | Berg validation (v1 and, beside it, v2 grounding-aware), F3 current coarsening, F4 melt estimate, per-berg 0 to 9 day forecast tracks for the site's chart | `berg_hindcast.json`, `berg_resolution.json`, `berg_melt.json`, `berg_tracks.json` |
| `real_route_run.py` | Router on `RealWorld` plus weather gate; reports where the track ends relative to the station (`route_ends_km_from_station`) and a `lattice_note`; `CorrectedIceWorld` adds the U-Net delta (corrected minus raw, nearest 25 km cell, nearest lead) to the router's SIC; `corrected_ice_check` compares raw and corrected routes when a cycle has both a correction and an archived wave file (section 5e) | `real_route.json` |
| `pull_checkpoints.sh` | Pull the four checkpoints from the Kaggle kernel `jiteeshghodke/notebookd39fdf7959`, write `SHA256SUMS`, run `dakshin/test_model_io.py` and both scorers; its closing message gives the `gh release create model-v0.1` command. The checkpoints were committed in `5612621` | `models/sic_correction/checkpoints/` |
| `verify_claims.py` | Checks 29 quantitative claims against source JSON | stdout |
| `gen_*_drawio.py` | Diagram generators | `docs/*.drawio` |

---

## 4. The grid story

### 4.1 The truth grid

The NSIDC CDR grid is a 25 km south polar stereographic grid, EPSG:3412 (Hughes 1980 ellipsoid, `+proj=stere +lat_0=-90 +lat_ts=-70`; `dakshin/grid.py`). Measured here from a real file (`sic_pss25_20191201_F17_v06r00.nc`): `y` has 332 values starting at 4,337,500 m and decreasing in steps of 25,000 m, `x` has 316 values starting at -3,937,500 m and increasing in steps of 25,000 m, 104,912 cells in all, latitude range -89.84 to -39.36 degrees. Row 0 is therefore the northernmost row. The dimensions 332 x 316 closed an assumption in `docs/ML_ARCHITECTURE.md` section 1.3 (the backlog line that said "asserted from memory" has since been removed from `docs/backlog.md`).

A cell is 625 km2 (25 km x 25 km). `features.iiee_km2` uses that constant for every cell. In a polar stereographic projection with a standard parallel at 70 S the true area of a cell varies with latitude, so the constant is an approximation; the repository does not quantify the error, and neither does this document.

### 4.2 Why the truth is never resampled

The rule is in `dakshin/grid.py` and ADR-024: the model field is regridded onto the truth grid, never the reverse. Resampling the field you score against creates ice-edge artefacts that cannot be told from model error, and IIEE is measured on that field.

### 4.3 What the regridder actually does

The `grid.py` docstring used to speak of area-averaging; since `1a9ff0b` it describes the implementation as an unweighted mean of source cell centres, "a close approximation of the area average at this 9-vs-25 km ratio". The implementation is this. For every source point (a GLO12 cell centre) it transforms lon/lat to EPSG:3412, converts to a target row and column by rounding (`np.rint((x - x0) / dx)`), and keeps those inside the grid. At call time it sums the finite source values per target cell with `np.bincount` and divides by the finite count. Target cells that receive no source point are NaN, not zero (an empty cell is unknown, not ice-free). So it is an unweighted mean of source cell centres falling in each target cell. It is not a conservative remap that weights by overlap area; ADR-024 (`docs/DECISIONS.md` line 281) and `docs/ML_ARCHITECTURE.md` (line 699) still describe the regridder in words as "conservative area-weighted". For a source about 9 km wide and a target 25 km wide the difference is small away from edges; it has not been measured.

Why a mean rather than bilinear: the source is finer than the target, so bilinear sampling would discard most of the source cells and would not preserve ice area (`grid.py` docstring).

Measured here with the 2026-11-19 cycle (`GlorysToNsidcRegridder` on the 277 x 961 GLO12 box): 14.7% of the NSIDC grid is covered by the harvest box (`coverage()` returned 0.14686); source points per covered target cell: minimum 1, median 16, maximum 41; one regridded field has 11,250 finite cells with values 0.0 to 0.9964. Everything outside the box is NaN and is zero-filled before the network (section 5c).

### 4.4 The source grids

GLO12 harvest: regular lat/lon at 1/12 degree, 277 latitudes (78 S to 55 S) by 961 longitudes (0 to 80 E), 10 daily steps per cycle (measured here with `xarray` on `data/cmems_forecast_archive/cmems_siconc_2026-11-19.nc`). Files carry four variables: `siconc`, `sithick`, `usi`, `vsi`.

Training background (GLORYS12 reanalysis) was subset to -5 to 85 E, -80 to -48 S in the notebook (`dakshin/kaggle/make_notebook.py`), a larger box than the scoring box (0 to 80 E, 55 to 78 S).

Router lattice: regular lat/lon, default spacing 0.55 degrees latitude by 0.9 degrees longitude (`dakshin/sim/router.py`), laid over the 1/12 degree fields. It is not a 1/12 degree router, and its nodes are about 60 km apart (`docs/WEAKNESS_ANALYSIS.md` section 11), so it cannot resolve the last ~50 km to a station (`dakshin/figures/real_route.json["lattice_note"]`). Bathymetry: 0.05 degree boxes, lon 0 to 90 E, lat 78 S to 30 S, IBCSO v2 ice-surface grid south of 50 S and GEBCO_2020 north of it (`dakshin/sim/bathymetry.py`, `scripts/subset_bathymetry.py`). The ice-surface grid is used rather than the bed grid so that an ice shelf reads as positive elevation and blocks the router like land; the bed grid would show hundreds of metres of "water" under the shelf.

### 4.5 How curvilinear NEMO coordinates plug in

`GlorysToNsidcRegridder.__init__` checks `source_lat.ndim`. If 2-D (as for NEMO's `nav_lon` and `nav_lat`) the arrays are used as given; if 1-D they are meshed. So `NemoReader.lon`/`.lat` pass straight in:

```python
from dakshin.readers.nemo import NemoReader
from dakshin.grid import GlorysToNsidcRegridder
r = NemoReader("grid_T.nc", "icemod.nc")            # NOT run on real NEMO output
rg = GlorysToNsidcRegridder(nsidc_template_ds, r.lat, r.lon)
sic_on_nsidc = rg(r.field("ice_concentration"))      # (332, 316), NaN outside the domain
```

Limits to state before a NEMO specialist does. `NemoReader` reads only the first time record and the top level of each variable. It does no C-grid destaggering: `uo` lives on U-points and `vo` on V-points in NEMO and is returned as stored. It does no rotation of grid-relative velocity components to east/north, which matters on a rotated or tripolar grid. Fill values above 1e19 in magnitude become NaN; zeros are kept as zeros. Its tests (`dakshin/readers/test_nemo.py`, 4 tests) use synthetic files in the documented layout, because no small open sample file ships with NEMO. The name ANHA appears in the repository only as an example of a regional NEMO configuration that could be run at several resolutions (`docs/RESOLUTION_STUDY.md`, `scripts/resolution_study.py`, `dakshin/readers/nemo.py`); the repository gives no domain for it. If ANHA is a Northern Hemisphere (Arctic and North Atlantic) domain, as the name suggests, then only the reader and the metrics transfer to it; the south-polar regridder and the 0 to 80 E corridor do not. Verify with the professor rather than assume.

---

## 5. The data pipelines

### 5a. Daily harvest

Scheduled job: `.github/workflows/cmems-harvest.yml`, cron `23 12 * * *`, `23 17 * * *` and `23 21 * * *` UTC, plus manual dispatch with an optional `cycle_date`. It installs `copernicusmarine`, `xarray`, `netCDF4`, logs in (three attempts), runs `scripts/harvest_cmems.sh`, verifies the file exists and exceeds 1,000,000 bytes, then commits `data/cmems_forecast_archive`, `data/cmems_harvest.log`, `data/ecmwf_wind` and `data/icebergs/archive` with up to three push attempts, rebasing in between. Between the harvest and the verify step two `continue-on-error` steps run: `pip install ecmwf-opendata cfgrib xarray netCDF4 numpy` then `python scripts/harvest_ecmwf_wind.py --out data/ecmwf_wind`, and, only when `date -u +%u` is 5 (Friday), `bash scripts/harvest_usnic.sh`. The bot's commit `4a4e103` (2026-11-21 22:14 UTC) is the first to carry a wind file produced by the workflow (`ecmwf_wind_2026-11-21_12z.nc`); no Friday has passed since the USNIC step was added, so that step has not yet produced a file in CI (the newest committed issue, 2026-11-20, came from `ca53946`).

Why those times (workflow comment): GitHub starts scheduled runs late (observed 10:38, 11:05, 10:40 UTC for a 06:00 cron), never schedule on the hour, run more than once because the already-have guard makes repeats free, and keep every slot after 12:00 UTC because the CMEMS product manual guarantees the daily bulletin only by 12:00 UTC (CMEMS-GLO-PUM-001-024, issue 2.4, as cited in the workflow). The script names its output from the wall clock, so a run before the bulletin lands would store the previous day's forecast under today's filename and the already-have guard would then block the correct capture. A missed day cannot be recovered: CMEMS overwrites each bulletin with the next.

What the script pulls, for one cycle date D (box lon 0 to 80, lat -78 to -55, from D 00:00 to D+10 days):

| Product | Dataset ID | Variables | Output file | Steps |
|---|---|---|---|---|
| Ice | `cmems_mod_glo_phy_anfc_0.083deg_P1D-m` (GLOBAL_ANALYSISFORECAST_PHY_001_024) | `siconc`, `sithick`, `usi`, `vsi` | `cmems_siconc_<D>.nc` | 10 daily |
| Currents | `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m` | `uo`, `vo`, depth 0 to 1 m (top level, 0.494 m) | `cmems_cur_<D>.nc` | 10 daily |
| Waves | `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i` (GLOBAL_ANALYSISFORECAST_WAV_001_027) | `VHM0`, `VMDR`, reduced to daily maximum `VHM0_dmax` (and `VMDR` at the step of the maximum) by `scripts/reduce_wav_daily.py` | `cmems_wav_<D>.nc` | 10 daily |

The stale-cycle rule. A real cycle has exactly 10 daily time steps, the cycle date plus nine forecast days (`EXPECTED_DAYS=10`). If the run is clock-dated (no manual `CYCLE_DATE`) and the hour is before 12 UTC, the cycle is filed under yesterday. After the download the script counts time steps; a file that is not exactly 10 steps is deleted, the status is reported as `not_published`, and a later run retries. Currents and waves are fetched only after the ice cycle is accepted, with the same length check, and their failures never fail the harvest (the runner is discarded after the job, so a late red would lose the already saved ice file). A manually typed date is treated as a deliberate back-fill and is not checked, with the caveat in the script that the analysis for a past date is served but the forecast as issued is gone.

Why `data/cmems_forecast_archive/KNOWN_STALE.md` exists. Found on 2026-11-18 by comparing every archived cycle with the one before. Four files hold the previous day's forecast with its first day cut off (9 steps, `siconc` identical on all 9 shared dates, maximum difference 0.0000): 2026-09-20, 2026-10-11, 2026-11-10, 2026-11-17. Two came from runs that started after midnight UTC (the clock named the file for the next day), two from runs after 12:00 UTC when Copernicus had not yet published (both Sundays). The real forecasts for those four dates were never saved and cannot be recovered. The rule was added after the fact. Consequence for scoring: those four cycles must not be used (their "day 0" is a day-old forecast), and every scorer applies the same 10-step test (`scripts/realforecast_hindcast.py::clean_cycles`, `scripts/score_cmems_archive.py`). Measured here: 83 `cmems_siconc_*.nc` files, 79 clean, 4 stale.

Compression. `copernicusmarine subset` writes uncompressed NetCDF, 42.62 MB per cycle (`scripts/compress_netcdf.py`). The harvest packs `siconc`, `sithick`, `usi`, `vsi` as int16 with deflate and shuffle: the log line for 2026-11-21 reads "42.62 MB -> 4.44 MB (9.6x smaller, int16 packed)" (`data/cmems_harvest.log`); the script's stated maximum error is 1.7e-5 for `siconc` and 3.3e-4 m for `sithick`. For files harvested after commit `2ffa6b2`, `uo`/`vo` (+-3 m/s), `VHM0_dmax` (25 m) and `thetao` (50 degC) are int16-packed as well (the pack table in `scripts/compress_netcdf.py`; the commit message quotes daily currents 10 MB to 3.9 MB). The committed 2026-11-21 currents, waves and SST files predate that change and are float32: 10,032,298, 2,110,150 and 10,675,481 bytes (`git cat-file -s HEAD:<path>`, measured here), and the 82 analysis-current files are float32 at about 1 MB each.

Other feeds, and what the repository does and does not schedule.

| Feed | Script | Cadence needed | Scheduled in the repository |
|---|---|---|---|
| ECMWF IFS 10 m wind (CC BY 4.0) | `scripts/harvest_ecmwf_wind.py` | open data keeps only the last ~12 runs (2 to 3 days), so daily | Yes since `a274a64`: a `continue-on-error` step of `cmems-harvest.yml` on all three slots. Two wind files are committed (`ecmwf_wind_2026-11-21_00z.nc` committed by hand in `c0055ce`, `_12z.nc` by the bot). Only the 00z file is read by `RealWorld`; `forecast_track` still sets wind to zero |
| USNIC Antarctic icebergs | `scripts/harvest_usnic.sh`, or `models/iceberg/catalogue.py <start> <end>` to back-fill from the archive back to 2014-11-07 | weekly | Yes since `a274a64`: Friday step of `cmems-harvest.yml`, not yet exercised (above). 14 weekly files are committed (2026-08-20 to 2026-11-20) |
| NSIDC NRT G10016 v4 | `scripts/download_nsidc_nrt.py` | the archive keeps about 3 months, so days roll off | No, still manual. 89 files committed since `a6fdc83` (2026-08-24 to 2026-11-20) with `data/nsidc_nrt/MANIFEST.sha256`; nothing after 2026-11-20 has been fetched into the repository |
| CMEMS surface SST for berg melt | `harvest_sst` in `scripts/harvest_cmems.sh` (dataset `cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m`, `thetao`, depth 0 to 1 m), added in `a274a64` | daily | Yes, with the CMEMS cycle. One file exists, `data/cmems_forecast_archive/cmems_sst_2026-11-21.nc`, and `scripts/berg_melt.py` reads it. Its provenance is now documented; no earlier cycle has SST |
| Analysis currents (for the berg hindcast) | `scripts/backfill_cur_analysis.py` | one-off | 82 daily files committed (2026-08-31 onward) |

The currents, waves and SST harvest steps have run in `scripts/harvest_cmems.sh` since 2026-11-21; the 83 historical ice cycles (2026-08-31 onward) carry `siconc` only, and forecasts cannot be back-filled. So today exactly one cycle (2026-11-21) has currents, waves and SST in `data/cmems_forecast_archive/`, and `cmems_wav_2026-11-21.nc` is the only wave file. Consequences: `scripts/berg_melt.py`, `scripts/berg_tracks.py` and `scripts/real_route_run.py` are single-cycle results (2026-11-21); the corrected-ice router check cannot run until a cycle has both a correction (which needs a day-0 satellite file, so it trails the forecast by about a day) and a wave file (section 5e); the newest corrected cycle is 2026-11-20 (`dakshin/figures/corrected_forecast.json`) and has no wave file. `scripts/berg_tracks.py` and `scripts/corrected_forecast.py` are not scheduled anywhere; they need `torch` or the site rebuild and run by hand (`docs/backlog.md`, last lines).

### 5b. Training pipeline

Data and code: `dakshin/kaggle/isih_train.ipynb`, generated by `dakshin/kaggle/make_notebook.py` (batch-run recipe: `dakshin/kaggle/README.md`). File and checkpoint names keep the historical prefix `isih_`; do not rename them (`dakshin/model_io.py`, `scripts/pull_checkpoints.sh`).

Truth. NSIDC CDR G02202 v6 south daily files, 25 km, F17 SSMIS era, years 2019 and 2020 (`YEARS = [2019, 2020]` in the notebook), downloaded by 8 threads from `https://noaadata.apps.nsidc.org/NOAA/G02202_V6/south/daily`. No authentication. Values outside 0 to 1 become NaN.

Background. GLORYS12 reanalysis `cmems_mod_glo_phy_my_0.083deg_P1D-m`, variable `siconc`, box -5 to 85 E, -80 to -48 S, regridded onto the NSIDC grid by `GlorysToNsidcRegridder` (section 4.3). Dates present in both are intersected. NaN is filled with 0 for the network; a validity mask `isfinite(background) & isfinite(truth)` marks where the loss counts.

An alignment sanity check runs before anything is trained: correlation between background and truth must exceed 0.5 or the notebook asserts.

The 12 channels (`dakshin/features.py::build_channels`), for forecast origin `t` and lead `L`:

| Channel | Content |
|---|---|
| 0 | background (GLORYS12) valid at the target date `t + L` |
| 1 to 7 | observed SIC at `t`, `t-1`, ..., `t-6` (channel `k` holds `observed[t - k + 1]`) |
| 8 | innovation: `background[t] - observed[t]` |
| 9, 10 | sin and cos of 2 pi doy/365.25 of the target date |
| 11 | validity mask at `t` |

The header comment of `features.py` used to say channels 1 to 7 are `t-1 ... t-7` and the innovation uses `observed(t-1)`, which the code did not do. It was corrected in `1a9ff0b` to "observed SIC at t, t-1, ... t-6 (newest first)" and "innovation: background(t) - observed(t)", and now agrees with the code and with `build_channels_operational` ("index 0 = day t, index 6 = day t-6").

A sample is built only where the 7-day look-back is genuinely consecutive and the gap to the target is exactly `L` days; a hole in the record is never treated as history.

Split and why. Samples are ordered by target date and cut 70% / 15% / 15% by index: train, validation (used only to choose the epoch), test (scored once). Time ordering is mandatory because sea ice barely changes overnight; a random split puts adjacent days on both sides and yields a spectacular, meaningless score (`docs/PROTOTYPE_RESULTS.md`). An earlier run reported +27% by selecting the best of 30 epochs on the set it then reported; that number was inflated and is not used (same file). There is no embargo between the three blocks, so input windows and targets at the boundaries share days across a cut; nothing in the repository measures how much this matters.

Why seed 0. `torch.manual_seed(0)` is called before the model is built at every lead, "same init at every lead, so leads are comparable". It fixes initialisation; it does not make the run bit-reproducible (GPU non-determinism, mixed precision).

Why a residual. The output of the network is `delta`, and the prediction is `clip(background + delta, 0, 1)`. The final 1x1 convolution is zero-initialised (`unet.py`), so an untrained model reproduces the background exactly; the floor is the background's skill, not zero. Model: 3 levels, base filters 32, 12 input channels, 1,929,601 parameters (measured here with `count_parameters`; `docs/PROTOTYPE_RESULTS.md` quotes the same). The unet.py defaults (19 channels, 40 filters, 3,015,481 parameters) are the production design, not the prototype.

Optimisation: masked MSE on the corrected field, Adam at 1e-3, `ReduceLROnPlateau` (factor 0.5, patience 3), mixed precision on GPU, batch size 8, at most 60 epochs, early stop after 12 epochs without validation improvement, best-validation checkpoint kept. One model per lead in {1, 3, 5, 7}. Baselines are scored before training at each lead so the bar is fixed first: raw background, persistence (the newest observation, channel 1), background plus a constant offset, background plus a per-pixel mean bias map fitted on train.

Why same-day correction is not a task: measured over full-year 2020, persistence from yesterday scores RMSE 0.0359 for the same day, better than any correction of a background field (`features.py` docstring). The notebook therefore studies leads 1, 3, 5, 7 days.

Training-time results (test slice, last 15% of 2019 to 2020, melt season), from `docs/PROTOTYPE_RESULTS.md`; the training run's own table, `models/sic_correction/checkpoints/isih_skill_by_lead.csv` (committed with the checkpoints), carries the same values to four places (lead 1: 0.04646, 0.05703, 0.14611, 0.16300):

| Lead | Model | Persistence | background + pixel bias | Raw GLORYS12 |
|---|---|---|---|---|
| 1 d | 0.0465 | 0.0570 | 0.1461 | 0.1630 |
| 3 d | 0.0720 | 0.0958 | 0.1461 | 0.1630 |
| 5 d | 0.0938 | 0.1204 | 0.1468 | 0.1637 |
| 7 d | 0.0968 | 0.1395 | 0.1468 | 0.1637 |

Read these as an upper bound on forecast skill, not a measurement (section 5c). The original 2026-08-31 checkpoints were never in Kaggle's output store, and the saved notebook's training cell was typed as markdown so batch runs trained nothing (`docs/CURRENT_STATE.md`). The committed checkpoints are from the identical-recipe re-run that completed on 2026-11-21 (GPU version 8; version 7 had died on a pip numpy upgrade; `docs/CURRENT_STATE.md`, "Overnight run update"), and the skill table it wrote agrees with the 2026-08-31 table above to the four places printed there. Update 4 of `docs/CURRENT_STATE.md` records a further same-seed re-run (Kaggle kernel `dakshin-prototype-train-gpu2`): lead-1 held-out RMSE 0.04649 against the released 0.04646 (agreement to 3e-5), leads 3 to 7 spread by up to 0.012 between runs (GPU non-determinism), persistence beaten at every lead in every run. No committed JSON holds that second run's numbers; the figures are the ones in `docs/CURRENT_STATE.md`. The notebook generator gained two fixes on the way: numpy is pinned to the image's own build in the install cell (`d7b0d0f`), and the NSIDC download retries three times through `.part` files after a transient HTTP 500 killed a run (`0848d7e`).

The no-background ablation (zero channel 0, retrain at lead 3) exists as a notebook cell and as a stated next step; no result is recorded (`docs/PROTOTYPE_RESULTS.md`, "Not yet run").

### 5c. The real-forecast hindcast

`scripts/realforecast_hindcast.py`. The question: if the ship had used the real CMEMS forecast issued on day `t`, how do raw CMEMS, persistence and the U-Net score against the satellite on day `t + L`?

Procedure. For each clean cycle `t` and lead `L` in {1, 3, 5, 7}: forecast step `L` of the cycle, regridded to the NSIDC grid, is "raw CMEMS"; the NRT observation at `t` is persistence; truth is the QA-masked NRT observation at `t + L`. History needs the 7 days `t-6 ... t` to be present. Scoring uses cells inside the box 0 to 80 E, 55 to 78 S where truth and forecast are finite, pools squared error over all cycles (RMSE) and averages IIEE at the 15% threshold per cycle. Truth NaNs are zero-filled in the squared-error term and excluded by the mask. Run once; no tuning on this set.

What `build_channels_operational` changes relative to training:

| Item | Training (`build_channels`) | Operational (`build_channels_operational`) |
|---|---|---|
| Channel 0 | GLORYS12 reanalysis valid at `t + L` | CMEMS forecast issued at `t`, valid at `t + L` |
| Channel 8 | `background[t] - observed[t]` with reanalysis at `t` | day-0 field of the same forecast cycle minus `observed[t]` |
| Observations | not QA-masked in the notebook (spillover zeros sit in targets and history) | QA-masked by `ice_quality.load_sic` (suspect cells NaN, then zero-filled) |
| Truth sensor | F17 SSMIS (G02202 v6) | AMSR2 (G10016 v4 NRT, file tag `am2`, since 2025-01-01 per `scripts/download_nsidc_nrt.py`) |
| Region | -5 to 85 E, -80 to -48 S | 0 to 80 E, 55 to 78 S (14.7% of the grid; rest zero-filled) |
| Valid mask (channel 11) | from the paired training mask | `isfinite(analysis_t) & isfinite(obs_t)` |

Why this is the honest operational test. A forecast issued at `t` cannot contain information from after `t`; the function takes only things knowable on day `t` and the docstring says nothing after `t` can enter by construction. The reanalysis in training had assimilated observations near the target date, which a real forecast has not.

The leakage question and its answer. The sharpest question is whether training channel 0 leaked the target. `docs/PROTOTYPE_RESULTS.md` caveat 1 answers it in the affirmative in part, and withdraws an earlier defence. The withdrawn defence ("if GLORYS12 contained the answer its own RMSE would be near zero, not 0.163") does not follow, because 0.163 measures grid, algorithm and ice-model mismatch between a 1/12 degree model field and a 25 km passive-microwave product; it is a bias term. The positive evidence of leakage is the flat raw-GLORYS12 error across lead (0.1630 at 1 d, 0.1637 at 7 d, essentially no growth), which is what a field that has seen the target looks like, together with the fact that channel 0 is the reanalysis at `t + L` and channel 8 is the reanalysis at `t`, whose difference (the assimilated tendency) is a linear combination the first convolution can form. Therefore the training-time table is an upper bound on forecast skill. The test that settles the matter is the hindcast on real forecast cycles (this section), plus the not-yet-run ablation.

Results, `dakshin/figures/realforecast_hindcast.json` (generated 2026-11-21 23:13 UTC, with the model; its `model` field reads "re-run 2026-11-21 of the 2026-08-31 Kaggle training (identical code, seed and split; credentials cell only change)"). The first version of this document quoted the model-free file (n = 76 at lead 1, RMSE 0.10199 and 0.11977, IIEE 195,058 km2 for raw CMEMS); the file has been regenerated since, with the 2026-11-19 cycle scorable, and now holds:

| Lead | n cycles | RMSE U-Net | RMSE raw CMEMS | RMSE persistence | IIEE U-Net (km2) | IIEE raw CMEMS (km2) | IIEE persistence (km2) |
|---|---|---|---|---|---|---|---|
| 1 d | 77 | 0.0914 | 0.10219 | 0.11914 | 93,231 | 196,031 | 186,997 |
| 3 d | 75 | 0.08741 | 0.10479 | 0.14391 | 142,467 | 194,575 | 277,167 |
| 5 d | 74 | 0.0946 | 0.10981 | 0.15508 | 182,601 | 200,203 | 319,189 |
| 7 d | 72 | 0.10245 | 0.1153 | 0.16414 | 221,094 | 210,200 | 353,255 |

Reading it. The U-Net has the lowest RMSE at every lead (margin over raw CMEMS 0.011 at lead 1, 0.017 at lead 3, 0.015 at lead 5, 0.013 at lead 7, arithmetic on the table). It has the lowest IIEE at leads 1, 3 and 5; at lead 7 it is worse than raw CMEMS (221,094 against 210,200 km2) while still ahead of persistence, so the edge advantage decays with lead and RMSE alone would hide it: quote both. Lead 1 is the large effect (93,231 against 196,031 km2). By IIEE persistence beats raw CMEMS at lead 1 (186,997 against 196,031) and loses from lead 3, so "raw CMEMS beats persistence at all leads" (`docs/CURRENT_STATE.md`) is true for RMSE only. Persistence IIEE grows with lead, as it should; `docs/RESOLUTION_STUDY.md` now carries those values, but its raw-CMEMS rows still hold the earlier n = 76 numbers (for example 0.1020 and 195.1 at lead 1 against 0.10219 and 196,031 here). The run-to-run training spread recorded in `docs/CURRENT_STATE.md` (up to 0.012 at leads 3 to 7) is the same size as the RMSE margin over raw CMEMS; the hindcast uses one checkpoint per lead, no confidence interval or significance test exists, and the effective sample is one spring of strongly autocorrelated cycles (`README.md` section 1, `docs/WEAKNESS_ANALYSIS.md` section 11).

Resolution columns, `dakshin/figures/resolution_study.json`: the same forecasts block-averaged to about 1/4 degree and 1 degree, with the U-Net applied to each. Corrected IIEE at 1/12, 1/4 and 1 degree: 93,231, 93,287, 97,792 km2 at lead 1 and 221,094, 223,342, 246,580 km2 at lead 7. The correction does not restore resolution the background has lost (`docs/RESOLUTION_STUDY.md`, last section).

What the scoring cannot tell you, and the caveats carried in the JSON (`CAVEATS` in the script): the sensor change from F17 to AMSR2; corridor only; one spring season (72 to 77 cycles per lead, strongly autocorrelated, so the effective sample is far smaller than the count); the assumption that the day-`t` satellite file is in hand on day `t`; four stale cycles excluded. Further train-versus-serve differences that no document lists: persistence takes the QA-masked day-`t` observation with NaN zero-filled, which slightly handicaps persistence where the day-`t` cell is suspect (unquantified). ADR-027 makes IIEE and CRPS the build-blocking acceptance gate, but the scorer computes RMSE and IIEE only, so that gate cannot yet be evaluated whatever the U-Net returns.

The decision-level check (slice 3), `scripts/corrected_forecast.py`. RMSE and IIEE are field scores; the router's question is binary: is Bharati's approach open. `reachable(sic, d2_station_km)` asks whether any cell within 50 km of Bharati is 4-connected (`scipy.ndimage.label`, default cross structure) to cells 400 km or more away through cells that are finite and at or under 0.80, on the 25 km grid, with no depth blocking (its docstring says so; it should become the `Router` if the two ever disagree on a real cycle). The 4-connectivity is stricter than the router's 8-neighbourhood, so the check errs toward "not reachable" (docstring, `ad97f88`). The corrected field stays on the model's native 25 km grid; it adds no resolution (`corrected_forecast.json["grid"]`).

- Single cycle, `dakshin/figures/corrected_forecast.json`: the newest cycle with a full 7-day satellite history is 2026-11-20 (the NRT files end 2026-11-20). At all four leads (targets 2026-11-21, 23, 25, 27) raw CMEMS mean-pooled to 25 km says reachable, the corrected field says not reachable, and the day-0 satellite says not reachable (`ai_changed_reachability: true`; mean absolute correction 0.0629, 0.0636, 0.0578, 0.0592). The spurious opening in the raw field is a one-cell-wide thread (`docs/PROTOTYPE_RESULTS.md`).
- Season, `--all`, `dakshin/figures/corrected_all.json`: 78 cycles (2026-08-31 to 2026-11-20), every lead's verdict scored against the satellite field on the target date, not on day 0; targets beyond the archive are not counted, so 78 x 4 = 312 lead-decisions give 298 verifiable ones (the remaining 14 fall after 2026-11-20). `verification`: raw CMEMS 287 of 298 correct, U-Net-corrected 298 of 298, persistence (the day-0 satellite verdict carried forward) 298 of 298. All 11 raw errors are false "reachable" verdicts (counted here from the JSON). The JSON's own caveat is that the station's state never changed inside a lead window, so persistence scores perfectly too and the record separates the corrected field from the raw forecast, not from persistence. Measured here from the same file: the satellite verdict on the target date is "not reachable" in all 298 verifiable decisions and the day-0 satellite verdict is "not reachable" in all 78 cycles, so a constant "closed" rule also scores 298 of 298 (`docs/PROTOTYPE_RESULTS.md` says the same since `ad97f88`). The record measures false-alarm removal at one station in one spring, not sensitivity and not decision skill across regimes. Corrected fields for every cycle are packed in `corrected_all.npz` (about 2 MB) for the site's AI edge; they exist only for the 78 of the 83 archived cycles with a full satellite history (`docs/backlog.md`).

The live forecast cycle has no AI edge, by measurement. NSIDC NRT publishes about a day late, so a correction for the newest cycle would have to run on history ending at day-1. `scripts/stale_history_eval.py` scores that setting (history obs[t-1 ... t-7], `stale`) against the hindcast's (obs[t ... t-6], `fresh`) on the same cycles, mask, checkpoints and scoring; `dakshin/figures/stale_history_eval.json`:

| Lead | n | RMSE fresh | RMSE stale | RMSE raw CMEMS | IIEE fresh (km2) | IIEE stale (km2) | IIEE raw CMEMS (km2) |
|---|---|---|---|---|---|---|---|
| 1 d | 77 | 0.0914 | 0.10763 | 0.10219 | 93,231 | 139,334 | 196,031 |
| 3 d | 75 | 0.08741 | 0.09388 | 0.10479 | 142,467 | 159,967 | 194,575 |
| 5 d | 74 | 0.0946 | 0.09715 | 0.10981 | 182,601 | 190,084 | 200,203 |
| 7 d | 72 | 0.10245 | 0.10383 | 0.1153 | 221,094 | 225,790 | 210,200 |

At lead 1 the stale correction is worse than the raw forecast on RMSE (0.10763 against 0.10219), which is the number the repository quotes (`README.md`, `docs/PROTOTYPE_RESULTS.md`, `docs/WEAKNESS_ANALYSIS.md`); the short-lead skill lives in the day-0 image. The same JSON shows two things the headline leaves out: on RMSE the stale correction still beats raw CMEMS at leads 3, 5 and 7 (for example 0.09388 against 0.10479 at lead 3), and on IIEE it is still ahead of raw CMEMS at leads 1, 3 and 5 (139,334 against 196,031 km2 at lead 1) and behind it only at lead 7. The rejection of a live-cycle edge therefore rests on the lead-1 RMSE reading, which `docs/PROTOTYPE_RESULTS.md` now says explicitly (`ad97f88`). The corrected cycle therefore always trails the newest forecast by at least a day.

### 5d. Iceberg pipeline

1. Catalogue. USNIC weekly CSV (`https://usicecenter.gov/File/DownloadCurrent?pId=134`; the archive back to 2014-11-07 via `fetch_usnic_archive`). USNIC names bergs of at least 20 sq nautical miles or 10 nautical miles on the longest axis, about 18.5 km. `load_usnic` converts nautical miles to metres, orders length and width, derives the harmonic length S = LW/(L+W), and raises on malformed or non-southern data; no synthetic bergs are ever generated. The last committed issue is 2026-11-20 (33 bergs in the 2026-08-27 issue summarised in `models/iceberg/regime_report.json`; largest D15A, 3,037.47 km2).
2. Velocity. `models/iceberg/drift.iceberg_velocity`: current plus a wind-driven term, section 2 of `PHYSICS_AND_PAPERS.md`. In the forecast, wind is set to zero; the wind harvest is now scheduled and archived (section 5a) but not wired into the drift, and `dakshin/figures/berg_hindcast.json` calls that "a stated limitation, not an approximation" and the coupling "open work". Each track records R computed with an assumed 10 m/s wind and the model current speed at the start.
3. Currents. `CurrentField.from_files` reads the daily `uo`, `vo` files, takes the top level, treats each daily mean as valid at 12:00 UTC, interpolates bilinearly in space (NaN if any of the four neighbours is NaN: near a coast no velocity is invented) and linearly in time, using the nearest day outside the first and last centres.
4. Integration. `forecast_track`: midpoint (RK2) with a 1 h step. k1 from the position, a half step to the midpoint (time `t + h/2`), k2 there, then the full step with k2. Positions in degrees use 111,195 m per degree of latitude and a cosine-of-latitude factor for longitude. A step that lands on NaN current stops the track and sets status "grounded or unknown": motion is never invented. v2 (`a274a64`) adds a bathymetry argument: if the assumed keel (207.5 m, printed as 208 m in `berg_hindcast.json` and 207 m in `berg_tracks.json`; USNIC publishes no thickness) reaches the IBCSO/GEBCO seabed at the start, or at the first step that lands on such a cell, the berg is held and not advected further. Without that argument the behaviour is the original v1, which section 10.5 runs: a 9-day track has 217 hourly positions (measured here for D37 from the 2026-11-21 cycle, status ok, 17.2 km net displacement). With the bathymetry argument the same D37 track stops after 211 positions (about 210 h) with status "grounded or unknown" (measured here; `dakshin/figures/berg_tracks.json`, written by `scripts/berg_tracks.py`, carries the drift up to the grounding point and the status).
5. Validation. `scripts/berg_hindcast.py`: for every consecutive pair of USNIC fixes of a berg inside the 0 to 80 E, 55 to 78 S box, within the period covered by the analysis currents (2026-08-31 to 2026-11-20), integrate from fix to fix on the analysis currents and compare the landing point with the later fix; the baseline is persistence (the berg did not move). 88 segments from 8 bergs (B09G, C18B, C18C, C39, D15C, D15D, D23, D37). Results in `dakshin/figures/berg_hindcast.json`: 81 segments with status ok, 7 "grounded or unknown"; median error 4.35 km/day for the model against 0.0 for persistence; mean 5.06 against 0.43; of the 81, 68 stationary (persistence displacement of 3 km or less between fixes) and 13 moving; moving median 6.01 km/day for the model against 2.45 for persistence; stationary-segment model median 4.26 km/day. The finding: most corridor giants are grounded, and a current-advection model without grounding detection advects anchored ice. The site's forecast-cone growth rate was changed to the measured 4.35 km/day (`uncertainty_radius_km_per_day`), replacing an unverified 12 km/day. The v2 grounding-aware variant is scored beside v1 in the same file (`v2_grounding`), never replacing it: 26 of the 88 segments are held as grounded and 62 drift freely; the median error over all 88 segments is 4.13 km/day (held segments predict no motion, so their error equals the persistence error); on the 62 free-drifting segments the median is 4.45 km/day for the model against 0.0 for persistence, and on the moving free-drifting segments 5.76 against 2.37. Persistence still wins; v2 reduces the error of the all-segment median only from 4.35 to 4.13 km/day.
6. Coarse-current experiment (F3), `dakshin/figures/berg_resolution.json`: with currents block-averaged to 1/4 degree the median error falls to 4.07 km/day (86 ok, 2 flagged), at 1 degree to 3.49 (88 ok, 0 flagged), against 4.35 at 1/12 degree (81 ok, 7 flagged); on moving bergs 6.01, 5.93, 5.06. The explanation offered in `docs/RESOLUTION_STUDY.md`: resolved eddy velocity advects ice that is actually grounded, so smoothing drifts the forecast toward "does not move", which happens to be right for this sample. On the 13 moving segments the gap narrows but coarse still wins slightly; that sub-sample is too small to resolve an eddy effect at weekly fix cadence and few-kilometre USNIC accuracy.
7. Melt estimate (F4), `scripts/berg_melt.py`, `dakshin/figures/berg_melt.json`: for the 8 bergs in the box, the 9-day track on the 2026-11-21 forecast currents with SST and daily-max Hs sampled at the nearest grid cell, freshwater input in m3/day with an assumed 250 m thickness. Mean daily values now range from 96,618 (C18C) to 447,673 (D37) m3/day (`dakshin/figures/berg_melt.json`, regenerated in `df7f39e`); the first version quoted 157,451 to 1,913,104, which came from passing the absolute current speed as the water-relative speed. `scripts/berg_melt.py` now computes the berg's velocity with `iceberg_velocity` (zero wind) and passes `|v_w - v_i|`, which with zero wind is about zero, so the estimate is carried by the convection and wave-erosion terms. Every output is labelled "ESTIMATE" (Arctic-calibrated coefficients, assumed 250 m thickness). Section 3 of `PHYSICS_AND_PAPERS.md` discusses it.

Wind is a neglected term. The regime check in `models/iceberg/regime_report.json` sweeps wind and current speeds because observed forcing at each berg is not held. In the segment table of the hindcast the per-segment R (computed with an assumed 10 m/s wind and the berg's model current speed) has median 0.25, minimum 0.037, maximum 1.73 over the 88 segments (measured here from `berg_hindcast.json`), with 81 of 88 above the 0.1 line the code treats as current-dominated and one above 1. The docstrings of `berg_forecast.py` ("the wind term is ~1% of drift") and `scripts/berg_resolution.py` ("R << 1 in every segment") used to disagree with that; both were rewritten in `1a9ff0b` to state the zero-wind limitation and the measured median R of 0.25. The honest statement is that R scales as 1/|v_w|, so slow or near-zero model currents at grounded bergs inflate it, and the wind-free simplification drops a term of order a quarter of the current speed in this sample. Section 2 of `PHYSICS_AND_PAPERS.md` gives the envelope.

### 5e. Routing and gates

The contract. `RealWorld(cycle)` exposes `sample(lat, lon, t)` where `t` is days since the cycle date, returning a dict with `sic`, `hs`, `wind_u`, `wind_v`, `wind_ms` and bookkeeping counters. It is the same call signature as the synthetic `World.sample`, so the `Router` runs unchanged on real data. Rules enforced in `real_world.py`:

- Daily fields: `t` is rounded to the nearest forecast day and clamped to the 10-day horizon; `beyond_horizon` reports when the clamp fired.
- Bilinear interpolation, NaN outside the box or next to NaN.
- Inside the box, a cell with no ice value (under-shelf or model land sliver) is UNKNOWN, treated as impassable (`sic = 1.0`) and counted in `sic_unknown_impassable`; never as open water.
- The wave model leaves `VHM0` NaN under ice. Where `sic > 0.15` waves are set to 0.0 (swell is damped by ice) and counted in `hs_filled_ice`. Coastal slivers with no wave cell but open ocean are filled with the day's worst wave in the box so missing data can only over-cost a leg, counted in `hs_filled_coastal_worstcase`.
- No visibility field exists in any harvested data, so none is returned and the weather gate lists visibility as unassessed.
- Wind: the 6-hourly IFS step nearest `day * 24 + 12` hours; the IFS latitude axis is descending and is reversed before interpolation.

The router (`dakshin/sim/router.py`). Dijkstra on a lat/lon lattice, 8-connected. For each node expansion the elapsed hours since departure select a 6-hour slot (`slot = int((depart_t * 24 + t_here) // 6)`), the world is sampled once per slot (cached), and the cost of moving to a neighbour uses the ice and waves valid at that arrival time. That is the time dimension PolarRoute lacks. Rules: a neighbour is skipped if it is land (`on_land`), shallower than the vessel's `min_depth_m` (IBCSO v2 depth, 20 m for Golovnin, `NaN < x` is False so no data is not shallow, it is unknown), or if its SIC exceeds the ice limit (a hard constraint, never priced). The vessel model: speed is `max_speed * (1 - 0.92 * (sic/limit)^1.35)` times a sea factor `1 - 0.45 * clip((Hs - 4)/5, 0, 1)`, floored at 2 kn, zero above the limit; defaults 16.4 kn, ice limit 0.80. The objective is time or fuel; fuel is expressed per distance, `0.000120 v^2 + 0.0200 sic^1.5 + 0.00035 Hs^2` tonnes per km, scaled so a calm 16.4 kn passage burns about 24 t/day, and is explicitly relative only. Stations sit ashore: the node nearest Bharati is on the ice sheet (221 m above sea level in IBCSO). The start snaps to the nearest navigable node (`_nearest`). For the goal, `_goal_nodes` (commit `478ecd2`, the one-lattice-cell arrival rule) makes the nearest node the only goal if it is navigable; otherwise every navigable node within one lattice diagonal of the goal (`hypot(dlat, dlon * cos(lat))`) counts as an arrival and the search ends at whichever it reaches first. Its docstring gives the reason: at 0.55 x 0.9 degree spacing the nearest navigable nodes to Bharati lie 44 and 51 km off in different directions, and picking one by distance made the answer hinge on a 7 km difference and on that one node's ice. `arrival_offset_km` in the result reports how far short of the requested goal the ship stops. The consequence is that `solve` returning a route no longer means the ship reaches the station. `critical_ice_limit` steps the limit down from 0.85 to 0.30 and returns where the destination stops being reachable, so the output does not rest on one invented threshold.

The real run, `scripts/real_route_run.py`, `dakshin/figures/real_route.json` (cycle 2026-11-21, regenerated 2026-11-22 04:13 UTC): start (-55.5, 45.0), goal Bharati (-69.4, 76.2), lattice lat -70.6 to -55.0, lon 13.0 to 79.5. Under the one-lattice-cell rule the router now finds a route to the goal (`approach_closed_at_ice_limit: false`, `closest_approach_km: null`); the first version of this document, run before the report was changed, read `true` and 50.6 km from the fallback branch (`solve_with_fallback`, which still routes to the closest reachable cell when `solve` returns None). The honest number is the new field `route_ends_km_from_station`: 50.6 km, the distance from the last leg to Bharati (`0d7be9f`: the arrival rule had silently turned "closed" into "open" while the track still ended 50.6 km out). The route takes 5.55 days over 45 legs with worst ice 0.723, worst Hs 4.77 m, worst wind 14.9 m/s; the weather gate returns FAIL ("waves 4.77 m exceed the assumed 3.0 m limit; wind 14.9 m/s in Beaufort 7"). The 5.55 days is the segment south of 55 S, not a voyage time: no real wave or wind data exists north of 55 S. `lattice_note` in the same file states that the 0.55 x 0.9 degree lattice over native 1/12 degree fields cannot resolve the final ~50 km and that the 25 km reachability check (`corrected_forecast.json`, section 5c) covers the approach; that check says the approach is not reachable for this period. The two answers are different statements on different grids and are both kept.

The corrected-ice router check. `real_route_run.py` also defines `CorrectedIceWorld`, which wraps a `RealWorld` and adds the U-Net delta (`corrected_lead<L>` minus `raw_lead<L>` from `corrected_forecast.npz`) to the sampled SIC at the nearest 25 km NSIDC cell (KD-tree on EPSG:3412 coordinates) and the nearest available lead, clipped to 0 to 1; non-ice fields and attributes pass through. `dakshin/test_real_route_corrected.py` (2 tests, synthetic grids, plumbing only) pins the delta, the clip and the pass-through. The check itself, `corrected_ice_check` in `real_route.json`, solves the same route on raw and on corrected ice for the newest corrected cycle. It is skipped, and the JSON says so: the newest corrected cycle (2026-11-20) has no archived wave file and the router needs waves, and 2026-11-21 has waves but no correction. It will run on the first cycle that has both, so no comparison of routes on corrected ice with real weather exists yet.

PolarRoute alternatively. The September prototype's published corridors use PolarRoute 1.1.11 and meshiphi 2.3.1 (British Antarctic Survey, MIT), in a separate Python 3.11 environment (`dakshin/make_route_figure.py` docstring). The sandbox now has one (`/home/agent/.venvs/prenv`, with `polar_route-1.1.11` and `meshiphi-2.3.1` in site-packages, seen here with `ls`), and the route-regret, destination-window and alternatives experiments were re-run in it on 2026-11-21 (commit `06d7d70`); this document did not re-run them. See section 7.

Route health from gates (`dakshin/decision.py`). Health is the worst level over the gates, never a score: FAIL gives CRITICAL if `fails_in_hours > 0` (ahead of the ship) and INVALID otherwise; MARGINAL and UNKNOWN both give DEGRADED; all PASS gives VALID. The binding gates are those at the worst level, ordered FAIL, MARGINAL, UNKNOWN. Missing evidence therefore caps health at DEGRADED, by design (a false "all clear" is the expensive error).

---

## 6. The nine gates

Order follows `dakshin/decision.py::GATES`: capability, chart, ice, weather, traffic, logistics, communications, contingency, execution.

| Gate | Question | Evidence it uses | Possible states in code | Can it PASS? |
|---|---|---|---|---|
| capability | May this ship be here, legally and physically? | Vessel config; the force limit 96,634.5 is carried over from another hull | UNKNOWN only | Never. No Polar Ship Certificate or PWOM is held, and inventing vessel thresholds is forbidden |
| chart | Is there water under the keel along the route? | IBCSO v2 (south of 50 S) and GEBCO_2020 (north) depth at each route point vs the vessel `min_depth` (20 m) | FAIL if any known point is shallower; MARGINAL otherwise; UNKNOWN if no points lie in coverage or the mesh has no bathymetry | Never. IBCSO is a scientific compilation, not an official ENC; `CHART_NOT_ENC` is the stated reason |
| ice | Will expected ice exceed the working limit? | Worst SIC on the route vs 80% | FAIL / MARGINAL / PASS | Yes. MARGINAL band is 7.4 points: one median standard deviation of the CDR retrieval across the 70 to 90% band (`cdr_seaice_conc_stdev`, December 2019: median 7.4, mean 8.0, p90 11.7). The limit is flagged as assumed because ice class is defined by thickness, not concentration |
| weather | Will wind, waves or visibility make the corridor unsafe? | Worst `VHM0` daily max and worst 10 m wind on the route at arrival times | FAIL if Hs > 3.0 m or wind >= 17.2 m/s (Beaufort 8); MARGINAL within 0.5 m or wind >= 13.9 m/s (Beaufort 7); UNKNOWN with no data | Yes, but visibility is always listed as unassessed. Limits are assumptions (3.0 m is the PolarRoute example `max_wave`), not this hull's PWOM |
| traffic | Conflict with other vessels? | Ship AIS receiver via `ais_feed.py`; bands 2 nm (FAIL) and 5 nm (MARGINAL) are assumptions, not COLREGS distances | UNKNOWN with no live feed | Only with a live feed. Shore aggregators reach about 40 nm and are empty in the Southern Ocean, and satellite AIS is paid |
| logistics | Will the track meet the station's operating window? | Destination-cell passability from the daily destination window | PASS / FAIL, UNKNOWN if the destination was never scored (not "closed") | Yes |
| communications | Can the ship get warnings and coordinate? | would need GMDSS/satcom link-budget model | UNKNOWN only | Never in code |
| contingency | If the route closes ahead, where do we go? | Number of computed alternative corridors | FAIL (0), MARGINAL (1), PASS (2 or more) | Yes |
| execution | Are observations consistent with what was approved? | Live bridge sensors | UNKNOWN; PASS only if `live_sensors=True` | Only if the flag is set; the demo always passes `live_sensors=False` |

So three gates can never PASS in the code as written (capability, chart, communications), two more can PASS only with live data the repository does not have (traffic, execution), and four can be evaluated from data held (ice, weather, logistics, contingency, with chart returning a depth-based FAIL or MARGINAL). The header docstring of `gates.py` used to say "of the nine gates we can evaluate four"; it was rewritten in `1a9ff0b` to say six can be evaluated from real data (ice, chart, logistics, contingency, weather, and traffic when a live AIS feed exists), chart never passes, and weather always lists visibility as unassessed. It now agrees with the table above.

The chart gate has a history worth knowing. The first claim of "8.6 days Cape Town to Bharati" was withdrawn on 2026-11-21 because the route's final point is Bharati station, which IBCSO v2 places above sea level (91 m in the withdrawal note). The same day the published route was regenerated on the same 1 December 2019 ice with real IBCSO v2 / GEBCO_2020 depth in the mesh: 8.66 days, arriving 16 km off the station, never over water shallower than 89 m (`docs/TRUE_CLAIMS.md` claim 1.11, `docs/PROTOTYPE_RESULTS.md` section 4, commit `13861d9`). It is a steaming-time lower bound with no sea-state penalty (PolarRoute defines `wave_resistance()` and never calls it). The route-regret table was re-run on depth-aware meshes on 2026-11-21 (commit `06d7d70`, `dakshin/figures/route_regret.json`): STATIC planned 8.66 d, actual 8.65 d, regret -0.01 d, 0 h blocked; STATIC-noQA 8.63 d; DAILY 9.0 d with 9.5 h blocked and 9 daily re-plans. The pre-depth values were 8.61 d and 9.00 d (`docs/PROTOTYPE_RESULTS.md` section 3), and `scripts/verify_claims.py` now checks -0.01 and 8.7. The destination window and the alternatives were re-run in the same commit: `dakshin/figures/destination_window.json` now scores "Bharati" at the published route's arrival point (23 of 31 December 2019 days closed at the 80% limit, 74.2%), "Bharati approach (100 km N)" 0 of 31 closed, and "Bharati station cell (ashore)" 31 of 31 closed on every day; the stale Maitri row is gone. `docs/TRUE_CLAIMS.md` claim 1.6 was reworded to match.

---

## 7. Two routing engines, and why

| | PolarRoute 1.1.11 + meshiphi 2.3.1 | `dakshin/sim/router.py` |
|---|---|---|
| Role | September prototype: published corridors, route-regret, alternatives, destination window | Real-forecast run: time-dependent routing on `RealWorld` |
| Time dimension | None (frozen mesh; verified by source grep, `docs/backlog.md`) | Arrival-time costs on 6-hour slots |
| Cost model | `SDA` performance model; fuel polynomial fitted to RRS Sir David Attenborough; `wave_resistance()` dead code | Simple derating curve; fuel per distance; stated not to be a hull model |
| Environment | Python 3.11 only, separate env | Same environment as the rest |
| Mesh | Non-uniform adaptive, meshiphi | Regular lat/lon lattice, 0.55 x 0.9 degrees |
| Run here | Not re-run by this document; last run 2026-11-21 in `06d7d70` (route regret, destination window, alternatives, on depth-aware meshes) | Run, section 10 |

The choice was ADR-009 (wrap rather than reimplement) for the prototype, and the in-house router exists because PolarRoute cannot consume a forecast (`dakshin/sim/router.py` docstring, `docs/TRUE_CLAIMS.md` 2.3).

---

## 8. What is real and what is synthetic

Real, and on disk: every satellite and model field used for any number in section 5 and in `README.md`; USNIC positions; IBCSO/GEBCO depth; the Natural Earth coastline; the Antarctic Treaty protected-area register; ECMWF wind (one cycle, two runs); and the model inference outputs (`dakshin/figures/corrected_forecast.*`, `corrected_all.*`, the hindcast and stale-history JSONs), which are the committed checkpoints applied to real forecast cycles and real satellite history.

Synthetic and labelled so: `dakshin/sim/` generates a seeded world (default seed 20261207) of pressure, wind, ice edge, SST, waves, visibility, berg population, traffic and warnings. The model is "real physics, synthetic state": wind is the gradient of the pressure field, waves grow from wind and are damped by ice, fog forms where warm air meets cold water, and the ice edge moves because the modelled wind pushed it. It exists so the bridge console and the router tests have a full environment to exercise, and the console page says "SYNTHETIC ENVIRONMENT". It is not used for any reported result, and `RealWorld` replaces it for real-data runs. Two further items are described as simulations in `dakshin/demo/app.py` ("Baymax Mode and the local-LLM assistant"). The routes under `dakshin/sim/` use the real depth lookup and real coastline for land and depth blocking.

The other places where a number is not measured: router ice thickness and density are the literature lookup table inside meshiphi (ADR-013); the 80% working ice limit, 3.0 m wave limit and traffic bands are assumptions stated as such in code and output; melt thickness is assumed at 250 m.

---

## 9. Data on disk: committed or not

| Data | Location | Committed? | Re-fetch |
|---|---|---|---|
| CMEMS forecast cycles (ice, plus one cur, wav, sst set) | `data/cmems_forecast_archive/` (87 files: 83 `siconc`, `KNOWN_STALE.md`, `cmems_cur_2026-11-21.nc`, `cmems_wav_2026-11-21.nc`, `cmems_sst_2026-11-21.nc`) | Yes | Cannot be re-fetched: forecasts as issued are gone |
| Analysis currents | `data/cmems_cur_analysis/` (82 files) | Yes | `scripts/backfill_cur_analysis.py` |
| ECMWF wind | `data/ecmwf_wind/` (2 files: 2026-11-21 00z and 12z) | Yes | cannot, beyond 2 to 3 days; the workflow adds files going forward (section 5a) |
| USNIC | `data/icebergs/archive/` (14 weekly files) and `usnic_antarctic_20260902.csv` | Yes | `catalogue.fetch_usnic_archive` |
| Bathymetry subset | `data/bathymetry/ibcso_v2_corridor_0p05.nc` | Yes (`raw/` gitignored) | `scripts/subset_bathymetry.py` |
| NSIDC NRT G10016 v4 | `data/nsidc_nrt/` (89 files, 2026-08-24 to 2026-11-20, plus `MANIFEST.sha256`) | Yes, since `a6fdc83` (no longer gitignored; the download script's docstring still says it is) | `scripts/download_nsidc_nrt.py`, only the last ~3 months, so the committed copy is the only source for the oldest days from 24 November |
| NSIDC G02202 v6, 2018 to 2020 | `dakshin/data/nsidc_sic/` (1,096 files) | No | `python dakshin/download_nsidc.py --start-year 2018 --end-year 2020` |
| Checkpoints | `models/sic_correction/checkpoints/` (4 `.pt` of 7,763,017 bytes, `SHA256SUMS`, skill CSV, 2 PNGs) | Yes (`5612621`); also release `model-v0.1` | `gh release download model-v0.1`, or `scripts/pull_checkpoints.sh` from the Kaggle kernel |
| Model outputs | `dakshin/figures/corrected_forecast.{npz,json}`, `corrected_all.{npz,json}`, `stale_history_eval.json` | Yes | `scripts/corrected_forecast.py [--all]`, `scripts/stale_history_eval.py` (reproduced exactly here, section 10.4) |

A fresh clone therefore lacks only the 2018 to 2020 CDR archive (`dakshin/data/`, gitignored): the QA audit, the demo's day slider and the tests that read those files will not run until it is fetched. The hindcast, the corrected-forecast scripts and the real route run read only committed files.

---

## 10. Data operations: if someone asks you to do something

Each block says whether it was executed while writing this document. "Ran here" means executed in the study sandbox with the output shape observed, on 2026-11-21 for the first version of this document and on 2026-11-22 where a block says so. Several scripts overwrite committed figure files in `dakshin/figures/`; when running them for a demonstration, copy the repository first or restore with `git checkout -- dakshin/figures/<file>`. The outputs below were obtained from a scratch copy so nothing committed was changed.

Environment: Python 3.12 with `numpy`, `xarray`, `netCDF4` (or `h5netcdf` + `h5py`), `pyproj`, `scipy`, `pandas`, `matplotlib`, `torch` for model runs, `copernicusmarine` for CMEMS. Run everything from the repository root.

### 10.1 Fetch one day of NSIDC data

Near-real-time (AMSR2, the 2026 truth), ran here:

```bash
python scripts/download_nsidc_nrt.py --start 2026-11-19 --end 2026-11-19 --out /tmp/nrt
# ok   sic_pss25_20261119_am2_icdr_v04r00.nc 389301 bytes
# 1 files in manifest; 0 failed
```

Takes about 2 s. Exit code is 1 if any day failed. The NRT archive keeps roughly 3 months, so the default `--start 2026-08-24` will begin to fail as days roll off; the committed `data/nsidc_nrt/` already holds 2026-08-24 to 2026-11-20, so this fetch is only needed for later days. The file name hard-codes the `am2` sensor tag, correct since 2025-01-01.

Final CDR G02202 v6 (F17 SSMIS), one day, ran here:

```bash
mkdir -p /tmp/g02202
curl -sSf -o /tmp/g02202/sic_pss25_20191201_F17_v06r00.nc \
  https://noaadata.apps.nsidc.org/NOAA/G02202_V6/south/daily/2019/sic_pss25_20191201_F17_v06r00.nc
# 399,012 bytes
```

A year range (about 130 MB per year, 6 parallel workers), not run: `python dakshin/download_nsidc.py --start-year 2019 --end-year 2020`.

Read it with the QA flag applied, ran here:

```python
import sys; sys.path.insert(0, "dakshin")
from ice_quality import load_sic, qa_breakdown
sic, suspect = load_sic("/tmp/g02202/sic_pss25_20191201_F17_v06r00.nc")
# sic.shape == (332, 316); 112 suspect cells; 22,005 NaN in total
qa_breakdown("/tmp/g02202/sic_pss25_20191201_F17_v06r00.nc")
# {'BT weather filter': 36931, 'NT weather filter': 36323, 'land spillover filter': 112,
#  'no input data': 0, 'invalid ice mask': 24396, 'spatial interpolation': 7,
#  'temporal interpolation': 0, 'cells total': 104912}
```

The Bharati cell (row 152, column 245 by `pyproj` from 69.4044 S, 76.19 E) reads 0.0 with `apply_qa=False` and NaN with `apply_qa=True` on 2019-12-01: the spillover artefact of `dakshin/ice_quality.py`.

### 10.2 Subset CMEMS

Needs `copernicusmarine login` once (credentials are not stored in the repository). A small test subset, ran here (about 10 s):

```bash
copernicusmarine subset \
  --dataset-id cmems_mod_glo_phy_anfc_0.083deg_P1D-m --variable siconc \
  --start-datetime 2026-11-21T00:00:00 --end-datetime 2026-11-22T00:00:00 \
  --minimum-longitude 70 --maximum-longitude 80 \
  --minimum-latitude -72 --maximum-latitude -66 \
  --output-directory /tmp/cmems --output-filename test_siconc.nc
# {"file_size": "0.08 MB", ..., "status": "000", "message": "The request was successful."}
# dims: time 2, latitude 73, longitude 121; variable siconc, max 0.9971
```

The full daily harvest (`bash scripts/harvest_cmems.sh`, optional `CYCLE_DATE=YYYY-MM-DD`) was not run, because it writes into the committed archive and a hand-typed date skips the stale check.

### 10.3 Regrid a field onto the NSIDC grid

Ran here, with the 2026-11-19 cycle and the NRT file from 10.1 as the grid template:

```python
import sys; sys.path.insert(0, "dakshin")
import numpy as np, xarray as xr
from grid import GlorysToNsidcRegridder
tpl = xr.open_dataset("/tmp/nrt/sic_pss25_20261119_am2_icdr_v04r00.nc")
a = xr.open_dataset("data/cmems_forecast_archive/cmems_siconc_2026-11-19.nc")
rg = GlorysToNsidcRegridder(tpl, a.latitude.values, a.longitude.values)
rg.coverage()                                   # 0.1469
out = rg(a.siconc.isel(time=0).values.astype(np.float32))
# out.shape == (332, 316), float32, 11250 finite cells, range 0.0 to 0.9964, NaN elsewhere
```

### 10.4 Run the real-forecast hindcast

Ran here on 2026-11-22 in a scratch copy of the repository (CPU, with the model, 58 s). It overwrites `dakshin/figures/realforecast_hindcast.json`:

```bash
python scripts/realforecast_hindcast.py            # add --no-model to skip the U-Net
# clean cycles: 79, NRT days: 89, factors: (1,)
# regridder coverage of NSIDC grid: 14.7%
# lead 1: n=77 (1/12°) f1:cmems=0.10219
# lead 3: n=75 ... 0.10479 ; lead 5: n=74 ... 0.10981 ; lead 7: n=72 ... 0.1153
# wrote dakshin/figures/realforecast_hindcast.json
```

The regenerated JSON equals the committed one in every field except `generated` (compared with a Python dict comparison). The first version of this document ran `--no-model` and found a lead-1 delta against the then-committed file (n = 77 against 76); the committed file has since been regenerated and the delta is gone. The model columns appear as `unet` entries under `rmse` and `iiee_km2_mean`.

### 10.4b Run the correction, the decision record and the stale-history test

Ran here in the same scratch copy, CPU, same day:

```bash
python scripts/stale_history_eval.py              # 124 s
# lead 1 (n=77): rmse fresh 0.0914 stale 0.10763 cmems 0.10219 | iiee fresh 93231 stale 139334 cmems 196031
# ... lead 7 (n=72): rmse fresh 0.10245 stale 0.10383 cmems 0.1153 | iiee fresh 221094 stale 225790 cmems 210200
python scripts/corrected_forecast.py --all        # 70 s; 78 cycles, then the newest cycle (2026-11-20)
# lead 1 (2026-11-21): station reachable raw True corrected False (limit 0.8)  [same at leads 3, 5, 7]
```

`stale_history_eval.json`, `corrected_all.json`, `corrected_forecast.json` and `real_route.json` (below) equal the committed files except `generated`; `corrected_all.npz` and `corrected_forecast.npz` are array-for-array identical to the committed ones (`numpy.array_equal`). So the model results in sections 5c and 5e reproduce bit-for-bit on CPU from the committed checkpoints.

### 10.5 Run the iceberg forecast

One berg, one 9-day track, ran here:

```python
import sys, datetime as dt; sys.path[:0] = ["dakshin", "models/iceberg", "."]
from pathlib import Path
from berg_forecast import CurrentField, forecast_track, great_circle_km
from catalogue import load_usnic
cur = CurrentField.from_files([Path("data/cmems_forecast_archive/cmems_cur_2026-11-21.nc")])   # u shape (10, 277, 961)
b = load_usnic("data/icebergs/archive/AntarcticIcebergs_20261120.csv")                            # 33 bergs
r = b[b.name == "D37"].iloc[0]                  # lat -69.21, lon 36.36, 55.56 x 12.964 km, 477.77 km2
tr = forecast_track("D37", r.lat, r.lon, r.length_m, r.width_m, cur, dt.datetime(2026, 11, 21, 12), days=9)
# 217 hourly positions, status 'ok', wind_forcing_R 0.583 (assumed 10 m/s wind), net displacement 17.2 km
```

The validation against later USNIC fixes, ran here (about 5 s, overwrites `berg_hindcast.json`):

```bash
python scripts/berg_hindcast.py
# wrote dakshin/figures/berg_hindcast.json: 81/88 ok segments, median model 4.35 km/day vs persistence 0.0 km/day
python scripts/berg_resolution.py      # F3; 1/12°: 81 ok, 4.35 | 1/4°: 86 ok, 4.07 | 1°: 88 ok, 3.49 km/day
python scripts/berg_melt.py            # F4; 8 bergs, mean 96,618 (C18C) to 447,673 (D37) m3/day
python scripts/berg_tracks.py          # per-berg 0 to 9 day tracks for the chart; D15D grounds mid-track with 90.8 km net drift
```

`berg_hindcast.py` now also computes and writes the v2 grounding-aware block beside v1. All four reproduce the committed JSONs (equal in every field except `generated`), measured here on 2026-11-22.

### 10.5b Regime report

Ran here, reproduces the committed `models/iceberg/regime_report.json` exactly when pointed at the 2026-08-27 issue:

```bash
python models/iceberg/regime_report.py --csv data/icebergs/archive/AntarcticIcebergs_20260827.csv
```

Without `--csv` it downloads the current USNIC catalogue (today: issue 2026-11-20, smallest berg 45.36 km2, median long axis 25.9 km), so the output differs from the committed file.

### 10.6 Run a route

Ran here (about 2 s, overwrites `dakshin/figures/real_route.json`):

```bash
python scripts/real_route_run.py 2026-11-21
# approach_closed_at_ice_limit false, closest_approach_km null, route_ends_km_from_station 50.6,
# eta_days 5.55, worst_ice 0.723, worst_hs_m 4.77, worst_wind_ms 14.9, weather_gate FAIL, n_legs 45,
# corrected_ice_check {"skipped": "newest corrected cycle (2026-11-20) has no archived wave file ..."}
```

The first version recorded `approach_closed_at_ice_limit true, closest_approach_km 50.6`; those two fields changed meaning with the one-lattice-cell rule (section 5e), and `route_ends_km_from_station` is the number to quote.

The prototype PolarRoute routes need the Python 3.11 environment (`uv venv --python 3.11 prenv; uv pip install --python prenv/bin/python polar-route==1.1.11 matplotlib`) and were not re-run here (their committed outputs date from `06d7d70`): `prenv/bin/python dakshin/make_route_figure.py`, `dakshin/route_regret.py --depart 2019-12-01`, `dakshin/destination_window.py --start 2019-12-01 --days 30`, `dakshin/alternatives.py`.

### 10.7 Run the tests

Ran here:

```bash
/home/agent/.venvs/sih-work/bin/python -m pytest -q
# 209 passed, 2 skipped, 1 warning in 54.29s   (clean tree at 0cda289, 2026-11-22; 47.99 s on a second run)
python scripts/verify_claims.py
# PASSED 29 ; All claims verified against source files.
```

The demo app tests need the NSIDC 2018 to 2020 archive (gitignored). `models/iceberg/test_drift.py` has 23 tests (the "23/23" of `docs/TRUE_CLAIMS.md` claim 1.9).

### 10.8 Run the resolution study

Ran here on 2026-11-22 in the scratch copy (CPU, with the model, 205 s; the first version ran `--no-model` in about 14 s). It overwrites `resolution_study.json` and `.png`:

```bash
python scripts/resolution_study.py                # add --no-model to skip the U-Net
# lead 5: n=74 (1/12° | 1/4° | 1°) f1:cmems=0.10981 f3:cmems=0.10816 f12:cmems=0.10988
# lead 7: n=72 (1/12° | 1/4° | 1°) f1:cmems=0.1153 f3:cmems=0.11365 f12:cmems=0.11417
# wrote dakshin/figures/resolution_study.json and .png
```

The regenerated JSON equals the committed one in every field except `generated`. It now holds the U-Net columns at all three resolutions (section 5c) and n = 77 at lead 1 (1/12 degree 0.10219, 1/4 degree 0.10055, 1 degree 0.10419).

### 10.9 Plug in NEMO output

Not run on real NEMO output. The pattern is in section 4.5; use `NemoReader(...).available()` first to see which fields were resolved.

### 10.10 Retrain, pull checkpoints, run the demo

Retraining and pulling were not run here (they need Kaggle credentials and hours of GPU). The checkpoints are already in the repository, so `pull_checkpoints.sh` is only needed to overwrite them from a new Kaggle run (it also re-runs both scorers):

```bash
python dakshin/kaggle/make_notebook.py            # regenerate isih_train.ipynb from unet.py, grid.py, features.py
KAGGLE_API_TOKEN=... bash scripts/pull_checkpoints.sh   # when the kernel is COMPLETE
uvicorn dakshin.demo.app:app --port 8000          # demo; see docs/PROTOTYPE_README.md for the venv
```

The demo's model card, ran here in-process with `fastapi.testclient.TestClient` (no server): `GET /api/model` returns 200 with keys `name, release, checkpoints, held_out_skill, source, decision_verification`; `release` is `model-v0.1`, the first checkpoint is `isih_prototype_lead1.pt` with sha256 prefix `acacc55432d7` and 7.8 MB, `held_out_skill[0]` is lead 1 with model RMSE 0.0465, persistence 0.057, gain 18.5%, and `decision_verification` is 298 decisions, raw 287, corrected 298. The page was not opened in a browser here (the browser test is skipped, section 2).

---

## 11. State of the model and the open items

Model status, 2026-11-22. The model is trained, committed, released and in use; no training run is pending.

- Artifacts. Four checkpoints (leads 1, 3, 5, 7), `SHA256SUMS`, `isih_skill_by_lead.csv` and two training figures are in `models/sic_correction/checkpoints/` (commit `5612621`) and in GitHub release `model-v0.1`. `dakshin/model_io.py` verifies each file against `SHA256SUMS` before loading and refuses otherwise (config 12 channels, 32 base filters, depth 3; 1,929,601 parameters). They come from the 2026-11-21 re-run of the 2026-08-31 recipe on Kaggle (GPU version 8); the 2026-08-31 originals were never retrievable (`docs/CURRENT_STATE.md`).
- Training-time skill, an upper bound because the background is a reanalysis: section 5b. Operational skill on real CMEMS forecasts against 2026 AMSR2 truth, the weight-bearing evidence: section 5c. U-Net RMSE is lowest at every lead; IIEE is lowest at leads 1, 3, 5 and worse than raw CMEMS at lead 7 (221,094 against 210,200 km2).
- Decision level: 298 of 298 target-date approach verdicts correct against 287 of 298 for raw CMEMS, with the constant-rule caveat of section 5c.
- Where it is wired in: the hindcast and resolution scorers (`scripts/realforecast_hindcast.py`, `resolution_study.py`), `scripts/corrected_forecast.py` and `stale_history_eval.py`, the demo's `/api/model` and bridge-console "AI correction" panel, and the companion viewer's ice-edge overlay for the 78 cycles with a full satellite history (`README.md`, status section). The tests in `dakshin/test_model_io.py`, `test_corrected_forecast.py`, `test_real_route_corrected.py` and `dakshin/demo/test_app.py::test_model_card_is_real_artifacts` exercise it.
- Where it is not: no AI edge on the live cycle (section 5c); no route comparison on corrected ice with real weather yet (section 5e); no CI step runs `corrected_forecast.py` (needs `torch`).

Open items, each with its evidence. The authoritative lists are `docs/WEAKNESS_ANALYSIS.md` section 11 and `docs/backlog.md`.

1. No-background ablation, the test that would settle the training-time leakage question, is written as a notebook cell and has no result (`docs/PROTOTYPE_RESULTS.md`, "The ablation that settles caveat 1").
2. Corrected-ice router check is wired and skipped. It needs a cycle with both a correction and an archived wave file. Waves are archived from 2026-11-21 only; the correction for that cycle needs the 2026-11-21 NRT satellite file, which is published about a day late, fetched by hand (`scripts/download_nsidc_nrt.py`) and followed by `scripts/corrected_forecast.py` and `scripts/real_route_run.py`. None of the three is scheduled. Data gap, `docs/WEAKNESS_ANALYSIS.md` section 11.
3. The live cycle gets no correction. Lead-1 RMSE on day-1 history is 0.10763 against raw 0.10219; the rest of `stale_history_eval.json` (stale ahead of raw on RMSE at leads 3 to 7 and on IIEE at leads 1 to 5) is not reflected in the verdict. Scope is an owner decision (`docs/backlog.md`).
4. Evaluation weaknesses: no confidence intervals, significance tests or CRPS, so the ADR-027 gate (corrected must beat raw CMEMS on both IIEE and CRPS at each lead, else that lead is not claimed; `docs/DECISIONS.md`) cannot be evaluated, and at lead 7 the IIEE half already fails; one spring of 72 to 77 autocorrelated cycles; one checkpoint per lead; the run-to-run training spread (up to 0.012, `docs/CURRENT_STATE.md`) is of the order of the RMSE margins over raw CMEMS (0.0108, 0.0174, 0.0152, 0.0129 at leads 1, 3, 5, 7, computed from `realforecast_hindcast.json`), measured on different sets.
5. The decision record has no positive case: all 298 verified target verdicts are "not reachable", so sensitivity is unmeasured and persistence or an always-closed rule scores the same. The 0.80 limit is an assumption, the check sits on QA-suspect coastal cells (43.2% of days in the Bharati box, `docs/WEAKNESS_ANALYSIS.md`), and no sensitivity scan over limit or radius has been run.
6. Training and serving differ at the coast and in time: the training notebook does not QA-mask truth or history while the hindcast does; the 70/15/15 time split has no embargo; the truth sensor changes from F17 SSMIS to AMSR2 (`docs/backlog.md`).
7. The Kaggle batch recipe is documented but not generated. `dakshin/kaggle/make_notebook.py` emits the Kaggle-Secrets credentials cell for interactive runs; the successful batch runs used a swapped credentials cell that searches `/kaggle/input/**/cmems.json` (private dataset `jiteeshghodke/cmems-creds`). Commit `779cf83` records that swap and the push metadata in `dakshin/kaggle/README.md` and `dakshin/kaggle/kernel-metadata.json` (read here), and `docs/CURRENT_STATE.md` now says the glob lives in the pushed batch kernel and only the NSIDC retry is in the generator (`0848d7e`). The committed `isih_train.ipynb` regenerated as is is therefore not the notebook of the successful runs; the second run's figures (3e-5, 0.012) are in `docs/CURRENT_STATE.md` prose only.
8. Scheduling and data windows: NSIDC NRT download is manual and the server window starts dropping days from 2026-11-24 (the committed copy is the only source for those days); the USNIC Friday step has not yet produced a file in CI; `berg_tracks.py` and `corrected_forecast.py` run by hand; currents, waves and SST exist for one cycle and forecasts cannot be back-filled; no wave or wind data north of 55 S.
9. Icebergs: persistence still beats the drift forecast (v1 median 4.35 km/day against 0.0 over 81 usable segments; v2 median 4.45 against 0.0 over the 62 free-drifting segments, 4.13 over all 88); wind is not coupled into the drift although R has median 0.25 and maximum 1.73; keel draught is assumed (207.5 m); melt coefficients are Arctic-calibrated and `wave_erosion_m_per_day` has a non-zero floor at Hs = 0 (`docs/backlog.md`).
10. `dakshin/readers/nemo.py` has never run on real NEMO output and does no C-grid destaggering or grid rotation.

Not built, per `docs/TRUE_CLAIMS.md` section 5 and `docs/backlog.md`: the time-expanded graph for PolarRoute, a five-model ensemble and conformal calibration (ADR-020; designed, with a pre-committed pass/fail gate, nothing fitted), a thickness output channel for POLARIS compliance, quality-masked retraining with error reported by distance to coast, and a compression-risk field. Grounding detection for bergs, listed here in the first version as not built, is now committed (v2, section 5d), with the assumptions stated there.

Inconsistencies. The first version listed inconsistencies "rather than fixed". The ones that have since been fixed in the repository: the `features.py` channel comment, the `grid.py` regridder docstring, the `gates.py` header, the `drift.py` 45-degree statement (now 51.8 degrees, `models/iceberg/drift.py`), the berg docstrings on wind, the `model_io.py` pointer to a non-existent `dakshin/config.py`, `docs/ML_ARCHITECTURE.md` naming G02202 v4 (now v6), the stale Maitri row in `destination_window.json`, the persistence IIEE column of `docs/RESOLUTION_STUDY.md`, the undocumented SST provenance, the missing top-level `requirements.txt`, the unscheduled wind and USNIC harvests, and the n = 76 hindcast file. Still open, found while updating this document: `README.md` section 5 and `docs/TRUE_CLAIMS.md` claim 1.16 say the Bharati approach is "closed" with the closest reachable point 50.6 km out, while `real_route.json` has `approach_closed_at_ice_limit: false` and `route_ends_km_from_station: 50.6`; `README.md` section 2 and the raw columns of `docs/RESOLUTION_STUDY.md` still carry the n = 76 raw-CMEMS values; ADR-024 and `docs/ML_ARCHITECTURE.md` still say "conservative area-weighted"; the docstring of `scripts/download_nsidc_nrt.py` says the NRT folder is gitignored; `docs/WEAKNESS_ANALYSIS.md` section 11 gives the NRT roll-off as "~30 days" against about three months in the script (2026-11-24 is three months after the first committed NRT file, 2026-08-24); `dakshin/kaggle/make_notebook.py` has two "## 11" headings and a "Sept 8 ISIH" intro. Most of these are collected in `docs/backlog.md`.
