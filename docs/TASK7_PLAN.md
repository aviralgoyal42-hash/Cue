# Task 7: a misalignment correction that allows for bladder filling (Experiment 9)

**Frozen 2026-11-10, before any Task 7 code was written or run.** This plan does not change after results are seen. Any change goes in the change log at the bottom and in §5 of `VALIDATION_AND_LIMITATIONS.md`, with the reason.

**Status: approved by Aviral on 2026-11-10 with one addition (§7, frozen before any code or run).**

**Results will be model predictions, not evidence for a device.**

**This plan is POST-HOC.** It was written after seeing the Experiment 8 results (`results/task6/SUMMARY.md`, E106), and it exists because of them. It is tested on the same 30 physiology traces, with new sensor seeds. Every Task 7 result must carry the POST-HOC label.

---

## 1. The problem (E106)

In Experiment 8 the flag worked, but the correction rescued only 2 of 6 cells. The correction divides the estimate by

> ratio = mean of the 15 readings after the fall ÷ mean of the 15 readings before it.

The bladder keeps filling between those two groups. So even a patch that had not moved would give a ratio above 1, and a patch reading at 0.70 gave a measured ratio of 0.818 (median). The estimate stayed about 14% low, and alerts at the 400 and 450 mL thresholds still came too late.

## 2. The change

**Only the ratio changes. The two flag rules are not touched,** so when a flag is raised stays exactly as in Experiment 8.

1. **Remember more.** The monitor keeps the times and values of its last 90 valid readings.
2. **Draw the filling line.** When rule 1 fires, the monitor fits a straight line (ordinary least squares, volume against time) through the remembered readings that are older than the newest 15. Those are all from before the flag's "after" group.
   - If fewer than 30 such readings exist, or the slope is negative, the slope is set to 0 and the line is flat at the mean of the 15 "before" readings. That is exactly the Task 6 correction.
3. **Compare with the line.** ratio = mean of the "after" readings ÷ mean of what the line says at those same times.
4. **Settle.** As in Task 6, the ratio is re-measured for the next 15 valid readings against the same line, then kept.
5. **Limits.** The ratio is kept between 0.40 and 1.00. Below 0.40 the device would be multiplying its estimate by more than 2.5, which is too much to trust from one measurement.

In plain words: *the device works out how fast the bladder was filling before the patch moved, works out what it should be reading now, and compares that with what it actually reads.*

| Value (all ASSUMED, fixed now) | Setting |
|---|---|
| Readings remembered | 90 |
| Fewest readings for the line | 30 |
| Slope allowed | 0 or more (the bladder does not shrink by itself) |
| Ratio limits | 0.40 to 1.00 |
| Every Task 6 monitor value | Unchanged |

The new behaviour is switched on by a new monitor setting, `fill_adjust`. It is **off by default**, so Experiment 8 and every earlier result reproduce as they are. `config.py` is not edited.

## 3. Runs

### 3.1 Experiment 9 (open loop)

- **Traces:** the same 30 Experiment 2b traces (15 inflow seeds × 2 sphincter strengths).
- **Scenarios:** the same 21 as Experiment 8 (the declared target, 6 variants, 14 without misalignment).
- **Sensor seeds:** new, 10 per trace and scenario: `SeedSequence([2000, scenario number, scaling × 100, inflow seed, repeat])`. **150 runs per scenario and sphincter strength**, 6,300 in all.
- **Thresholds:** 350, 400 and 450 mL.
- **Device variants on the same readings:** monitor off; Task 6 correction ("old"); filling-adjusted correction ("new"). The user never re-seats the patch.
- **Run time:** a few minutes.

### 3.2 Closed-loop probe (descriptive only)

The Task 6 probe again, with the new correction: pattern `e0.6_s0.0_5on5off`, ceiling 55, threshold 400, ×1.0 and ×0.9, seeds 42, 1, 2, for the anchor sensor and for `misaligned_at_4h`. **12 runs, about 5–10 min.** Reported next to the Task 6 probe rows. Invariants A2–A4 must hold. No verdict (3 seeds).

## 4. Criteria

| ID | Criterion | Required |
|---|---|---|
| **F1** | The flags are unchanged: with the same readings, the old and new variants raise the same flags at the same times, in every run | 100% of 6,300 runs |
| **M1, M2** | As in Task 6, recomputed on the new seeds | M1 ≥ 90% at each strength; M2 ≤ 5% in each of 28 cells |
| **R1** | `misaligned_at_4h`: median measured ratio, new correction | Between 0.65 and 0.75 at each sphincter strength (true value 0.70) |
| **M4** | With the new correction on, no cell without misalignment changes from "Cue works" (C1–C3 of Experiment 2) to "does not work" | 0 of 84 cells |

**M3, "less of a concern" (the Task 6 claim rule, unchanged).** For `misaligned_at_4h`, each of the 6 cells (3 thresholds × 2 strengths) is scored with C1–C3 for all three variants.
- A cell is rescued only if it passes C1, C2 and C3 with the new correction.
- Misalignment is called "less of a concern" **only for the rescued cells**. Each cell that still fails is reported as still failing.
- **The new correction is called an improvement only if** F1, M1, M2, R1 and M4 all pass **and** it rescues more of the 6 cells than the old correction does on the same readings, losing none that the old one rescued.
- **No number of rescued cells is promised.** The alert still needs 3 confirming readings, and the correction is only available some 15–30 minutes after the patch moves.

**Reported regardless**
- For every variant of misalignment: measured ratio (median, 5th and 95th percentile) against the true ratio, old and new; the 6 cells for all three device variants; late and missed alert rates; true volume at the first genuine alert.
- **Over-correction:** the share of runs where the new ratio is more than 0.05 below the true ratio, and the false-alert rate (C2) in every cell.
- How often the line fell back to a flat line, and why (too few readings, or negative slope).
- For the 14 scenarios without misalignment: C1–C3 with the monitor off, old and new.

## 5. How it would run

- **Code:** a `fill_adjust` option in `devices/misalignment_monitor.py`; `experiments/task7_experiment9.py`. Output only to `results/task7/`.
- **Tests first:** `tests/test_task7.py`, plus the whole fast suite, which must show the same single known failure (E88) and no change in the Task 6 tests.
- **Reproduction check before the experiment:** with `fill_adjust` off, the Experiment 8 run files must be reproduced exactly from the Experiment 8 seeds for the declared target (300 runs, file to file, by value). If not, the experiment does not start.
- **Truth stays on the evaluation side.** The line is fitted to readings only.
- **Old results** are not touched. Errors and surprises go in §5 from **E111**.
- **Keep-awake:** not needed for the open-loop part. For the 12 closed-loop runs, Aviral is asked first.

## 6. Declared limitations

- **POST-HOC.** The design answers a weakness seen in Experiment 8, on the same traces.
- **A straight line is a guess about the future.** If filling slows or the bladder starts to leak after the patch moves, the line reads too high, the ratio comes out too low, and the device **over-corrects**. That makes alerts early, not late, but early alerts are a cost and are reported.
- **Slope noise.** With an 11% sensor error the fitted slope is uncertain by roughly a sixth (an estimate, to be measured). Noisier sensors will give worse lines.
- **After an emptying session** the monitor has forgotten its readings, so for the next half hour the line is flat and the correction is the old one.
- **Everything in Task 6 §"Declared limitations" still applies:** synthetic sensor, step-shaped falls only, rule 1 sees falls only, no user who re-seats the patch, 150 runs per cell.
- **Small falls and the level rule's blind spots (E107) are not addressed here.**

## 7. Held-out gains (added at approval, before any code or run)

Aviral approved this plan on 10 Nov with one addition: **also test the new correction on gains 0.5 and 0.85, which were not used in the design, and report them separately, labelled held-out.**

- **Scenarios:** `mis_x0.5_at_4h` and `mis_x0.85_at_4h`, as defined in Experiment 8 (the fall starts at 4 h, with 30% extra missing readings). They are already among the 21 scenarios in §3.1, so no run is added.
- **What "held-out" means here, exactly.** The correction was designed from the ×0.70 result alone (E106), and no value in §2 was chosen using ×0.5 or ×0.85. But both gains were run in Experiment 8 with the old correction, and those results had been seen before this plan was written (measured ratio 0.579 for ×0.5 and 0.973 for ×0.85). They are held out from the design, not unseen.
- **Sensor seeds:** the new Experiment 9 seeds, like every other scenario.

| ID | Held-out criterion | Required |
|---|---|---|
| **H1** | ×0.5: median measured ratio with the new correction, over runs where the correction was applied | Between 0.45 and 0.55 at each sphincter strength |
| **H2** | ×0.85: the same | Between 0.80 and 0.90 at each sphincter strength |

**Reported for both, in their own section labelled HELD-OUT:** the share of runs in which a correction was applied at all; the measured ratio (median, 5th and 95th percentile), old and new; the share over-corrected (more than 0.05 below the true ratio); and the 6 cells for monitor off, old and new.

**How they count.** H1 and H2 are judged on their own. They are **not** part of the "improvement" rule in §4, which stays on the declared ×0.70 target. If H1 or H2 fails, the summary must say that the new correction is not shown to generalise to that gain, whatever the ×0.70 result is.

**Known in advance for ×0.85:** in Experiment 8 the level rule fired in only 40% (×1.0) and 76% (×0.9) of those runs, so many runs will have no correction at all. That share is reported, not hidden inside the median.

## Change log
- **2026-11-10, at approval, before any Task 7 code was written or run.** Added §7 (held-out gains 0.5 and 0.85, criteria H1 and H2) at Aviral's request. Nothing else changed. Status is now: approved, keep-awake approved for the closed-loop probe, new log entries from E111.
