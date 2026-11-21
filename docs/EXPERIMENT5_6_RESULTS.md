# Experiments 5 and 6: results (extra work)

Date: 2026-11-04. Criteria were frozen in `docs/EXPERIMENT5_6_CRITERIA.md` and not changed. Both experiments are open-loop monitoring on the Experiment 2b traces, with 150 runs per cell (15 inflow seeds × 10 sensor seeds).

Files: `results/extra/exp5_device_params_summary.csv` and `results/extra/exp6_misalignment_summary.csv`. All numbers are model predictions with a synthetic sensor.

## Experiment 5: device parameters (one at a time)

Number of passing combinations, out of 12 (4 sensor scenarios × 3 thresholds), per sphincter strength:

| Variant | Default sphincter | ×0.9 | Mean alerts per run, all cells | Mean alerts per run, 30% error |
|---|---|---|---|---|
| Default (window 5, confirm 3, hysteresis 50, timeout 600) | 7 | 6 | 3.73 | 10.26 |
| Median window 1 | 7 | 6 | 11.93 | 30.64 |
| Median window 3 | 7 | 7 | 6.39 | 17.84 |
| Median window 9 | 7 | 6 | 1.98 | 4.89 |
| Confirmation 1 | 7 | 7 | 4.89 | 13.82 |
| Confirmation 5 | 7 | 6 | 3.16 | 8.67 |
| Hysteresis 25 mL | 7 | 6 | 5.19 | 12.81 |
| Hysteresis 100 mL | 7 | 6 | 2.21 | 6.05 |
| Stale timeout 300 s, 1200 s | 7 | 6 | 3.73 | 10.26 |

**Findings:**
- **No single device setting changes the overall picture.** Pass counts move by at most one, and each change swaps one marginal case for another. Slower settings (window 9, confirmation 5) pass mre_30pct at 400 mL, but lose anchor_11pct at 450 mL (×0.9) and missing_50pct at 450 mL (default). The cost is more delay.
- **Misalignment fails at all 60 cells.** No device setting rescues it (0 of 60 passes, with the 350–450 mL thresholds used here).
- **The parameters do strongly control alert churn.** A shorter median window gives far more alerts (30.6 per run at 30% error with window 1, 4.9 with window 9). A larger hysteresis halves them roughly (12.8 at 25 mL, 6.05 at 100 mL). This addresses E27, but no setting was adopted as a new default.
- **Stale timeout** changes only how many gaps count: 3 at 1200 s, 357 at 600 s and 10,470 at 300 s. All were flagged in every variant. As in E29, this is largely by construction.

## Experiment 6: simple misalignment detector

The detector flags when the estimate falls below (1 − d) × its 15-minute peak. Required: M1 ≥ 90% detection within 30 min of the misalignment; M2 ≤ 5% false flags per scenario.

| d | M1: flagged within 30 min (default / ×0.9) | False flags: anchor 11% | mre_20pct, mre_30pct | Ideal sensor |
|---|---|---|---|---|
| 0.15 | 0.020 / 0.013 (flags too early, on noise) | 1.00 | 1.00 | 0.00 |
| **0.25 (declared)** | 0.687 / 0.647 | 0.907 / 0.967 | 1.00 | 0.00 |
| 0.35 | 0.513 / 0.453 | 0.053 / 0.053 | 1.00 | 0.00 |

**Negative result: the detector fails M1 and M2 at every value.** Noise in the median estimate is large enough that a drop rule either misses the 30% step or fires on ordinary noise, even at the best-case 11% error. No value was tuned. A useful detector would need more than a drop rule on the volume estimate alone, for example a second independent signal from the patch. That is future work and has not been tested.
