# Experiment 3b: POST-HOC, OPTIMISTIC sweep on patterns that empty (frozen)

**Written 2026-11-04, before any Experiment 3b run.** Any change is logged at the bottom. The original text stays as it is.

## Status of this experiment

- **POST-HOC.** The patterns were chosen **after** seeing the stimulation map and Experiment 3, because they empty. This answers E47: the earlier threshold and max-duration sweeps ran only on a pattern that never empties.
- **OPTIMISTIC.** These patterns have **no sphincter co-activation**, so they assume a stimulator that drives the detrusor alone. Sacral roots carry both kinds of fibre, so this is the favourable case. The declared reference pattern (co-activation 0.5) empties nothing, and that remains the planned result.
- Nothing here may be presented as the planned reference, as a recommended setting, or as a clinical parameter. All values are normalised model drives or ASSUMED cutoffs. No setting becomes a new default because of this experiment.

## Grid (agreed with the user before running)

| Factor | Values | Label |
|---|---|---|
| Stimulation pattern | `e0.6_s0.0_5on5off`, `e1.0_s0.0_5on5off` | ASSUMED, chosen post-hoc |
| Maximum duration | 30, 60, 120 s | ASSUMED |
| Alert threshold | 350, 400, 450 mL | ASSUMED |
| Pressure ceiling | 40, 55, 70 cmH₂O | ASSUMED |
| Sphincter strength | ×1.0, ×0.9 | ×1.0 SOURCED upstream; ×0.9 ASSUMED |
| Inflow seeds | 42 and 1–14 (15 seeds) | ASSUMED |

That is 2 × 3 × 3 × 3 × 2 = **108 settings**, × 15 seeds = **1,620 runs**, all factors crossed.

**Held fixed**, as in Experiment 3: anchor sensor (11.17%, best case), prompt user, "ok" pressure channel, 100 mL volume stop, 30 min lockout, 60 s ultrasound rate, 12 h duration, 1000 mL volume ceiling. Sensor, user and pressure seeds equal the inflow seed.

## Declared limitation: reduced grid

The full grid (4 patterns, 3,240 runs) was estimated at about 4.3–5 h, over the agreed 2-hour limit, so the user chose this reduced grid.

**Dropped:** the two continuous patterns, `e0.6_s0.0_continuous` and `e1.0_s0.0_continuous`. **Nothing here describes continuous stimulation.** Their only data remain the 3-seed Experiment 3 results.

## Criteria (the same as Experiment 3, unchanged)

Safety invariants A2, A3 and A4 must hold in **100%** of runs.

For each of the 108 settings:

| ID | Criterion | Required |
|---|---|---|
| P1 | Sessions that void ≥ 50% of the pre-session true volume | ≥ 80% of sessions |
| P2 | Runs with no leakage outside sessions after the first alert | ≥ 95% of runs (with 15 runs per setting, every run must be clean) |
| P3 | Sessions in which true p_D never exceeds the ceiling by more than 5 cmH₂O while stimulating | ≥ 95% of sessions |

"Full loop works" for a setting means P1, P2, P3 and the invariants all hold.

## Reported for every setting, pass or fail

Number of sessions, median residual, which cutoff ended each session, maximum true p_D during stimulation, overflow, leaked volume, and maximum volume. Main effects of each factor are also reported, along with any interactions visible in the crossed grid.

## Consistency check (must pass)

Runs that share a setting and seed with Experiment 3 (seeds 42, 1 and 2; 60 s duration; 400 mL threshold; all three ceilings; the same two patterns) must reproduce the Experiment 3 results exactly. If they do not, the experiment is not valid and that is reported.

## Change log
(empty)

- 2026-11-04, after the run: **no criterion changed.** The script that performed the consistency check was wrong and was fixed (E58). It compared numbers read from a CSV with numbers in memory, and a parser rounding of about 1e-14 made it report a failure. It now compares the two result files exactly, across more columns and the session table as well. The requirement is still an exact match, and it passes.
