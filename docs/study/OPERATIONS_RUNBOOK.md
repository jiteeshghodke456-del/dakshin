# Dakshin: operations runbook

For the question "if I am asked to perform an action on the data, what exactly
do I run?" Every command is run from the repository root unless it says
otherwise. Every path is relative to that root.

Read this first. Several operations overwrite tracked files:

- `scripts/realforecast_hindcast.py` overwrites `dakshin/figures/realforecast_hindcast.json`,
  the committed result that the project has scored once. That file now holds the U-Net scores.
  **`--no-model` is no longer the safe variant**: it still writes the same file, with `"model": null`
  and no `unet` keys, so it replaces the committed U-Net numbers (the write is unconditional in
  `main()`). The same applies to `scripts/resolution_study.py --no-model`.
- `scripts/resolution_study.py`, `stale_history_eval.py`, `berg_hindcast.py`, `berg_resolution.py`,
  `berg_melt.py`, `berg_tracks.py` and `real_route_run.py` overwrite their JSON outputs in the same folder.
- `scripts/corrected_forecast.py` overwrites `corrected_forecast.{npz,json}`; with `--all` it also
  overwrites `corrected_all.{npz,json}`.
- `scripts/stale_history_eval.py` has no argument parser. **Do not pass `--help` to it**: the
  argument is ignored and the full evaluation starts (this happened in the 2026-11-22 refresh and
  the run was stopped before it wrote). `scripts/corrected_forecast.py --help` is also not a help
  flag: it dies with `ValueError: Invalid isoformat string: '--help'`.
- `scripts/pull_checkpoints.sh` overwrites the four checkpoints and `SHA256SUMS`, then re-scores
  with the model (§2.12).
- The CMEMS, NSIDC, ECMWF and USNIC scripts write into `data/`.

Re-running a script changes the numbers if the inputs have changed (new cycles
arrive every day). Record the date of any re-run next to the number you quote.
The scorers say "scored once, reported as it comes out" (`scripts/realforecast_hindcast.py`
docstring). A re-run is a new score, not a second look at the same one.

Items marked **not run** were read from the code but not executed in this pass.
Times marked **not recorded** have no measurement in the repository.

---

**Last refreshed: 2026-11-22**, about 04:50 to 05:15 UTC, against `main` at `ad97f88` (HEAD moved from
`0cda289` to `ad97f88` during the refresh, from other commits; other writers were also editing `docs/study/*` in the working tree).
The first version was a snapshot read between about 17:56 and 18:21 UTC on 2026-11-21.
"In this pass" means the latest pass.

What was run in the 2026-11-22 pass, and nothing else: `pytest dakshin models` (§2.11), `scripts/verify_claims.py`
(§2.10), `sha256sum -c SHA256SUMS` on the checkpoints and a load of all four through `model_io.load_checkpoint` (§2.12),
`GET /api/model` through the app's in-process test client (§2.14), `--help` on `realforecast_hindcast.py` and
`resolution_study.py` (which have an argument parser), and one read-only `gh release view model-v0.1` (a GitHub metadata call).
Two scripts were also started by mistake with `--help`: `corrected_forecast.py` died at once on the argument, and
`stale_history_eval.py` began its evaluation and was stopped about two minutes in, before it wrote (its JSON still carries the
04:31 UTC timestamp and `git status` showed no change to `dakshin/figures/`). No harvest, download, training or scoring run completed,
and no committed JSON was changed by this pass. Expected outputs below for the scoring scripts
come from the committed JSON and from the `print` calls in the code. They are marked **not re-run**.

The ECMWF wind and weekly USNIC steps (workflow) and the SST harvest (`harvest_cmems.sh`) from `a274a64` are now
folded into §§2.1 to 2.5 and §2.8c.

## 1. Environment

There is no root `pyproject.toml` or lockfile. The only requirements file is
`dakshin/demo/requirements.txt` (for the demo). The three analysis environments
below live outside the repository, in `/home/agent/.venvs/`. Versions were read
from the installed packages in this pass.

| Venv | Python | Key packages (installed versions) | Used by |
|---|---|---|---|
| `/home/agent/.venvs/sih-work` | 3.12.12 | numpy 2.5.5, xarray 2026.9.0, netCDF4 1.7.5.1.post1, scipy 1.18.1, pyproj 3.8.0, torch 2.15.0+cpu, copernicusmarine 2.5.1, pytest 9.2.0, pyais 3.3.1, ecmwf-opendata (importable), matplotlib 3.11.2, fastapi 0.165.0, uvicorn 0.54.0, pydantic 2.14.4 | Everything except PolarRoute. Default for `pull_checkpoints.sh`. Also runs the demo tests and serves the demo app (§2.11, §2.14). `playwright` is not installed here, which skips one demo test. |
| `/home/agent/.venvs/prenv` | 3.11.14 | polar-route 1.1.11, meshiphi 2.3.1, netCDF4 1.7.4, numpy 2.4.6, xarray 2026.7.0, scipy 1.17.1, pyproj 3.7.2, pytest 9.1.1 | PolarRoute and meshiphi. No copernicusmarine, no ecmwf-opendata. |
| `/home/agent/.venvs/isih-demo` | 3.14.4 (when inspected at about 18:08) | numpy 2.5.2, xarray 2026.7.0, scipy 1.18.1, fastapi 0.141.1, uvicorn 0.52.4, pytest 9.1.1 | **Absent** (checked 2026-11-22: `/home/agent/.venvs/` holds `oci-cli`, `prenv`, `shoot`, `sih-work`). It was already gone on 2026-11-21; use `sih-work` for the demo. `.venv-demo` in the repo root does not exist either (§2.14). |

Command-line tools outside the venvs:

- `kaggle` CLI: `/home/agent/.local/bin/kaggle`, version 2.2.4 (checked 2026-11-22). It is not installed in `sih-work`.
  Add `/home/agent/.local/bin` to `PATH` if `kaggle` is not found.
- `copernicusmarine`: the CLI from `sih-work`. Authenticate once with `copernicusmarine login`
  (the cached credential is what the scripts use). The GitHub workflow uses the environment variables
  `COPERNICUSMARINE_SERVICE_USERNAME` and `COPERNICUSMARINE_SERVICE_PASSWORD` from repository secrets
  (`.github/workflows/cmems-harvest.yml`).
- `uv`: the demo instructions use it (`docs/PROTOTYPE_README.md`). Its presence was not checked here.

Credentials used by the scripts (values never stored in the repository):

| Service | How it is supplied | Used by |
|---|---|---|
| Copernicus Marine | cached `copernicusmarine login`, or the two environment variables above | `harvest_cmems.sh`, `backfill_cur_analysis.py` |
| Kaggle | `KAGGLE_API_TOKEN` environment variable (a `KGAT_`-style API token; export it, never write it into a file), or `~/.kaggle` | `pull_checkpoints.sh`, notebook push (§2.13) |
| Copernicus Marine, inside a Kaggle batch kernel | a private Kaggle dataset, `jiteeshghodke/cmems-creds` (batch kernels pushed from the CLI cannot read Kaggle Secrets) | the training notebook (§2.13) |
| NSIDC NRT, NSIDC CDR, ECMWF open data, USNIC, IBCSO (PANGAEA) | none (public) | `download_nsidc_nrt.py`, `download_nsidc.py`, `harvest_ecmwf_wind.py`, `harvest_usnic.sh`, `subset_bathymetry.py` |

Path-dependent scripts. Several scripts import bare module names
(`from features import ...`, `from ice_quality import ...`) and rely on
`sys.path.insert` lines to find `dakshin/` and `models/iceberg/`. Run them as
`python3 scripts/<name>.py` from the root. Do not import them from another directory.

Two sandbox-specific paths: `scripts/pull_checkpoints.sh` defaults `PY` to
`/home/agent/.venvs/sih-work/bin/python`, and `dakshin/data` is a real directory in
this checkout (not a symlink). Set `PY=` to your own interpreter.

---

## 2. Operations

Each operation gives its purpose, the command, what it produces, how long it takes,
and what can go wrong.

### 2.1 Daily CMEMS forecast harvest (ice, currents, waves, SST)

**Purpose.** Archive today's CMEMS sea-ice forecast cycle, and the matching
currents, waves and surface temperature, before CMEMS overwrites it. The archive is the only source
of forecasts as they were issued; see §3.

**Command (scheduled):** the GitHub workflow `.github/workflows/cmems-harvest.yml`
runs at 12:23, 17:23 and 21:23 UTC, with a manual trigger (`workflow_dispatch`) that
takes an optional `cycle_date`.

**Command (local):**

```
bash scripts/harvest_cmems.sh
```

With `CYCLE_DATE` unset, the cycle date comes from the clock: before 12:00 UTC
the cycle is yesterday's date, after that it is today's. Setting `CYCLE_DATE=YYYY-MM-DD`
is a deliberate back-fill. A back-filled date is the analysis for that day, not the
forecast that was issued, and the length check is skipped.

**Environment variables (all optional):**

| Variable | Default | Effect |
|---|---|---|
| `ARCHIVE_DIR` | `data/cmems_forecast_archive` | Where files are written |
| `LOG_FILE` | `data/cmems_harvest.log` | Appended to, and echoed to stdout |
| `MIN_LON`, `MAX_LON` | `0`, `80` | Corridor longitude box |
| `MIN_LAT`, `MAX_LAT` | `-78`, `-55` | Corridor latitude box |
| `CYCLE_DATE` | blank (clock) | Cycle date to fetch |
| `EXPECTED_DAYS` | `10` | Daily steps a real cycle must have (date plus nine days) |
| `GITHUB_OUTPUT` | unset locally | If set, the script writes `cycle=` and `status=` for the workflow |

**Outputs.** In `data/cmems_forecast_archive/`:

- `cmems_siconc_<cycle>.nc`: dataset `cmems_mod_glo_phy_anfc_0.083deg_P1D-m`, variables
  `siconc`, `sithick`, `usi`, `vsi`, 10 daily steps. Compressed to about 5 MB from 42.6 MB.
- `cmems_cur_<cycle>.nc`: dataset `cmems_mod_glo_phy-cur_anfc_0.083deg_P1D-m`, `uo`, `vo` (m/s) for the top
  model level (0 to 1 m), 10 daily steps.
- `cmems_wav_<cycle>.nc`: dataset `cmems_mod_glo_wav_anfc_0.083deg_PT3H-i`, `VHM0` and `VMDR` (3-hourly) reduced by
  `scripts/reduce_wav_daily.py` to a daily maximum, `VHM0_dmax`, with the wave
  direction at the peak (commit `e0ee2b2`). `VHM0_dmax` is the variable downstream code reads.
- `cmems_sst_<cycle>.nc`: dataset `cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m`, `thetao` for the top level
  (0 to 1 m), same box and window. Read by `scripts/berg_melt.py`.
- Lines appended to `data/cmems_harvest.log`.

**Currents, waves and SST exist for one cycle only.** They have been saved since 2026-11-21, and the archive
holds exactly one of each, for 2026-11-21 (`ls data/cmems_forecast_archive | grep -v siconc`). Cycles before that have ice only.
The harvest tries all three on every run, including an `already_have` run (the last log lines on 2026-11-22
01:23 UTC are three "already have ... skipping" entries).

The script ends with a status line in `GITHUB_OUTPUT`:

| Status | Meaning | Exit code |
|---|---|---|
| `saved` | ice cycle downloaded and length-checked | 0 |
| `already_have` | the cycle file already exists; currents, waves and SST are still tried | 0 |
| `not_published` | the server still held the previous day's forecast (step count wrong); nothing saved. Currents, waves and SST are not tried | 0 |

Any other failure (login, network) exits non-zero. Currents, waves and SST never fail the
run: they log a warning and the ice cycle is kept.

**Time.** Not recorded. The workflow job has a 25-minute timeout
(`timeout-minutes: 25`).

**What can go wrong.**

- A run before 12:00 UTC files the previous day's forecast under today's name. The
  clock rule and the step-count check (`EXPECTED_DAYS`) are the guards. Four archived
  files got through before those guards existed; see `data/cmems_forecast_archive/KNOWN_STALE.md`.
- The guard is clock-based, not data-based. The backlog's critical item is to derive
  the date from the dataset's time axis (`docs/backlog.md`, `[critical][data]`). Not built.
- A missed bulletin cannot be recovered. CMEMS overwrites each cycle with the next.
- Login: the workflow retries three times, 30 seconds apart. Locally, a stale credential
  fails with a login error.
- The step-count (stale-cycle) check covers the ice, currents and waves files. The SST function in the script has
  no such check, so a clock-dated SST file could be a stale copy that nothing rejects (read from `harvest_sst`;
  not observed).
- The workflow commits the archive and pushes to `main` as `cmems-harvest-bot`, with three
  rebase-and-retry attempts. A local run does not push; the files stay in the working tree.
- Compression: `scripts/compress_netcdf.py` int16-packs `siconc`, `sithick`, `usi`, `vsi` and, now, `uo` and `vo`
  (`PACK_RANGE`, ±3 m/s). A failed compression keeps the uncompressed file and logs a warning.

### 2.2 The workflow itself

**Purpose.** Run §2.1 at fixed times on GitHub's infrastructure, so it does not depend on
a laptop being on.

**Command.** Triggered by the schedule in `.github/workflows/cmems-harvest.yml`. Manually,
from the GitHub Actions page (the `workflow_dispatch` input `cycle_date`), or with
`gh workflow run cmems-harvest.yml -f cycle_date=YYYY-MM-DD` if `gh` is authenticated (standard `gh` syntax; not run).

**Behaviour recorded in the workflow's comments.**

- Cron slots are never on the hour, and never before 12:00 UTC.
- The second and third slots are cheap: `harvest_cmems.sh` exits early when the cycle is on disk.
- A "verify" step fails the run if the ice file is under 1 MB (a truncated download).
- Scheduled runs were four to five hours late on three consecutive days in the first week.

**Other steps in the same workflow.** `.github/workflows/` still contains only this one workflow. After the
harvest step it now also runs, each with `continue-on-error: true` so a failure cannot cost the day's ice cycle:

- `Harvest ECMWF wind`: `pip install ecmwf-opendata cfgrib xarray netCDF4 numpy`, then
  `python scripts/harvest_ecmwf_wind.py --out data/ecmwf_wind` (§2.4). It runs on all three cron slots.
- `Weekly USNIC iceberg list (Fridays)`: runs `bash scripts/harvest_usnic.sh` when `date -u +%u` is 5, otherwise prints
  "not Friday, skipping" (§2.5).

The commit step stages `data/cmems_forecast_archive`, `data/cmems_harvest.log`, `data/ecmwf_wind` and
`data/icebergs/archive`. It does **not** stage `data/nsidc_nrt` or `data/cmems_cur_analysis`, so the NSIDC NRT
download (§2.3) and the analysis-currents back-fill (§2.15) are manual.

### 2.3 NSIDC near-real-time sea-ice truth

**Purpose.** Download the observed sea-ice concentration that the real-forecast hindcast scores
against. NSIDC keeps this stream for about three months, and it publishes about one day late, so
the newest day available is roughly yesterday (`scripts/stale_history_eval.py` docstring). On 2026-11-22
about 05:00 UTC the newest local file is 2026-11-20.

**Command.**

```
python3 scripts/download_nsidc_nrt.py --start 2026-08-24 --end 2026-11-21 --out data/nsidc_nrt
```

Defaults: `--start 2026-08-24`, `--end` today, `--out data/nsidc_nrt`.

**Outputs.** `data/nsidc_nrt/sic_pss25_<YYYYMMDD>_am2_icdr_v04r00.nc` (NOAA/NSIDC G10016 v4,
south, daily), plus `MANIFEST.sha256` listing every file fetched and the count of failures.
Checked 2026-11-22: the folder holds 89 `.nc` files from 2026-08-24 to 2026-11-20, plus `MANIFEST.sha256`, 35 MB.

**Output lines.** One line per day, `ok   <name> already have` or `ok   <name> <n> bytes`, or `FAIL <name> <error>`;
at the end `<N> files in manifest; <F> failed`. **Not re-run** (it needs the network).

**Behaviour.** The script skips a file whose destination exists and is non-empty, so
re-running is cheap. It records each file's SHA-256 in the manifest. Exit code is 1 if any day failed.
There is no retry and no `.part` file in this script: a failed day writes nothing and is simply tried
again on the next run. (The 3-try retry with `.part` files lives in `dakshin/download_nsidc.py`, and in the
Kaggle notebook's NSIDC cell, §2.13.)

**Time.** Not recorded. The downloads are about 0.4 MB each.

**What can go wrong.**

- The NRT stream is kept for about three months (`git show 5f32ae3` commit message). Days older
  than that are gone from NSIDC. The earliest local file, 2026-08-24, reaches three months old
  on or about 2026-11-24. Files the repository does not already hold cannot be fetched after that.
- The folder is now **tracked in git** (90 files including the manifest; `.gitignore` no longer lists it),
  and the local `origin/main` tracking ref was level with `main` on 2026-11-22. So there is a second copy,
  if the push reached GitHub. Pushing it is the only protection against the roll-off.
- `--end` defaults to today. Because of the one-day lag, today (and possibly yesterday) will usually print
  `FAIL` and give exit code 1 even though everything older was fetched. Read the failed names, not the exit code.
  That the newest days fail is inferred from the lag, not observed in this pass.

### 2.4 ECMWF 10 m wind forecast

**Purpose.** Daily wind forecast for the weather gate and the iceberg wind term (slice 6).

**Command.**

```
python3 scripts/harvest_ecmwf_wind.py --out data/ecmwf_wind
```

**Outputs.** `data/ecmwf_wind/ecmwf_wind_<YYYY-MM-DD>_<HH>z.nc`: 10u and 10v at steps 0 to 240 h
(6-hourly), cropped to 0 to 80 E, 55 to 78 S, from the latest 00z or 12z IFS run. Two files exist
(2026-11-21 00z and 2026-11-21 12z, 6.5 MB together). The script header says the required attribution, "Contains modified ECMWF open
data (CC BY 4.0), https://www.ecmwf.int/en/forecasts/datasets/open-data", is written into the file attributes.

**Time.** Not recorded.

**What can go wrong.** ECMWF open data keeps only the last 12 runs, two to three days. A missed day
is unrecoverable. The workflow runs the script on every cron slot (§2.2), non-fatally; a local run is only for a missed
day. The script requires `ecmwf-opendata`, which is installed in `sih-work` only (the workflow installs it with pip). Open-Meteo is the documented fallback,
but its free tier is non-commercial, so it is not used in outputs (`ATTRIBUTION.md`).

**Current wiring.** The real-route run reads the wind through `dakshin/real_world.py`
(`WIND_DIR = data/ecmwf_wind`, file `ecmwf_wind_<cycle>_00z.nc`, used if present). The iceberg code does
not: `scripts/berg_hindcast.py`, `scripts/berg_tracks.py` and `dakshin/berg_forecast.py` use zero wind. Only the
`<cycle>_00z` file is read by `RealWorld`; the 12z file is archived but unused.

### 2.5 USNIC weekly Antarctic iceberg list

**Purpose.** The weekly list of giant-iceberg positions, used for validation and for the
iceberg forecast's starting positions.

**Command.**

```
bash scripts/harvest_usnic.sh
```

**Outputs.** `data/icebergs/archive/AntarcticIcebergs_<YYYYMMDD>.csv`, named by the newest
"Last Update" date in the file. Idempotent: re-running on the same issue overwrites the identical file.
The archive holds 14 weekly issues, from `AntarcticIcebergs_20260820.csv` to `AntarcticIcebergs_20261120.csv`.

**Time.** Not recorded (one HTTP GET).

**What can go wrong.** The script fails with "unexpected USNIC payload" if the response does not start
with the expected header. Only the current issue is served by USNIC, so older issues came from the
USNIC archive (commit `fd4eba6`). Whether USNIC keeps those archive files was not verified here.
The workflow runs the script on Fridays only (§2.2), non-fatally; run it by hand if a Friday run is missed.

### 2.6 Real-forecast hindcast (CMEMS forecast against NSIDC truth)

**Purpose.** The honest test: score the raw operational forecast, persistence and the U-Net correction on real
satellite truth, at each lead, in the corridor.

**Commands.** Both overwrite the committed JSON (see the top of this file). Neither was re-run in this pass.

With the trained correction (the default). Needs the four checkpoints and `SHA256SUMS` in
`models/sic_correction/checkpoints/`, which are present and checksum-clean in this checkout (§2.12):

```
python3 scripts/realforecast_hindcast.py
```

Baselines only (`cmems` and `persistence`, no `unet`). This replaces the committed U-Net results with a
`"model": null` file, so use it only with a different output in mind:

```
python3 scripts/realforecast_hindcast.py --no-model
```

`--help` (run in this pass) prints `usage: realforecast_hindcast.py [-h] [--no-model]` and the one option,
`--no-model  baselines only (checkpoints not yet on disk)`.

**Inputs.** Forecast cycles from `data/cmems_forecast_archive/` (the four stale cycles listed in
`KNOWN_STALE.md` are excluded), truth from `data/nsidc_nrt/`, and the corridor box 0 to 80 E, 55 to 78 S.

**Output.** One line on stdout, `wrote <root>/dakshin/figures/realforecast_hindcast.json`, exit code 0.
The JSON is overwritten. Each lead has `n_cycles`,
`first_cycle`, `last_cycle`, pooled RMSE, and mean IIEE at the 15% threshold, each for `cmems`
and `persistence` (and `unet` with the model). The committed file (generated 2026-11-21 23:13 UTC) has
`"model": "re-run 2026-11-21 of the 2026-08-31 Kaggle training ..."`. Its values:

| Lead | `n_cycles` (first to last cycle) | RMSE cmems / persistence / unet | IIEE km² cmems / persistence / unet |
|---|---|---|---|
| 1 | 77 (2026-08-31 to 2026-11-19) | 0.10219 / 0.11914 / 0.0914 | 196031 / 186997 / 93231 |
| 3 | 75 (to 2026-11-16) | 0.10479 / 0.14391 / 0.08741 | 194575 / 277167 / 142467 |
| 5 | 74 (to 2026-11-15) | 0.10981 / 0.15508 / 0.0946 | 200203 / 319189 / 182601 |
| 7 | 72 (to 2026-11-13) | 0.1153 / 0.16414 / 0.10245 | 210200 / 353255 / 221094 |

At lead 7 the U-Net has the lower RMSE but a higher IIEE than raw CMEMS (221094 against 210200 km²).

**Cycle counts.** 83 siconc files from 2026-08-31 to 2026-11-21, less the 4 stale cycles, less the
cycles without truth `lead` days later (the NRT truth ends 2026-11-20, so for lead 1 the last usable cycle is 2026-11-19).
That gives 77 at lead 1, 75 at lead 3, 74 at lead 5, 72 at lead 7. These counts reconcile with the JSON. (The
2026-11-21 version of this file said 76 at lead 1 and 2026-11-18 as the last cycle; the committed JSON has 77 and
2026-11-19.)

**Time.** Not recorded. It runs on CPU torch.

**What can go wrong.**

- Re-running after new cycles or new NRT days arrive changes the numbers, and the script's
  docstring forbids re-tuning on this set. Record the run date with any number you quote. The JSON
  does not record its input file list, so a later reader cannot tell which cycles were used except
  by counting. The truth switches sensor on 2025-01-01 (AMSR2 for F17 SSMIS), which the JSON notes.
- Missing checkpoint: `FileNotFoundError: ... missing -- pull it from the Kaggle run`. Missing `SHA256SUMS`:
  `FileNotFoundError ... refusing to load unverified weights`. A changed file:
  `ValueError: checksum mismatch for <name>` (from `dakshin/model_io.py`, §2.12).
- The model is applied with the information a forecaster would have on day t (`build_channels_operational`). The
  scoring still assumes the day-t satellite file is in hand on day t, which is false for the live cycle; §2.6b measures that.

### 2.6a Corrected forecast (apply the U-Net to a real cycle, check the approach decision)

**Purpose.** Apply the released checkpoints to the newest archived cycle that has a full 7-day satellite
history, and ask whether the correction changes the Bharati approach decision. With `--all`, do it for every usable
cycle and score each lead's decision against the satellite on the target date.

**Commands.** Needs the checkpoints (§2.12), `data/cmems_forecast_archive/`, and `data/nsidc_nrt/`. Run from `sih-work`.
Not re-run in this pass. The cycle argument and `--all` are mutually exclusive (`--all` is only recognised as the
first argument).

```
python3 scripts/corrected_forecast.py                 # newest usable cycle
python3 scripts/corrected_forecast.py 2026-11-20      # one named cycle (YYYY-MM-DD)
python3 scripts/corrected_forecast.py --all           # every usable cycle, then the newest one again
```

A cycle is usable when the NRT satellite files for the cycle date and the six days before it all exist (`N_HISTORY` = 7).
Today the newest is 2026-11-20, because the 2026-11-21 satellite file is not published yet; there are 78 usable cycles,
2026-08-31 to 2026-11-20 (`corrected_all.json`).

**Outputs** (all in `dakshin/figures/`, overwritten):

- `corrected_forecast.npz`: `lat`, `lon`, and `raw_lead{1,3,5,7}` and `corrected_lead{1,3,5,7}` on the 25 km NSIDC grid.
  1.1 MB. `corrected_forecast.json`: the approach decision for that cycle (`cycle`, `satellite_day0_reachable`,
  `ai_changed_reachability`, and per lead `station_reachable.{raw,corrected}` and `mean_abs_correction`).
- With `--all` also `corrected_all.npz` (2.0 MB; keys `c<YYYYMMDD>_l<lead>`, uint8 `sic*200`, 255 = no data) and
  `corrected_all.json` (`encoding`, `ice_limit`, `verification`, and `cycles`, one block per cycle). `--all` writes the
  `corrected_forecast.*` pair as well, for the newest cycle.

**Expected output** (printed lines, from the code; the values are those in the committed JSON written 2026-11-22 04:18 UTC):

```
lead 1 (2026-11-21): station reachable raw True corrected False (limit 0.8)
lead 3 (2026-11-23): station reachable raw True corrected False (limit 0.8)
lead 5 (2026-11-25): station reachable raw True corrected False (limit 0.8)
lead 7 (2026-11-27): station reachable raw True corrected False (limit 0.8)
wrote <root>/dakshin/figures/corrected_forecast.json and <root>/dakshin/figures/corrected_forecast.npz (1.1 MB); satellite day-0 reachable: False, AI changed reachability: True
```

With `--all`, one `<date>: done` line per cycle comes first, and then
`wrote .../corrected_all.json and .../corrected_all.npz (2.0 MB, 78 cycles); decision verification raw 287/298 corrected 298/298`.
In the committed `corrected_all.json`: 298 verifiable decisions, raw 287 correct, corrected 298, persistence 298. The record's own caveat
says the station never changed state inside a lead window this season, so it separates the corrected field from raw CMEMS and
not from persistence. The mean absolute correction per lead is 0.0629, 0.0636, 0.0578, 0.0592 (leads 1, 3, 5, 7).

**What "reachable" means.** Any cell within 50 km of Bharati that is 4-connected, through cells at or under the 80% ice
limit, to open water 400 or more km away. Depth blocking is not applied. The 4-connected rule is stricter than the router's
8-neighbourhood, so it errs toward "not reachable" (stated in the function's docstring).

**Time.** Not recorded.

**What can go wrong.**

- `no cycle with a full 7-day satellite history` and exit code 1, when the named date is not usable (for 2026-11-21 today).
- A date that is not `YYYY-MM-DD` raises `ValueError`. `--help` does the same (observed: `Invalid isoformat string: '--help'`).
- Missing or altered checkpoints raise the `model_io` errors listed in §2.6.
- The corrected field is a 25 km correction to the forecast, not a higher-resolution product (the JSON says so).
- Running without `--all` after a `--all` run replaces `corrected_forecast.*` but leaves `corrected_all.*` as it was.

### 2.6b Stale-history evaluation (cost of the one-day satellite lag)

**Purpose.** The live cycle never has a day-0 satellite file (NRT is about a day late), so an AI correction for the live
cycle would run on history ending at day-1. This scores the correction with history `obs[t-0..t-6]` (fresh, the hindcast's
setting) against `obs[t-1..t-7]` (stale, the live setting), on the same cycles and the same mask.

**Command.** No arguments, and no `--help`. Not re-run in this pass.

```
python3 scripts/stale_history_eval.py
```

**Output.** `dakshin/figures/stale_history_eval.json`, overwritten (written 2026-11-22 04:31 UTC in the committed copy). Per lead:
`n_cycles`, `rmse` and `iiee_km2_mean` for `cmems`, `fresh` and `stale`. Committed values:

| Lead | n_cycles | RMSE cmems / fresh / stale | IIEE km² cmems / fresh / stale |
|---|---|---|---|
| 1 | 77 | 0.10219 / 0.0914 / 0.10763 | 196031 / 93231 / 139334 |
| 3 | 75 | 0.10479 / 0.08741 / 0.09388 | 194575 / 142467 / 159967 |
| 5 | 74 | 0.10981 / 0.0946 / 0.09715 | 200203 / 182601 / 190084 |
| 7 | 72 | 0.11530 / 0.10245 / 0.10383 | 210200 / 221094 / 225790 |

At lead 1 the stale RMSE (0.10763) is worse than raw CMEMS (0.10219): the correction's lead-1 edge does not survive the lag.
`docs/CURRENT_STATE.md` records the decision that follows (no live-cycle AI edge on day-1 history). The `cmems` and `fresh`
columns equal the hindcast's `cmems` and `unet` columns, which is a consistency check between the two scripts.

**Time.** Not recorded. An accidental start in this pass had not finished after 120 s before it was stopped, so allow several minutes.

**What can go wrong.** Same checkpoint errors as §2.6. Re-running after new NRT days changes the numbers, as in §2.6.

### 2.7 Resolution study (does ocean-model resolution change the answer?)

**Purpose.** Coarsen the same CMEMS cycles to about 1/4° and 1°, and score each against the same
truth (RESOLUTION_STUDY.md, F1).

**Command.** With the model (the default; checkpoints are present). Not re-run in this pass:

```
python3 scripts/resolution_study.py
```

`--no-model` skips the U-Net and overwrites the committed JSON without it (see the top of this file). `--help` (run) prints
`usage: resolution_study.py [-h] [--no-model]`.

**Outputs.** `dakshin/figures/resolution_study.json` and `dakshin/figures/resolution_study.png`,
both overwritten. Stdout: `wrote <root>/dakshin/figures/resolution_study.json`, then `wrote .../resolution_study.png`.
The JSON has one block per resolution under `resolutions` (`1/12°`, `1/4°`, `1°`), each with the lead-by-lead values from §2.6.
The committed JSON includes the `unet` columns. Lead 1 as committed: raw CMEMS RMSE 0.10219 (1/12°), 0.10055 (1/4°), 0.10419 (1°);
IIEE 196031, 190714, 204367 km²; U-Net RMSE 0.0914, 0.0914, 0.09183 and IIEE 93231, 93287, 97792 km².

**Time.** Not recorded.

**What can go wrong.** The study coarsens one model's output. It does not run a coarser model
(the JSON's own caveat). Without the checkpoints and `SHA256SUMS` the default run fails with the `model_io` errors from §2.6.

### 2.8 Iceberg hindcast, resolution study and melt estimate

These three scripts share the iceberg forecast code (`dakshin/berg_forecast.py`, `models/iceberg/drift.py`).

**2.8a Hindcast against USNIC positions.**

```
python3 scripts/berg_hindcast.py
```

- Inputs: CMEMS analysis currents in `data/cmems_cur_analysis/` (82 daily files, 2026-08-31 to 2026-11-20), and
  the USNIC archive in `data/icebergs/archive/`.
- Output: `dakshin/figures/berg_hindcast.json` (committed copy written 2026-11-21 19:16 UTC). The file records 88 segments, 81 usable, the split into
  stationary (68) and moving (13, persistence displacement above 3 km), median and mean errors (model 4.35 and 5.06 km/day,
  persistence 0.0 and 0.43), and the uncertainty radius (4.35 km/day). The `v2_grounding` block is the grounding-aware
  model: an assumed keel draught of 208 m, 26 segments held as grounded and 62 free-drifting, median error over all segments
  4.13 km/day; on the free-drifting ones, model 4.45 and persistence 0.0 km/day.
- Wind: zero in `dakshin/berg_forecast.py`. The JSON now says this is a stated limitation (measured wind-forcing ratio R has
  median 0.25 and max 1.73), not "slice 6 pending". `scripts/berg_hindcast.py` does not read `data/ecmwf_wind/`.
- Not re-run in this pass. Time: not recorded.

**2.8b Resolution of the currents.**

```
python3 scripts/berg_resolution.py
```

- Output: `dakshin/figures/berg_resolution.json`, with the currents at 1/12°, 1/4° and 1°.
- The usable-segment counts differ between rows (81, 86, 88). Medians are over different subsets.
- Time: not recorded.

**2.8c Freshwater (melt) estimate.**

```
python3 scripts/berg_melt.py 2026-11-21
```

- Optional argument: the cycle date, `YYYY-MM-DD`. Inputs for that cycle: `cmems_cur_<cycle>.nc`,
  `cmems_sst_<cycle>.nc`, `cmems_wav_<cycle>.nc`, and a USNIC issue. The committed JSON names
  `AntarcticIcebergs_20261120.csv`, which is in the archive.
- Output: `dakshin/figures/berg_melt.json`, labelled "ESTIMATE" in its `label` field (committed copy: cycle 2026-11-21).
- **Provenance gap closed.** `scripts/harvest_cmems.sh` now produces `cmems_sst_<cycle>.nc` (§2.1). The practical limit
  is that the archive holds currents, waves and SST for 2026-11-21 only, so that is the only cycle this script can run on today.
  The cycle argument is optional, and the script defaults to the fixed date 2026-11-21, not to the latest cycle. Not re-run.
- Time: not recorded.

**2.8d Forecast drift tracks for the chart.**

```
python3 scripts/berg_tracks.py [2026-11-21]
```

- For each USNIC giant inside the corridor box, in the newest `data/icebergs/archive/AntarcticIcebergs_*.csv`, integrates 0 to 9 days
  on the cycle's forecast currents (`cmems_cur_<cycle>.nc`, grounding-aware, zero wind) and writes daily positions and the net
  drift vector. A berg grounded at its start keeps a zero vector.
- Output: `dakshin/figures/berg_tracks.json` (committed copy: cycle 2026-11-21, 8 tracks, written 2026-11-21 19:00 UTC). The default
  cycle in the source is 2026-11-21, a fixed date. Only that cycle has a currents file. **Not run.** Time: not recorded.
- Its own `validation` note: persistence beats the model on the 2026 sample, so the arrows are advisory.

### 2.9 Real-route run and weather gate

```
python3 scripts/real_route_run.py 2026-11-21
```

- Argument: the cycle date. Optional, but when omitted the script uses the fixed date 2026-11-21, not the latest cycle.
  The script routes the unmodified Dijkstra router (`dakshin/sim/router.py`)
  on the real GLO12 ice, CMEMS waves and ECMWF wind for that cycle, on the corridor segment south of 55 S.
  It blocks land and depth using the IBCSO subset.
- Inputs: the cycle's ice, currents and waves in `data/cmems_forecast_archive/`, wind in
  `data/ecmwf_wind/ecmwf_wind_<cycle>_00z.nc`, and `data/bathymetry/ibcso_v2_corridor_0p05.nc`. Only the 2026-11-21 cycle has
  currents and waves, so only that cycle can be routed today.
- Output: `dakshin/figures/real_route.json` (overwritten) and the same JSON printed to stdout, exit code 0. If no route exists the script
  prints `no route found`, writes `{"cycle", "route": null, "reason"}`, and exits 1.
- Not re-run in this pass. The committed `real_route.json` was regenerated on 2026-11-22 04:13 UTC, after the router change
  `478ecd2`, so the old warning that it predated that change no longer applies. Its values for cycle 2026-11-21:

| Field | Committed value |
|---|---|
| `approach_closed_at_ice_limit` | `false` |
| `closest_approach_km` | `null` (only filled when the approach is closed) |
| `eta_days`, `n_legs` | 5.55, 45 |
| `worst_ice`, `worst_hs_m`, `worst_wind_ms` | 0.723, 4.77, 14.9 |
| `weather_gate.state` | `FAIL`: waves 4.77 m exceed the assumed 3.0 m limit; wind 14.9 m/s in Beaufort 7; visibility not assessed |
| `route_ends_km_from_station` | 50.6 |
| `corrected_ice_check` | `{"skipped": "newest corrected cycle (2026-11-20) has no archived wave file ..."}` |

**New fields.**

- `route_ends_km_from_station`: distance from the last leg of the track to Bharati, always reported. Since the router's
  one-lattice-cell arrival rule (`478ecd2`), `solve()` succeeds once the ship is within one lattice diagonal of a station
  that is ashore, so `approach_closed_at_ice_limit: false` does not mean the ship reaches the station. Read this field with it.
- `lattice_note`: fixed text. The router lattice is 0.55 by 0.9 degrees over native 1/12° fields and cannot resolve the final
  50 km or so; the 25 km reachability check in `corrected_forecast.json` (§2.6a) covers the approach.
- `corrected_ice_check`: only written when `corrected_forecast.npz` and `corrected_forecast.json` exist. It takes the cycle from
  `corrected_forecast.json` (`cycle`, currently 2026-11-20) and routes the same vessel on raw and on U-Net-corrected ice for it
  (`CorrectedIceWorld` adds the corrected-minus-raw difference at the nearest 25 km cell and lead). **Skip condition:** that cycle's
  world must have a wave file, because the router needs waves. If it does not, the field holds `{"skipped": "..."}` as above. The check
  therefore runs only for a cycle that has **both** a correction (a `corrected_forecast.py <cycle>` run, which needs that cycle's NRT
  satellite history, §2.6a) and a wave file in the archive. Today the only wave file is 2026-11-21 and the newest correction is
  2026-11-20, so the check is skipped until the 2026-11-21 NRT file is downloaded and `corrected_forecast.py 2026-11-21` is run.
  When it runs, it holds `cycle`, `raw` and `corrected` blocks (`arrived_within_lattice_rule`, `closest_approach_km`,
  `eta_days`, `worst_ice`, `route_ends_km_from_station`) and a `note`.
- Time: not recorded.
- What can go wrong: the gate limits (3.0 m waves, Beaufort 7 and 8 wind thresholds) are assumptions,
  not the hull's PWOM. The 80% ice limit is a stand-in. The run covers only the segment south of 55 S.

### 2.10 Claim verification

```
python3 scripts/verify_claims.py
```

- Read-only. It opens files under `dakshin/figures/` and prints a pass or fail line for each claim.
  Point it at another checkout with `DAKSHIN_ROOT=/path/to/checkout`.
- Output on 2026-11-22, run in this pass (`python -I scripts/verify_claims.py` in `sih-work`): last two lines `PASSED 29` and
  `All claims verified against source files.` (Same result as on 2026-11-21.)
- The earlier caveat about the 8.6-day transit check is resolved: the check now tests `transit days (rounded)` = 8.7 against a
  depth-aware `route_regret.json` (re-run 2026-11-21), and `docs/TRUE_CLAIMS.md` §1.11 gives 8.7 days (8.66), a steaming-time lower bound.
- Time: not recorded.
- What it does not check: claims that are not written as a check (anything not in its list).

### 2.11 Test suite

```
/home/agent/.venvs/sih-work/bin/python -m pytest dakshin models -q -p no:cacheprovider
```

`dakshin/demo/` is inside `dakshin/`, so this one command also runs the demo tests (no separate demo venv is needed in this sandbox).

- Measured 2026-11-22 on `sih-work`: **209 passed, 2 skipped, 1 warning in 26.31 s.** `pytest --collect-only -q` reports
  `209 tests collected`. The skip reasons (`-rs`): `dakshin/demo/test_bridge_ui.py:41` "playwright not installed", and
  `dakshin/test_protected_areas.py:32` "ATS shapefile absent -- run dakshin/download_protected_areas.py". The warning is a
  Starlette deprecation notice about `httpx`.
- The `model_io` tests are no longer skipped: the checkpoints are in the repository. The earlier "194 passed, 7 skipped" and
  "186 passed, 7 skipped" in `docs/CURRENT_STATE.md` are older counts.
- `-p no:cacheprovider` stops pytest writing `.pytest_cache`.
- If you do build a demo venv (§2.14), the command from `docs/PROTOTYPE_README.md` is `.venv-demo/bin/python -m pytest dakshin/demo -q`;
  that venv does not exist here, so this was not run.

### 2.12 The trained model: checkpoints, release `model-v0.1`, loader, and re-pull

**Purpose.** The four trained checkpoints (one U-Net per lead of 1, 3, 5 and 7 days) are now in the repository and in a
GitHub release. This entry says how to check them, load them, restore them, and, only if you mean to, replace them.

**State, checked 2026-11-22.**

- `models/sic_correction/checkpoints/` is tracked in git and holds `isih_prototype_lead{1,3,5,7}.pt` (7,763,017 bytes each),
  `SHA256SUMS` (360 bytes), and the training run's `isih_skill_by_lead.csv`, `isih_skill_curve.png`, `demo_comparison.png`.
  (The `isih_` prefix is the pre-rename artifact id, kept on purpose.)
- GitHub release **`model-v0.1`** on `jiteeshghodke456-del/dakshin`, published 2026-11-21 23:16:58 UTC, with five assets: the four `.pt`
  files and `SHA256SUMS` (`gh release view model-v0.1 --json tagName,assets,publishedAt`, a read-only metadata call made in this pass).
- `models/sic_correction/` in git also holds `unet.py`; the checkpoints use the prototype config, not the `unet.py` defaults.

**Check the checksums (read-only; run in this pass).**

```
cd models/sic_correction/checkpoints && sha256sum -c SHA256SUMS
```

Expected output, one line per file:

```
isih_prototype_lead1.pt: OK
isih_prototype_lead3.pt: OK
isih_prototype_lead5.pt: OK
isih_prototype_lead7.pt: OK
```

**Load a checkpoint in code.** `dakshin/model_io.py` exposes `LEADS = (1, 3, 5, 7)`, `checkpoint_path(lead)`, `verify_checksum(path)` and
`load_checkpoint(lead)`. `load_checkpoint` builds `SICCorrectionUNet(in_channels=12, base_filters=32, depth=3)`, verifies the file's
SHA-256 against `SHA256SUMS` **before** loading, loads the weights on CPU (`weights_only=True`), and returns the model in `eval()` mode.
Run in this pass from the repository root:

```
/home/agent/.venvs/sih-work/bin/python -I -c "import sys; sys.path.insert(0,'.'); from dakshin.model_io import load_checkpoint, LEADS; [print(L, type(load_checkpoint(L)).__name__) for L in LEADS]"
```

Each lead loads a `SICCorrectionUNet` with 1,929,601 parameters, `training` False. The test `dakshin/test_model_io.py` checks the parameter
count and a forward pass on a 1 by 12 by 332 by 316 input, per lead; it is skipped only when `SHA256SUMS` is absent. Failure modes of the loader:
`ValueError: lead must be one of (1, 3, 5, 7)`; `FileNotFoundError` when a `.pt` or `SHA256SUMS` is missing ("refusing to load unverified weights");
`ValueError: <name> not listed in ...SHA256SUMS`; `ValueError: checksum mismatch for <name>: expected ..., got ...`.

**Restore the checkpoints if they are missing.** Download the five release assets into the checkpoint folder and run the checksum command
above. Standard `gh` syntax, **not run**: `gh release download model-v0.1 -D models/sic_correction/checkpoints`.

**Re-pull from Kaggle (replaces the released model; do this only on purpose).**

```
KAGGLE_API_TOKEN=<token> PY=/path/to/python bash scripts/pull_checkpoints.sh
```

The script (unchanged apart from being used; **not run**):

1. `kaggle kernels output jiteeshghodke/notebookd39fdf7959 -p models/sic_correction/checkpoints` (the kernel slug is hard-coded in
   the script; `docs/CURRENT_STATE.md` also names a later reproducibility kernel, `dakshin-prototype-train-gpu2`, which this script does not pull).
2. Checks for `isih_prototype_lead{1,3,5,7}.pt`; prints `MISSING lead N` and exits 1 if one is absent.
3. Writes `SHA256SUMS` (`sha256sum`) and prints it.
4. Runs `pytest dakshin/test_model_io.py -q`, then `scripts/realforecast_hindcast.py` and `scripts/resolution_study.py`, both **with** the model.

It ends by printing the manual steps (update the results documents, commit the checkpoints, `gh release create model-v0.1 ...`). Those steps
were done for the first release on 2026-11-21; a second `gh release create model-v0.1` would collide with the existing tag, so a new model needs a new tag (not tried).

**Failure modes of the re-pull.**

- It overwrites the checkpoints, `SHA256SUMS`, and (through step 4) `realforecast_hindcast.json` and `resolution_study.json`. The
  new files will not match the release assets or the committed skill table. `docs/CURRENT_STATE.md` records that a GPU rerun reproduced
  lead-1 held-out RMSE to 3e-5 (0.04649 against the released 0.04646) while leads 3 to 7 spread by up to 0.012, from GPU nondeterminism. A
  re-pull is a different model, not the same one.
- A kernel that is not `COMPLETE` gives the MISSING line. For an errored kernel: `kaggle kernels logs <owner>/<slug>`.
- `kaggle` must be on `PATH` (§1); with `set -euo pipefail` any failed step stops the script. Network is needed. Time: not recorded.

### 2.13 Training notebook (regenerate, push, recipe)

**Regenerate** the notebook from the repository sources (not run in this pass):

```
python3 dakshin/kaggle/make_notebook.py
```

It writes `dakshin/kaggle/isih_train.ipynb` (the script's `OUT`). The embedded modules are `models/sic_correction/unet.py`,
`dakshin/grid.py` and `dakshin/features.py`; the generated notebook says to edit those sources, never the notebook. Training scope: NSIDC
G02202 v6 truth and GLORYS12 background for 2019 and 2020, leads 1, 3, 5, 7, `SICCorrectionUNet(in_channels=12, base_filters=32, depth=3)`,
60 epochs with patience 12.

**Push** with the Kaggle CLI (version 2.2.4 has `kaggle kernels push -p FOLDER [-t TIMEOUT] [--accelerator ACC]`, checked with `-h`).
The folder must hold the notebook and a `kernel-metadata.json`. Neither the metadata file nor the push command is stored in the repository;
the slug and settings used before are not recorded here. Authentication is the `KAGGLE_API_TOKEN` environment variable
(§1; export it for the shell, never put the value in a file or a command that is logged).

**Recipe: what had to be true for the kernel to complete** (from `docs/CURRENT_STATE.md`, the notebook source, and the owner's notes;
the Kaggle runs themselves were not repeated in this pass):

1. **Credentials.** A batch kernel pushed from the CLI cannot read Kaggle Secrets. The CMEMS login is supplied through a private Kaggle
   dataset (`jiteeshghodke/cmems-creds`) attached to the kernel. **Gap in the repository:** `make_notebook.py` still generates the cell that
   reads `CMEMS_USERNAME` and `CMEMS_PASSWORD` from Kaggle Secrets (lines 107 to 117), and does not contain the dataset-reading cell. The
   pushed kernel used a different credentials cell, which is not in the repository. The dataset's file layout is not recorded either.
2. **Dataset mount path.** A **new** kernel mounts attached datasets at `/kaggle/input/datasets/<owner>/<slug>/`; a **legacy** kernel mounts them
   at `/kaggle/input/<slug>/`. Code that reads the credentials dataset must handle the path the kernel actually has. `docs/CURRENT_STATE.md` says the
   glob fix for this is in `make_notebook.py` (commit `0848d7e`); the file contains no `/kaggle/input` string, so that claim could not be confirmed
   in this checkout (the message of commit `0848d7e` names only the NSIDC retry).
3. **numpy pin.** The install cell is `pip install -q copernicusmarine pyproj xarray netCDF4 "numpy==$(python -c 'import numpy; print(numpy.__version__)')"`.
   Pinning numpy to the image's own version inside the same `pip install` stops pip upgrading it half-way, which broke scipy on import
   (kernel v7 died this way; fixed in `d7b0d0f`).
4. **NSIDC download retries.** The notebook's NSIDC cell downloads each file to a `.part` name, renames it on success, and tries up to 3 times,
   sleeping 15 s and then 30 s between tries (a transient NSIDC HTTP 500 killed a run on 2026-11-22, fixed in `0848d7e`).
   `dakshin/download_nsidc.py` does the same with `retries=3` and a 1 s then 2 s backoff. `scripts/download_nsidc_nrt.py` has no retry (§2.3).
5. **Cell type.** The training cell must be a code cell. The first saved kernel had it as markdown, so no checkpoints were ever written to
   Kaggle's output (fixed in v6).
6. **Switches.** Internet on, GPU on (T4 x2). Budget roughly 15 to 25 minutes per lead on a T4, and about 1 to 2 hours for the whole notebook
   (`docs/PROTOTYPE_RESULTS.md`, "Reproducing"). Without a GPU the notebook warns it is about 20 times slower; a CPU re-run was on pace to hit Kaggle's 12 hour limit during lead 1 and was discarded (`docs/CURRENT_STATE.md`).

**Time.** About 1 to 2 hours on Kaggle (above). v8 completed on 2026-11-21 at 22:51 UTC and produced the released checkpoints.
The 20-minute no-background ablation is a separate run described in `docs/PROTOTYPE_RESULTS.md`.

### 2.14 Demo application

The demo needs `fastapi`, `uvicorn`, `xarray`, `h5netcdf` and the rest of `dakshin/demo/requirements.txt`. The documented route (`docs/PROTOTYPE_README.md`):

```
uv venv .venv-demo --python 3.12
uv pip install --python .venv-demo/bin/python -r dakshin/demo/requirements.txt
.venv-demo/bin/uvicorn dakshin.demo.app:app --port 8000
```

`.venv-demo` does not exist in this checkout, and `uv` was not checked. The same app imports and answers in `sih-work` (below), so in this
sandbox the equivalent start command is:

```
/home/agent/.venvs/sih-work/bin/uvicorn dakshin.demo.app:app --port 8000
```

That `uvicorn` entry point was not started in this pass (no server was run). Before starting it, the demo needs the data it reads, which is
`dakshin/data/nsidc_sic/` (the 1,096 NSIDC training-era files, §3; present here). The app's `data.preflight()` refuses to start when it is missing,
and its message names the folder. To expose it from the sandbox, publish the port from the host (`sbx ports <sandbox-name> --publish 8000:8000/tcp`).

**`GET /api/model`: the model card.** Added in `dakshin/demo/app.py` (`model()`); `dakshin/demo/data.py` `model_card()` builds it from release artifacts only,
and its only inputs are the checkpoint folder's `SHA256SUMS` and `isih_skill_by_lead.csv` and `dakshin/figures/corrected_all.json`. It returns HTTP 404, "model checkpoints not present in this checkout", if
`SHA256SUMS` or `isih_skill_by_lead.csv` is missing. Run in this pass through the app's in-process test client (`TestClient(app).get('/api/model')`):

- status 200; keys `name`, `release`, `checkpoints`, `held_out_skill`, `source`, `decision_verification`;
- `release` is `model-v0.1`; `checkpoints` has 4 entries (`file`, first 12 characters of the SHA-256, size in MB);
- `held_out_skill` has one row per lead (`lead`, `model_rmse`, `persistence_rmse`, `gain_pct`); lead 1 is 0.0465 against persistence 0.057, gain 18.5%.
  These are the training run's held-out numbers read from `isih_skill_by_lead.csv`, not the 2026 hindcast;
- `decision_verification` is the `verification` block of `corrected_all.json`: 298 decisions, raw 287, corrected 298, persistence 298, with its caveat.

The result is cached for the life of the process (`lru_cache`), so it does not change until the app restarts.

- Serves committed outputs from `dakshin/figures/` and simulated fields from `dakshin/sim/`. The
  backlog records that the page still labels the synthetic fields as "replay", which is an open item
  (`docs/backlog.md`, world model section). Until it is fixed, say "simulated" aloud.
- Boot time: 3.5 to 3.8 seconds (four runs in the sandbox, 2026-09-07, `docs/backlog.md`). Not re-measured.
- A live re-route is documented as needing a Python 3.11 PolarRoute environment (`prenv`). It is a backlog item.

### 2.15 Other scripts

Not run in this pass. Each entry gives the purpose and the header's stated output.

| Script | Purpose (from its header) | Output | Notes |
|---|---|---|---|
| `scripts/backfill_cur_analysis.py` | Back-fill the daily analysis currents | `data/cmems_cur_analysis/` (default `--start 2026-08-31 --end 2026-11-20`) | Uses the `copernicusmarine` package. The analysis is not the forecast as issued. |
| `scripts/subset_bathymetry.py` | Cut bathymetry to the corridor at 0.05°, on the whole sim box (lat 78 S to 30 S, lon 0 to 90 E). IBCSO v2 south of 50 S; GEBCO_2020 north of 50 S | `data/bathymetry/ibcso_v2_corridor_0p05.nc` (3.5 MB, in git) | Rewritten in `24317da`. IBCSO raw (254 MB) comes from the PANGAEA URL in its header into `data/bathymetry/raw/` (gitignored). GEBCO comes from NOAA CoastWatch ERDDAP. The shallowest-cell buffer is one box, about 5 km. Not run in this pass. |
| `scripts/compress_netcdf.py <file> [--lossless] [--keep-original]` | Pack a NetCDF; int16 with scale factors for the ice variables (`PACK_RANGE`) | the file, unless `--keep-original` is given (flag name; not read in full) | Called after each harvest download. `PACK_RANGE` now includes `uo` and `vo` (±3 m/s), so currents are int16-packed too. (An older backlog note and a comment in `harvest_cmems.sh` still say they are not; the table in the script is current.) |
| `scripts/reduce_wav_daily.py <file>` | Reduce 3-hourly waves to a daily maximum (`VHM0_dmax`) | the file (inferred from the harvest's use; not read) | Called by the harvest. |
| `dakshin/download_nsidc.py` | Training truth: NSIDC G02202 v6, south, daily F17 SSMIS, 2018 to 2020 | `dakshin/data/nsidc_sic/` (1,096 files) | Public, no auth. Gitignored. The URL base is `noaadata.apps.nsidc.org/NOAA/G02202_V6/south/daily`. Each file is fetched to a `.part` name and renamed, with `retries=3` (1 s then 2 s backoff). |
| `dakshin/route_regret.py` | Route-regret experiment, static versus daily plans | route and regret JSON | `docs/backlog.md` cites a `--depart` option for per-date sweeps. Flag not checked here. |
| `dakshin/make_route_figure.py` | Route figure with PolarRoute | `dakshin/figures/route_map.png` | Needs the PolarRoute venv (`prenv`). |
| `dakshin/audit_ice_quality.py` | Land-spillover and hard-zero audit | the committed `dakshin/figures/ice_quality_audit.json` (writer path not checked) | Defines the 17 by 17 cell box (`APPROACH_RADIUS_CELLS = 8`). |
| `dakshin/destination_window.py` | Bharati and Maitri open or closed by day | the committed `dakshin/figures/destination_window.json` (writer path not checked) | 80% limit; Maitri's offload point is unknown (backlog). |
| `scripts/score_cmems_archive.py` | Score CMEMS against its own later day-0 field | — | **Do not quote.** The backlog flags this scorer as flattering CMEMS. |
| `models/iceberg/regime_report.py` | Drift regime on the USNIC catalogue | `models/iceberg/regime_report.json` | The backlog cites its 10 m/s and 30 m/s wind cases. |
| `dakshin/mlflow_backfill.py` | MLflow backfill | `mlruns/` (gitignored) | Purpose taken from its name and `docs/MLFLOW_SETUP.md`; not read in full. |
| `scripts/gen_*_drawio.py` | Generate the decision-flow and gate diagrams | `docs/*.drawio` | Documentation only. |

---

## 3. Data inventory

Sizes and counts re-measured 2026-11-22 (`du -sh`, `ls`, `git ls-files`).

| Path | Contents and naming | Size | In git | Can it be regenerated? |
|---|---|---|---|---|
| `data/cmems_forecast_archive/` | 83 `cmems_siconc_<cycle>.nc` (2026-08-31 to 2026-11-21), 1 `cmems_cur_<cycle>.nc`, 1 `cmems_wav_<cycle>.nc`, 1 `cmems_sst_<cycle>.nc` (all three for 2026-11-21 only), `KNOWN_STALE.md` | 522 MB | yes (87 files) | **No, for the forecasts.** CMEMS overwrites each cycle with the next, so the forecast as issued cannot be fetched again. The repository's git history is a second copy, if the pushes succeeded. Check `git log origin/main` before relying on it. |
| `data/cmems_cur_analysis/` | 82 `cmems_cur_analysis_<date>.nc`, 2026-08-31 to 2026-11-20 (analysis currents, not forecasts) | 81 MB | yes (82) | Yes, for past analysis dates (`backfill_cur_analysis.py`), while CMEMS serves them. |
| `data/nsidc_nrt/` | 89 `sic_pss25_<YYYYMMDD>_am2_icdr_v04r00.nc` (2026-08-24 to 2026-11-20), `MANIFEST.sha256` | 35 MB | yes (90 files with the manifest; no longer gitignored) | **Only while NSIDC keeps it, about three months.** The earliest file reaches that age around 2026-11-24. The git copy is now the only durable one once NSIDC drops it, so make sure it is pushed. The workflow does not stage this folder (§2.2), so new days are added by hand and committed by hand. |
| `data/ecmwf_wind/` | `ecmwf_wind_<date>_<HH>z.nc`, two files (2026-11-21 00z and 12z) | 6.5 MB | yes (2) | **No, after 2 to 3 days.** ECMWF open data keeps the last 12 runs. Missed days are gone. |
| `data/icebergs/archive/` | `AntarcticIcebergs_<YYYYMMDD>.csv`, 14 weekly USNIC issues | 60 KB | yes | Current issue: yes (`harvest_usnic.sh`). Older issues: from the USNIC archive, whether still served was not verified. |
| `data/icebergs/usnic_antarctic_20260902.csv` | A copy of an archived issue (backlog says byte-identical to the 2026-08-27 issue) | not measured | yes | Yes, by deletion of the duplicate. Not verified in this pass. |
| `data/bathymetry/ibcso_v2_corridor_0p05.nc` | Corridor subset, 960 by 1800 cells at 0.05°, variables `elevation` (block maximum, negative is water depth, zero or positive is land or ice shelf) and `elevation_mean` (display only) | 3.4 MB | yes (1) | Yes, from the raw file with `subset_bathymetry.py`. |
| `data/bathymetry/raw/IBCSO_v2_ice-surface_WGS84.nc` | Full IBCSO v2 ice-surface grid. **Absent**: the whole `data/bathymetry/raw/` directory is missing (checked 2026-11-22). It was present at 18:11 on 2026-11-21 and went missing in the minute `24317da` (which rewrote the subset script) landed; the cause is not established. | 254 MB when present | no (gitignored) | Yes, from PANGAEA (`subset_bathymetry.py` header). The subset itself is in git and does not depend on it. |
| `data/cmems_harvest.log` | Appended log of every harvest run | 76 KB | yes | It is the record. Keep it. |
| `dakshin/data/nsidc_sic/` | 1,096 `sic_pss25_<YYYYMMDD>_F17_v06r00.nc` (2018 to 2020, CDR v6, F17 SSMIS) | 403 MB | no (gitignored) | Yes, from NSIDC G02202 v6 (`dakshin/download_nsidc.py`). The demo needs it (`docs/backlog.md`, `[BLOCKER][demo]`). |
| `dakshin/figures/` | JSON and PNG outputs of the scripts in §2, plus `sic_points.csv` and `waypoints.csv` | 25 tracked files (25 on disk), now including `corrected_forecast.{npz,json}`, `corrected_all.{npz,json}`, `stale_history_eval.json` and `berg_tracks.json` | yes | Yes, by re-running the scripts, but a re-run is a new score (top of this file). The committed JSON is the number that was quoted. |
| `models/sic_correction/` | `unet.py`; `checkpoints/` with `isih_prototype_lead{1,3,5,7}.pt` (7.76 MB each), `SHA256SUMS`, `isih_skill_by_lead.csv`, `isih_skill_curve.png`, `demo_comparison.png` | 30 MB (checkpoints folder, `ls`) | yes | Restore from release `model-v0.1` (§2.12); retraining gives a different model. |
| `models/iceberg/` | `drift.py`, `melt.py`, `catalogue.py`, `regime_report.py`, the JSON, and tests | — | yes | Code. |
| `dakshin/kaggle/` | `make_notebook.py`, `isih_train.ipynb` | — | yes | Code. The notebook is regenerated from the sources (§2.13). |

Naming conventions in use. CMEMS files are named by the cycle (issue) date. NSIDC files by the observation
date. USNIC by the newest "Last Update" date in the issue. Figures by the script that writes them.
Checkpoints by the lead in days (`isih_prototype_lead1.pt`); the `isih_` prefix is the pre-rename name and
is kept on purpose (`pull_checkpoints.sh`, `dakshin/model_io.py`).

Irreplaceable, in order of urgency:

1. **`data/nsidc_nrt/`**: rolls off NSIDC after about three months. In git now (verify the push).
2. **`data/cmems_forecast_archive/` forecasts**: CMEMS overwrites them. In git only if pushed.
3. **`data/ecmwf_wind/`**: two to three days of retention at ECMWF.
4. **`data/icebergs/archive/`** (older issues): depends on USNIC's archive.

Everything else in this table can be regenerated from one of these or from a public source.

---

## 4. Glossary

"Defined at" gives the file that defines or uses the term in a way that fixes its meaning here.
"Standard usage" means the term is not defined in the repository, and the expansion or meaning is the
usual one in the field.

| Term | Meaning | Source |
|---|---|---|
| **SIC** | Sea-ice concentration, a fraction (0 to 1) or a percentage, depending on the product | Standard usage; used in `dakshin/features.py` |
| **IIEE** | Integrated ice-edge error: the area (km²) where the 15% ice-extent masks of forecast and truth disagree (exclusive OR, times 625 km² per cell) | Defined at `dakshin/features.py` `iiee_km2`; cites Goessling et al. 2016 |
| **RMSE** | Root mean squared error, pooled over cycles and valid cells | Standard usage; `scripts/realforecast_hindcast.py` |
| **CRPS** | Continuous ranked probability score, a proper score for probabilistic forecasts | Standard usage; named in ADR-027 (`docs/DECISIONS.md`); not computed in any file |
| **CDR** | Climate Data Record, the NOAA/NSIDC passive-microwave sea-ice concentration product | Defined at `ATTRIBUTION.md` (NSIDC CDR v6, G02202) |
| **NRT** | Near-real-time: the NSIDC stream kept for about three months | `scripts/download_nsidc_nrt.py` header; `git show 5f32ae3` |
| **ICDR** | Interim CDR, the NRT file-name tag `icdr` | `scripts/download_nsidc_nrt.py` file names; expansion standard |
| **G02202 v6, G10016 v4** | NSIDC product identifiers for the CDR (training) and the NRT stream (truth) | `ATTRIBUTION.md`, `scripts/realforecast_hindcast.py` |
| **NSIDC** | National Snow and Ice Data Center | Standard usage |
| **SSMIS** | Special Sensor Microwave Imager/Sounder, on the DMSP F17 satellite in the training record | Standard usage; `dakshin/figures/realforecast_hindcast.json` caveats |
| **AMSR2** | Advanced Microwave Scanning Radiometer 2, the sensor behind the NRT truth from 2025-01-01 | Standard usage; the JSON caveat |
| **GLO12** | CMEMS global 1/12° ocean analysis and forecast system | Defined at `scripts/harvest_cmems.sh` (dataset `cmems_mod_glo_phy_anfc_0.083deg_P1D-m`) and `ATTRIBUTION.md` |
| **GLORYS12** | CMEMS global 1/12° ocean reanalysis (the training background) | Defined at `ATTRIBUTION.md` (`cmems_mod_glo_phy_my_0.083deg_P1D-m`) |
| **CMEMS** | Copernicus Marine Environment Monitoring Service | `ATTRIBUTION.md` |
| **Cycle** | One daily CMEMS forecast issue, named by its issue date | `scripts/harvest_cmems.sh` comments |
| **Lead, lead time** | Days from the cycle (issue) date to the target date. Leads 1, 3, 5 and 7 are scored | `dakshin/features.py` (`build_channels`); `docs/PROTOTYPE_RESULTS.md` |
| **Analysis vs forecast** | The analysis is the best estimate for a past date, which CMEMS still serves. The forecast is what was issued on a given day, and CMEMS overwrites it | `scripts/harvest_cmems.sh` comments; `docs/PROTOTYPE_RESULTS.md` |
| **Stale cycle** | A file under a date whose content is the previous day's forecast, with the first day cut off | `data/cmems_forecast_archive/KNOWN_STALE.md` |
| **Persistence** | The baseline that carries the last observation forward unchanged | `scripts/realforecast_hindcast.py` docstring. The prototype's persistence is the same idea (`isih/RESULTS.md` in `27308ff`); ADR-006 names a damped anomaly version, which was demoted |
| **Raw CMEMS** | The operational forecast used without correction. ADR-027's mandatory baseline | `docs/DECISIONS.md` ADR-027 |
| **Innovation channel** | Background minus the newest observation at each cell, the signal that tells the model how wrong the background is now | `dakshin/features.py`, channel 8 |
| **Double penalty** | RMSE charges a sharp forecast twice for a misplaced edge (a miss and a false alarm) and a smoothed one once | `docs/RESOLUTION_STUDY.md` |
| **VHM0** | Spectral significant wave height (CMEMS wave variable) | `dakshin/real_world.py` docstring; `scripts/harvest_cmems.sh` |
| **VHM0_dmax** | Daily maximum of VHM0, the variable the router uses | `scripts/reduce_wav_daily.py` output; `dakshin/real_world.py` |
| **VMDR** | Mean wave direction (CMEMS wave variable) | `scripts/harvest_cmems.sh` |
| **Hs** | Significant wave height, in metres | `models/iceberg/melt.py` header |
| **siconc, sithick, usi, vsi** | CMEMS ice variables: concentration, thickness, and the two velocity components | `scripts/harvest_cmems.sh` `VARIABLES` |
| **uo, vo** | Eastward and northward surface current (m/s) | `scripts/harvest_cmems.sh` comments |
| **thetao** | Sea-water potential temperature (the SST input to melt) | `scripts/berg_melt.py` |
| **EPSG:3412** | NSIDC south polar stereographic projection, the 25 km grid | `dakshin/build_dataset.py` (grid label) |
| **IBCSO** | International Bathymetric Chart of the Southern Ocean, version 2; the ice-surface grid is used | `ATTRIBUTION.md`; `scripts/subset_bathymetry.py` header |
| **GEBCO** | General Bathymetric Chart of the Oceans; the north of 50 S in the subset | `scripts/subset_bathymetry.py` header; ADR-026 |
| **TID** | GEBCO type indicator: measured or predicted depth | ADR-026 (`docs/DECISIONS.md`) |
| **ENC** | Electronic navigational chart, the official chart the chart gate needs before it can pass | `dakshin/gates.py` `chart_gate`; `docs/TRUE_CLAIMS.md` §1.17 |
| **ECDIS** | Electronic chart display and information system | `docs/backlog.md` (MSC.232(82)) |
| **QA flag** | The CDR's `cdr_seaice_conc_qa_flag` bit field | `dakshin/ice_quality.py` |
| **Land spillover filter** | CDR filter that writes 0.0 for coastal cells whose footprint overlaps land. QA flag value 4 (`docs/PROTOTYPE_RESULTS.md` calls this "bit 4") | `dakshin/ice_quality.py` docstring and `QA_LAND_SPILLOVER = 4` |
| **Invalid ice mask** | CDR QA flag value 16 | `dakshin/ice_quality.py` (`QA_INVALID_ICE_MASK = 16`) |
| **No input data** | CDR cell with no retrieval input | `dakshin/ice_quality.py` |
| **Grounded or unknown** | Iceberg track state when a forecast step lands on a NaN current (land or outside the data) | `dakshin/berg_forecast.py` |
| **USNIC** | U.S. National Ice Center, source of the weekly Antarctic iceberg list | `ATTRIBUTION.md` |
| **WDE17** | Wagner, Dell and Eisenman 2017, the closed-form iceberg drift model used | `ATTRIBUTION.md`; `models/iceberg/drift.py` |
| **RK2** | Second-order midpoint (Runge-Kutta) integration of berg position | `dakshin/berg_forecast.py` |
| **R (wind forcing)** | Ratio of wind-driven to current-driven drift, per segment, at an assumed 10 m/s wind | `dakshin/berg_forecast.py`; `berg_hindcast.json` |
| **ADE, FDE** | Average and final displacement error, as used in the IDRIFTNET paper; the horizon is not stated there | `docs/backlog.md`; `docs/ICEBERG_RESEARCH.md` |
| **Keghouche et al. 2010** | The melt-term set (basal, buoyant convection, wave erosion) used for freshwater, Arctic-calibrated | `models/iceberg/melt.py` header |
| **Freshwater estimate** | Melt volume per day along a track, an estimate (`berg_melt.json` label) | `scripts/berg_melt.py` |
| **PolarRoute** | British Antarctic Survey routing engine (MIT) that the project wraps | `ATTRIBUTION.md`; ADR-009 |
| **meshiphi** | British Antarctic Survey mesh and ice-physics package used with PolarRoute | `ATTRIBUTION.md`; ADR-013 |
| **excluded_zones** | PolarRoute's vessel-config hook that marks mesh cells inaccessible | ADR-010 (`docs/DECISIONS.md`) |
| **Dijkstra** | Shortest-path search used by the project's router | `dakshin/sim/router.py`; `scripts/real_route_run.py` |
| **POLARIS** | The IMO polar operational limit assessment and risk indexing system (MSC.1/Circ.1519). Its expansion is standard; the repository does not expand it | `docs/backlog.md`; `docs/TRUE_CLAIMS.md` §4 |
| **RIO, RIV** | Risk index outcome, and risk index value per ice class (POLARIS) | `docs/backlog.md` (`RIO = Σ(Ci × RIVi)`) |
| **WMO egg code** | The World Meteorological Organization sea-ice code (stage of development, concentration, form) | `docs/backlog.md` |
| **ULA** | Old Russian ice-class notation for the vessel's class | `docs/PROTOTYPE_RESULTS.md` §5 |
| **MIZ** | Marginal ice zone | `docs/DECISIONS.md` ADR-020; standard usage |
| **Gate states (PASS, MARGINAL, FAIL, UNKNOWN)** | The four outcomes of each decision gate. UNKNOWN names the dataset that would settle it | `dakshin/gates.py` |
| **Conformal prediction (split, stratified)** | A calibration method that gives a coverage guarantee from held-out residuals. Designed for the uncertainty layer | ADR-020 (`docs/DECISIONS.md`) |
| **Ensemble** | Several models whose disagreement is used as uncertainty | ADR-004, ADR-005 |
| **Route regret** | Extra time (or fuel) from planning on stale ice, compared with planning on the day's ice | `docs/PROTOTYPE_RESULTS.md` §3 |
| **STATIC, STATIC-noQA, DAILY** | The three route arms in the regret experiment: planned once on departure ice; the same with spillover cells trusted; re-planned each morning | `docs/PROTOTYPE_RESULTS.md` §3 |
| **Dominance filter** | Removing any route that another route beats on every objective | ADR-021 |
| **Time-expanded graph** | A routing graph with one ice layer per forecast day, so a forecast can change the route | `docs/TRUE_CLAIMS.md` §5 |
| **ASPA, ASMA** | Antarctic Specially Protected Area and Antarctic Specially Managed Area, under the Antarctic Treaty | `dakshin/protected_areas.py`; `docs/backlog.md` |
| **MARPOL Annex I, Reg. 43** | Ban on heavy fuel oil south of 60 S (the reason the vessel runs marine diesel) | `docs/backlog.md` |
| **MV Vasiliy Golovnin** | The chartered vessel the project is calibrated to | `docs/PROTOTYPE_RESULTS.md` §5 |
| **Bharati, Maitri** | Indian Antarctic stations; Bharati is the resupply destination | `docs/PROTOTYPE_RESULTS.md` |
| **ISEA** | The Indian Scientific Expedition to Antarctica series | Standard usage; `docs/PROTOTYPE_RESULTS.md` |
| **NCPOR** | National Centre for Polar and Ocean Research | Standard usage; `docs/backlog.md` |
| **ISIH** | The pre-rename prefix of the prototype (the package was renamed to `dakshin`; file names keep `isih_`) | `docs/CURRENT_STATE.md`; `docs/backlog.md` |
| **Kernel** | A Kaggle notebook run, identified by its owner and slug | `docs/CURRENT_STATE.md` |
| **NEMO, ANHA** | The NEMO ocean model, and the ANHA family of regional NEMO configurations | `docs/RESOLUTION_STUDY.md` |
| **OSI SAF** | Ocean and Sea Ice Satellite Application Facility (ice drift and ice products) | `docs/backlog.md` |
| **ERA5, IFS** | ECMWF's reanalysis and its Integrated Forecasting System | `scripts/harvest_ecmwf_wind.py` header; ATTRIBUTION |
| **AIS** | Automatic Identification System, ship position broadcasts; the Southern Ocean has very little shore-side coverage | `dakshin/ais_feed.py`; `docs/backlog.md` |
| **Beaufort** | Wind-force scale; the weather gate uses Beaufort 7 and 8 thresholds | `dakshin/gates.py` (`WIND_FAIL_MS`, `WIND_MARGINAL_MS`) |
| **USNIC catalogue, "Last Update"** | Weekly list of giant bergs; the newest date in the file names the archive copy | `scripts/harvest_usnic.sh` |
| **Stage A, Stage B** | Stage A is training on the reanalysis; Stage B is fine-tuning and acceptance on the real forecast archive | `docs/DECISIONS.md` ADR-019 |
| **NMEA** | National Marine Electronics Association sentence format for ship instruments and AIS | Standard usage; `dakshin/ais_feed.py` |
| **AIVDM** | The AIS message sentence type used for ship position reports | Standard usage; `dakshin/ais_feed.py` |
| **PC1 to PC7** | IACS Polar Class notations; `dakshin/polaris.py` has the PC table (`CLASSES`) used for the POLARIS speed caps | `dakshin/polaris.py` line 45 |
| **OOW** | Officer of the watch | Standard usage; used in `dakshin/test_workflow.py` and `dakshin/demo/test_app.py` |
| **NM** | Nautical mile; the traffic gate uses 2 and 5 NM bands | `dakshin/gates.py` (`TRAFFIC_FAIL_NM`, `TRAFFIC_MARGINAL_NM`) |
| **ETA** | Estimated time of arrival, in days from departure in the real-route output | `dakshin/figures/real_route.json` (`eta_days`); `dakshin/alternatives.py` |
| **ACC** | Antarctic Circumpolar Current | Standard usage |
| **UKC** | Under-keel clearance, the depth margin above the draught | `docs/DECISIONS.md` ADR-026 |
| **GBM** | Gradient-boosted machine, the planned iceberg residual model (stretch goal) | `docs/DECISIONS.md` ADR-008 |
| **LUT** | Lookup table (the literature thickness and density table) | `docs/DECISIONS.md` ADR-013 |
| **AOI** | Area of interest (the corridor box as a configuration input) | `docs/backlog.md`, configuration requirement |
| **GAMMA, C_A, C_W** | WDE17 drift coefficients: gamma from the air and water drag coefficients (`C_A` = 1.3, `C_W` = 0.9) | `models/iceberg/drift.py` |
| **MATLAB reference code** | The author's reference implementation of WDE17, used to settle the drag-coefficient swap | `docs/backlog.md` (`[resolved][ml]`) |
| **REPLAY, SIMULATED** | Provenance labels on the demo's fields. The backlog records that the synthetic fields still say REPLAY | `dakshin/demo/static/provenance.js`; `docs/backlog.md` |
| **CMIP-style names** | Variable and coordinate naming conventions that the NEMO reader accepts | `dakshin/readers/nemo.py` (F2) |
| **model-v0.1** | The GitHub release holding the four trained checkpoints and `SHA256SUMS` (2026-11-21) | §2.12; `dakshin/demo/data.py` (`"release"`) |
| **Fresh vs stale history** | Satellite history ending at day 0 (the hindcast's setting) against ending at day-1 (the live cycle, since NRT is about a day late) | `scripts/stale_history_eval.py` docstring |
| **Station reachable** | Some cell within 50 km of Bharati is 4-connected, through cells at or under the 80% ice limit, to open water 400 km or more away; depth blocking not applied | `scripts/corrected_forecast.py` (`reachable`) |
| **Lattice arrival rule** | The router reports success once the ship is within one 0.55 by 0.9 degree lattice cell of a station ashore, so a found route can still end tens of km short (`route_ends_km_from_station`) | `scripts/real_route_run.py`; router commit `478ecd2` |
| **ADR** | Architecture decision record in `docs/DECISIONS.md` | — |
| **Claims ledger** | `docs/TRUE_CLAIMS.md`, each claim with its evidence file | — |
