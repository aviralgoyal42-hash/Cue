# Task 8 results: a second, independent bladder-volume signal ("sensor B") (Experiment 10)

Date: 2026-11-11. Plan and criteria: `docs/TASK8_PLAN.md`, frozen before any code was written. Its change log is empty: nothing was changed. Background reading (reference only): `docs/TASK8_REFERENCE_NOTES.md`.

**Results are model predictions, not evidence for a device.** Sensor B is a formula. It is not a model of near-infrared light, an implant, bioimpedance or any product. **The simulation cannot say whether any real device meets the requirement below.**

**Post-hoc parts:** the fusion design drew on Tasks 6 and 7, which used the same 30 traces as the main sweep. The sensor B grid and the independence grid did not. The held-out check uses fresh inflow seeds and gains that no design used.

## Short answers

1. **By the frozen criteria, no sensor B on the grid fixes misalignment.** The disagreement test raises too many false flags. The limit is 5% in each of 28 cells; the worst cell is 76%, and the test fails that limit at every B error level (E118).
2. **Leaving the false-flag criterion aside, the requirement is narrow and clear.** "Trust B" makes all 6 target cells pass, including the 450 mL threshold, and all 6 early-misalignment cells, **only when B's error is about 11% or better and a patch shift does not touch B at all.**
   - B error 20%: 0 of 6 cells. The flag comes too late (on time in 48% of runs).
   - Independence 0.25 (B shares a quarter of the shift): 2 to 4 of 6 cells.
   - Independence 1 (common-mode): 0 of 6 cells, identical to having no sensor B. **This is the failure case.**
3. **Averaging the two sensors never fixes it** (at most 4 of 6 cells) and it harms cells that worked.
4. **If B is the sensor that moves, "trust B" turns a working system (6 of 6 cells) into a failing one (0 of 6).** The test cannot tell which sensor is wrong.

So the answer to "how good and how independent": **B must be at least as accurate as the patch at its best and essentially unaffected by whatever moves the patch**, and even then the disagreement test as designed here flags too often to be accepted.

---

## 1. What ran

| Step | Result |
|---|---|
| Fast test suite | 243 passed, 1 failed (the known E88). 22 new tests |
| Reproduction, sensor B off, open loop | **Identical:** 900 of 900 alert rows of the Experiment 9 target (11 columns) |
| Reproduction, sensor B off, closed loop | **Identical:** 6 of 6 runs (34 columns) and 12 of 12 sessions (27 columns) against Task 5 |
| Timing test | Projected 11.7 min for the main sweep, so sensor seeds stayed at 15. **The sweep took 26.5 min** (E117) |
| Held-out physiology | 20 fresh traces (inflow seeds 101–110, both strengths) |
| Main sweep | 540 jobs, 8,100 runs, 81,450 flag rows, 537,300 alert rows. No crash, no stall, no restart |
| Held-out sweep | 80 jobs, 1,200 runs. 7.4 min |
| Closed-loop probe | 24 runs, 0 errors, invariants A2–A4 held in all |

Rule (a) was run for real at one grid point: its alerts equal sensor A alone in all 108 cells checked (24 in the held-out set), as expected for a flag nobody acts on.

## 2. The false-flag criterion fails (M2)

Share of runs flagged in scenarios **without** misalignment. Limit: 5% in each of 28 cells (14 scenarios × 2 strengths).

| B error | Worst cell | Cells over 5% (of 28) | Anchor sensor (×1.0 / ×0.9) |
|---|---|---|---|
| 0.05 | **76.0%** | 7 | 2.2% / 1.8% |
| 0.1117 | **60.9%** | 9 | 4.0% / 3.6% |
| 0.20 | 36.9% | 19 | 6.7% / 8.4% |
| 0.30 | 26.7% | 27 | 9.3% / 11.6% |
| 0.40 | 23.6% | 28 | 14.7% / 15.6% |

**Two separate causes (E118):**
- **A delayed sensor A is read as a disagreement.** `delay_15min` is flagged in 58–76% of runs with a good B, and `delay_5min` in 6–9%. A reading that lags a filling bladder is low by a share that shrinks as the bladder fills, so the A ÷ B ratio drifts upward. The test was designed so that filling cancels; with a delay it does not. This reading of the cause fits the direction of the flags but was not examined further.
- **The test is lopsided, and it looks too often.** Outside the delay cases, 89–100% of false flags on the anchor sensor are in the "A reads high" direction, and the changes sit just above the threshold. Dividing by B's average makes a low B average count for more than a high one, and the test looks every minute for 12 hours. A multiple of 4.0 was not enough, and the excess grows with B's error.

Without the two delay scenarios, 3 cells still fail at B error 0.05 and 5 at 0.1117 (drift, gain and the ideal sensor).

## 3. The requirement curve

**Verdict by the frozen rule: nothing is "fixed" in the main sweep, for any rule, B error or independence**, because M2 fails at every B error (rule b) and no averaging point reaches 6 of 6 cells (rule c).

The tables below show what lies underneath that verdict: **target cells passing C1–C3 (of 6: thresholds 350, 400, 450 mL × 2 sphincter strengths).** With sensor A alone: 0 of 6.

**Rule (b), trust B after the flag**

| B error | Indep. 0 | 0.25 | 0.5 | 0.75 | 1 (common-mode) | Flag on time at indep. 0 | Working cells harmed (of 84) |
|---|---|---|---|---|---|---|---|
| 0.05 | 5 | 4 | 1 | 0 | 0 | 0.991 | 0 |
| 0.1117 | **6** | 2 | 0 | 0 | 0 | 0.982 | 0 |
| 0.20 | 0 | 0 | 0 | 0 | 0 | 0.484 | 0 |
| 0.30 | 0 | 0 | 0 | 0 | 0 | 0.027 | 2 |
| 0.40 | 0 | 0 | 0 | 0 | 0 | 0.000 | 3 |

**Rule (c), average**

| B error | Indep. 0 | 0.25 | 0.5 | 0.75 | 1 | Working cells harmed (of 84) |
|---|---|---|---|---|---|---|
| 0.05 | 3 | 2 | 2 | 0 | 0 | 3 |
| 0.1117 | 4 | 2 | 2 | 0 | 0 | 2 |
| 0.20 | 4 | 3 | 2 | 1 | 0 | 0 |
| 0.30 | 4 | 3 | 2 | 1 | 0 | 5 |
| 0.40 | 3 | 4 | 2 | 2 | 0 | 16 |

**Reading the curve**
- **The weakest B at which all 6 target cells pass is error 0.1117 at independence 0.** That single point also passes M1 (0.982) and M4 (0 harmed). It fails only M2.
- **B error is a cliff, not a slope.** Between 0.1117 and 0.20 the flag drops from on time in 98% of runs to 48%, and rule (b) goes from 6 cells to 0. The boundary between those two grid values is not resolved, and nothing is interpolated.
- **Independence is just as sharp.** A B that shares a quarter of the shift loses 2 to 4 cells.
- **A more accurate B is not automatically better.** At error 0.05 one cell fails (450 mL, ×0.9): every run gets a useful alert, but the median warning time is 22.5 min against the 30 needed. A noisier B alerts earlier by chance, and the alert tests reward that (E119, and E26 before it).
- **Common-mode gives the no-B result.** The flag is on time in 0.4% of runs, and the alert numbers are almost identical to sensor A alone.

**The cells that still failed after Tasks 6 and 7**, at B error 0.1117, independence 0, rule (b):

| Scenario | A alone | Task 7 correction | Rule (b) | Flag on time |
|---|---|---|---|---|
| Target, ×0.7 at 4 h | 0 of 6 | 4 of 6 | **6 of 6** | 0.982 |
| Early, ×0.7 at 2 h | 0 of 6 | 0 of 6 | **6 of 6** | 0.973 |
| ×0.7 at 4 h, no extra missing readings | 0 of 6 | 5 of 6 | **6 of 6** | 0.987 |
| Small fall, ×0.85 at 4 h | 2 of 6 | 3 of 6 | 3 of 6 | **0.142** |

- The 450 mL threshold and early misalignment both pass at this one point. The Task 7 column is from Experiment 9, on different sensor seeds.
- **A small fall is still not caught.** Even with B at 5% error the flag is on time in only 40% of runs.

## 4. Costs

**False flags:** §2. With rule (b) a false flag is not only a prompt: it switches the device to B for the rest of the run.

**Early and false alerts** (target, independence 0, rule b):

| B error | Worst false-alert rate (C2 limit 5%) | Median true volume at alert, 400 mL threshold (×1.0) | 5th percentile |
|---|---|---|---|
| 0.05 | 0.0% | 403 mL | 380 mL |
| 0.1117 | 0.9% | 390 mL | 359 mL |
| 0.20 | 3.6% | 391 mL | 327 mL |

For early misalignment at B error 0.20 the false-alert rate reaches 7.1%, over the limit.

**Harm to cells that worked (M4)**
- Rule (b): 0 of 84 harmed at B error 0.05 to 0.20; 2 at 0.30; 3 at 0.40.
- Rule (c): 3, 2, 0, 5 and 16 harmed across the five error levels. At good B the harm is at the 450 mL threshold (warning time falls just under 30 min). At B error 0.40 it is false alerts, mostly at 350 mL, in up to 38% of runs in a harmed cell.
- Rule (c) also gains cells in noisy-sensor scenarios: 16, 16, 14, 14 and 10.

**When B has its own faults** (B error 0.1117, independence 0, rule b). Target cells of 6, and whether the anchor sensor's 6 working cells survive:

| B fault | Target cells | Anchor cells kept | Flag on time (×1.0 / ×0.9) |
|---|---|---|---|
| None | 6 | 6 | 0.987 / 0.982 |
| gain_B 0.8 (reads 20% low) | **2** | 6 | 0.991 / 0.982 |
| gain_B 1.2 | 4 | 6 | 0.987 / 0.982 |
| Drift −2% per hour | 3 | 6 | 0.964 / 0.947 |
| Drift +2% per hour | 4 | 6 | 0.991 / 0.987 |
| 50% missing readings | **2** | 6 | **0.760 / 0.720** |
| **B is the one that moves (×0.7 at 4 h, A fine)** | – | **0** | 0.991 / 0.996 |

- **A constant gain error in B does not disturb the flag, but it spoils the fix:** the device switches to a sensor that reads 20% low.
- **B drifting downward raises false flags** on the anchor sensor to 9.8% and 16.4%.
- **When B moves and A is fine, the test flags every run and rule (b) then trusts the wrong sensor.** The useful-alert rate at 400 mL falls to 2.2% (×1.0). Averaging keeps 3 of 6 cells.

## 5. HELD-OUT check (fresh inflow seeds 101–110; gains ×0.6 and ×0.8)

150 runs per scenario and strength. Target cells passing with rule (b), by B error, at independence 0 and 0.25:

| Scenario | Indep. 0: errors 0.05 / 0.1117 / 0.20 / 0.30 / 0.40 | Indep. 0.25 | Flag on time at 0.1117, indep. 0 |
|---|---|---|---|
| ×0.7 at 4 h (fresh seeds) | 5 / **6** / 0 / 0 / 0 | 4 / 3 / 0 / 0 / 0 | 0.980 |
| **×0.6 at 4 h (held-out gain)** | 5 / **6** / 4 / 0 / 0 | 3 / 4 / 0 / 0 / 0 | 0.987 |
| **×0.8 at 4 h (held-out gain)** | 3 / 2 / 2 / 2 / 2 | 2 / 2 / 2 / 2 / 2 | **0.467** |

- **The shape repeats on fresh seeds:** 5, then 6, then 0 cells for the ×0.7 shift, the same as in the main sweep.
- **A bigger shift (×0.6) is easier:** at B error 0.20 the flag is on time in 91% of runs and 4 cells pass.
- **A smaller shift (×0.8) is not fixed at any B on the grid.** The flag is on time in 85% of runs at B error 0.05 and 47% at 0.1117. With sensor A alone 2 of 6 cells work.
- **False flags on the held-out anchor sensor:** 2.7% / 5.3% at B error 0.05, **4.0% / 2.7% at 0.1117**, then 8.7–20%. Only B error 0.1117 stays within 5%.
- **By the frozen rule, the held-out set shows a fix at one point** (B error 0.1117, independence 0, for ×0.7 and ×0.6). But the held-out set has only 2 cells without misalignment, against 28 in the main sweep. The plan says the weaker claim is the one made: **not fixed.**

## 6. Closed-loop probe (24 runs, 3 seeds, descriptive, no verdict)

Pattern `e0.6_s0.0_5on5off`, ceiling 55, threshold 400 mL, B error 0.1117. Results were the same at both sphincter strengths except where shown.

| Case | Disagreement flags | First alert | Highest true volume | Sessions voiding ≥ 50% |
|---|---|---|---|---|
| Anchor A, rule (b) | **0 in 6 runs** (12 sessions) | 5.5–6.5 h | 391–411 mL | 12 of 12 |
| Misaligned A, rule (b), independence 0 | 6 of 6 runs, at 4.12–4.27 h | 5.7–6.0 h | **391–417 mL** | 12 of 12 |
| Misaligned A, rule (c), independence 0 | 6 of 6 runs | 6.1–7.4 h | 452–484 mL | 8 of 8 |
| **Misaligned A, rule (b), common-mode** | **0 of 6 runs** | 7.0–8.1 h at ×1.0; **no alert in 2 of 3 runs at ×0.9** | 549–600 mL at ×1.0; 488–491 mL at ×0.9 | 3 of 8 at ×1.0; 1 of 1 at ×0.9 |

- With an independent B, the misaligned runs look like the anchor runs: no session started above 417 mL.
- The common-mode runs equal the Task 6 runs with no monitor at all.
- Emptying caused no false flag in the 6 anchor runs.

## 7. What this cannot show

- **Whether any real second signal is this accurate or this independent.** The reference notes found no volume error figure for near-infrared monitoring, and name posture as a failure mode for both bioimpedance and implanted pressure sensors. Posture is also what moves a patch.
- **What independence means physically.** Here it is one number that scales a step. Real shared faults would not be tidy.
- **Which sensor is wrong.** Rule (b) assumes it is the patch. §4 shows the damage when that is false.
- **A better test.** The false-flag failure belongs to this test (a ratio, a symmetric threshold, a look every minute), not to the idea of a second sensor. A fixed test would be a new frozen plan and would be post-hoc.
- **Anything about a user.** Nobody re-seats the patch, so rule (a) is judged on its flag only.
- **Rates near the limits.** 225 runs per cell from 15 inflow seeds; 150 from 10 in the held-out set.
- **Gradual or intermittent shifts, and shifts that hit both sensors by different amounts at different times.**

## 8. Passed, failed, not tested

| | |
|---|---|
| **Passed** | Reproduction with B off (open and closed loop). Flag on time (M1) at B error ≤ 0.1117 with independence 0. No working cell harmed by rule (b) at B error ≤ 0.20. All 6 target cells and all 6 early cells with rule (b) at B error 0.1117, independence 0. The same shape on fresh seeds and at held-out gain ×0.6 |
| **Failed** | False flags (M2) at every B error, so no point counts as a fix. Every point with B error ≥ 0.20. Every point with independence ≥ 0.25. Common-mode. Averaging. Small falls (×0.85, held-out ×0.8). B as the moving sensor |
| **Not tested** | Any real device. A user who acts on the flag. Combining the two-sensor test with the Task 6 single-sensor monitor. B error between 0.1117 and 0.20. Independence between 0 and 0.25. Gradual shifts |

## Errors and surprises

Logged in `VALIDATION_AND_LIMITATIONS.md` §5 as E117–E125.
