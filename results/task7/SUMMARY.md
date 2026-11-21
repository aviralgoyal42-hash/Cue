# Task 7 results: a misalignment correction that allows for bladder filling (Experiment 9)

Date: 2026-11-10. Plan and criteria: `docs/TASK7_PLAN.md`, frozen before any code was written. The held-out criterion (§7) was added at approval, before any code or run.

**Results are model predictions, not evidence for a device.** The sensor is a synthetic experimental proxy.

**Every result here is POST-HOC.** The correction was designed after seeing Experiment 8, and it is tested on the same 30 physiology traces, with new sensor seeds.

## Short answers

1. **The new correction measures the fall correctly.** For a patch reading at 0.70, the median measured ratio is 0.700 (×1.0) and 0.706 (×0.9). The Task 6 correction gave 0.816 and 0.824 on the same readings.
2. **It rescues 4 of 6 cells, against 2 of 6.** The 350 and 400 mL thresholds now work at both sphincter strengths. **The 450 mL threshold still fails** at both.
3. **Held-out gains: both pass their ratio criterion.** At ×0.5 it rescues 4 of 6 cells against 2. **At ×0.85 it rescues no extra cell** (3 of 6, the same as before), because most of those runs get no correction at all.
4. **It has a cost.** The measured ratio is noisier than it is biased: about 1 corrected run in 6 is over-corrected. False alerts appear where there were none, and at an early misalignment (2 h) they pass the 5% limit.

By the frozen rule the new correction **is an improvement** on the declared target. Misalignment is "less of a concern" at the 350 and 400 mL thresholds only.

---

## 1. Checks before the experiment

| Check | Result |
|---|---|
| Fast test suite | 221 passed, 1 failed (the known E88). The 24 Task 6 tests are unchanged and pass |
| Reproduction: option off, Experiment 8 seeds, declared target | **Identical.** 300 of 300 flag rows (14 columns) and 2,700 of 2,700 alert rows (17 columns), no differences |

## 2. Criteria

6,300 runs: 21 scenarios × 2 sphincter strengths × 15 inflow seeds × 10 new sensor seeds. Files: `results/task7/exp9_*.csv`, `exp9_criteria.json`.

| ID | Criterion | Required | Result | Verdict |
|---|---|---|---|---|
| F1 | Old and new corrections raise the same flags at the same times | 100% of 6,300 runs | **0 differences in 6,300 runs** (see the note below) | **Pass** |
| M1 | `misaligned_at_4h` flagged within 30 min, none before | ≥ 90% | 0.993 (×1.0), 1.000 (×0.9) | **Pass** |
| M2 | Runs flagged in each of 14 scenarios without misalignment | ≤ 5% in each of 28 cells | Highest cell **4.0%** (anchor sensor, ×0.9). 29 flagged runs in 4,200 | **Pass, with less margin than in Experiment 8 (2.0%)** |
| R1 | Median measured ratio, new correction (true 0.70) | 0.65–0.75 | **0.700 (×1.0), 0.706 (×0.9)** | **Pass** |
| M4 | Cells without misalignment that change from "works" to "does not work" | 0 | **0 of 84** (54 work with the monitor off, with the old correction and with the new) | **Pass** |

**Note on F1 (E111).** The first scoring reported F1 as failed, with 1,785 differences. The cause was the scoring code: it compared a column that holds the correction the device starts using at the flag, which is meant to differ between old and new. The plan defines F1 as the same flags at the same times. The comparison was corrected to exactly that and the saved runs were rescored; nothing was rerun. The first output is kept as `results/task7/exp9_criteria_first_scoring_F1_wrong_column.json`.

**M2 on new seeds.** The flag rules did not change, so the rise from 2.0% to 4.0% in the worst cell is seed-to-seed variation. With 150 runs per cell, the 5% line is not far away (E112).

## 3. The declared target, `misaligned_at_4h` (M3)

Share of runs with a useful alert (C1 needs ≥ 0.95), with the median true volume at the alert:

| Threshold, strength | Monitor off | Task 6 correction | New correction | Works with the new one? |
|---|---|---|---|---|
| 350 mL, ×1.0 | 0.707, 489 mL | 0.993, 406 mL | 0.980, 347 mL | **Yes** |
| 350 mL, ×0.9 | 0.480, 485 mL | 0.993, 402 mL | 0.987, 344 mL | **Yes** |
| 400 mL, ×1.0 | 0.000, 558 mL | 0.873, 457 mL | **0.993**, 393 mL | **Yes (newly rescued)** |
| 400 mL, ×0.9 | 0.000, 487 mL | 0.793, 462 mL | **0.993**, 388 mL | **Yes (newly rescued)** |
| 450 mL, ×1.0 | 0.000, 626 mL | 0.407, 514 mL | 0.940, 439 mL | **No** (C1: 0.940 is under 0.95) |
| 450 mL, ×0.9 | 0.000 | 0.240, 486 mL | 0.900, 445 mL | **No** (C1) |

- **Rescued: 4 of 6**, against 2 of 6 for the Task 6 correction on the same readings and 0 of 6 with the monitor off. No cell the old correction rescued was lost.
- **The two 450 mL cells still fail**, narrowly. The alert volume is now right (439 and 445 mL), but 6–10% of runs still alert too late.
- **Measured ratio:** median 0.700, 5th–95th percentile **0.623–0.783** (×1.0). It is right on average and scattered.
- **Over-corrected** (more than 0.05 below the true ratio): 18.1% (×1.0) and 16.7% (×0.9) of corrected runs. Under-corrected by the same margin: 16.1% and 17.3%.
- **False alerts:** 1.3% (×1.0) and 0.7% (×0.9) of runs at the 350 mL threshold, where there were none before. Still under the 5% limit.

## 4. HELD-OUT gains (plan §7)

**What held-out means here:** no value in the design was chosen using ×0.5 or ×0.85. But both gains had been run in Experiment 8 with the old correction and those results had been seen. They are held out from the design, not unseen.

| | ×0.5 (true ratio 0.50) | ×0.85 (true ratio 0.85) |
|---|---|---|
| Criterion | H1: median 0.45–0.55 | H2: median 0.80–0.90 |
| Median measured ratio, new (×1.0 / ×0.9) | **0.496 / 0.499** | **0.846 / 0.870** |
| Verdict | **H1 passes** | **H2 passes** |
| Median with the Task 6 correction | 0.576 / 0.578 | 0.976 / 0.955 |
| 5th–95th percentile, new (×1.0) | 0.457–0.544 | 0.745–0.966 |
| **Runs in which a correction was applied at all** | 100% / 100% | **41.3% / 80.7%** |
| Over-corrected, of corrected runs | 2.0% / 13.3% | 24.2% / 11.6% |
| Cells working: monitor off → Task 6 → new | 0 → 2 → **4** | 2 → 3 → **3** |

- **×0.5: the correction generalises.** It rescues the 350 and 400 mL cells at both strengths, like the declared target. The 450 mL cells fail on C1 (0.933 and 0.900).
- **×0.85: the ratio is right when it is measured, but it changes no verdict.** Rule 1 seldom fires on a 15% fall, so 59% of runs at ×1.0 and 19% at ×0.9 get no correction. H2 is judged only on the runs that were corrected, so **passing H2 does not mean a 15% fall is handled.** This is the E107 weak spot, unchanged.
- False alerts at the 350 mL threshold: 2.0% / 3.3% at ×0.5 and 2.0% / 0.7% at ×0.85.

## 5. Other variants (reported, not criteria)

Cells working out of 6 (monitor off → Task 6 → new), and the median measured ratio (×1.0):

| Variant | Cells | Ratio, Task 6 → new | Note |
|---|---|---|---|
| ×0.7 at 4 h, no extra missing readings | 0 → 3 → **5** | 0.790 → 0.698 | |
| ×0.7 at 6 h | 2 → 4 → 4 | 0.785 → 0.708 | The 450 mL cells: useful rate 0.62 → 0.94 and 0.53 → 0.91, still under 0.95 |
| **×0.7 at 2 h** | 0 → 0 → **0** | 0.944 → 0.703 | See below |
| Extra missing readings only (patch has not moved) | 6 → 6 → 6 | 1.000 → 0.953 | See below |

- **Early misalignment (2 h) is better but still fails.** The ratio is now right, and the useful-alert rate at 400 mL rises from 0.27 to 0.85 (×1.0). But no cell passes: C1 stays under 0.95, and **at 350 mL the false-alert rate is 6.0% (×1.0) and 5.3% (×0.9), over the 5% limit**. With a small bladder, an over-correction pushes the estimate past the threshold while the true volume is still under 300 mL.
- **When only readings go missing and the patch has not moved, the correction sometimes acts anyway.** After a dropout flag, rule 1 asks for less proof and fired in 14% (×1.0) and 69% (×0.9) of those runs. The new correction then lowers a ratio that should be 1.00 to a median of 0.953 and 0.914. No cell changed, but it is a correction with nothing to correct. The Task 6 correction did the same at ×0.9 (0.936).
- **The line fell back to flat in 14 corrected runs** (all for a downward slope, all at ×0.9; the cause was not examined). It never fell back for too few readings.

## 6. Closed-loop probe (12 runs, 3 seeds, descriptive, no verdict)

Pattern `e0.6_s0.0_5on5off`, ceiling 55, threshold 400 mL, seeds 42, 1, 2. 12 runs, 0 errors, invariants A2–A4 held in all. The Task 6 rows are from `results/task6/` on the same seeds.

| Case | Patch checks | First alert | Highest true volume | Sessions voiding ≥ 50% |
|---|---|---|---|---|
| Anchor sensor, new correction (×1.0 and ×0.9) | **0 in 6 runs** (12 sessions) | 5.5–6.5 h | 391–411 mL | 12 of 12 |
| Misaligned, Task 6 correction, ×1.0 | 3 of 3 runs | 6.3–7.1 h | 411–548 mL | 5 of 6 |
| Misaligned, **new correction**, ×1.0 | 3 of 3 runs, at 4.15–4.30 h | **5.8–5.9 h** | **369–453 mL** | **6 of 6** |
| Misaligned, Task 6 correction, ×0.9 | 3 of 3 runs | 6.3–7.9 h | 411–490 mL | 5 of 5 |
| Misaligned, **new correction**, ×0.9 | 3 of 3 runs, at 4.15–4.30 h | **5.8–5.9 h** | **369–453 mL** | **6 of 6** |

- In these 3 seeds the first alert comes 0.4 to 2.1 hours earlier than with the Task 6 correction, and no session starts above 453 mL.
- The late run of Task 6 (seed 42, a session starting near 490–500 mL, with an 8 mL leak at ×0.9) now starts its first session at 387 mL, with no leak.
- **One run alerted early** (seed 2): its sessions started at 360 and 369 mL true volume, under the 400 mL threshold, while the device estimated 426 and 449 mL. The anchor runs show estimate errors of a similar size (for example 389 mL true against 444 mL estimated), so this may be sensor noise as much as over-correction.
- Emptying caused no false flag in the 6 anchor runs.

Three seeds, so this is a description, not a rate (E99).

## 7. What this does and does not show

- **Shown, in this model and POST-HOC:** allowing for filling removes the bias in the measured ratio, at the design gain and at one held-out gain, and moves the 400 mL threshold from failing to working.
- **Not solved:** the 450 mL threshold; a 15% fall; misalignment at 2 h; a correction applied when only readings go missing.
- **New cost:** scatter in the ratio. Roughly one corrected run in six alerts earlier than it should. That is the safe direction, but early alerts are false alarms to the user.
- **Still not tested:** a user who re-seats the patch, which remains the real remedy. Gradual shifts, shifts that come and go, and shifts that read high are not flagged by design.
- **Limits:** 150 runs per cell on 15 inflow seeds; synthetic sensor; step-shaped falls; ASSUMED noise and missing-reading rates.

## Errors and surprises

Logged in `VALIDATION_AND_LIMITATIONS.md` §5 as E111–E116.
