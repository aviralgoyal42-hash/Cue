# Experiments 5 and 6 (extra work): criteria (frozen)

**Written 2026-11-04, before either experiment was run.** Both experiments are open-loop monitoring, like Experiment 2. They replay the Experiment 2b ground-truth traces: 15 inflow seeds × 2 sphincter strengths, with 10 sensor seeds each. All values are ASSUMED.

## Experiment 5: device parameter variation

- **Method:** one factor at a time around the default (median window 5, confirmation 3, hysteresis 50 mL, stale timeout 600 s).
  - Median window: 1, 3, 9.
  - Confirmation count: 1, 5.
  - Hysteresis: 25, 100 mL.
  - Stale timeout: 300, 1200 s.
- **Sensor scenarios:** anchor_11pct, mre_30pct, missing_50pct, misaligned_at_4h.
- **Thresholds:** 350, 400 and 450 mL.
- **Criteria:** C1–C4 exactly as in `docs/EXPERIMENT2_SUCCESS_CRITERIA.md`. The POST-HOC band rate and the mean number of alerts per run ("churn") are also reported.
- **Question:** does any single setting change which scenarios pass? The answer is reported either way. No setting is adopted as a new default because of this experiment.

## Experiment 6: a simple misalignment detector

- **Rule:** the device flags POSSIBLE_MISALIGNMENT once if its estimate falls below (1 − d) × the highest estimate of the last 15 min, while that highest estimate is at least 100 mL. In monitoring there is no emptying, so a sudden fall has no physiological explanation in this model. (After SCI a leak can hold volume steady, but it does not make it fall quickly.)
- **Values:** d = 0.25 is the declared value. 0.15 and 0.35 are reported as a sweep.
- **Detection target:** the scenario misaligned_at_4h (×0.7 gain from 4 h). Comparison scenarios: ideal, anchor_11pct, mre_20pct, mre_30pct, drift_minus2ph, gain_minus20, missing_50pct.

| ID | Criterion | Required |
|---|---|---|
| M1 | misaligned_at_4h runs flagged within 30 min after 4 h | ≥ 90% |
| M2 | Runs flagged in any scenario without misalignment | ≤ 5% (per scenario) |

The detector only flags. It does not change alerts. In a closed loop it would also have to be suppressed around stimulation sessions; that is not tested here.

## Change log
(empty)
