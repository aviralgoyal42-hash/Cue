# Experiments 3 and 4 rerun with 15 seeds: plan (frozen)

**Status: FROZEN, 2026-11-04, before any run of this rerun.** Any later change is logged at the bottom. The original text stays as it is. This is the last experiment in the project.

All values are ASSUMED or carried over unchanged, the sensor is a synthetic experimental proxy, and nothing here shows clinical safety or effectiveness.

## What changes

Only the number of seeds. Each cell goes from 3 inflow seeds (42, 1, 2) to 15 (42 and 1 to 14).

As in the original experiments, one seed value sets the inflow, sensor, user and pressure-channel random streams together. This must stay the same, or seeds 42, 1 and 2 could not reproduce the old runs.

## What does not change

- The grids, in `experiments/stage6_experiments3_4.py`. The new script calls those same functions.
- The criteria, in `docs/STAGE5_EXPERIMENT3_4_CRITERIA.md`, including its logged second reference.
- Every ASSUMED value. `config.py` is not edited. The 15 seeds are set in the new script, and `EXPERIMENT3.physiology_seeds` stays at 42, 1, 2.
- The session guard stays off. This reruns Experiments 3 and 4, not Experiment 7.

## Grid

| Part | Original runs | Rerun | What it covers |
|---|---|---|---|
| Experiment 3 main | 288 | 1,440 | 8 patterns × 3 ceilings × 2 ultrasound rates × 2 sphincter strengths |
| Experiment 3 reference sweeps | 24 | 120 | Thresholds 350 and 450 mL, durations 30 and 120 s, 2 strengths |
| Experiment 4 faults | 324 | 1,620 | 27 fault cases × 2 references × 2 strengths |
| **Total** | **636** | **3,180** | |

Experiment 3 has 104 settings. Experiment 4 has 108 cells.

## Estimated run time

**About 8.7 h, with a likely range of 7 to 9 h, on 12 cores.**

| Basis | Time per run | Total |
|---|---|---|
| Experiment 7 rate, flat: 3.8 h for 1,710 runs | 8.0 s of wall time | 7.1 h |
| Experiment 7 rate, adjusted for this grid: old runs averaged 117.8 s each | 9.8 s of wall time | **8.7 h** |

The adjusted figure is the better one. In Experiment 7, summed run time divided by 12 cores matched the wall time (3.78 h against 3.80 h), so that method is sound. This grid is heavier than Experiment 7, because half of Experiment 4 uses the co-activation reference (173 s per run, against 82 s without it).

Experiment 7 took about 40% longer than estimated because I had used no-fault run times for fault runs (E74). The old run times here already include those slow runs, so I have not added 40% on top. If the computer sleeps, the sweep pauses and takes longer. Partial results are saved every 25 runs, and the script can continue from them.

## Reproduction check (must pass)

For seeds 42, 1 and 2, every run row and every session row must match `results/stage6/` exactly, for Experiments 3 and 4, in every shared column except `runtime_s`. Files are compared to each other with exact number reading (E58), and by value rather than storage type (E73).

If this fails, that is reported as a result, and the scores are not presented as an extension of the old experiments until the cause is known.

## Verdicts

**Experiment 3, per setting, unchanged:**
- P1: at least 80% of sessions void at least 50%.
- P2: at least 95% of runs have no overflow after the first alert. With 15 runs this means every run.
- P3: at least 95% of sessions stay within the ceiling plus 5 cmH₂O.
- "Full loop works" means P1, P2 and P3 all pass.
- A2, A3 and A4 hold in 100% of runs.

**Experiment 4, unchanged:**
- A2, A3 and A4 hold in 100% of runs, under every fault.
- With a dead pressure channel and an estimate stuck high, every session ends at maximum duration.
- Everything else is reported, not passed or failed. To show which results moved, I will also mark cells that cross the P1, P2 or P3 lines. Those marks are descriptive, not criteria.

**A verdict change** is any setting whose P1, P2, P3, full-loop or invariant result differs from `results/stage6/exp3_settings_summary.csv`, or any Experiment 4 requirement that changes. Every one is listed and logged in section 5 of `VALIDATION_AND_LIMITATIONS.md`, whichever way it moved.

## Expected from data already seen

Stated now so it cannot be claimed as a discovery later.

- **The working count of 38 of 104 may fall.** With 3 seeds, one overflow in about 20 runs would usually go unseen. With 15 seeds, a single overflowing run fails P2.
- **The peak on the stuck-high declared reference should rise from 58.6 to 59.4 cmH₂O**, as the Experiment 7 rule-off runs already showed (E80).
- **The peak in the other Experiment 3 settings may rise above 58.5 cmH₂O** for the same reason: more seeds find more of the noise.
- **The declared reference should still fail everywhere.** Experiment 7 rule-off runs and Experiment 3b point that way.

## Old results

`results/stage6/` and every other old result folder are read and never written. A SHA-256 hash of every old result file is taken before the sweep and checked after it. New results, including traces, go to `results/task4/`.

## Declared limitations

- These limits carry over from Experiments 3 and 4: the sensor is a best-case or synthetic proxy, the model has no dyssynergia and no sacral anatomy, and all stimulation is hypothetical.
- 15 clean runs give a lower bound of about 82%, not 95% (E68).
- The second reference was chosen after seeing the stimulation map, and all patterns without co-activation are the optimistic case.
- The seeds are not independent across cells. The same seed gives the same inflow in every cell, so cells are compared on matched runs, and a single unusual seed can affect many cells at once.
- This rerun is not blind: 3 of the 15 seeds are the original ones, and I have seen Experiments 3b and 7.

## Change log
(empty)
