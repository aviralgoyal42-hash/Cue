# Task 8: a second, independent bladder-volume signal ("sensor B") (Experiment 10)

**Frozen 2026-11-11, before any Task 8 code was written or run.** This plan does not change after results are seen. Any change goes in the change log at the bottom and in §5 of `VALIDATION_AND_LIMITATIONS.md`, with the reason.

**Results will be model predictions, not evidence for a device.** Sensor B is abstract. It is not a model of near-infrared light, an implant, bioimpedance or any product. **The simulation cannot say whether any real device meets the requirement it computes.** Background reading is in `docs/TASK8_REFERENCE_NOTES.md` (reference only; not used to set any value here).

**The user's request (11 Nov, paraphrased).** One sensor does not fix patch misalignment: after Tasks 6 and 7 the 450 mL threshold and early misalignment still fail. How good, and how independent from the patch, must a second signal be to fix it? Planned run about 3 hours, hard stop at 3.5 hours. Keep-awake approved. Log errors from E117. Do not stop to ask questions; say which reading was taken.

---

## 1. Sensor B

> reading B = gain_B × true volume × (1 + noise), or missing

- It is built with the existing synthetic sensor class, with its own random stream. Like sensor A, it is the only kind of component allowed to see true volume.
- **Noise:** the same form as sensor A (Gaussian, proportional to the reading), set by B's mean relative error.
- **Reading taken:** the request wrote "gain_B × true volume + noise". Noise proportional to volume is used so that B's error level means the same thing as A's "11% error".

| Value (all ASSUMED, fixed now) | Main grid | Side cases (one at a time, at B error 11.17%, independence 0) |
|---|---|---|
| **B error** (mean relative error) | **0.05, 0.1117, 0.20, 0.30, 0.40** | – |
| gain_B | 1.0 | 0.8, 1.2 |
| B missing readings | 10% | 50% |
| B drift | 0 | −2% and +2% per hour |
| B sampling | With every A reading | – |

**Independence setting, 0 to 1 ("shared fault").** It says how much of a patch shift also hits B:

> B's shift = 1 − independence × (1 − A's shift), and B's extra missing readings = independence × A's extra missing readings.

- **0:** a patch shift does not touch B at all (implanted-like).
- **1:** the same fault hits B in full (common-mode). **This is reported as the failure case.**
- **Grid: 0, 0.25, 0.5, 0.75, 1.0.** With A shifting to ×0.70, B reads at ×1.00, 0.925, 0.85, 0.775 and 0.70.
- **Reading taken:** the setting applies to the patch shift only. A's other faults (gain error, drift, delay, noise, missing readings) never touch B.

## 2. The three fusion rules

One disagreement test feeds all three rules, so the flags are the same whichever rule is used.

**The disagreement test.** It watches the ratio A ÷ B, not either sensor alone. Both sensors look at the same bladder, so filling and emptying cancel in the ratio, and so does a constant gain error in either sensor.
- "Now" = the last 20 minutes. "Before" = the 90 minutes before that.
- ratio = mean of A's valid readings ÷ mean of B's valid readings, in each window. change = ratio now ÷ ratio before − 1.
- Needs at least 10 valid readings from each sensor in "now" and 30 from each in "before".
- noise of the comparison = √(σA²/nA + σB²/nB), added for both windows, where σA and σB are each sensor's scatter measured from its own readings (last 120 jumps, floor 2%, as in Task 6).
- **Flag when |change| ≥ 4.0 × that noise, and |change| ≥ 10%, and B's mean now is at least 100 mL.** Either direction. Once only, until the user confirms the patch is back.
- Around a stimulation session the test is paused and restarted from fresh readings.
- **Reading taken:** the request said "more than a multiple of B's noise". The multiple is applied to the noise of the comparison, which is B's noise combined with A's. With B's noise alone, the rule would flag on A's own noise whenever A is the noisier sensor.

| Rule | Estimate the device uses | Flag |
|---|---|---|
| **(a) Flag** | Sensor A, always | `CHECK_PATCH` when the test fires |
| **(b) Trust B** | Sensor A until the test fires, then sensor B | The same |
| **(c) Average** | The mean of A and B (the valid one if only one is valid), always | The same |

The fused readings go into the unchanged `CustomTechDevice` (median of 5, 3 confirmations, 50 mL hysteresis). The Task 6 monitor and the Task 7 correction are **off** in every Task 8 run, so that B's contribution is seen alone.

| Fusion value (all ASSUMED, fixed now) | Setting |
|---|---|
| "Now" window; "before" window | 20 min; 90 min |
| Fewest valid readings (now; before) | 10; 30 |
| Multiple of the noise | 4.0 |
| Smallest change that can flag; smallest level | 10%; 100 mL |

## 3. Runs

### 3.1 Main sweep (open loop, Experiment 10)

- **Traces:** the 30 saved Experiment 2b traces (15 inflow seeds × 2 sphincter strengths).
- **Sensor seeds:** 15 per trace and scenario, new: A from `SeedSequence([3000, scenario number, scaling × 100, inflow seed, repeat])`, B from the same with 3001. B uses the same random stream at every grid point, so points differ only by the setting. **225 runs per scenario and sphincter strength.**
- **Thresholds:** 350, 400, 450 mL.

| Kind | Sensor A scenarios | B grid |
|---|---|---|
| Misalignment | `misaligned_at_4h` (×0.7 at 4 h, 30% extra missing readings): **the declared target**. Early: ×0.7 at 2 h. No extra missing readings: ×0.7 at 4 h. Small fall: ×0.85 at 4 h | 5 error levels × 5 independence levels |
| No misalignment | All 14 other `config.SENSOR_SCENARIOS` | 5 error levels (independence has no effect) |
| B side cases | Target and `anchor_11pct`, with gain_B 0.8, 1.2; drift −2, +2 %/h; B missing 50% | One point each |
| **B is the one that moves** | A = `anchor_11pct`; B shifts to ×0.7 at 4 h | B error 0.1117 |

### 3.2 Held-out check

- **Fresh inflow seeds 101–110**, never used in this project, at both sphincter strengths: 20 new physiology traces, simulated by the unchanged Experiment 2 code into `results/task8/heldout/physiology/`.
- **Gains never used in any design: ×0.6 and ×0.8 at 4 h** (Tasks 6–8 used 0.5, 0.7 and 0.85), plus ×0.7 at 4 h and `anchor_11pct`, on those fresh traces.
- 15 sensor seeds per trace (prefix 3100 / 3101): **150 runs per scenario and sphincter strength**, full 5 × 5 grid.
- Reported in its own section, labelled HELD-OUT, with the same criteria. **If the held-out requirement curve differs from the main one, both are shown and the weaker claim is the one made.**

### 3.3 Closed-loop probe (descriptive only)

Pattern `e0.6_s0.0_5on5off`, ceiling 55, threshold 400, ×1.0 and ×0.9, seeds 42, 1, 2. B error 0.1117. Four cases: anchor A with rule (b); misaligned A with rule (b), independence 0; misaligned A with rule (c), independence 0; misaligned A with rule (b), independence 1 (the failure case). **24 runs.** Invariants A2–A4 must hold. No verdict (3 seeds).

## 4. Criteria (all taken from earlier tasks)

Scored per B error level *e* and independence *c*:

| ID | Criterion | Required |
|---|---|---|
| **M1** | Target: no flag before 4 h and the first flag within 30 min after | ≥ 90% of runs at each sphincter strength |
| **M2** | Runs with any flag, in each of the 14 scenarios without misalignment | ≤ 5% in each of 28 cells (per *e*) |
| **C1–C3** | The Experiment 2 alert tests, on the 6 target cells (3 thresholds × 2 strengths) | All 6 cells pass |
| **M4** | Cells without misalignment that change from "Cue works" with A alone to "does not work" with the rule | 0 of 84 (per *e* and rule) |

**Verdicts**
- **The flag works at (*e*, *c*)** if M1 and M2 pass.
- **Rule (b) or (c) fixes the target at (*e*, *c*)** if all 6 target cells pass and M4 passes at that *e* for that rule. For rule (b), M1 and M2 must pass too, because the rule acts on the flag.
- **Rule (a) cannot fix an alert in this experiment.** It only flags and no user acts on the flag here, so its alert results equal sensor A alone. That is checked and reported, not assumed.
- **Early misalignment (×0.7 at 2 h)** is scored the same way on its own 6 cells and reported as a second requirement curve. "Fully fixed" means target and early both fixed.

**Main output: the requirement curve.** For each rule and each independence level, the B error levels at which the target is fixed, and the largest such level ("the weakest B that still works"). If the working levels are not one block from 0.05 upward, every level is reported as found. **Nothing is interpolated between grid points.**

**Reported regardless**
- Cost of flags: flag rate in every cell without misalignment, by B error.
- Cost of early alerts: false-alert rate (C2) in every cell, and the median and 5th percentile of true volume at the first genuine alert.
- M4 in both directions: cells harmed and cells gained, by rule.
- Flag timing, and how often rule (b) switched to B.
- The side cases, and the case where B is the sensor that moves. In that case rule (b) trusts the wrong sensor by design; the damage is reported.
- The common-mode column (independence 1) in every table.

## 5. What is post-hoc and what is not

- **Post-hoc:** the fusion design. The 10% minimum, the 100 mL minimum and the way noise is measured are copied from Task 6. Watching a ratio so that filling cancels comes from E106. The 4.0 multiple and the 20-minute window were chosen with the Task 6–7 flag rates in mind. All of that experience came from the same 30 traces the main sweep uses.
- **Not post-hoc:** the sensor B grid and the independence grid. They were set before any two-sensor run existed.
- **Held-out:** inflow seeds 101–110 and gains ×0.6 and ×0.8. Nothing in this plan was chosen with them.
- **Not held-out:** the physiology model, the sensor noise model and the sensor A anchor error are the same everywhere.

## 6. How it runs

- **Order:** tests, reproduction check, timing test, held-out physiology, main sweep, held-out sweep, scoring, probe.
- **Code, all off by default:** `sensors/second_sensor.py` (builds B's scenario), `devices/sensor_fusion.py` (the test and the three rules), an optional `fusion` entry in the rig's case (`None` = the old rig, exactly), `experiments/task8_experiment10.py`. `config.py` is not edited.
- **Tests first:** `tests/test_task8.py` plus the whole fast suite, which must show only the known E88 failure.
- **Reproduction check, B off, before any sweep:** (1) open loop: the Task 8 script, with no sensor B and the Experiment 9 seeds, must reproduce the 900 "monitor off" alert rows of the Experiment 9 target exactly; (2) closed loop: 6 runs (detrusor 0.6, block 1.0, both strengths, seeds 42, 1, 2) must reproduce their Task 5 rows exactly. If either fails, no sweep starts.
- **Timing test:** on a made-up trace, results discarded. **If it projects more than 60 minutes for the main sweep, sensor seeds drop from 15 to 10 per trace** (150 runs per cell) and the change is logged. Nothing else may change.
- **Saving as it goes:** one job per trace and scenario, each writing its own files in `results/task8/runs/` (temporary file, then rename). A restart skips finished jobs. Partial files are never deleted by hand and never scored as the full grid: scoring refuses unless every job file is present.
- **No code is edited while a job runs.**
- **Truth stays on the evaluation side.** The fusion code sees readings only; a test enforces it.
- **Keep-awake:** the app's hold (approved), with progress lines to keep the session active.
- **Old results** are not touched. Errors, stalls, crashes and scoring mistakes go in §5 from **E117**, and first outputs are kept.

## 7. Declared limitations

- **Sensor B is a formula.** Its error, its missing readings and above all its independence are settings, not properties of anything real.
- **Independence is one number.** Real shared faults (posture, movement, sweat, a belt) would not scale a second sensor's reading by a tidy fraction of the first's.
- **The disagreement test cannot tell which sensor is wrong.** Rule (b) assumes it is A.
- **A fully shared fault is invisible to it.** The Task 6 single-sensor monitor might still see it; the two are not combined here.
- **Step-shaped shifts only.** Gradual or intermittent shifts are not tested.
- **No user.** Nobody re-seats the patch, so rule (a) can only be judged on its flag.
- **Statistics:** 225 runs per cell from 15 inflow seeds (150 from 10 in the held-out check). A rate near 5% or 90% cannot be placed precisely (E68, E112).
- **The alert tests have known weaknesses** (E26, E27): early alerts above 300 mL count as useful.

## Change log
- (none)
