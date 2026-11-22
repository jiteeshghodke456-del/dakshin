# Dakshin: evolution, findings, and what is still open

Scope: the project from the first commit (2026-08-31, `0020fba`) to HEAD
`779cf83` (2026-11-22 05:12 UTC): the night build of 2026-11-21 and the morning
of 2026-11-22. 382 commits on `main` in that window (`git rev-list --count HEAD`),
172 of them daily CMEMS harvest commits (subject "CMEMS harvest"). The first
study pass read the repository on 2026-11-21 (snapshot paragraph below). The
2026-11-22 update, which covers `44e3efa..HEAD` (46 commits, 4 of them harvest),
adds stages 6 to 11 (Section 1), findings 2l to 2q (Section 2), Section 3 and 4
rows, Appendix A items 29 to 41 and Appendix D. Every
number below comes from a file in this repository; the path is cited next to
it. Three labels are used throughout:

- **Measured**: a number in a file under `dakshin/figures/` or a log, produced
  by a script in `scripts/` or `dakshin/`.
- **Designed**: specified in `docs/DECISIONS.md` or a design doc, with no run
  behind it yet.
- **Claimed**: written in a narrative doc but not traced to a measured file.

Where the repository disagrees with itself, the disagreement is listed in
Appendix A rather than resolved here. Read Appendix A before quoting any
figure from the docs.

---

**Snapshot.** The repository was read between about 17:56 and 18:21 UTC on 2026-11-21. "In this pass" means the study pass that wrote this file. Commits and uncommitted edits by other agents that landed or appeared later are listed in Appendix C. **Update pass (2026-11-22):** read against HEAD `0cda289`, then re-checked against `ad97f88` (05:04 UTC, a claims-review commit) and `779cf83` (05:12 UTC, the Kaggle batch recipe and refreshed runbook and physics volumes), both by other agents and both landed while this pass was running; they already correct some mismatches below, and each affected item says so. Sections 1, 2l to 2q, 3, 4 and Appendices A, B, D carry the new material; where a 2026-11-21 statement is now false it carries an inline "Superseded" or "Committed update" note rather than being rewritten, so the earlier state stays readable. Times in stages 6 to 11 are UTC unless marked IST (UTC+5:30).

## 1. Stage timeline

Commit dates are from `git log --reverse --format='%h %ad %s' --date=short`.
Commit counts per month at HEAD (`TZ=UTC git log --format=%ad --date=format-local:%Y-%m`):
August (31st only) 27, September 158, October 71, November 126; total 382, of
which 172 are daily CMEMS harvest commits. The first pass's monthly counts
(30, 155, 72, 75 of 332) do not reproduce (Appendix A item 38).

| Stage | Dates | What was built | Motivating question |
|---|---|---|---|
| 0. Scoping and first prototype | 2026-08-31 | Phase 1 research and architecture (`0020fba`); daily CMEMS harvest and GitHub Actions cron (`3d95515`, `ac4ccda`); Kaggle training notebook generated from repo sources (`c802288`); NSIDC truth downloader (`5ba8d30`); GLORYS12 to NSIDC regridding (`1c23670`); bias-correction U-Net (`698e827`); reframed as lead-time forecasting with baselines (`90fe99e`); multi-lead results and reanalysis-leakage ablation recorded (`27308ff`, `98c5e8c`); first route computation (`e165f79`) | Can a learned correction beat the baselines that matter for Antarctic sea-ice concentration at 1 to 7 days? And what data can never be recovered once it is missed? |
| 1. Data verification and first physical checks | 2026-09-01 to 09-04 | Research on the POLARIS framework and PolarRoute gaps (`8e3d6bd`); ice-data QC and the destination-window result (`73b0e44`); Wagner-Dell-Eisenman drift model (`16cef7c`), USNIC catalogue loader (`2fbf084`), drift regime measurement on real USNIC data (`6fc7034`); TRUE_CLAIMS ledger and verifier (`c5b5af4`); harvest compression from 42.6 to about 5 MB per day (`f2de08e`); first local demo (`4add2cd`) | Does the satellite record agree with itself at the destination? Is the drift model right on real icebergs? |
| 2. Audit and withdrawals | 2026-09-03 to 09-08 | Harvest made to fail loudly (`3f9f9a2`); claims withdrawn or corrected (`320cb17`, `fb20a3e`, `a2ab4c9`); protected areas modelled (`641e20f`); adversarial audit passes A to AT (`d71d67f` through `ecc82e0`); bridge console, live time-aware router, synthetic world model for the demo (`82242d3`, `97fd814`, `00f3c78`); one land mask shared by bergs, wind and router (`7288d80`) | Which of our own claims would not survive a reviewer? |
| 3. Archive growth | 2026-09-09 to 11-17 | Daily harvest continues; prompt pack and materials (`f568877`, 10-05); harvest fixes for late and stale bulletins (`1a00b3b`, 11-18) | Can the forecast archive be kept intact while the rest of the system changes? |
| 4. Pre-build measurement | 2026-11-18 to 11-20 | Stale-forecast rejection rule (`1a00b3b`); CMEMS forecasts scored against persistence (`5be27ca`); 13 weekly USNIC issues back-filled (`6d2a212`); login retries (`47e0ce1`) | What does the archive say about skill, before any model is retrained? |
| 5. Night build (2026-11-21) | 2026-11-21 | Seven slices (1, 2, 4, 5, 6, 7, 8), resolution studies F1 to F4, licence and claims verifier (slice 11), package rename to `dakshin` | Each slice answers one question: model loading (1), real-forecast skill (2), currents in the harvest (4), iceberg drift on real currents (5), real wind and waves (6), real bathymetry (7), AIS decoding (8), and the resolution, melt and rename work |
| 6. Kaggle training saga, completed (2l) | 2026-11-21 to 11-22 | Original 2026-08-31 checkpoints found unretrievable (training cell saved as markdown); v6 fixed the cell type; v7 died on a pip numpy half-upgrade, pinned in `d7b0d0f`; v8 completed 22:51 UTC; checkpoints and SHA256SUMS committed in `5612621`, Release `model-v0.1`. Reproducibility clone (`dakshin-prototype-train-gpu2`): v1, v2 died on a changed dataset mount layout, v3 on a transient NSIDC HTTP 500 (retry and `.part` files, `0848d7e`), v4 completed | Can the 2026-08-31 numbers be reproduced, and what broke on the way? |
| 7. Model scored once on 2026 real forecasts (2m) | 2026-11-21 ~23:13 to 23:18 UTC | `scripts/realforecast_hindcast.py` and `scripts/resolution_study.py` re-run with the checkpoints (`cf04a4d`); docs folded (`1dc4e95`) | Does the correction beat raw CMEMS on data it never saw, on both RMSE and IIEE? |
| 8. Slice 3 and the season decision record (2n) | 2026-11-21 23:21 (case study); 2026-11-22 04:05 to 04:18 (record) | Reachability flood fill on the 25 km grid, one-cycle case study (`620d3a3`, `a4c37a9`); `corrected_forecast.py --all` over 78 cycles with decisions verified on target dates (`9e332bd`); persistence caveat welded to the headline (`fb246b2`) | Does the AI change the go/no-go decision at the station, and against which baseline? |
| 9. Stale-history experiment (2o) | 2026-11-22 04:29 to 04:41 | `scripts/stale_history_eval.py` (`6dc4719`); verdict and state (`e32332b`, `71a8b08`) | Can the live forecast cycle carry an AI edge when the newest satellite file is a day old? |
| 10. Route honesty (2p) | 2026-11-22 04:15 | `real_route_run.py` reports `route_ends_km_from_station`; `CorrectedIceWorld` wired and gated; "1/12 degree router" overclaim corrected (`0d7be9f`) | What does "the route arrives" mean after the one-lattice-cell rule? |
| 11. Deployment and documentation sweep (2q) | 2026-11-22 04:05 to 04:45 | Demo AI panel from release artifacts (`0c3b9ef`); AI edge on 78 cycles in the companion viewer (site repo, not in this repository); local IEEE-format paper (gitignored); frank capability addendum (`d178f95`); README results rewrite (`0cda289`) | Where does the model honestly appear in the product, and what is the written record of what does and does not work? |

Slice numbers come from the handoff specification that `docs/CURRENT_STATE.md`
and `docs/backlog.md` refer to as HANDOFF_TONIGHT. That file is not in the
repository, so slices 9 and 10 cannot be described from the repository.
Slice 3 can now be described from its commits and figures (stage 8, 2n).
Slice 10 (the site) lives in a separate repository (2q). Note that
`docs/CURRENT_STATE.md` still lists slice 3 under "In flight" below its own
Update 4 (Appendix A item 39).

---

## 2. Findings

Each finding has three parts: the question that was asked, what the data
said, and what changed because of it.

### 2a. The land-spillover QA discovery

**Question.** The satellite record shows open water where there should be
coast. Is that real, and does it change the route?

**What the data said.** The NOAA/NSIDC CDR applies a land-spillover filter to
coastal cells. When it fires, the product writes 0.0 rather than a fill value,
and 0.0 lies inside `valid_range [0, 100]`, so an unguarded reader accepts it
as open water. `dakshin/ice_quality.py` (module docstring) gives the specific
case: on 2019-12-01 the cell at 69.1 S, 75.9 E, about 35 km from Bharati,
reads 0.0 with `cdr_seaice_conc_qa_flag = 4` (`Land_spillover_filter_applied`),
beside cells reading 0.60; three days later the same cell reads 0.90.

Measured over the whole archive (`dakshin/figures/ice_quality_audit.json`,
1,096 daily files, 2018-01-01 to 2020-12-31):

| Measure | Value |
|---|---|
| Days on which the spillover filter fires | 1,096 of 1,096 |
| Cells suppressed per day | mean 118.2, max 488 |
| "Hard zero flush against heavy ice" | 100% of days, mean 14.8, max 87 |
| Worst no-input outage | 59,350 cells in one day |
| Days with suspect cells in the Bharati approach box | 474 (43.2%) |
| Days with suspect cells in the Maitri box | 262 (23.9%) |

The box is `APPROACH_RADIUS_CELLS = 8` in `dakshin/audit_ice_quality.py`: 8
cells in each direction around the station, 17 by 17 cells, about 400 km on a
side. The docs call it "the 200 km box". That is the half-width, not the full
width. The 43.2% and 23.9% figures are unchanged by this, but the phrase
should be corrected before it is quoted.

The consequence for the station (`dakshin/figures/destination_window.json`,
`docs/PROTOTYPE_RESULTS.md` §1 to §2): at the 80% working limit in December
2019, Bharati's cell was closed on 23 of 31 days (74.2%). This is an ice-only
figure. Once depth is in the mesh, the station cell is ashore and is closed on every day
(`docs/backlog.md`, the line added by `13861d9`), so the destination-window run has to be repeated
on depth meshes before the 23-of-31 figure is combined with the bathymetry results (Appendix C). The approach point
100 km north was open on all 31. Eight days read as open at Bharati, and four
of them (2019-12-01, 12-07, 12-08, 12-09) read exactly 0.0 with the QA flag
set. The other four open days (12-21 at 80.0%, and 12-29 to 12-31 at 75 to
79%) are real, but close to the working limit.

The masking moves coastal ice in the safe direction. Mean SIC in the Bharati
200 km box rises from 46.8% to 54.6% on 1 December 2019 and from 62.5% to 65.4%
on 10 December (`docs/PROTOTYPE_RESULTS.md` §2).

**What changed.**

- **Committed update (`1a9ff0b`, after the snapshot).** With depth in the mesh, the committed
  `dakshin/figures/destination_window.json` reports Bharati's station cell closed on **31 of 31** days,
  because the station is ashore in the depth mesh. The 23-of-31 and four-artifact-day results above are
  ice-only and are superseded in HEAD. The 43.2% spillover figure is unchanged, because
  `ice_quality_audit.json` was not part of that commit.
- `dakshin/ice_quality.py` reads the QA flag and sets spillover and no-input
  cells to NaN. The mesh builder drops them, so an unknown coastal cell takes
  its parent cell's value rather than asserting open water.
- Parent-cell fill is not a correct answer, only a less wrong one. On the
  artifact days it gives 30 to 36% where the surrounding pixels read 80 to 95%
  (`docs/PROTOTYPE_RESULTS.md` §2). The backlog records the next step as
  treating these cells as unknown and high-risk (`docs/backlog.md`,
  `[critical][data]`), which is not built.
- The STATIC route arm in the regret experiment arrives on 2019-12-09, which is
  one of the four artifact days. Its 0.03-day "regret" therefore depends on a
  cell the document itself says should not be trusted (`docs/PROTOTYPE_RESULTS.md`
  §6). The arm that trusts spillover cells records 0.00 days.
- **Not fixed:** the prototype's training data. `dakshin/kaggle/make_notebook.py`
  builds its valid mask as `np.isfinite(bg) & np.isfinite(tr)` and does not
  import `ice_quality`. The model was trained with the spillover zeros as
  valid open water at the coast (`docs/backlog.md`, `[major][ml]`).

### 2b. Raw CMEMS beats persistence on real operational forecasts, on RMSE at every lead

**Question.** The prototype was tested against reanalysis background and
persistence. Does the raw operational forecast that the vessel would really
have received beat persistence, on real satellite truth, at the leads a voyage
plans over?

**What the data said.** `dakshin/figures/realforecast_hindcast.json`, written by
`scripts/realforecast_hindcast.py` (`--no-model` run, so the U-Net column is
null). Setup from the JSON: 76 archived CMEMS GLO12 cycles at lead 1 (2026-08-31
to 2026-11-18), 72 at lead 7; truth is NSIDC NRT G10016 v4 (AMSR2, QA-masked);
corridor 0 to 80 E, 55 to 78 S; four stale cycles excluded per
`data/cmems_forecast_archive/KNOWN_STALE.md`.

| Lead (days) | Scored cycles | RMSE raw CMEMS | RMSE persistence | CMEMS RMSE vs persistence | IIEE raw CMEMS (10³ km²) | IIEE persistence (10³ km²) | CMEMS IIEE vs persistence |
|---|---|---|---|---|---|---|---|
| 1 | 76 | 0.10199 | 0.11977 | 14.8% lower | 195.1 | 187.7 | 3.9% higher |
| 3 | 75 | 0.10479 | 0.14391 | 27.2% lower | 194.6 | 277.2 | 29.8% lower |
| 5 | 74 | 0.10981 | 0.15508 | 29.2% lower | 200.2 | 319.2 | 37.3% lower |
| 7 | 72 | 0.11530 | 0.16414 | 29.8% lower | 210.2 | 353.3 | 40.5% lower |

The percentages are computed from the JSON values. IIEE is the mean
ice-edge error at the 15% threshold (see the glossary, Section 4 of the
runbook). The RMSE values match `docs/TRUE_CLAIMS.md` §1.13.

**Committed update (`cf04a4d`, 2026-11-21 23:16 UTC).** The regenerated
`dakshin/figures/realforecast_hindcast.json` has 77 cycles at lead 1, not 76
(cycle 2026-11-19 became scorable): raw CMEMS 0.10219, persistence 0.11914, IIEE
196,031 and 186,997 km². Leads 3, 5, 7 are unchanged. At lead 1 raw CMEMS is
now 14.2% lower than persistence on RMSE and 4.8% higher on IIEE, so the
qualification below is slightly larger. The table above is the 76-cycle value.
The regenerated file also carries the U-Net column (2m).

**The qualification the repo's summary omits.** On RMSE, raw CMEMS beats
persistence at every lead. On IIEE, it does not beat persistence at lead 1: the
edge error of the operational forecast is 3.9% higher than persistence's. The
claim "raw CMEMS beats persistence at every lead" is therefore true for RMSE
only. ADR-027 (`docs/DECISIONS.md`) requires the corrected forecast to beat raw
CMEMS on both IIEE and CRPS at each lead before it is claimed. This table does
not test that rule, because it has no corrected forecast. It does show that raw
CMEMS is itself 3.9% worse than persistence on IIEE at lead 1, so any statement
about lead 1 has to rest on RMSE alone. CRPS is not computed in any file in
`dakshin/figures/`.

**Caveats.** One spring season, about 75 cycles, so the leads are strongly
autocorrelated and no confidence interval has been computed. The truth changes
sensor in the middle of the record: AMSR2 from 2025-01-01, where the training
truth was F17 SSMIS (the JSON's own caveat). Persistence is computed from the
NSIDC observation carried forward (`scripts/realforecast_hindcast.py`
docstring). The reanalysis-based figures in §2g are not comparable with this
table. They use a different region, truth product, period and background.

**What changed.**

- The metric that the mandatory baseline is judged by is now the operational
  forecast, not the reanalysis or the damped persistence (`docs/DECISIONS.md`
  ADR-027, which replaced ADR-006's baseline).
- The earlier scorer, `scripts/score_cmems_archive.py`, compared CMEMS against
  its own later day-0 field, which flatters it (`docs/backlog.md`, `[major][eval]`).
  The git history of that path starts on 2026-11-19 (`5be27ca`), although the
  backlog line that flags it is dated 2026-09-03. The discrepancy is recorded
  in Appendix A.
- The learned correction has not been scored on these cycles. The checkpoints
  are not in the repository (`models/sic_correction/` contains only `unet.py`),
  so the "U-Net" column is pending. `docs/CURRENT_STATE.md` lists the re-run as
  queued on Kaggle. **Superseded:** the checkpoints were committed in `5612621`
  and scored once in `cf04a4d` (2l, 2m).

### 2c. RMSE cannot see model resolution; the ice-edge metric can

**Question.** Does the resolution of the ocean model change the answer a
captain would get? A standard score was the first thing to check.

**What the data said.** `scripts/resolution_study.py` block-averages the same
76 cycles from 1/12° to about 1/4° and about 1°, then scores each against the
same truth on the same cells. `dakshin/figures/resolution_study.json` holds the
numbers.

RMSE, raw CMEMS forecast:

| Lead | 1/12° | 1/4° | 1° | Persistence |
|---|---|---|---|---|
| 1 | 0.10199 | 0.10035 | 0.10402 | 0.11977 |
| 3 | 0.10479 | 0.10314 | 0.10598 | 0.14391 |
| 5 | 0.10981 | 0.10816 | 0.10988 | 0.15508 |
| 7 | 0.11530 | 0.11365 | 0.11417 | 0.16414 |

IIEE at the 15% threshold (10³ km²), with the change against 1/12°:

| Lead | 1/12° | 1/4° | vs 1/12° | 1° | vs 1/12° | Persistence |
|---|---|---|---|---|---|---|
| 1 | 195.1 | 189.7 | -2.8% | 203.3 | +4.2% | 187.7 |
| 3 | 194.6 | 190.3 | -2.2% | 209.3 | +7.6% | 277.2 |
| 5 | 200.2 | 197.7 | -1.3% | 222.7 | +11.2% | 319.2 |
| 7 | 210.2 | 208.3 | -0.9% | 244.2 | +16.2% | 353.3 |

**What it says.** RMSE gets slightly better when the model is coarsened. At 1°
it is worse at leads 1 to 3 and a tie at lead 5, then marginally better than
1/12° at lead 7. IIEE, which measures where the 15% edge sits, gets worse
at 1°, by 4 to 16% growing with lead. Between 1/12° and 1/4° the IIEE
difference is 1 to 3%, and the sign is in favour of 1/4°. The study calls
that difference "indistinguishable" (`docs/RESOLUTION_STUDY.md`). No
confidence interval was computed, so the statement that 1/12° adds nothing
measurable is weaker than the table suggests: the study does not show that the
two are the same, only that this sample cannot tell them apart.

The explanation the document gives for RMSE's blindness is the double-penalty
effect: a sharp forecast that misplaces an edge pays for a miss and a false
alarm, while a smoothed field pays once. That is the standard explanation and
it is consistent with the table, but the study does not include a separate
test of it (for example a displaced-edge synthetic case).

**Caveat stated in the document.** Coarsening one model's output is not the
same as running a coarser model. Block-averaging removes resolved structure but
keeps the eddy-informed physics. A real test needs the same model run at
several resolutions, for example the ANHA configurations (`docs/RESOLUTION_STUDY.md`).
The NEMO-native reader added on the night (`93ff026`, slice F2) is intended
for that. It is "untested on real NEMO output" by its own commit message.

**Pending.** The U-Net columns are pending the checkpoints, as in §2b.
**Superseded:** the U-Net column landed in `cf04a4d` (2m). The same commit
regenerated `resolution_study.json` at 77 cycles for lead 1: raw RMSE 0.10219
(1/12°), 0.10055 (1/4°), 0.10419 (1°); IIEE 196,031, 190,714, 204,367 (1° is
+4.3%, was +4.2%). Leads 3, 5, 7 are unchanged. The tables above are the
76-cycle values, as are the raw columns in `docs/RESOLUTION_STUDY.md`
(Appendix A item 29).

**What changed.** RMSE is no longer used as a resolution criterion anywhere in
the docs. IIEE is the metric the decision layer should use. The 1/12° versus
1/4° question is recorded as an honest null in this sample, not as a result.

### 2d. Corridor giants are grounded; persistence beats the drift model; grounding detection matters more than resolution

**Question.** Can the Wagner-Dell-Eisenman drift model, driven by real currents,
forecast where a giant iceberg will be after a week?

**What the data said.** `scripts/berg_hindcast.py` integrates each USNIC
position fix forward to the next fix on CMEMS analysis currents
(`dakshin/berg_forecast.py`, midpoint RK2, dt = 1 h) and compares the landing
point with where USNIC places the berg. The reference is persistence: the
berg did not move. `dakshin/figures/berg_hindcast.json`:

| Quantity | Model | Persistence |
|---|---|---|
| Segments | 88 total, 81 usable, 7 "grounded or unknown" | |
| Median error, all usable segments | 4.35 km/day | 0.0 km/day |
| Mean error, all usable segments | 5.06 km/day | 0.43 km/day |
| Moving segments (persistence displacement > 3 km; 13 segments, 4 bergs) median | 6.01 km/day | 2.45 km/day |
| Stationary segments (68) median | 4.26 km/day | 0 |

Persistence wins on the stationary sample by construction: a berg that did not
move has zero persistence error. It also wins on the moving sample, at weekly
fix cadence. The JSON records this as the finding: a current-advection model
without grounding detection drifts anchored bergs.

The "grounded" label is an inference, not a bathymetric check. A segment is
classed as stationary when the USNIC displacement is at most 3 km. The "grounded
or unknown" status (7 segments) means only that a forecast step landed on a
NaN current, which is land or outside the data (`dakshin/berg_forecast.py`,
module docstring). Neither test uses IBCSO. The claim "most corridor giants are
grounded" is therefore a behavioural statement that has not been checked
against the seabed at each berg position.

Committed in `1a9ff0b` after the snapshot: `berg_hindcast.json` was regenerated. Its medians and split quoted above (4.35 and 6.01 km/day, 2.45 km/day persistence, 68 and 13 segments) are unchanged in HEAD.

Uncommitted edits in `dakshin/berg_forecast.py` at the snapshot add a `BathymetryGrid`
and an assumed keel draught (0.83 × 250 m, about 207 m) for grounding detection. They are not
part of any committed figure. The same diff changes how `wind_forcing_R` is computed. It does
not change the zero-wind default, as far as the diff shows.

**Resolution of the currents.** `scripts/berg_resolution.py` runs the same
segments on currents block-averaged to 1/4° and 1°
(`dakshin/figures/berg_resolution.json`):

| Currents | Usable segments | Grounded or unknown | Median error, all (km/day) | Median error, moving (km/day) |
|---|---|---|---|---|
| 1/12° | 81 | 7 | 4.35 | 6.01 |
| 1/4° | 86 | 2 | 4.07 | 5.93 |
| 1° | 88 | 0 | 3.49 | 5.06 |

Coarser currents give lower error, which is the opposite of the naive
expectation. The explanation the study gives: blurring the currents suppresses
the velocity at anchored bergs, so the forecast moves toward "does not move",
which happens to be right for this sample. The usable-segment count differs
between rows (81, 86, 88), so the medians are not computed over the same
segments. That is the most important caveat on this table. Comparing medians
over different subsets is not a clean comparison.

**Errors in the write-up of this finding.**

- The docstring in `scripts/berg_resolution.py` says that drift is "almost pure
  current (R << 1 in every segment)". The segment file records `wind_forcing_R`
  from 0.037 to 1.73, median 0.25. R above 1 is in at least one segment, so
  "every segment" is wrong.
- `dakshin/figures/berg_hindcast.json` says the wind is "zero (slice 6 pending)".
  Slice 6 (ECMWF wind harvest) is recorded as done in `docs/CURRENT_STATE.md`,
  and `data/ecmwf_wind/` holds the 2026-11-21 file. The JSON predates the
  forcing change. The hindcast has not been rerun with wind.
- The error figure that the document uses as the forecast cone rate, 4.35
  km/day (`docs/TRUE_CLAIMS.md` §1.15), is the median. ADR-025 (`docs/DECISIONS.md`)
  defines the exclusion radius as a p90 of leave-one-out error, which is not yet
  measured (`docs/backlog.md`, `[minor][ml]`). The median is not a
  conservative radius.

**What changed.**

- The drift model is kept as built and tested (23 tests in `models/iceberg/test_drift.py`,
  per `docs/TRUE_CLAIMS.md` §1.9), with the Ca/Cw swap fixed.
- The binding constraint is recorded as grounding detection, which needs
  IBCSO depth against the keel draught. Neither is in the drift model yet. The
  backlog lists it as `[major][bergs]` and it is the next iceberg item.
- Resolution of the current field is treated as second order until anchored bergs
  stop being advected (`docs/RESOLUTION_STUDY.md`, F3).

### 2e. IBCSO bathymetry exposed the old headline route ending on land; the claim was withdrawn twice, then re-derived

**Question.** Does the router respect the seabed? A route that ends at a
station needs to end in water.

**What the data said, in order.**

1. **17.4 days (superseded).** The first transit time was computed with a
   vessel configuration that had beam 18.6 m (real 22.4 m) and maximum speed
   14 km/h (real service speed 16.4 kn, 30.4 km/h). The ship was modelled at
   about half its real speed (`docs/PROTOTYPE_RESULTS.md`, routing section,
   correction paragraph).
2. **8.6 days (2026-09-02).** With the corrected vessel, the route on real
   NSIDC ice, day by day, gives 8.58 days of ideal steaming time. The document
   states this is steaming time only and is not a voyage duration
   (`docs/PROTOTYPE_RESULTS.md` §4).
3. **Withdrawn (2026-11-21).** The IBCSO v2 subset (`data/bathymetry/ibcso_v2_corridor_0p05.nc`)
   places the route's final point at +91 m. The chart gate now fails it.
   `docs/TRUE_CLAIMS.md` §1.11 withdraws the number. The same section of TRUE_CLAIMS
   records the earlier withdrawal of 17.4 days, so the 8.6-day figure has been withdrawn
   twice.
4. **Re-derived (same day, `13861d9`, on main after this document's reads; Appendix C).**
   With depth in the mesh (IBCSO south of 50 S, GEBCO_2020 north, subset built by `24317da`)
   and the router's nearest-node rule changed in `478ecd2`, the route on the same 1 December 2019
   ice is **8.66 days steaming**, arriving **16 km off** the station, never over water shallower than
   89 m. `docs/TRUE_CLAIMS.md` §1.11 now carries this number and calls it a lower bound. The route-regret,
   destination-window and alternatives experiments were computed on meshes without depth and have not
   been re-run (`docs/backlog.md`, `[major][eval]`). The 8.66-day figure is therefore not yet supported
   by the regret experiment.

**A caveat about the withdrawal's evidence.** The IBCSO subset is a
conservative block maximum: "the shallowest source elevation within one box of
this box" and its neighbours (about 5 km buffer), and its own comment says that
"zero or positive is land or ice-shelf surface" (`scripts/subset_bathymetry.py`
attributes and header). A value of +91 m therefore means land or ice shelf. The
repository does not separate the two at Bharati. `docs/backlog.md`
(`[minor][data]`) quotes the IBCSO v2 paper as giving 23.79% direct measurement
south of 50 S and naming East Antarctica as singlebeam-dominant, which describes
this corridor. That quotation was not re-checked against the paper in this pass.

**What changed.**

- `dakshin/gates.py` `chart_gate` returns UNKNOWN or MARGINAL and never PASS
  without an official ENC. A leg shallower than 20 m is refused in both routers
  (`docs/TRUE_CLAIMS.md` §1.17, slice 7 in `docs/CURRENT_STATE.md`).
- The day-0 Cape Town to Bharati route did not solve at the time of the earlier reads: IBCSO put the
  goal's lattice point in 85% simulated ice on day 0, and days 2 to 14 solved at 7.8 to 8.4 days
  (`docs/backlog.md`, `[major][demo]`, before `13861d9` removed that line). `478ecd2` changed the
  snapping rule that made day 0 hinge on one ice-locked node, and its commit message says the tests
  cover every departure day. Whether day 0 solves now was not re-run in this pass.
- `dakshin/figures/routes.json` was regenerated with depth in `13861d9` (item 4 above).
  The backlog line that asked for this regeneration was removed in the same commit.

### 2f. The Bharati approach was closed by real spring ice

**Question.** On a real forecast cycle, is the Bharati approach open to this
vessel at the working ice limit, and is the weather survivable?

**What the data said.** `scripts/real_route_run.py` on the 2026-11-21 cycle
(`dakshin/figures/real_route.json`). The goal is given as `[-69.4, 76.2]`; the
order is not labelled in the JSON. The values match Bharati's position as
described elsewhere (76.2 E in `docs/backlog.md`), which suggests latitude first.

| Field | Value |
|---|---|
| Approach closed at the ice limit | true |
| Closest reachable point | 50.6 km from the goal |
| Estimated time to closest point | 5.55 days |
| Worst SIC along the route found | 0.723 (72.3%) |
| Worst significant wave height along the route | 4.77 m |
| Worst wind | 14.9 m/s (Beaufort 7) |
| Weather gate | FAIL, waves 4.77 m against an assumed 3.0 m limit |
| Visibility | not assessed |

The "closed" state is computed as "no route under the limit to the goal". The
run then routes to the closest passable cell (`scripts/real_route_run.py`
lines 42 to 56). The worst SIC of 0.723 is below the 0.80 limit because it is the
maximum along the route to that closest cell, not at the goal, so the two
figures do not conflict.

**Caveats.** One cycle. The route covers only the segment south of 55 S,
because the wave and wind harvests do not cover further north (per the
`segment_note` in the JSON). The 80% ice limit is a stand-in that
`docs/PROTOTYPE_RESULTS.md` §5 states is not derived from the ice class; POLARIS
is indexed by ice type, which the repository does not yet model. The 3.0 m wave
limit is an assumption ("limits are assumptions, not this hull's PWOM", per the
JSON). The wind and wave values are real forecast values, and the gate decision
uses assumed thresholds.

**Superseded in part (`0d7be9f`, 2026-11-22; see 2p).** The table above is the
pre-regeneration file. Under the one-lattice-cell arrival rule the regenerated
`real_route.json` reads `approach_closed_at_ice_limit: false` and
`closest_approach_km: null`, with the track unchanged (5.55 days, worst ice
0.723, worst waves 4.77 m, weather gate FAIL) and a new
`route_ends_km_from_station: 50.6`.

**What changed.** The weather and traffic gates are implemented in
`dakshin/gates.py` (`weather_gate`, `traffic_gate`) and used by the real-route
run. `real_route.json` was generated before the router's nearest-node rule changed in `478ecd2`
(Appendix C), so a re-run may give a different closest approach. This pass did not re-run it. The traffic gate returns UNKNOWN without an AIS feed, which in the Southern
Ocean is the normal case (`docs/backlog.md`, `[minor][ais]`).

### 2g. Kaggle checkpoint forensics: the outputs were never in the store, and the training cell was not code

**Question.** Why did the scheduled training runs produce no checkpoints, and
can the 2026-08-31 numbers be reproduced?

**What the record says.** `docs/CURRENT_STATE.md`:

- The original 2026-08-31 checkpoints were never in Kaggle's output store.
- The training-loop cell in the saved notebook was typed as markdown, so
  batch runs executed nothing. Version 6 of the kernel is said to fix the cell type.
- CMEMS credentials are read from a private Kaggle dataset, because CLI batch
  runs cannot read Kaggle Secrets.
- At the time of writing, kernel `jiteeshghodke/notebookd39fdf7959` version 6
  was queued, and a background watcher polled every five minutes. I did not
  query Kaggle.

**What the repository shows.**

- `dakshin/kaggle/make_notebook.py` now builds the training loop with `code()`
  (around line 240). The committed `dakshin/kaggle/isih_train.ipynb` has a code
  cell containing `torch.manual_seed(0)`. The defect that the record describes
  was in the notebook as saved on Kaggle, not in this generator's current output.
- The split is a temporal 70/15/15 split of sorted dates over 2019 and 2020
  only (`YEARS = [2019, 2020]`, `i_tr, i_va = int(n*0.70), int(n*0.85)`). It is
  not the production split in ADR-019 (train 1993 to 2018, validate 2019 to 2021,
  test 2022 to 2024).
- The seed is `torch.manual_seed(0)`, set before each lead's model, so all four
  leads start from the same initialisation.
- There is no QA mask in the notebook's valid mask (finding 2a).
- `models/sic_correction/` in the repository contains `unet.py` and nothing
  else. The four `isih_prototype_lead{1,3,5,7}.pt` files and their
  `SHA256SUMS` are absent. The headline numbers in `docs/PROTOTYPE_RESULTS.md` (0.0465
  to 0.0968) therefore cannot be re-derived from this repository.

**A correction to the brief this document was written from.** The brief says
`docs/CURRENT_STATE.md` records the re-run with an identical seed and split. It
does not. `CURRENT_STATE` says nothing about the seed or split of the re-run.
The generator does fix the seed and the split, so the reproducibility argument
can be stated as "the generator fixes them", which is a weaker and accurate
claim.

**What changed.**

- `scripts/pull_checkpoints.sh` pulls the four files, writes `SHA256SUMS`, runs
  `dakshin/test_model_io.py`, and then reruns the hindcast and the resolution
  study with the model. It is written to be run once the kernel completes.
- `dakshin/model_io.py` loads the checkpoints only after their checksums match.
- The prototype numbers are labelled as an upper bound on forecast skill (see 2h),
  because the reanalysis background is in the input. The document states this
  next to the numbers.

**Resolved 2026-11-21 to 22 (2l).** v8 completed at 22:51 UTC on 2026-11-21,
the four checkpoints and `SHA256SUMS` were committed (`5612621`), and the hindcast
and resolution study were scored with them (`cf04a4d`). The correction to the
brief above is partly superseded: `realforecast_hindcast.json` now records the
re-run as "identical code, seed and split; credentials cell only change".
`docs/CURRENT_STATE.md` still says nothing about the seed or split.

### 2h. The reanalysis background leaks the target, and the leak is not yet measured out

**Question.** The prototype's input includes a reanalysis field. Does that field
contain the answer?

**What the data and code say.** `dakshin/features.py` (`build_channels`) sets
channel 0 to `background[t + lead]`, which is the reanalysis valid at the target
date. The reanalysis assimilates satellite observations, including ones near
the target date. The raw reanalysis error is flat across lead (0.1630 at lead 1,
0.1637 at lead 7; `docs/PROTOTYPE_RESULTS.md`), which the document calls "the
fingerprint of a field that has seen the target". The first version of the
argument defending the reanalysis was withdrawn (commit `fb20a3e`), because the
reanalysis error measures grid and model bias, not information about the target.

The no-background ablation is written. `docs/PROTOTYPE_RESULTS.md` says it "costs
~20 minutes" and that it has "not yet run". No ablation output exists in the
repository.

**What the innovation channel shows.** Channel 8 is `background[t] - observed[t]`
in code. Version 1 of the model saw the background only and scored 0.1051,
losing to persistence. Adding the observations closed the gap (`docs/PROTOTYPE_RESULTS.md`,
"What the model actually is").

**The second leak that was identified and avoided.** ERA5 2 m temperature at
t + lead would add a larger leak, because sea ice is a prescribed lower boundary
in ERA5 and 2 m temperature is close to a deterministic function of the observed
ice (`docs/PROTOTYPE_RESULTS.md` "Next improvements", item 4). The design uses
winds valid at t instead.

**What changed.** The prototype numbers are labelled an upper bound. The
ablation is the highest-value experiment in the backlog that is not yet run
(`docs/backlog.md`, `[critical][ml]`). The production path, which corrects real
forecast cycles rather than the reanalysis, is the test that would remove the
caveat, and it is the one the night build's hindcast (2b) starts.

### 2i. The early headline moved between commits, and the repository does not record why

**Question.** Is the 3-day result stable?

**What the data said.** The same results file, recorded on the same day
(2026-08-31), reports two different 3-day scores:

| Commit | File | Model RMSE, 3-day | Persistence | Headline |
|---|---|---|---|---|
| `27308ff` (record results), `fc366ad` (notebook v3) | `isih/RESULTS.md` | 0.0765 | 0.0958 | +20.2% vs persistence |
| `98c5e8c` (multi-lead results and ablation) | `isih/RESULTS.md`, now `docs/PROTOTYPE_RESULTS.md` | 0.0720 | 0.0958 | +24.9% vs persistence |

Both are labelled as the Kaggle run of 2026-08-31, on a single seed. The
repository does not record which run produced the 0.0720, or why the model
number changed.

**What changed.** The results document says "these are the numbers to quote".
The single seed means there is no error bar on any of this, which the backlog
records (`[major][ml]`, "One seed means no error bar"). The shift of about 6%
in the same model's 3-day score is a direct measure of how much a single run
can move. Three or more seeds are required before any comparison that differs
by a few percent is adopted (`docs/backlog.md`).

**Update (2l).** The committed `models/sic_correction/checkpoints/isih_skill_by_lead.csv`
from the 2026-11-21 re-run gives 0.07196 at lead 3, which rounds to the later
headline (0.0720), not to 0.0765. The independent clone (v4) spread by up to
0.012 at leads 3 to 7 (`docs/CURRENT_STATE.md`), larger than the 0.0045 gap
between the two 2026-08-31 numbers.

### 2j. The CMEMS archive has stale cycles, and the harvest's clock rule is the fix

**Question.** Is every archived forecast the forecast issued on its date?

**What the data said.** `data/cmems_forecast_archive/KNOWN_STALE.md` (found on
2026-11-18 by comparing each cycle with the one before) lists four files that
are copies of the previous day's forecast with its first day cut off: 9 daily
steps instead of 10, and identical sea-ice concentration on all 9 shared dates.
They are `cmems_siconc_2026-09-20`, `2026-10-11`, `2026-11-10` and `2026-11-17`.

Two causes are recorded. The 11-10 and 11-17 runs started after midnight UTC
and named the file from the clock while the server still held Monday's forecast.
The 09-20 and 10-11 runs started after 12:00 UTC, before Copernicus had
published that day's forecast, and both were Sundays. CMEMS overwrites each
forecast with the next, so the true forecasts for those four dates are gone.

**What changed.**

- `scripts/harvest_cmems.sh` derives the cycle date from the clock, with a
  rule: before 12:00 UTC the cycle is yesterday. It rejects any file whose step
  count is not 10 (`EXPECTED_DAYS`), and it records `not_published` rather than
  saving a wrong file.
- `.github/workflows/cmems-harvest.yml` runs three times a day at 12:23, 17:23
  and 21:23 UTC, always after the 12:00 UTC guarantee. Its header records that
  a scheduled run was four to five hours late on three consecutive days in the
  first week, and that the cron must never be on the hour.
- The four stale files are still in the archive, labelled in `KNOWN_STALE.md`.
  The realforecast hindcast excludes them, which is why the scored cycle counts
  are 76, 75, 74 and 72.
- **Still open.** The fix is clock-based, and the backlog's critical item
  is to derive the bulletin date from the dataset's own time axis
  (`docs/backlog.md`, `[critical][data]`). The backlog also asks for a sentinel
  that fails loudly when a bulletin is missed (`[high][ops]`).

### 2k. Melt and freshwater: an estimate with a known, large uncertainty

**Question.** How much freshwater do the giant bergs release along their forecast
tracks?

**What the data said.** `scripts/berg_melt.py` integrates the three
deterioration terms in `models/iceberg/melt.py` (basal turbulent melt, buoyant
convection, wave erosion; Keghouche et al. 2010 coefficient set, reimplemented
from the papers, not imported from GPL OpenDrift) along each giant's 10-day
track, on the 2026-11-21 cycle. `dakshin/figures/berg_melt.json` labels the
whole output "ESTIMATE". Thickness is an assumed 250 m, because USNIC publishes
no draught.

| Berg | Area (km²) | Mean freshwater (10⁶ m³/day) |
|---|---|---|
| D15C | 115.0 | 1.91 |
| D15D | 55.9 | 1.17 |
| D37 | 477.8 | 1.00 |
| B09G | 160.1 | 0.77 |
| D23 | 105.6 | 0.51 |
| C39 | 45.4 | 0.43 |
| C18B | 110.4 | 0.39 |
| C18C | 53.1 | 0.16 |
| **Total (8 bergs)** | | **6.35** |

**Caveats, in the module's own header.** The coefficients were tuned for Arctic
bergs orders of magnitude smaller than USNIC giants, so applying them to a 50 km
tabular berg extrapolates far outside their calibration. The output is a bulk
estimate of freshwater input, not a deterioration forecast.

Two further points. First, the berg with the largest area (D37, 478 km²) does not
have the largest melt rate, and the two bergs of nearly equal area (C18C at 53 km²
and D15D at 56 km²) differ by about 7 times. The melt terms depend on relative
speed, sea-surface temperature and wave height along each track, not on area
(`models/iceberg/melt.py` header). The JSON does not record per-berg speed or
temperature, so the attribution of the difference to a particular term is not
verified. Second, the wave height is set to 0 under ice ("ice-covered: waves
damped", `scripts/berg_melt.py` line 79), which removes the wave-erosion term
where pack ice damps waves. That is a physically reasonable choice, but it is a
choice.

**A provenance gap.** The script reads `data/cmems_forecast_archive/cmems_sst_<cycle>.nc`
and takes `thetao`. No script in the repository fetches that file. `scripts/harvest_cmems.sh`
fetches ice, currents and waves only, and `ATTRIBUTION.md` does not list an SST dataset.
The one SST file in the archive (2026-11-21) therefore came from a command that is
not recorded in the repository. The melt number cannot be regenerated from the
repository until that is fixed.

**Committed update (`df7f39e`, after the snapshot).** The melt was re-run with a berg-relative speed term. The committed `dakshin/figures/berg_melt.json` gives per-berg means of 10⁶ m³/day: D37 0.448, B09G 0.222, D15C 0.372, C18B 0.154, D23 0.186, D15D 0.251, C18C 0.097, C39 0.155, total 1.885. The table above is the snapshot value and is superseded. The spread across similar-area bergs is smaller now (C18C and D15D differ by about 2.6 times, not 7).

**What changed.** F4 (`7307f12`) is recorded as done. The output is labelled as
an estimate in the JSON and in the module, and is not used in any decision in
the routing code.

### 2l. The Kaggle training saga, completed: environment failures, two working runs, and a batch recipe that lives beside the generator, not in it

*Continues 2g. Sources: `docs/CURRENT_STATE.md` ("Overnight run update", "Update 4"), the messages of `d7b0d0f` and `0848d7e`, the `model` field of `dakshin/figures/realforecast_hindcast.json`.*

**Question.** The checkpoints behind the 2026-08-31 headline were gone (2g). Can the training be re-run, and do the numbers come back?

**The runs, in order.**

| Run | Outcome | Cause recorded | Fix |
|---|---|---|---|
| 2026-08-31 original (saved notebook) | Numbers recorded in `docs/PROTOTYPE_RESULTS.md`; checkpoints never in Kaggle's output store | The training-loop cell was typed markdown, so batch runs executed nothing (`docs/CURRENT_STATE.md`). How the 08-31 numbers were produced from that notebook is not recorded in the repository | v6 of kernel `jiteeshghodke/notebookd39fdf7959` fixed the cell type; `make_notebook.py` builds the cell with `code()` |
| v6 | Outcome not recorded beyond "fixed the cell type" | | |
| v7 (GPU) | Died on first import | pip's resolver upgraded numpy to 2.5.5 over the image's compiled core; `numpy.testing` then referenced `_blas_supports_fpe`, which the loaded C core does not export, which broke scipy and so xarray (`d7b0d0f` message). The CPU image survived "by chance" | `d7b0d0f` (21:41 UTC): pin numpy to the already-installed version in the same pip command |
| v8 (GPU) | **Completed 2026-11-21 22:51 UTC** | | Checkpoints and `SHA256SUMS` committed 23:16 (`5612621`); Release `model-v0.1` |
| Clone `dakshin-prototype-train-gpu2` v1, v2 | Died | Kaggle changed the dataset mount layout for new kernels to `/kaggle/input/datasets/<owner>/<slug>/`; legacy kernels keep the old path. The creds dataset `jiteeshghodke/cmems-creds` was not found (implied: v3 "found the creds") | Glob for the path (see the delta below) |
| v3 | Died | Transient NSIDC HTTP 500; the download had no retry | `0848d7e` (2026-11-22 02:40): 3 attempts, sleep 15 s times the attempt number, download to `.part` and rename on success |
| v4 | **Completed** | | |
| CPU clone | Output discarded | On pace to hit Kaggle's 12 h wall mid-lead-1; partial log agreed (best val 0.0434 to 0.0439) | Redundant once v8 completed |

**What the reruns show.** All from `docs/CURRENT_STATE.md` Update 4 unless marked:

- v4's lead-1 held-out RMSE is 0.04649 against the released 0.04646: 3e-5. Leads 3 to 7 spread by up to 0.012 (attributed to GPU nondeterminism). Persistence was beaten at every lead in every run.
- Derived here: the committed `models/sic_correction/checkpoints/isih_skill_by_lead.csv` (the v8 run) holds 0.04646, 0.07196, 0.09377, 0.09685 at leads 1, 3, 5, 7, which round to the 2026-08-31 headline table in `docs/PROTOTYPE_RESULTS.md` (0.0465, 0.0720, 0.0938, 0.0968) at all four leads. v8 therefore reproduces the original to four decimals, while v4 (same notebook, different kernel) spreads by up to 0.012. The repository does not say why, and does not record the hardware of v4. For the two lead-3 numbers in 2i, v8 is consistent with 0.0720, not 0.0765; v4's lead-3 value is not recorded, and its spread is larger than the 0.0045 gap between them.
- Every figure in the two bullets above except the CSV rests on prose in `docs/CURRENT_STATE.md`. No committed file holds v4's numbers or the discarded CPU log. They are **Claimed** in the sense of the labels at the top.

**What was not in the repository, and what is now.** `docs/CURRENT_STATE.md` Update 4 said the glob and the retry fixes were "both now in `make_notebook.py`, commit 0848d7e". The commit contains only the retry. At HEAD the generator's credentials cell still reads `kaggle_secrets.UserSecretsClient` (`dakshin/kaggle/make_notebook.py`, section 3), which batch runs cannot do. The hindcast JSON says the re-run was "identical code, seed and split; credentials cell only change", and that changed cell, a dataset-mount glob over `/kaggle/input/**/cmems.json`, existed only on Kaggle. `779cf83` (2026-11-22 05:12, landed during this pass) records it: `dakshin/kaggle/README.md` holds the replacement cell and the failure modes, `dakshin/kaggle/kernel-metadata.json` the push template (`dataset_sources: jiteeshghodke/cmems-creds`), and `docs/CURRENT_STATE.md` was corrected to say the creds-glob "lives in the pushed batch kernel". So the recipe is now in the repository as documentation; the generator still emits the Secrets cell and the swap is manual, so regenerating the notebook alone does not reproduce v8 or v4. The kernel metadata names `jiteeshghodke/dakshin-prototype-train`, a third kernel id beside `notebookd39fdf7959` (`scripts/pull_checkpoints.sh`) and the clone `dakshin-prototype-train-gpu2`; which pushes used which id is not recorded.

**Lessons.** Each is tied to one failure above.

1. **A notebook cell's type is part of the code.** A markdown training cell executes nothing and a batch run still ends. Assert `cell_type == "code"` for the training cell after generation, and treat "the output store holds four `.pt` files" as the definition of done. `dakshin/kaggle/README.md` (`779cf83`) lists "check cell types before pushing" as a manual step; no test asserts either (`grep cell_type` finds only the generator).
2. **Keep weights outside the platform's store.** The 08-31 weights are unrecoverable. Now: checkpoints committed, `SHA256SUMS`, `dakshin/model_io.py` verifies before loading, Release `model-v0.1`. The sums are computed by `scripts/pull_checkpoints.sh` after the pull, so they pin integrity from then on, not provenance.
3. **pip can half-upgrade a preinstalled compiled package.** Pin it to the image's own version in the same command as the install (`d7b0d0f`). A survived CPU run proves nothing about the GPU image.
4. **A platform's filesystem layout is part of its interface, and it changes per kernel generation.** Legacy kernels keep the old path, so the old kernel keeps working while a new clone fails, which is the worst case for a reproducibility check. Glob, do not hard-code.
5. **Transient 5xx from a public archive is normal.** Retry with backoff, and write to `.part` first. The skip test in the downloader is "file exists and larger than 1000 bytes", so a truncated file left behind by a failed try would be accepted as complete on the next.
6. **CLI batch runs cannot read Kaggle Secrets.** Credentials went into a private dataset. Whatever delta a run needs from the generator has to be committed beside it; this one was recorded only after the fact (`779cf83`), and in prose rather than in the generator.
7. **Budget against the wall clock.** The CPU clone would have hit Kaggle's 12 h limit during lead 1. A GPU run completes in well under that (v8 completed 70 minutes after the numpy-pin commit; its start time is not recorded; the "23 min on a free T4" figure appears in `docs/WEAKNESS_ANALYSIS.md` section 11 and `docs/study/PHYSICS_AND_PAPERS.md`; no run log is committed to check it against).
8. **Failures surfaced one at a time.** Each fix exposed the next stage's failure (numpy, then layout, then the 500). A cheap smoke test per stage (imports, input mount, one download) would have found them in minutes rather than as a series of full runs.
9. **Reproduction is statistical.** Report the spread beside the margin. The hindcast margin of the U-Net over raw CMEMS is 0.0108, 0.0174, 0.0152 and 0.0129 RMSE at leads 1, 3, 5, 7 (computed from `realforecast_hindcast.json`); the rerun spread at leads 3 to 7 is up to 0.012, measured on the held-out training split, not on the hindcast. The two are different evaluation sets, so the comparison is indicative only. The hindcast uses one checkpoint per lead.
10. **A redundant hedge was cheap and was used.** The CPU clone was started in parallel and discarded when the GPU run completed.

### 2m. The model scored once on 2026 real forecasts: RMSE wins at every lead, the ice-edge win ends before lead 7

*Sources: `dakshin/figures/realforecast_hindcast.json` (generated 2026-11-21 23:13:34 UTC, `cf04a4d`), `dakshin/figures/resolution_study.json` (23:15:37), `docs/PROTOTYPE_RESULTS.md` section "Real-forecast hindcast (2026)", `docs/RESOLUTION_STUDY.md` "The U-Net column".*

**Question.** 2b left the U-Net column pending. Does the correction beat raw CMEMS on data it has never seen, on both RMSE and IIEE?

**Setup.** Same as 2b: archived CMEMS GLO12 cycles at issue time, NSIDC NRT G10016 v4 truth (AMSR2, QA-masked), corridor 0 to 80 E, 55 to 78 S, 4 stale cycles excluded. Checkpoints from the v8 run (2l). The scorer's rule is "scored once, reported as it comes out". Out of sample twice: 2026 against 2019 to 2020 training, and AMSR2 against F17 SSMIS truth.

| Lead | Cycles | RMSE U-Net | RMSE raw | RMSE persistence | U-Net vs raw | IIEE U-Net (km²) | IIEE raw | IIEE persistence | U-Net vs raw |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 77 | 0.0914 | 0.10219 | 0.11914 | -10.6% | 93,231 | 196,031 | 186,997 | -52.4% |
| 3 | 75 | 0.08741 | 0.10479 | 0.14391 | -16.6% | 142,467 | 194,575 | 277,167 | -26.8% |
| 5 | 74 | 0.0946 | 0.10981 | 0.15508 | -13.9% | 182,601 | 200,203 | 319,189 | -8.8% |
| 7 | 72 | 0.10245 | 0.1153 | 0.16414 | -11.1% | 221,094 | 210,200 | 353,255 | +5.2% |

The percentage columns are computed from the JSON values.

**What the data said.**

- RMSE improves at every lead. The edge error is cut by 52.4% at lead 1, 26.8% at lead 3 and 8.8% at lead 5, then is **5.2% worse than raw CMEMS at lead 7**. The edge advantage decays monotonically with lead. The documents say to quote both metrics (`docs/PROTOTYPE_RESULTS.md`).
- Against persistence, the U-Net wins IIEE at every lead including lead 1 (-50.1%), the lead at which raw CMEMS loses to persistence (2b). So the correction removes the one place raw CMEMS lost to persistence.
- **Against ADR-027** (`docs/DECISIONS.md`: the corrected forecast must beat raw CMEMS on both IIEE and CRPS at every lead, and "a lead that fails is not claimed", with the declared skill horizon shortening): lead 7 fails on IIEE, and CRPS is computed nowhere in `dakshin/figures/`, so the rule cannot be shown to pass at any lead. Read strictly, the claimable horizon is at most 5 days. Yet the decision record (2n) and the site AI edge (2q) include lead 7. Appendix A item 36.
- **The baseline moved by one cycle.** 2b's table had 76 cycles at lead 1 (raw 0.10199, persistence 0.11977, IIEE 195.1 and 187.7 thousand km²). The regenerated files have 77 (cycle 2026-11-19 became scorable; a `docs/backlog.md` line said so and was removed in this pass): raw 0.10219, persistence 0.11914, IIEE 196,031 and 186,997. Leads 3, 5, 7 are unchanged. Raw CMEMS against persistence at lead 1 is now 14.2% lower on RMSE (was 14.8%) and 4.8% higher on IIEE (was 3.9%). The qualification in 2b stands and is slightly larger.
- **Resolution, with the U-Net** (`resolution_study.json`, corrected IIEE in km², change against 1/12 degree):

| Lead | 1/12° | 1/4° | 1° |
|---|---|---|---|
| 1 | 93,231 | 93,287 (+0.1%) | 97,792 (+4.9%) |
| 3 | 142,467 | 143,208 (+0.5%) | 155,683 (+9.3%) |
| 5 | 182,601 | 183,818 (+0.7%) | 198,902 (+8.9%) |
| 7 | 221,094 | 223,342 (+1.0%) | 246,580 (+11.5%) |

  The 2c conclusion holds with the correction in the loop: 1/12 degree and 1/4 degree are not separable, 1 degree loses the edge. Raw loses 4.3%, 7.6%, 11.2% and 16.2% at 1 degree (same file). Applied to a 1 degree field the correction still beats raw at 1/12 degree at leads 1, 3 and 5 (97,792 against 196,031; 155,683 against 194,575; 198,902 against 200,203, a margin of 0.7%) but not at lead 7 (246,580 against 210,200). It does not restore the 1/12 degree edge. RMSE of the corrected field barely moves across resolutions (lead 1: 0.0914, 0.0914, 0.09183).

**Caveats** (in the JSON, plus two): one spring, one corridor, sensor change AMSR2 against F17, day-t satellite file assumed available on day t (stage 9 tests exactly this), no confidence intervals, no CRPS. Added here: one checkpoint per lead, and the training truth was not QA-masked while the hindcast truth is (`docs/backlog.md`, `[minor][ml]`), so the coastal effect of that train/serve mismatch is unquantified.

**What changed.** The prototype's upper-bound training numbers (2h) now have a production-path companion. The claim the project makes is the pair of tables above, not the training table (`docs/PROTOTYPE_RESULTS.md`: "Do not compare these RMSEs with the training table"). The no-background ablation remains unrun (4.6).

### 2n. Slice 3: a reachability flood fill, a one-cycle case study, then a season-long decision record whose baseline ties

*Sources: `scripts/corrected_forecast.py`, `dakshin/figures/corrected_forecast.json`, `dakshin/figures/corrected_all.json`, commits `620d3a3`, `a4c37a9`, `9e332bd`, `fb246b2`, `0c3b9ef`.*

**Question.** Does the corrected ice change the router's go/no-go at the station?

**Method.** The lead-matched checkpoint is applied to a cycle on the model-native 25 km NSIDC grid (the correction adds no resolution). The decision: is any cell within 50 km of Bharati 4-connected to open water 400+ km out through cells at or under the 80% ice limit? Depth blocking is not applied (the JSON's `question` field). The fill is 4-connected, which the docstring (`scripts/corrected_forecast.py`, since `ad97f88`) says is stricter than the router's 8-neighbourhood and so "errs toward 'not reachable'": a structural lean toward the one answer every verified target turned out to have. The flood fill is unit-tested and the ice limit is pinned to the router's `VesselModel` default by a test (`620d3a3` message).

**Case study (`620d3a3`, cycle 2026-11-20).** Raw CMEMS mean-pooled to 25 km says reachable at all four leads (targets 11-21, 11-23, 11-25, 11-27), a spurious one-cell-wide thread. The corrected field says not reachable at all four. The day-0 satellite says not reachable. Mean absolute correction 0.0629, 0.0636, 0.0578, 0.0592 SIC. The cycle is 2026-11-20 and not the live 11-21 because the newest correctable cycle needs a day-0 file (2o). The case-study text claimed the 1/12 degree router "had already said closed"; that is the overclaim corrected in 2p.

**Decision record (`9e332bd`, 04:05 UTC 2026-11-22).** Every archived cycle with a full 7-day satellite history, 78 cycles from 2026-08-31, four leads each: 312 lead-decisions, 298 verifiable against the satellite on the target date (14 targets fall beyond the archive). `corrected_all.json["verification"]`:

| Field | Correct go/no-go | Rate |
|---|---|---|
| Raw CMEMS at 25 km | 287 / 298 | 96.3% (11 false "reachable") |
| U-Net corrected | 298 / 298 | 100% |
| Persistence (day-0 verdict carried) | 298 / 298 | 100% |

The first write-up (`0c3b9ef`, 04:05) had no persistence row and justified the scope with "the station was closed nearly all season, so the base rate favours 'not reachable'". Thirteen minutes later (`fb246b2`, 04:18) the persistence arm was added to the script, it scored 298 of 298, and the caveat was welded to the headline in the JSON, the doc, the demo text and the README: the record separates the corrected field from raw CMEMS, not from persistence. The baseline that should have been in the first run was found by the project's own pass over its own headline.

**Derived here, stronger than the caveat.** In `corrected_all.json` every one of the 298 `satellite_target` values is false and so is every one of the 78 `satellite_day0_reachable` values. The station was closed on every verified date. "Never flipped" understates it: there is no positive case at all, so the 298 of 298 measures false-alarm avoidance only, and sensitivity (a correction that wrongly closes a real opening) cannot be measured on this sample. An always-"not reachable" rule also scores 298 of 298. The 11 raw errors are all in November: cycles 11-04, 11-11, 11-12, 11-13, 11-14, 11-15, 11-16, 11-18, 11-19; by lead, 4 at lead 7, 3 at lead 5, 2 at lead 3, 2 at lead 1. Four of the 11 are at lead 7, a lead ADR-027 would not claim (2m).

**What changed.** The README and `docs/WEAKNESS_ANALYSIS.md` section 11 state the persistence tie. `ad97f88` (05:04, after this analysis was drafted) added the constant-rule sentence to `docs/PROTOTYPE_RESULTS.md` and the README: "a rule that always says no would also score 298", measuring false-alarm removal, "not sensitivity". The README also says the router "has not yet run on corrected ice with real weather": `CorrectedIceWorld` is wired and tested (`dakshin/test_real_route_corrected.py`) but gated on a cycle with both a correction and a wave file, and only one wave file was ever archived (`docs/backlog.md`, `[med][harvest]`). The next real-opening season is the missing test; the forecast archive cannot be back-filled to produce one.

### 2o. The stale-history experiment: measured, rejected, and the rejection is narrower than its verdict

*Sources: `scripts/stale_history_eval.py`, `dakshin/figures/stale_history_eval.json` (generated 2026-11-22 04:31 UTC), `docs/PROTOTYPE_RESULTS.md` "Why there is no AI edge for the live cycle", commits `6dc4719`, `e32332b`, `71a8b08`.*

**Question.** The NSIDC NRT file publishes about a day late, so a correction of the live forecast cycle must run on satellite history ending at day-1, outside the training assumption. What does that cost?

**Method.** Same cycles, mask, checkpoints and scoring as the hindcast, scored once. Fresh history is obs[t-0 .. t-6]; stale history is obs[t-1 .. t-7]. The evaluation was committed (`6dc4719`) before any live-cycle AI edge was built ("measure the cost ... before any live-cycle AI edge"). Cycles are 77, 75, 74, 72 as in 2m.

| Lead | RMSE fresh | RMSE stale | RMSE raw | Stale vs raw | IIEE fresh | IIEE stale | IIEE raw | Stale vs raw |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.0914 | **0.10763** | 0.10219 | **+5.3%** | 93,231 | 139,334 | 196,031 | -28.9% |
| 3 | 0.08741 | 0.09388 | 0.10479 | -10.4% | 142,467 | 159,967 | 194,575 | -17.8% |
| 5 | 0.0946 | 0.09715 | 0.10981 | -11.5% | 182,601 | 190,084 | 200,203 | -5.1% |
| 7 | 0.10245 | 0.10383 | 0.1153 | -9.9% | 221,094 | 225,790 | 210,200 | +7.4% |

**What the data said.** Stale lead-1 RMSE is 17.8% worse than fresh and 5.3% worse than raw CMEMS (0.1076 against 0.1022): the short-lead skill lives in the day-0 image. Degradation shrinks with lead: stale against fresh RMSE is +7.4%, +2.7%, +1.3% at leads 3, 5, 7.

**The verdict and what it rests on.** The documents conclude that no stale-input edge ships and that the AI layer trails the live cycle by a day (`docs/PROTOTYPE_RESULTS.md`, `docs/WEAKNESS_ANALYSIS.md` section 11, `README.md` section 6). The JSON supports that for lead-1 RMSE. It does not show stale loss elsewhere: stale RMSE beats raw at leads 3, 5, 7 (by 9.9% to 11.5%), and stale IIEE beats raw at leads 1, 3, 5 (by 28.9%, 17.8%, 5.1%). Only lead 1 RMSE and lead 7 IIEE lose. `ad97f88` (05:04) added the same two points as a "for completeness" sentence in `docs/PROTOTYPE_RESULTS.md` and left the verdict unchanged. So "rejected" is a product decision on one metric at one lead. It may be the right decision, because a live consumer of lead 1 gets a worse concentration field than the raw forecast, but the table also supports a narrower deployment (leads 3 to 5), and the documents do not say why that was not chosen. Appendix A item 40; open in 4.30.

**What changed.** The AI layer is shown only for cycles with full satellite history (78 of 83, `docs/backlog.md` `[low][site]`). The negative result is published with the number that caused it. This is the clearest instance of the method the README names: "The project treats its own negative results as findings."

### 2p. Route honesty: the arrival rule silently turned "closed" into "open", and the router was never at 1/12 degree

*Sources: `scripts/real_route_run.py`, `dakshin/figures/real_route.json`, commits `478ecd2`, `620d3a3`, `0d7be9f`.*

**Question.** What does "the route arrives" mean after the router's arrival rule changed?

**What happened.**

1. `478ecd2` (2026-11-21, 18:21; Appendix C) let the router arrive anywhere navigable within one lattice cell of a station ashore.
2. The committed `real_route.json` before that (generated 17:51 on 11-21, `ba37f25`) said `approach_closed_at_ice_limit: true`, `closest_approach_km: 50.6`.
3. Regenerated on 2026-11-22 04:13 under the new rule, the same run gives `approach_closed_at_ice_limit: false`, `closest_approach_km: null`, with the track unchanged: 45 legs, 5.55 days, worst ice 0.723, ending 50.6 km from the station. A reader of the flag alone would have taken the approach as open. The repository does not record how this was noticed; the fix is `0d7be9f`.

**The fix.** `real_route.json` always carries `route_ends_km_from_station` (50.6, computed from the last leg) and a `lattice_note`: the router lattice is 0.55 by 0.9 degrees over native 1/12 degree fields and cannot resolve the final 50 km, which the 25 km reachability check (2n) covers. The site ribbon says so (`docs/CURRENT_STATE.md`). Three statements about one approach now coexist and each is labelled: the router flag (open under the one-cell rule), the track end (50.6 km short), the 25 km check (not reachable).

**The second overclaim.** The slice-3 commit message and `docs/PROTOTYPE_RESULTS.md` called the router "full-resolution 1/12 degree". The fields are 1/12 degree; the lattice is 0.55 by 0.9 degrees (`lattice_note`). Corrected in `docs/PROTOTYPE_RESULTS.md`, `docs/CURRENT_STATE.md` and the JSON in `0d7be9f`.

**Gated check.** `CorrectedIceWorld` adds delta = corrected minus raw (from `corrected_forecast.npz`) to the router's ice, by nearest 25 km cell at the nearest lead. The `corrected_ice_check` in the JSON is `skipped`: the newest corrected cycle (2026-11-20) has no archived wave file and the router needs waves. It runs on the first cycle that has both. Two tests in `dakshin/test_real_route_corrected.py`.

**Superseded.** The 2f table (approach closed true, closest reachable 50.6 km) describes the pre-`0d7be9f` file. The README (section 5) still says the router "finds the Bharati approach closed ... the closest reachable cell is 50.6 km away", which matches the 25 km check and the track end but not the JSON flag (Appendix A item 31).

### 2q. Deployment: where the model honestly appears, and what the written record says

- **Demo bridge console** (`0c3b9ef`): an "AI correction" panel fed only by release artifacts (`/api/model`, provenance kind *real*). Changes in `dakshin/demo/app.py`, `dakshin/demo/data.py`, `dakshin/demo/static/bridge.js`, `provenance.js`. The panel text was reworded in `fb246b2` when the persistence caveat landed.
- **Companion viewer (separate repository, not read in this pass).** `docs/CURRENT_STATE.md` Update 4 and `docs/backlog.md` give: the AI edge drawn on every one of the 78 cycles that have a full 7-day satellite history (of 83); weekly USNIC berg fixes following the issued date (14 issues); drift chains true to the grid; day replay 0.45 s. This document cannot verify the site's behaviour from this repository.
- **Router on corrected ice** is wired and gated (2p), not deployed.
- **Paper.** An IEEE-format paper was drafted, reviewed and revised, local only: `paper/` (gitignored in `d10cc44`; the directory exists in the working tree with `main.tex` and `main.pdf`) and `~/dakshin-paper.pdf`, "per the owner" (`docs/CURRENT_STATE.md`). Not pushed; whether it is ever pushed is the owner's decision. It was not read in this pass, so no number in it is vouched for here.
- **Honesty sweep.** `d10cc44`: training years corrected to 2019 to 2020 (`YEARS = [2019, 2020]`), not 2015 to 2020. `d178f95`: `docs/WEAKNESS_ANALYSIS.md` section 11, three lists (confident, does not work and why, what can go wrong with mitigations), plus a state and backlog sweep. `0cda289`: README results rewritten with the U-Net in the tables, the decision record, the stale-history rejection, a "Withdrawn claims" table, and a status paragraph. Suite: 209 passed, 2 skipped (`docs/CURRENT_STATE.md` Update 4).
- **Mismatches in that sweep** are in Appendix A items 31 to 37.

---

## 3. How we innovate

The claims below are limited to what the repository demonstrates. Each item
says whether it is built, designed, or claimed.

| Practice | Evidence in the repository | Status |
|---|---|---|
| **Gates that stay UNKNOWN when the data does not decide** | `dakshin/gates.py`: `capability_gate` returns UNKNOWN because no vessel threshold is sourced (line 69 comment cites the §48A.3 rule). `chart_gate` never returns PASS without an official ENC. The weather gate fails honestly at 4.77 m (`real_route.json`). The ice-gate MARGINAL band is 7.4 concentration points, derived in the module (`MARGINAL_BAND_BASIS`). | Built |
| **Claims ledger with withdrawals** | `docs/TRUE_CLAIMS.md` lists 17 claims, each with a file, and records two withdrawals (§1.11, §3). `scripts/verify_claims.py` runs 18 `check()` calls covering 29 claims against source files; on 2026-11-21, after `13861d9`, it printed `PASSED 29`. One of its checks still tests the pre-depth 8.6-day transit (Appendix A, item 27). | Built |
| **Score once, report as it comes out** | `scripts/realforecast_hindcast.py` docstring: "Scored once, reported as it comes out — no re-tuning on this set, ever." The prototype's test set is scored once. | Built, but see 2i: a single seed moved the headline by about 6% between commits. Applied again to the trained model (2m) and to the stale-history evaluation (2o). |
| **Operational-first data engineering** | Daily CMEMS harvest from 2026-08-31 (168 harvest commits). Stage B forecasts cannot be back-filled, so the harvest started on day 0 (`docs/DECISIONS.md` ADR-019). NSIDC NRT truth is downloaded before it rolls off. Harvest contract: never fail the ice cycle because of currents or waves (`scripts/harvest_cmems.sh`, `run_currents`, `run_waves`). Compression from 42.6 MB to about 5 MB per day (`f2de08e`). | Built |
| **Physics-grounded residual correction** | The network predicts a correction to the forecast, not the field: an untrained model returns zero and reproduces the forecast (`docs/PROTOTYPE_RESULTS.md`). The innovation channel is the observation-versus-background difference at each cell (`dakshin/features.py`, channel 8). | Built and scored once on the 2b baseline (2m, `dakshin/figures/realforecast_hindcast.json`): lower RMSE than raw CMEMS at every lead, lower IIEE at leads 1 to 5, higher at lead 7. |
| **Iceberg drift from first principles, tested against the paper** | `models/iceberg/drift.py` implements the closed-form WDE17 model, with the drag-coefficient swap that changes wind-driven drift by 44% fixed (`docs/backlog.md`, `[resolved][ml]`). 23 tests reproduce the paper's coefficient table and its 765 m critical length (`docs/TRUE_CLAIMS.md` §1.9). | Built |
| **Choosing the metric the decision depends on** | IIEE, the ice-edge error, is the metric for the decision, because RMSE does not register resolution (2c). | Built |
| **Calibrated uncertainty by stratified conformal prediction, with a pre-committed pass/fail gate** | ADR-020 in `docs/DECISIONS.md`: coverage in the marginal ice zone at lead 5 must be 85% to 96%, mean width below 25 SIC points, and calibrated spread must beat inter-source disagreement. | Designed. Not implemented. The gate has not been run. |
| **A five-member ensemble whose disagreement widens the route** | ADR-005 and ADR-020. | Designed. The prototype is a single model per lead (`docs/PROTOTYPE_RESULTS.md` caveat 3). |
| **A time-expanded routing graph** | `docs/TRUE_CLAIMS.md` §2.3 and §5, item 1. PolarRoute's router has no time dimension, verified by reading its source. | Designed. The router is still static (`docs/backlog.md`, `[critical][routing]`). |
| **A 12-run dominance-filtered route sweep** | ADR-021. | Designed. `objective_function` is hard-coded to `traveltime` in two scripts (`docs/backlog.md`, `[major][routing]`). |
| **Robust routing across scenarios** | Not built. `docs/backlog.md` records it as a gap against the research matrix. | Gap |
| **A synthetic world model for the bridge demo** | `docs/backlog.md` "synthetic world model": designed in `docs/audit/WORLD_MODEL_DESIGN.md`, partly built in `dakshin/sim/`, and labelled as simulated input. Changed again by `f67493b` (Appendix C). | Partly built |
| **Negative results published with the number that caused them** | Stale-history evaluation: lead-1 RMSE 0.10763 against raw 0.10219 (`dakshin/figures/stale_history_eval.json`), so no live-cycle AI edge ships (2o). Raw-CMEMS-loses-to-persistence on IIEE at lead 1 kept in the record (2b). `README.md` "Withdrawn claims" table. Stage 5's grounding result: persistence beats the drift model (2d). | Built. The verdict in 2o is narrower in the data than in the prose. |
| **Add the missing baseline, then weld the caveat to the headline** | The decision record had no persistence arm for 13 minutes; adding it gave 298 of 298 and rewrote the claim in the JSON, doc, demo and README (`fb246b2`, 2n). | Built |
| **Report where the thing actually ends, not whether a flag is set** | `real_route.json` carries `route_ends_km_from_station` (50.6) beside the arrival flag after the one-cell rule flipped the flag (`0d7be9f`, 2p). | Built |
| **Product reads release artifacts only** | Demo `/api/model` panel (provenance kind *real*), site AI edge on 78 cycles (2q). Checkpoints are loaded only after SHA-256 match (`dakshin/model_io.py`), Release `model-v0.1`. | Built (site not verifiable from this repository) |
| **Gated check that runs itself when its data exists** | `CorrectedIceWorld` router check is `skipped` in `real_route.json` with its reason, and runs on the first cycle with a correction and a wave file (2p). | Built, not yet run on real data |

The strongest evidence of honest reporting is the withdrawals in
`docs/TRUE_CLAIMS.md`. The weakest is the reanalysis background, whose leakage has
been named but not measured (2h). The project's own audit passes (`d71d67f`,
`77cb1d9`, `787f2c2`, `ecc82e0` and others) are the process that produced most of
the withdrawals; their commit messages are the record of which claims were
corrected in which pass.

Novelty claims are not made here. The backlog records that "no study propagates
sea-ice forecast uncertainty into a routing decision" is medium confidence
because the search was cut short (`docs/TRUE_CLAIMS.md` §2.1 and `docs/backlog.md`).

---

## 4. What's next

Grouped by what it blocks, and ordered within each group. Each line states the
item, its severity from the backlog, and whether the code still matches the
item. Items the backlog marks as resolved are listed in Appendix B, not here.

### Data continuity (do first; these cannot be recovered later)

1. **NSIDC NRT truth rolls off.** `data/nsidc_nrt/` holds 89 files from
   2026-08-24 to 2026-11-20 (`scripts/download_nsidc_nrt.py`). The NRT archive
   keeps about three months (commit `5f32ae3`), so the first file reaches that
   age on or about 2026-11-24. The directory is gitignored and not on origin.
   Without a copy elsewhere, the real-forecast hindcast cannot be re-run from
   scratch after roll-off. This is not an item in `docs/backlog.md`.
   **Superseded:** `a6fdc83` (2026-11-21 18:37 UTC) committed the archive:
   `data/nsidc_nrt/` holds 89 `.nc` files, 2026-08-24 to 2026-11-20, plus
   `MANIFEST.sha256`. `docs/WEAKNESS_ANALYSIS.md` section 11 says the files roll
   off "after ~30 days"; the downloader and the commit message say about three
   months (Appendix A item 33).
2. **CMEMS file dates come from the clock.** `[critical][data]`. Still open;
   mitigated by the 12:23, 17:23 and 21:23 UTC schedule.
3. **Missed-bulletin sentinel.** `[high][ops]`. Still open.
4. **SST input has no producer.** `berg_melt.py` reads `cmems_sst_<cycle>.nc`.
   Not in the harvest, not in ATTRIBUTION. This is not in the backlog.
5. **Pin harvest dependencies.** `[minor][ops]`. Still open.

### Model validity (the claims the prototype makes)

6. **Run the no-background ablation.** `[critical][ml]`. Written, not run
   (`docs/PROTOTYPE_RESULTS.md`).
7. **Run the conformal gate on held-out 2022 to 2024 and on real forecast cycles.**
   `[critical][ml]`, the riskiest assumption in `docs/ML_ARCHITECTURE.md` §6. Not built.
8. **Mask the land-spillover zeros in training.** `[major][ml]`. The notebook's
   valid mask is `isfinite`, not the QA-masked field (2a).
9. **Pull the checkpoints and score the U-Net column.** `[major][model]`. **Done**
   (`5612621`, `cf04a4d`; 2l, 2m).
10. **Three or more seeds before adopting or rejecting any forcing or architecture
    change.** `[major][ml]`. Not started (2i).
11. **Stratify skill by distance to coast, marginal ice zone and ice edge.**
    `[major][eval]`. The current error pools the whole box, which is dominated by
    open ocean and pack where model and persistence agree trivially.
12. **Use the CDR's per-pixel uncertainty.** `[major][ml]`. `cdr_seaice_conc_stdev` is
    shipped and unused.
13. **Feed the wind-advected first guess, not raw wind.** `[minor][ml]`. Designed.

### Iceberg behaviour

14. **Grounding detection.** `[major][bergs]`. IBCSO depth against draught. This is
    the binding constraint according to 2d. Partly in progress: uncommitted code in `dakshin/berg_forecast.py` at the snapshot (2d). Not wired into any committed figure.
15. **Lock-in above 90% concentration.** `[major][model]` (Lichey and Hellmer 2001).
    The drift model has no term for it. The cheap fix (switch to the drift field
    above about 90%) is unbuilt (`docs/research/FORECAST_HORIZONS.md` §3.4, as cited
    in the backlog).
16. **Rerun the hindcast with the ECMWF wind.** The JSON still says "zero (slice 6
    pending)" (2d).
17. **Measure the p90 leave-one-out errors at 24, 48 and 72 hours.** `[minor][ml]`.
    ADR-025 names these as the exclusion radii.

### Routing claims

18. **Route-regret sweep over departure dates, with QA-suspect cells impassable.**
    `[critical][routing]` and `[critical][eval]`. One departure date is one sample (2e, 2a).
19. **Time-expanded router.** `[critical][routing]`. Designed. The single change
    that lets a forecast affect a route.
20. **Implement the 12-run sweep and report fuel relatively.** `[major][routing]`.
    ADR-021 is accepted in `docs/DECISIONS.md` but not implemented. Fuel is computed
    but never reported.
21. **Re-run the route-regret, destination-window and alternatives experiments on depth meshes.**
    The route is regenerated (`13861d9`, 8.66 days), but the experiments behind claims 1.6, 1.7 and the
    regret result were computed without depth (`docs/backlog.md`, `[major][eval]`).
22. **Confirm the day-0 route.** `478ecd2` changed the snapping rule that made day 0 hinge on one
    ice-locked node. Its commit message says the tests cover every departure day. The backlog line that
    reported day 0 as not solving was removed in `13861d9`. Not re-run in this pass.
23. **Maitri's offload point.** `[major][data]`. Unknown, so Maitri is excluded from
    the destination window.
24. **Vessel calibration.** `force_limit` is borrowed from another hull (`[major][vessel]`);
    the ice class is single-source (`[major][vessel]`); `max_ice_conc = 80` is a
    stand-in (`[major][routing]`) that POLARIS can only replace with a thickness
    output (`[major][ml]`).
25. **Mesh cell size at the station.** The cell containing Bharati spans 1.25 degrees,
    about 139 by 49 km (`[major][routing]`). The "station cell closed, approach open"
    comparison is between two neighbouring cells of that size.

### Documentation and claims hygiene

26. **Correct the claims listed in Appendix A.** Several are in the ledger itself.
27. **README rewrite for a physical oceanographer.** Queued in `docs/CURRENT_STATE.md`
    as the owner's second end-of-build ask. Not done in committed form. `README.md` was modified and uncommitted at the snapshot, so it is in progress elsewhere.
    **Done in `0cda289`** (2026-11-22 04:45 UTC), with the mismatches in Appendix A items 31, 32 and 40.

### Added 2026-11-22 (from stages 6 to 11)

28. **Make the generator emit the batch credentials cell (or a flag for it).** The recipe is
    documented in `dakshin/kaggle/README.md` (`779cf83`) but the swap is manual (2l).
    Not in `docs/backlog.md` as of this pass's edit.
29. **Assert the training cell is a code cell, and that a run's output holds four `.pt`
    files; add a per-stage smoke test (imports, input mount, one download).** 2l,
    lessons 1 and 8. The README lists the cell-type check as a manual step only.
30. **Decide the stale-input scope with the owner.** The JSON shows stale RMSE beating
    raw at leads 3 to 7 and stale IIEE beating raw at leads 1 to 5, while the prose
    rejects the whole live edge on lead-1 RMSE (2o).
31. **Reconcile ADR-027 with lead 7.** Corrected IIEE is 5.2% worse than raw at lead 7
    and CRPS is not computed, yet the decision record and the site include lead 7
    (2m, 2n). Either shorten the claimed horizon or compute CRPS.
32. **A season with a real opening, or a sensitivity measure.** All 298 verifiable
    target values are "not reachable", so the decision record has no positive case
    (2n). The forecast archive cannot be back-filled.
33. **Archive wave files per cycle, like `siconc`.** Gates the corrected-ice router
    check (`docs/backlog.md`, `[med][harvest]`; 2p).
34. **Correct the documents listed in Appendix A items 29 to 41.**
35. **Owner decision on the local paper** (`paper/`, gitignored). Not pushed (2q).

---

## Appendix A. Known inconsistencies between documents and figures

Listed, not fixed. Each entry names the files on both sides.

1. **Persistence IIEE at lead 3 (resolved in `1a9ff0b`).** `docs/RESOLUTION_STUDY.md` gives 211.7 (10³ km²);
   `dakshin/figures/resolution_study.json` and `realforecast_hindcast.json` give
   277.2.
2. **Persistence IIEE "decays with lead" (resolved in `1a9ff0b`; the word is gone from `RESOLUTION_STUDY.md`).** `docs/RESOLUTION_STUDY.md` says so.
   The JSON rises with lead: 187.7, 277.2, 319.2, 353.3.
3. **"Raw CMEMS beats persistence at every lead."** `docs/TRUE_CLAIMS.md` §1.13.
   True for RMSE. Not true for IIEE at lead 1 (2b).
4. **8.6 days in the prototype results.** `docs/PROTOTYPE_RESULTS.md` now has an update note
   (`13861d9`) giving 8.66 days, but its routing section still headlines 8.58 days and §4 and §5 use
   the older figures. `docs/TRUE_CLAIMS.md` §1.11 gives 8.7 days (8.66) as re-derived.
5. **"200 km box" around Bharati.** `docs/TRUE_CLAIMS.md` §1.5 and
   `docs/PROTOTYPE_RESULTS.md` §2. The box is ±200 km, so 400 km on a side
   (`dakshin/audit_ice_quality.py`).
6. **D15A "beside Bharati's approach".** `docs/TRUE_CLAIMS.md` §1.10. The backlog
   records it at 66.63 S, 81.92 E, about 390 km from the station
   (`docs/backlog.md`, `[minor][pitch]`).
7. **Wind in the berg hindcast.** `dakshin/figures/berg_hindcast.json` says
   "zero (slice 6 pending)". `docs/CURRENT_STATE.md` says slice 6 is done.
8. **"R << 1 in every segment." (the phrase is absent from `scripts/berg_resolution.py` at HEAD; `1a9ff0b` corrected the claim).** Docstring in `scripts/berg_resolution.py` and
   `dakshin/berg_forecast.py`. `berg_hindcast.json` segments give R from 0.037 to 1.73.
9. **Stationary count.** `docs/backlog.md` says "persistence 0 km on 75/88 segments".
   The segments give 75 of 88 at 3 km or less, including the 7 unknown. Exactly
   zero is 63 of the 81 usable segments.
10. **Seed and split of the re-run.** The brief says `docs/CURRENT_STATE.md`
    records an identical seed and split. It does not (2g).
11. **Test count.** `docs/CURRENT_STATE.md` gives both 186 passed (Done tonight)
    and 194 passed (Progress since). The later figure is probably current.
12. **F2 and F4 status.** `docs/backlog.md` (`[minor][features]`) says "not started".
    `docs/CURRENT_STATE.md` and the git history (`93ff026`, `7307f12`) say done.
13. **`dakshin/data` as a symlink.** `docs/backlog.md` BLOCKER and item 10 of
    `docs/audit/CORRECTIONS.md` (status OPEN, "P0") say it is a symlink into a
    sibling worktree. In this pass it is a real directory with 1,096 files
    (403 MB), and the `.gitignore` comment still describes the symlink. Either
    the fix was made without the registers being updated, or the registers are right
    and the directory listing is wrong. The first is more likely; check with `ls -la dakshin/data`.
14. **`min_depth` inert.** `docs/backlog.md` (`[major][routing]`) says the constraint
    can never fire. `docs/TRUE_CLAIMS.md` §1.17 and `docs/CURRENT_STATE.md` (slice 7)
    say the block is in both routers.
15. **Feature channel definitions.** `dakshin/features.py` docstring: channel 8 is
    `background(t) - observed(t-1)`; channels 1 to 7 are `observed(t-1)` to
    `observed(t-7)`. The code uses `background[t] - observed[t]` and
    `observed[t-lag+1]`, i.e. observations t to t-6. The docs in `docs/PROTOTYPE_RESULTS.md`
    describe the code.
16. **Checkpoint size.** `docs/DECISIONS.md` ADR-023 says weights are about 60 MB.
    `scripts/pull_checkpoints.sh` says about 8 MB each (about 32 MB for four).
17. **Checkpoint location.** `.gitignore` names `dakshin/checkpoints/` for committed
    weights. `dakshin/model_io.py` and `scripts/pull_checkpoints.sh` use
    `models/sic_correction/checkpoints/`.
18. **ADR-021 status.** `docs/DECISIONS.md` gives it no status, and the text reads
    as adopted. `docs/backlog.md` says it is designed and never implemented.
19. **Corrections register path.** `.gitignore` cites `docs/CORRECTIONS.md`. The file
    is at `docs/audit/CORRECTIONS.md`.
20. **Duplicate USNIC file.** `docs/backlog.md` says `data/icebergs/usnic_antarctic_20260902.csv`
    is byte-identical to the archived 2026-08-27 issue. Not verified in this pass.
21. **SST source.** `scripts/berg_melt.py` reads `cmems_sst_<cycle>.nc`. No script produces
    it and `ATTRIBUTION.md` does not list it (2k).
22. **Store of the prototype's numbers.** `docs/PROTOTYPE_RESULTS.md` says the figures
    are the numbers to quote. The checkpoint and output that produced them are not
    in the repository (2g).
23. **Stale backlog line on score_cmems_archive.** The backlog entry is dated
    2026-09-03. The file's git history begins 2026-11-19 (`5be27ca`).
24. **Weights, GitHub.** `docs/CURRENT_STATE.md` says commit the checkpoints and attach to
    a release; ADR-023 says weights are never synced over Iridium. Both can hold. They
    are different questions.
25. **Inputs removed during this pass.** `data/bathymetry/raw/` (the 254 MB IBCSO file) was present at 18:11 and absent at 18:21. `/home/agent/.venvs/isih-demo` was present at about 18:08 and absent at 18:27. This pass did not delete either. The cause is not identified. Anyone running the subset or demo steps should check both first.
26. **Snapshot date.** This document reads the repository between about 17:56 and 18:21 on 2026-11-21. Commits `478ecd2`, `24317da`, `f67493b` and `13861d9` reached `main` at 18:21, after the reads. Statements about the route, bathymetry, router and demo are dated to the earlier state. Appendix C lists those commits.
27. **The claims verifier tests a withdrawn figure.** `scripts/verify_claims.py` checks
    `transit days (rounded)` = 8.6 against `dakshin/figures/route_regret.json`. That file was computed without
    depth, and `docs/TRUE_CLAIMS.md` §1.11 now uses 8.66 days. The "PASSED 29" result therefore includes a
    check on the superseded figure.
28. **Destination-window figure.** Section 2a quotes 23 of 31 days closed at Bharati (ice-only). The committed
    file now says 31 of 31 (`1a9ff0b`, depth in the mesh). The text in §2a is the snapshot value. Superseded again by item 32.
29. **Hindcast numbers moved between passes.** Sections 2b and 2c carry the 76-cycle lead-1 values (raw 0.10199, persistence 0.11977, IIEE 195.1 and 187.7 thousand km²). `dakshin/figures/realforecast_hindcast.json` and `resolution_study.json` at HEAD have 77 cycles (0.10219, 0.11914, 196,031, 186,997 km²). Leads 3, 5, 7 agree. `docs/RESOLUTION_STUDY.md` still prints the 76-cycle raw and persistence columns ("187.7 vs 195.1").
30. **The Kaggle notebook delta was not in the repository.** `docs/CURRENT_STATE.md` Update 4 said the glob and retry fixes are "both now in `make_notebook.py`, commit 0848d7e"; the commit has only the retry. The generator's credentials cell uses Kaggle Secrets, which batch runs cannot read, and nothing in `dakshin/` referenced `cmems-creds` or a glob (grep, 2026-11-22). Partly resolved by `779cf83` (`dakshin/kaggle/README.md`, `kernel-metadata.json`, corrected CURRENT_STATE sentence): the recipe is documented, the generator still emits the Secrets cell (2l). The v4 figures (3e-5, 0.012, best val 0.0434 to 0.0439) remain in `docs/CURRENT_STATE.md` prose only.
31. **Three statements about the Bharati approach.** `real_route.json` at HEAD: `approach_closed_at_ice_limit: false`. `README.md` section 5: "finds the Bharati approach closed ... the closest reachable cell is 50.6 km away". The 25 km check (`corrected_forecast.json`): not reachable. The track ends 50.6 km short. They are reconcilable (2p) but the README sentence is not what the JSON flag says. Section 2f's table is the pre-`0d7be9f` file.
32. **Destination-window figure, again.** Section 2a and item 28 say the committed file reports Bharati closed 31 of 31. `dakshin/figures/destination_window.json` at HEAD (`06d7d70`) scores "Bharati" at the route's arrival point (23 of 31 closed, 74.2%) and adds a separate row "Bharati station cell (ashore)" (31 of 31). `README.md` section 4 calls the 23-of-31 row "Bharati's own cell", which the JSON's `target_note` contradicts. README's "four of the eight apparently open days were exact-zero artefacts" is the earlier ice-only count and was not re-checked against the regenerated file.
33. **NRT roll-off.** `docs/WEAKNESS_ANALYSIS.md` section 11: "after ~30 days". `scripts/download_nsidc_nrt.py` docstring and `5f32ae3`: "about 3 months". `docs/CURRENT_STATE.md`: rolls off from 2026-11-24, which is three months after the first file (2026-08-24).
34. **Seed variance against margin.** `docs/WEAKNESS_ANALYSIS.md` section 11 and `README.md` section 1 say the run-to-run spread (up to 0.012) is the same size as the RMSE margin over raw CMEMS, with the margin given as 0.011 to 0.013. The hindcast margins computed from `realforecast_hindcast.json` are 0.0108, 0.0174, 0.0152, 0.0129. The spread is on the held-out training split and the margin on the hindcast; they are different sets (2l, lesson 9). `ad97f88` corrected the WEAKNESS sentence to 0.0108 and 0.0129 at leads 1 and 7 and gives 0.0174 and 0.0148 for leads 3 and 5; the lead-5 value from the JSON is 0.10981 minus 0.0946 = 0.0152, not 0.0148. `README.md` section 1 still says "the same size".
35. **Under-sourced Kaggle claims in `docs/WEAKNESS_ANALYSIS.md` section 11.** "Mid-November ... 3 failed runs to diagnose": Update 4 gives two runs failing on the mount layout (v1, v2) and one on the NSIDC 500 (v3), and does not date v1 or v2; only the `0848d7e` message dates the 500 ("2026-11-22"). So "mid-November" may refer to when Kaggle changed the layout, which no file records. "Retrain is 23 min on a free T4" is in that section and in `docs/study/PHYSICS_AND_PAPERS.md`; no run log is committed to check it.
36. **ADR-027 against lead 7.** Corrected IIEE is 5.2% worse than raw CMEMS at lead 7 (2m) and CRPS is uncomputed, so ADR-027 as written would not claim lead 7. The decision record (298 decisions, all four leads), the README tables and the site AI edge include it. The README states the lead-7 IIEE loss; it does not mention ADR-027.
37. **"Never flipped" understates the decision record.** `corrected_all.json["verification"]` says the station never changed state. The `cycles` block shows all 298 `satellite_target` and all 78 `satellite_day0_reachable` values false: closed throughout, so there is no positive case (2n). The first write-up (`0c3b9ef`) said "closed nearly all season". `ad97f88` since states the always-"not reachable" point in `docs/PROTOTYPE_RESULTS.md` and the README; I did not find the 78 closed day-0 verdicts stated in either file.
38. **Monthly commit counts do not reproduce.** The first pass gave 30, 155, 72, 75 (sum 332) as of 17:56 on 2026-11-21. `git rev-list --count 44e3efa` (the commit this pass starts from, 18:28) is 337, by month 27, 158, 71, 81. Commits landed after 17:56 explain extra November commits (11 non-harvest commits between 18:00 and 18:21 alone), but not the August, September and October shifts (-3, +3, -1). Author date in the commit's own timezone and in UTC give the same buckets, so timezone bucketing is not the cause. Not established.
39. **`docs/CURRENT_STATE.md` is internally stale.** Update 4 and the overnight update sit above sections that still say slice 3 is "In flight", describe the Kaggle v6 as queued with a watcher, list the 186- and 194-test counts, and say the router closed the approach with "closest 50.6 km" (the "Done tonight" slice 6 row). The slice-3 commit `620d3a3` and `docs/PROTOTYPE_RESULTS.md` called the router full-resolution 1/12 degree; corrected in `0d7be9f` (2p).
40. **The stale-input verdict against its table.** Prose (`docs/PROTOTYPE_RESULTS.md`, section 11, README) rejects the live-cycle edge. `stale_history_eval.json` shows the stale correction beating raw on RMSE at leads 3, 5, 7 and on IIEE at leads 1, 3, 5 (2o). `docs/PROTOTYPE_RESULTS.md` quoted RMSE only until `ad97f88` added the IIEE and leads 3 to 7 sentence; the verdict was not changed and the README and section 11 still give the lead-1 RMSE alone.
41. **Original 2026-08-31 numbers reproduced to four decimals by v8, but not by v4.** `isih_skill_by_lead.csv` (v8) rounds to the headline at all four leads; v4 differs by up to 0.012 at leads 3 to 7 (`docs/CURRENT_STATE.md`). Not explained in the repository; v4's hardware is not recorded. Item 10 above is partly superseded: the hindcast JSON records "identical code, seed and split".

---

## Appendix B. Items marked resolved, checked against the code

- F1, F3: resolution study and currents study, done (`1a81215`, `d548eff`).
- F2: NEMO-native reader, done, untested on real NEMO output (`93ff026`).
- F4: melt estimate, done, labelled as an estimate (`7307f12`).
- Slice 7 bathymetry block: `dakshin/gates.py` `chart_gate` and the router's min-depth
  check (`ce236c7`).
- Iceberg drag-coefficient swap and the lambda sign: fixed in `models/iceberg/drift.py`
  (backlog `[resolved][ml]`).
- Harvest login failure and stale cycles: rejection rule and retries (`1a00b3b`,
  `47e0ce1`).
- The "Pareto set" naming: renamed; the sweep itself is still open (see 4.20).
- Checkpoints missing: committed with `SHA256SUMS` (`5612621`), Release `model-v0.1`; U-Net column scored (`cf04a4d`).
- Lead-1 n=76 hindcast files: regenerated at n=77 with the U-Net column (`cf04a4d`); the backlog line that asked for it was removed.
- NSIDC NRT archive not committed: committed with a manifest (`a6fdc83`).
- Kaggle numpy half-upgrade and NSIDC 500: pinned (`d7b0d0f`), retried (`0848d7e`). The mount-layout and credentials delta is documented in `dakshin/kaggle/README.md` (`779cf83`) but not emitted by the generator (Appendix A item 30).
- Router "closed" flipped to "open" by the arrival rule: `route_ends_km_from_station` reported (`0d7be9f`); the 1/12 degree router overclaim corrected.
- Decision record without a persistence baseline: added (`fb246b2`); the tie is disclosed.
- Training-years typo (2015 to 2020): corrected to 2019 to 2020 (`d10cc44`).

---

## Appendix C. Commits that reached main after this document's reads (2026-11-21, 18:21)

Listed in the order they appear in `git log`. Each is on `main`; this document was
written before they landed.

| Commit | Message (abridged) | Effect on the findings |
|---|---|---|
| `478ecd2` | Router: arrive anywhere navigable within one lattice cell of a station ashore | Changes how the router snaps the destination. The commit message says routes whose nearest node is navigable are unchanged. The commit message says the day-0 hinge is addressed; not re-run here. Affects §2e, §2f and §4 item 22. |
| `24317da` | Bathymetry to Cape Town: GEBCO_2020 north of 50 S, exact 0.05° grid over the whole sim box, 5 km shallowest buffer | Rewrites `scripts/subset_bathymetry.py` (243 lines). The subset grows from 1.36 MB to 3.50 MB. Adds the GEBCO attribution to `ATTRIBUTION.md`. Affects §2e and the runbook's data inventory. |
| `f67493b` | Demo: real seabed under the ship, chart light never PASS, decision chart gate on real route depths | Changes the demo's seabed and chart panels. Affects the synthetic-world row in §3. |
| `13861d9` | Regenerate the published route with depth in the mesh: 8.66 days, 16 km off Bharati; claim 1.11 re-derived | Replaces the 8.6-day route with 8.66 days and an endpoint 16 km off the station. Updates `docs/TRUE_CLAIMS.md` §1.11 and `docs/PROTOTYPE_RESULTS.md` (an update note at the top of its routing section). Removes the backlog line that asked for regeneration, and removes the line "GEBCO still not downloaded". Adds backlog items: re-run the three depth-free experiments; GEBCO north of 50 S from ERDDAP; `RealWorld` does not return depth. |

The `raw/` IBCSO file was absent at 18:21, the same minute that `24317da`
landed. That commit's script downloads its inputs to `data/bathymetry/raw/`. This document
does not establish whether the removal and the commit are related.

Uncommitted at the snapshot, and not in any commit: `dakshin/berg_forecast.py` (`BathymetryGrid`, assumed draught), `README.md`, and a new study file `docs/study/PHYSICS_AND_PAPERS.md` written by another agent. Later commit by another agent, on top of this document's commit: `aaddb78` (backlog inconsistencies).

**Working tree at the final commit (about 18:35 UTC).** The numbers in this document are the committed values at the snapshot. The checks above confirmed them against HEAD for `berg_hindcast.json`, `destination_window.json`, `realforecast_hindcast.json` and `real_route.json`. The working tree has since changed. `dakshin/figures/destination_window.json` reports Bharati closed on 31 of 31 days, against 23 of 31 committed (the earlier figure was ice-only). `berg_hindcast.json`, `route_regret.json`, `alternatives.json` and `vessel_comparison.json` are modified and uncommitted. A later regeneration will not match this document. Re-read the committed files before quoting.

**Later commits by other agents, on `main` after the snapshot.** `1a9ff0b` (truth pass: melt uses berg-relative speed; `RESOLUTION_STUDY.md` persistence IIEE corrected to 277.2 with the lead-1 nuance; the R << 1 phrase removed; docstrings aligned with code; regenerated `berg_hindcast.json`, `destination_window.json`, `route_regret.json`, `alternatives.json` and `vessel_comparison.json`). `1a9ff0b` also swept this document's uncommitted glossary and snapshot edits into its commit. `df7f39e` (melt rerun with berg-relative speed; top-level `requirements.txt`). The committed route-regret results changed too: the first three result rows now give 8.65, 8.63 and 9.00 days, against 8.61, 8.58 and 9.00 at the snapshot. Earlier, `09f6ad0` added the architecture and physics study docs and a README. The 0.03-day regret in §2a is therefore a snapshot number.

**Commit `a274a64` (after the snapshot).** The CMEMS workflow now runs the ECMWF wind harvest on every run and the USNIC list on Fridays. `scripts/harvest_cmems.sh` fetches SST (`cmems_mod_glo_phy-thetao_anfc_0.083deg_P1D-m`) under the same never-fail rule as the currents. These close the schedule gap in §2.2 and §4 item 4 (SST), and the "no schedule" statements in §2.4 and §2.5. The same commit adds a grounding-aware berg forecast, v2 (26 of 88 segments held, 4.13 km/day). §2d describes the snapshot version (4.35 km/day). Re-read those sections against HEAD before quoting. The SST and schedule statements in §2k and the runbook's §2.1 and §2.2 also describe the snapshot.

---

## Appendix D. Commits in `44e3efa..HEAD` not covered by Appendix C (UTC, 2026-11-21 unless marked)

46 commits, 4 of them harvest (`90d58e5`, `f8fa368`, `4a4e103`, `0fa7b32`, all "already_have"). Effects are taken from commit messages and diffs; none was re-run here.

| Commit | Time | Effect |
|---|---|---|
| `a6fdc83` | 18:37 | NSIDC NRT truth archive committed because it rolls off the server from 24 Nov and cannot be re-fetched (4.1) |
| `06d7d70` | 18:43 | Route regret, destination window and alternatives re-run on depth-aware meshes; changes the destination-window figure (Appendix A item 32) |
| `b9920e1`, `19c7f1c` | 19:00 | Per-berg forecast drift tracks and vectors for the chart (grounding-aware, caveats embedded); docstring matches mid-track grounding |
| `2ffa6b2` | 19:14 | uo, vo, waves and SST packed to int16: daily currents 10 MB to 3.9 MB at 0.05 mm/s error |
| `e724417` | 19:14 | `RealWorld` serves real seabed depth, so the chart gate is no longer UNKNOWN on real data |
| `2a7cfad`, `3106bb9` | 19:15, 19:16 | Transit prose quotes the depth-aware 8.66 days; hindcast JSON wind wording follows the measured R |
| `9cbab07`, `0d25c09`, `ed3a31c` | 19:34 to 19:40 | Backlog closes site items and adds the currents-versus-verification pairing gap; merge; state snapshot |
| `d7b0d0f` | 21:41 | numpy pinned in the Kaggle install cell (2l) |
| `5612621` | 23:16 | Four checkpoints committed from the 2026-11-21 re-run (2l) |
| `cf04a4d`, `1dc4e95` | 23:16, 23:18 | Hindcast and resolution study scored with the U-Net; results, resolution study and state updated (2m) |
| `620d3a3`, `a4c37a9` | 23:21 | Slice 3: corrected forecast for the live cycle and reachability check; docs (2n) |
| `0848d7e` | 2026-11-22 02:40 | NSIDC download retries with `.part` files (2l) |
| `d10cc44` | 03:47 | Training years corrected to 2019 to 2020; local `paper/` ignored (2q) |
| `9e332bd`, `0c3b9ef` | 04:05 | `corrected_forecast.py --all` decision record (raw 287, corrected 298 of 298); demo AI-correction panel and first doc write-up, without a persistence row (2n, 2q) |
| `0d7be9f`, `4437116` | 04:15 | Route honesty: `route_ends_km_from_station`, gated `CorrectedIceWorld` check, "1/12 degree router" overclaim removed (2p). The first commit also added two stray `.claude/worktrees` gitlinks; the second removes them |
| `fb246b2` | 04:18 | Persistence arm added (298 of 298); caveat welded to the JSON, doc and demo text (2n) |
| `d178f95` | 04:21 | Update 4 and `docs/WEAKNESS_ANALYSIS.md` section 11 (2q) |
| `6dc4719`, `e32332b`, `71a8b08` | 04:29 to 04:41 | Stale-history evaluation, verdict, state (2o) |
| `0cda289` | 04:45 | README results rewritten with the U-Net, decision record, stale-history rejection, release `model-v0.1` (2q) |
| `ad97f88` | 05:04 | Claims review by another agent, landed during this pass: adds the "always answers not reachable" caveat to the decision record (`docs/PROTOTYPE_RESULTS.md`, `README.md`); adds stale IIEE and leads 3 to 7 RMSE context to the stale-history paragraph; corrects the margin sentence in `docs/WEAKNESS_ANALYSIS.md` section 11; documents 4-connectivity in `scripts/corrected_forecast.py` |
| `779cf83` | 05:12 | `dakshin/kaggle/README.md` (batch recipe) and `kernel-metadata.json`; `docs/CURRENT_STATE.md` corrected on where the creds-glob lives; runbook and physics volumes refreshed (2l) |

**Not itemised in the table:** the four harvest commits (named at the top); six study-pack commits (`f84da4d`, `6e18a34`, `5356a69`, `e9164de` study docs, `53fc775` study guide index, `a640cba` merge); and five already in Appendix C (`1a9ff0b`, `df7f39e`, `a274a64`, `aaddb78`, `09f6ad0`). Every commit in `44e3efa..HEAD` is cited somewhere in this document by that accounting.

**Not covered here:** the companion viewer (separate repository) and the local paper. Re-read `dakshin/figures/*.json` before quoting any number in this document; several were regenerated during the window above.
