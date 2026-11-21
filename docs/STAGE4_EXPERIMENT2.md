# Project Cue: Stage 4, sensor, CustomTechDevice and Experiment 2 (monitoring only)

Date: 2026-11-04.
- Success criteria were frozen beforehand in `docs/EXPERIMENT2_SUCCESS_CRITERIA.md`. They were not changed.
- All numbers are **model predictions** made with a **synthetic experimental proxy sensor**. The sensor is not validated, and nothing here shows clinical safety.

## What was built

| Module | What it does | Sees ground truth? |
|---|---|---|
| `sensors/ultrasound_sensor.py` | `SyntheticUltrasoundSensor` takes true volume and adds random error, calibration (gain) error, drift, delay, missing readings and patch misalignment or posture change. It uses its own random generator, so it never disturbs the physiology's randomness. `ValidatedUltrasoundModel` and `RealUltrasoundDevice` exist only to refuse to run: neither is available. | Yes. A real patch measures the real bladder. |
| `devices/custom_tech_device.py` | `CustomTechDevice` receives **sensor readings only**. Its estimate is the median of the last 5 valid readings. It alerts after 3 consecutive estimates at or above the threshold and re-arms 50 mL below it. It raises "sensor stale" after 10 min without a valid reading. It does not use pressure. | **No.** A test inspects its code and imports to check this. |
| `evaluation/experiment2_metrics.py` | Scores alerts and errors against ground truth, using the frozen definitions. | Yes. This is the only place truth is compared. |
| `experiments/stage4_experiment2.py` | Runs the physiology once per case, then replays every sensor scenario through the device. This is valid because Experiment 2 is open-loop: the device changes nothing in the bladder. | — |

**Size of the run:**
- 2 sphincter strengths (default and ×0.9)
- × 3 inflow seeds
- × 15 sensor scenarios
- × 20 sensor seeds
- × 6 alert thresholds (250–500 mL)
- = **10,800 monitoring runs** of 12 h each.

**Check on the anchor.** The 11.17% best-case anchor is Toymus et al. 2024: 5 healthy volunteers, lying on their backs, compared against B-mode ultrasound. In our runs this scenario achieved a mean relative error of 11.2%, MAE 42 mL and RMSE 61 mL. After the 5-reading median, the device's estimate MAE was 23 mL.

## Results

Each cell: useful-alert rate / runs with a false alert. **PASS** means C1, C2 and C3 all hold. Full tables: `results/stage4/exp2_summary.csv`. Figures: `exp2_tradeoff_sphincter_x1.0.png`, `exp2_tradeoff_sphincter_x0.9.png`, `exp2_pass_map.png`, and example traces `exp2_example_*.png`.

**How many of the 14 non-ideal sensor scenarios pass, per threshold:**

| Threshold (mL) | 250 | 300 | 350 | 400 | 450 | 500 |
|---|---|---|---|---|---|---|
| Default sphincter | 0 | 1 | 8 | **11** | 10 | 5 |
| Sphincter ×0.9 (leaks at about 485 mL, about 7.0 h) | 0 | 2 | 8 | **9** | 7 | 4 |

**Best-case anchor (11.17%):** passes at **350, 400 and 450 mL** for both sphincter strengths.
- At 400 mL the median lead time is 89 min (default) and 78 min (weak).
- The true volume at the alert is 365–409 mL (5th–95th percentile).

### Main findings

1. **There is a trade-off, and no threshold works for every sensor fault.**
   - Below 300 mL every alert is false by definition.
   - Near 500 mL, alerts come too late, even with a perfect sensor. Three confirmations plus the median filter take several minutes, and with the weak sphincter the leak starts below 500 mL.
   - The best single threshold, 400 mL, still fails 3 of 14 scenarios (default) and 5 of 14 (weak).
2. **Calibration errors shift the working window rather than shrinking it.**
   - A gain of −20% passes only at 300–350 mL.
   - A gain of +20% passes only at 400–500 mL.
   - So a fixed threshold is only as good as the patch's calibration.
3. **Patch misalignment is the worst failure, and the device cannot see it.**
   - The scenario: from 4 h the patch reads 30% low and loses 30% of readings.
   - Cue fails at every threshold of 350 mL and above. The only pass is at 300 mL with the weak sphincter.
   - The device never goes "stale", because readings still arrive; they are just wrong.
4. **A noisy sensor can "pass" for the wrong reason.**
   - At 30–40% error, high thresholds pass because random upward spikes trigger the alert early.
   - Example: 40% error at the 500 mL threshold. The true volume at the alert was 338–459 mL (median 392), and there was no warning of the real crossing.
   - The noisy scenarios also produce **alert churn**: alerts that clear and fire again. The 40% scenario averages 13 alerts per 12 h across thresholds. The frozen criteria do not penalise early alerts above 300 mL, or churn. We report both instead of changing the criteria.
5. **Missing readings and delay hurt mostly at high thresholds.**
   - 50% missing or a 15-minute delay still pass at 350–400 mL.
   - The device flagged **336 of 336** gaps of 10 minutes or more (C4). This is largely by construction, because the same timeout defines both the gap and the flag.
6. **The weaker sphincter leaves less time.** The leak starts about 13 min earlier on average than the 500 mL crossing, and at a lower volume. Fewer combinations pass, mostly at 450–500 mL.
7. **Pressure gives no early warning in this model.** True p_D at a useful alert has a median of about 9.5 cmH₂O, against a peak of 56.6 just before 500 mL. With the Stage 3 fall in pressure on over-filling, this is why the device does not use pressure. It is not used as a fullness indicator anywhere.

## What this does and does not show

- **It shows:** in this simulation, a median-filtered threshold alert on a volume proxy can warn well before the model's adverse event, *if* the sensor's error is near the healthy-volunteer best case and the threshold sits in a window that depends on that error.
- **It does not show:**
  - that any threshold is clinically safe;
  - that the 11% figure applies to people with SCI (no validation in adult SCI exists; Kim & Kim 2026);
  - that 500 mL is anyone's real capacity.

## Known gaps, carried to Stage 5 and later
- The device parameters (window 5, confirmation 3, hysteresis 50 mL, timeout 10 min) were **not varied**.
- The device has no way to detect misalignment.
- After an early (false) alert the device stays alerted and never alerts again, so such runs also count as "missed". Whether to send reminders is a Stage 5 design question.

## Tests
`tests/test_stage4_sensor_device.py` has 20 tests, all passing. The full suite is 40 passed, plus 1 slow test that is skipped by default. They cover:
- the sensor's labelling, and that its error statistics match the target (for example a measured mean relative error of 11.2%);
- seed reproducibility, and that the sensor leaves numpy's global random state alone;
- missing readings, gain, drift, delay and misalignment;
- that the device never touches ground truth (code and imports inspected);
- alert confirmation, hysteresis, the median filter's resistance to spikes, and handling of missing readings;
- the stale and OK flags;
- the alert classification;
- adverse-event selection;
- the error metrics;
- stale-gap counting.
