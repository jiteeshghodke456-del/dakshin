# Sea-ice locking on the iceberg hindcast

Run on 2026-11-24. Scored once, at the paper's default parameters.

**Result in one line:** adding sea-ice locking did not reduce the hindcast
error on our 88 segments. It left the still bergs about where they were and
made the moving bergs worse. Persistence still beats every variant.

## The rule

Marson, J. M., Myers, P. G., Garbo, A., Copland, L., & Mueller, D. (2024).
Sea ice-driven iceberg drift in Baffin Bay. *JGR Oceans*, 129, e2023JC020697.
https://doi.org/10.1029/2023JC020697

The paper adds sea-ice locking (SIL) to the NEMO iceberg module. In dense,
strong pack ice a berg stops moving through the ice and moves with it.

At each step, at the berg position:

- `V_sumF` is the berg velocity from all other forces.
- `V_si`, `A` and `h` are the sea-ice velocity, concentration and thickness.
- Ice strength: `P = P* · h · exp(−20 (1 − A))`, with `P* = 20,000 N/m²` (Eq. 4).
- Drag threshold: `P_s = ½ · ρ_si · c_si · h · |V_si − V|²`, with
  `ρ_si = 916.7 kg/m³` and `c_si = 0.9`. This is the sea-ice drag of Eq. 2 per
  unit of berg width. `P_t = 0.8 · P_s`.
- Concentration thresholds: `A_s = 0.90`, `A_t = A_s − 0.04 = 0.86`.
- A ramp `α` goes from 0 at the lower threshold to 1 at the upper one (Eq. 5).
  It is applied to `A` and to `P`.
- `λ = α_A · α_P` (Eq. 6).
- Berg velocity: `V = (1 − λ) · V_sumF + λ · V_si` (Eq. 7).
- At `A ≤ 0.15` sea ice has no effect.

The code is `models/iceberg/sil.py`. The integrator hook is the `ice_field`
argument of `forecast_track` in `dakshin/berg_forecast.py`.

## Where our version differs from the paper

1. **Berg dynamics.** We use the closed form of Wagner, Dell and Eisenman
   (2017), not NEMO-ICB.
2. **No wind.** Wind is set to zero, as in the existing hindcast.
3. **Surface currents only.** No average over the keel depth.
4. **Daily sea ice.** We use day 0 of each archived CMEMS cycle, interpolated
   in time. The paper uses the model's own time step.
5. **The ramp sign.** The printed Eq. 5 divides by `(v_t − v_s)`, which is
   negative. We use `(v_s − v_t)`.
6. **The velocity inside `P_s`.** NEMO-ICB uses the berg's own velocity. We
   use `V_sumF`, because a closed form has no berg momentum to step.
7. **The unlocked case.** In the paper an unlocked berg can still feel
   sea-ice drag when `A > 0.15`. Our drift model has no such term, so an
   unlocked berg is plain WDE17. One consequence: the 15 % floor never
   changes anything in our version, because `λ` is already zero below
   `A_t = 0.86`.

Four sea-ice dates are stale in the archive (`KNOWN_STALE.md`). Each was
filled from the previous good day: 09-20 from 09-19, 10-11 from 10-10, 11-10
from 11-09, 11-17 from 11-16.

## Data

- 88 segments between consecutive weekly USNIC fixes, 4 Sep to 20 Nov 2026,
  eight bergs, inside 0–80°E and 55–78°S.
- 13 segments moved more than 3 km ("moving"). 75 did not ("still").
- Nine of the 13 moving segments are one berg, C39.
- Sea-ice data was present at every berg-hour. No step fell back for lack of ice.

## Results

Landing error in km/day, shown as median (mean). A held berg predicts no
further motion and is scored from where it was held.

| Variant | Held | All 88 | Moving 13 | Still 75 |
|---|---|---|---|---|
| Persistence (berg did not move) | – | 0.00 (0.39) | 2.45 (2.54) | 0.00 (0.02) |
| v1: WDE17 only | 7 | 4.31 (4.98) | 6.01 (5.82) | 4.23 (4.84) |
| v2: + grounding | 26 | 4.13 (4.52) | 6.01 (5.62) | 3.95 (4.33) |
| **v3: + SIL** | 7 | 4.38 (5.40) | 6.40 (8.60) | 4.29 (4.85) |
| **v4: + grounding + SIL** | 25 | 4.25 (4.83) | 6.40 (7.83) | 3.52 (4.31) |

v1 and v2 reproduce `berg_hindcast.json` row for row. The 4.35 km/day quoted
there is v1 over the 81 segments that were not stopped at the coast. The 4.31
here is the same run over all 88.

Segment by segment, v3 against v1: better on 38, worse on 44, equal on 6.

### SIL diagnostics (v3)

| | |
|---|---|
| Berg-hours integrated | 14,440 |
| Hours with any locking (`λ > 0`) | 85.3 % |
| Hours fully locked (`λ = 1`) | 75.6 % |
| Hours with no sea-ice data | 0 % |
| Segments with any locking | 82 of 88 |

Sea ice at the observed berg positions, sampled at noon each day:

| | Still bergs | Moving bergs |
|---|---|---|
| Mean ice concentration | 0.92 | 0.87 |
| Share of days at `A ≥ 0.90` | 78 % | 62 % |
| Mean ice speed | 6.7 km/day | 12.3 km/day |

### Sensitivity (not used to pick anything)

v3 re-run with other thresholds. Median (mean) km/day.

| `A_s` | All 88 | Moving 13 | Still 75 | Hours fully locked |
|---|---|---|---|---|
| 0.85 | 4.82 (5.56) | 6.64 (8.89) | 4.29 (4.98) | 86.7 % |
| **0.90 (paper)** | 4.38 (5.40) | 6.40 (8.60) | 4.29 (4.85) | 75.6 % |
| 0.95 | 4.38 (5.28) | 5.92 (7.84) | 4.26 (4.83) | 55.9 % |

`P*` at 10,000, 20,000 and 40,000 gave the same numbers to two decimals at
every `A_s`. So the strength test never decided the outcome here. Locking was
set by concentration alone.

## What it means

**Still bergs.** These bergs did not move, yet the model sea ice around them
drifts at 6.7 km/day on average. Locking a still berg to that ice moves it
about as far as the current did (median 4.29 against 4.23 km/day). Swapping
the current for the ice does not explain why these bergs stay put. Grounding
does part of that job: v2 holds 26 segments and lowers the still median to
3.95. Adding SIL on top gives 3.52 median but the same mean (4.31 against
4.33), so that gain is not robust.

**Moving bergs.** The moving bergs travelled a median of 2.45 km/day. The
model sea ice at their positions moves at 12.3 km/day. When the rule locks
them to that ice they overshoot. SIL was worse than WDE17 alone on 10 of the
13 moving segments and better on 2. The mean error rose from 5.82 to 8.60
km/day.

**Persistence.** "The berg did not move" beats every variant, on moving and
still segments alike. On the moving segments v1 beat persistence 2 times in
13 and v3 once.

**Sensitivity points one way on the mean.** The less locking, the lower the
mean error on the moving segments: 8.89 at `A_s = 0.85`, 8.60 at 0.90, 7.84 at
0.95, and 5.82 with no locking at all (v1). The medians are closer and do not
order the same way: 5.92 at `A_s = 0.95` against 6.01 for v1. This describes
the grid. No value was chosen from it.

## What this does not show

- **It is not a test of the paper's result.** The paper's bergs are in Baffin
  Bay and were checked against beacon tracks. Ours are giant Antarctic
  tabular bergs at USNIC's tracking size (about 10 nautical miles on the long
  axis, or 20 square nautical miles), and 75 of our 88 segments show no motion.
- **We cannot separate the rule from its inputs.** A bad landing point can
  come from the locking rule, from the CMEMS ice velocity, from the missing
  wind, or from a berg dragging its keel. This data cannot tell these apart.
- **Thirteen moving segments, nine from one berg.** That is too few to
  generalise from.
- **Weekly fixes, accurate to a few km.** There are no beacons. We only see
  where a berg was a week later, not the path it took. A berg that was locked
  for two days and free for five looks the same as one that drifted slowly
  all week.
- **Berg thickness and keel depth are assumed.** USNIC publishes neither.

## How to reproduce

```
python scripts/berg_sil_hindcast.py      # writes dakshin/figures/berg_sil_hindcast.json
python -m pytest models/iceberg/test_sil.py dakshin/test_berg_forecast.py dakshin/test_ice_field.py -q
```

The script stops if v1 or v2 no longer reproduce `berg_hindcast.json`.
