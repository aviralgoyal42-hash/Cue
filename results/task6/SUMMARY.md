# Task 6 results: sphincter block and misalignment monitor

Date: 2026-11-10. Plan and criteria: `docs/TASK6_PLAN.md`, frozen before any run. One change was logged there before any experiment ran (E104).

**Results are model predictions, not evidence for a device.** The sensor is a synthetic experimental proxy and the stimulator and block are hypothetical. Part A uses Experiment 3b settings, so it is **POST-HOC and OPTIMISTIC**.

## Short answers

1. **Sphincter block.** The stimulator now has a block that cuts the sphincter's drive during bursts. It reproduces Task 5 exactly, so the Task 5 answer carries over: **emptying needs at least an 80% block of the 0.5 co-activation**, and a complete block is better. Two new findings from 3-seed probes: a block held for the whole session empties more than a block during bursts only, and **a block that fails mid-session at full detrusor drive gave the highest pressure seen in the project (73.8 cmH₂O)**.
2. **Flagging misalignment.** The new monitor **passes both frozen criteria** that the Experiment 6 detector failed: it flagged the declared misalignment within 30 minutes in 150 of 150 runs at both sphincter strengths, and gave false flags in at most 2.0% of runs in any scenario without misalignment.
3. **Making it less of a concern.** The automatic correction **rescues 2 of 6 cells** (the 350 mL threshold at both sphincter strengths). At 400 and 450 mL it helps a lot but still fails. Misalignment is smaller, not solved.

---

## Part A: the sphincter block (closed loop, 3 seeds)

90 closed-loop runs, 0 errors. Invariants A2–A4 held in all 90. Files: `results/task6/block_*.csv`, `block_check.json`.

### A.1 The check: the block reproduces Task 5 exactly

| Compared | Rows | Columns | Differences |
|---|---|---|---|
| Runs (block 0.8, block 1.0, block failing at 0 s) against Task 5 levels 0.1, 0.0, 0.5 | 36 of 36 | 34 | **None** |
| Sessions | 176 of 176 | 27 | **None** |

So, for a block that acts during bursts only, the 15-seed Task 5 results apply as they stand (`results/task5/SUMMARY.md`):

| Block of the 0.5 co-activation | Task 5 result (15 seeds, 4 settings) |
|---|---|
| 0–60% | Does not work (fails P1) |
| **80%** | **Works in all 4 settings.** Leftover volume is higher: median 82–91 mL at detrusor 0.6 and 116–121 mL at detrusor 1.0 |
| 100% | Works in all 4 settings. Leftover median 2 mL at detrusor 0.6 and 62–68 mL at detrusor 1.0 |

The boundary between 60% and 80% is not resolved, as in Task 5.

### A.2 Probe: the block fails 20 s into the session (3 seeds, descriptive, no verdict)

| Detrusor drive | Sessions voiding ≥ 50% | Median voided | Median leftover | Peak true p_D | Sessions within ceiling + 5 |
|---|---|---|---|---|---|
| 0.6 (×1.0 / ×0.9) | 0 of 12 / 0 of 12 | 37% / 38% | 247 / 245 mL | 50.0 / 49.2 cmH₂O | 12 of 12 / 12 of 12 |
| **1.0** (×1.0 / ×0.9) | 9 of 9 / 9 of 9 | 58% / 58% | 166 / 161 mL | **72.0 / 73.8 cmH₂O** | **5 of 9 / 5 of 9** |

- **At detrusor 1.0 the pressure overshoots the 55 cmH₂O ceiling by 17–19 cmH₂O.** When the block fails, the sphincter closes against a fully driven detrusor. The pressure-ceiling cutoff ended every one of these sessions, but only after the spike. 73.8 is above the 67.2 that was the highest pressure quoted before (dead pressure channel, Task 4).
- At detrusor 0.6 the pressure stays under the ceiling, but emptying stops early and the person needs 4 sessions per run.
- A block that never works (fails at 0 s) is the old co-activation case: nothing empties.

**A sphincter block adds a new way to fail.** The existing cutoffs limit how long the spike lasts, not how high it goes.

### A.3 Probe: the block acts for the whole session (3 seeds, descriptive, no verdict)

Median leftover volume, burst-only block against whole-session block (×1.0 / ×0.9):

| Detrusor, block | During bursts only | Whole session |
|---|---|---|
| 0.6, 80% | 85 / 74 mL | **1.5 / 1.5 mL** |
| 0.6, 100% | 1.5 / 1.5 mL | 1.3 / 1.3 mL |
| 1.0, 80% | 136 / 107 mL | 75 / 78 mL |
| 1.0, 100% | 53 / 73 mL | 8 / 3 mL |

- Every session in these 24 runs voided at least 50% (lowest 69%).
- With the whole-session block, urine also flows in the gaps between bursts (in 31–100% of the gap time).
- Peak pressure at detrusor 0.6 is lower: 38–40 cmH₂O, against 46–49.
- No leak outside sessions. Flow stopped within 2 s of the end of stimulation.

**In these 3 seeds a whole-session block empties more, and an 80% block is then enough for near-complete emptying at detrusor 0.6.** Three seeds give poor rates (E99), so this is a lead, not a result. A 15-seed sweep would need a new frozen plan.

### A.4 What Part A does not show

A burst-only block is the same thing, in this model, as a lower co-activation level. The model cannot say whether a real block could reach 80%, how fast it starts or stops, or what it does to reflexes. The sources in the plan were checked through search summaries only.

---

## Part B: Experiment 8, the misalignment monitor (open loop)

6,300 runs: 21 scenarios × 2 sphincter strengths × 15 inflow seeds × 10 sensor seeds, each scored at 3 thresholds with 3 device variants. Files: `results/task6/exp8_*.csv`, `exp8_criteria.json`.

### B.1 Criteria

| ID | Criterion | Required | Result | Verdict |
|---|---|---|---|---|
| M1 | `misaligned_at_4h`: first flag within 30 min after 4 h, none before | ≥ 90% | **100% and 100%** (150 of 150 at ×1.0 and at ×0.9) | **Pass** |
| M2 | Runs flagged in each of 14 scenarios without misalignment | ≤ 5% in each of 28 cells | Highest cell **2.0%** (3 of 150). 25 flagged runs in 4,200 | **Pass** |
| M4 | Cells without misalignment that change from "works" to "does not work" | 0 | **0 of 84** (54 work with the monitor off and the same 54 with it on) | **Pass** |

**The flag works by the frozen rule (M1 and M2 both pass).** In Experiment 6 the best M1 was 68.7% and false flags reached 100%.

### B.2 How much depends on each rule

Share of `misaligned_at_4h` runs flagged on time (×1.0 / ×0.9):

| Rules used | On time |
|---|---|
| Both (as designed) | 1.000 / 1.000 |
| Rule 1 alone (level drop) | 0.933 / 0.920 |
| Rule 2 alone (dropout rise) | 0.927 / 0.953 |

- Each rule alone also clears 90%, with little margin. Together they reach 100%.
- Median time from misalignment to flag: **13 min**.
- **Rule 2 depends on an ASSUMED feature of the scenario** (30% extra missing readings). With no extra missing readings (`mis_x0.7_at_4h_gain_only`), rule 1 carries the flag alone: 0.953 / 0.960 on time.
- Of the 25 false flags, 22 came from rule 1 and 3 from rule 2.

### B.3 Other kinds of misalignment (reported, not criteria)

| Variant | Flagged on time (×1.0 / ×0.9) | Note |
|---|---|---|
| ×0.5 at 4 h | 1.000 / 1.000 | Median 9 min |
| ×0.7 at 6 h | 1.000 / 1.000 | |
| ×0.7 at 2 h | 0.967 / 0.967 | Rule 1 alone only 0.493 / 0.527: the bladder is small and fills fast, which hides the fall |
| ×0.7 at 4 h, no extra missing readings | 0.953 / 0.960 | Rule 1 only |
| Extra missing readings only | 0.947 / 0.933 | Rule 2 only |
| **×0.85 at 4 h** | 0.913 / 0.940 | **Rule 1 alone flags only 0.040 / 0.027.** A 15% fall is flagged only because of the extra missing readings |

**A small fall with no extra missing readings would go unflagged.** That case was not run, but rule 1 alone at ×0.85 shows it.

### B.4 "Less of a concern": the correction (M3)

`misaligned_at_4h`, share of runs with a useful alert (C1 needs ≥ 0.95), and the median true volume at the alert:

| Threshold, strength | Monitor off | Flag only | Flag and correction | Works with correction? |
|---|---|---|---|---|
| 350 mL, ×1.0 | 0.693, 490 mL | 0.693 | **1.000**, 403 mL | **Yes (rescued)** |
| 350 mL, ×0.9 | 0.393, 486 mL | 0.393 | **0.973**, 403 mL | **Yes (rescued)** |
| 400 mL, ×1.0 | 0.013, 552 mL | 0.013 | 0.887, 456 mL | No (C1) |
| 400 mL, ×0.9 | 0.000 | 0.000 | 0.753, 461 mL | No (C1 and C3) |
| 450 mL, ×1.0 | 0.000, 619 mL | 0.000 | 0.427, 515 mL | No |
| 450 mL, ×0.9 | 0.000 | 0.000 | 0.260, 486 mL | No |

- **Rescued: 2 of 6 cells.** Before Task 6: 0 of 6. By the frozen claim rule, misalignment is "less of a concern" **only at the 350 mL threshold**. The four cells at 400 and 450 mL still fail.
- **A flag alone changes nothing here**, because no user acts on it in this experiment. The flag-only numbers equal the monitor-off numbers in every cell.
- **Why the correction falls short: it under-corrects.** The true ratio is 0.70. The measured ratio has a median of **0.818** (5th–95th percentile 0.743–0.895 at ×1.0). The bladder keeps filling between the "before" and "after" readings (roughly half an hour apart; an estimate, not measured), and that filling hides part of the fall. The plan named this limitation; it is larger than "a little".
- The correction was applied in 150 of 150 runs at ×1.0 and 149 of 150 at ×0.9.
- No false alerts were added: the false-alert rate stays 0.000 in all 6 cells.

Other variants with correction on (cells working out of 6, before → after): ×0.5 at 4 h: 0 → 2. ×0.7 with no extra missing readings: 0 → 2. ×0.7 at 6 h: 2 → 4. ×0.85: 3 → 3. ×0.7 at 2 h: **0 → 0** (measured ratio 0.937, so almost no correction). Extra missing readings only: 6 → 6.

### B.5 What this does and does not show

- **Shown, in this model:** a step fall of 30% or more in a sensor with 11% error can be flagged within 30 minutes with few false flags, using readings only.
- **Not shown:** anything about a real patch. The step shape, the extra missing readings and the noise are ASSUMED. Gradual shifts, shifts that come and go, and shifts that read high are not flagged by design.
- **Not solved:** the alert volume under misalignment at 400 mL and above; early misalignment (2 h); small falls without extra missing readings.
- **Not tested:** a user who re-seats the patch when asked. That is the real remedy, and `patch_reseated` exists in the device for it, with unit tests only.

### B.6 Closed-loop probe (18 runs, 3 seeds, descriptive, no verdict)

Pattern `e0.6_s0.0_5on5off`, ceiling 55, threshold 400 mL.

| Case | Patch checks | First alert | Highest true volume | Sessions voiding ≥ 50% |
|---|---|---|---|---|
| Anchor sensor, monitor on (×1.0 and ×0.9) | **0 in 6 runs** (12 sessions) | 5.5–6.5 h | 391–411 mL | 12 of 12 |
| Misaligned, monitor off, ×1.0 | – | 7.0–8.1 h | 549–600 mL | 3 of 8 |
| Misaligned, monitor on, ×1.0 | 3 of 3 runs, at 4.15–4.30 h | 6.3–7.1 h | 411–548 mL | 5 of 6 |
| Misaligned, monitor off, ×0.9 | – | **No alert in 2 of 3 runs** | 488–491 mL (leaking) | 1 of 1 |
| Misaligned, monitor on, ×0.9 | 3 of 3 runs, at 4.15–4.30 h | 6.3–7.9 h | 411–490 mL | 5 of 5 |

- **Emptying did not cause a false flag** in any of the 6 anchor runs, so the pause around sessions works in the loop. Their summary numbers equal those of the same runs with the monitor off (the level-0 rows of Part A).
- With the monitor on, every misaligned run got an alert. One run in each strength (seed 42) was still late: the session started near 490–500 mL.
- Invariants A2–A4 held in all 18 runs.

---

## Errors and surprises

Logged in `VALIDATION_AND_LIMITATIONS.md` §5 as E104–E110.
