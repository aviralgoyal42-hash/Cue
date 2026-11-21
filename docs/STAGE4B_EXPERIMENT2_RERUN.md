# Stage 4 follow-up: Experiment 2b (15 inflow seeds)

Date: 2026-11-04.
- **Criteria:** C1–C4 unchanged (`docs/EXPERIMENT2_SUCCESS_CRITERIA.md`). The post-hoc metric is defined in `docs/EXPERIMENT2B_RERUN_CRITERIA.md`.
- **Size:** 15 inflow seeds × 20 sensor seeds = 300 runs per cell, 54,000 monitoring runs in total.
- **Outputs:** `results/stage4b/` (summary, all runs, figures). The comparison with Experiment 2 is `results/stage4b/exp2b_vs_exp2_comparison.csv`, made by `experiments/stage4b_compare.py`.

## How the pass map changed

Number of the 14 non-ideal sensor scenarios that pass C1–C3, per threshold:

| Threshold (mL) | 250 | 300 | 350 | 400 | 450 | 500 |
|---|---|---|---|---|---|---|
| Default sphincter, 3 seeds → **15 seeds** | 0 → 0 | 1 → 1 | 8 → **7** | 11 → **10** | 10 → 10 | 5 → 5 |
| Sphincter ×0.9, 3 seeds → **15 seeds** | 0 → 0 | 2 → **1** | 8 → **7** | 9 → **10** | 7 → 7 | 4 → 4 |

Overall, 69 of 180 combinations pass, against 72 with 3 seeds. Seven combinations changed result. Every one of them sat close to a limit.

**Now fail:**
- combined_bad at 350 mL, both strengths: false-alert run rate 0.087 and 0.077, above the 0.05 limit;
- mre_30pct at 400 mL, default: false-alert run rate 0.077;
- misaligned_at_4h at 300 mL, ×0.9: false-alert run rate 0.060;
- mre_40pct at 450 mL, ×0.9: false-alert run rate 0.060.

**Now pass:**
- delay_5min at 450 mL, ×0.9: lead 31.5 min, just above 30;
- drift_minus2ph at 400 mL, ×0.9: useful rate 0.973, lead 31.2 min.

**Reading:** with 60 runs per cell, a single false alert moved a rate by about 1.7 percentage points, so results near a limit could not be trusted. With 300 runs they are steadier. The conclusions from Experiment 2 still hold:
- no threshold passes for every fault;
- misalignment fails at every threshold of 350 mL and above;
- the anchor sensor passes at 350–450 mL for both strengths.

## Anchor sensor (11.17%), 15 seeds

| Strength | Threshold | Useful | False runs | Median lead (min) | POST-HOC band rate | Pass |
|---|---|---|---|---|---|---|
| ×1.0 | 350 | 1.000 | 0.003 | 123.6 | 0.223 | yes |
| ×1.0 | 400 | 1.000 | 0.000 | 83.9 | 0.987 | yes |
| ×1.0 | 450 | 1.000 | 0.000 | 45.9 | 0.773 | yes |
| ×0.9 | 350 | 1.000 | 0.007 | 113.1 | 0.197 | yes |
| ×0.9 | 400 | 1.000 | 0.000 | 72.9 | 0.983 | yes |
| ×0.9 | 450 | 1.000 | 0.000 | 38.7 | 0.810 | yes |

## POST-HOC band metric (true volume at the first useful alert in 350–450 mL)

This metric is **not a criterion.** At the 400 mL threshold:

| Sensor scenario | Band rate, default / ×0.9 |
|---|---|
| ideal | 1.000 / 1.000 |
| delay 5 or 15 min, missing 20% or 50% | 0.97–1.00 |
| anchor 11.17% | 0.987 / 0.983 |
| combined_bad | 0.783 / 0.777 |
| mre_20pct | 0.673 / 0.713 |
| drift −2%/h, drift +2%/h | 0.65 / 0.64, 0.48 / 0.55 |
| mre_30pct | 0.380 / 0.383 |
| mre_40pct | 0.190 / 0.223 |
| gain −20%, gain +20% | 0.057 / 0.053, 0.033 / 0.027 |
| misaligned_at_4h | 0.000 / 0.000 |

This confirms E26: noisy, biased or misaligned sensors that "pass" C1–C3 do so with alerts at the wrong volume.

## Lead time is not independent evidence

Lead time ≈ (adverse-event volume − alert volume) ÷ inflow. With inflow around 0.02 mL/s, a 100 mL gap is about 80 min. The median lead times above mostly restate the threshold and the filling rate. They are not separate evidence that Cue works.
