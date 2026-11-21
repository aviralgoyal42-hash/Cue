# Task 6: a sphincter block during bursts, and a patch-misalignment monitor

**Frozen 2026-11-10, before anything for Task 6 was run.** This plan does not change after results are seen. Any change goes in the change log at the bottom and in §5 of `VALIDATION_AND_LIMITATIONS.md`, with the reason.

**Results are model predictions, not evidence for a device.**

**The user's request (10 Nov, paraphrased):**
1. Have a way to control the sphincter: block it off so that it relaxes during a burst.
2. Make misalignment less of a concern, and have a way to flag misalignments.

Both mechanisms are **off by default**, so every earlier result is unchanged. Every new number below is **ASSUMED**, was chosen before any Task 6 run, and will not be tuned. `config.py` is not edited: the Task 6 values live in the Task 6 scripts, as in Task 5.

---

## Part A: the sphincter block

### A.1 What it is

A second hypothetical channel next to the hypothetical stimulator. It stops part of the sphincter's drive from reaching the muscle. In the model it is one number, `sphincter_block`, from 0 to 1:

> sphincter input = (what it would have been) × (1 − `sphincter_block`)

- 0 is no block (the old behaviour, exactly). 1 is a complete block.
- **Scope "burst"** (the request): the block acts only while a burst is ON. It removes co-activation and nothing else.
- **Scope "session"**: the block acts from the start to the end of the session, so it also cuts the sphincter's own reflex drive in the gaps between bursts. This is closer to how a nerve block would behave, and it has never been run.
- **Fault `block_fails_at_s`**: the block stops working this many seconds into the session.

Code: `devices/stimulator.py` (`BurstPattern`, `HypotheticalStimulator.sphincter_input`) and one line in `sci_test_rig.py`.

**What it is not.** It is a normalised model drive. It is not a nerve-block setting, and nothing here says a real device could reach any block level. The model has no nerve, no fibre types, no block onset and no dyssynergia.

**Why the idea is not invented here.** Animal studies report bladder emptying when sacral-root or pudendal stimulation is combined with a high-frequency electrical block of the pudendal nerve, which relaxes the external sphincter (Boger, Bhadra & Gustafson, *Neurourol Urodyn*, doi:10.1002/nau.20538). In people, the Brindley procedure avoids the problem differently, by cutting the sensory roots (Martens & Heesakkers 2011, review). **Both were checked through search-result summaries only on 10 Nov; the full texts were not read.** They show the idea exists. They are not evidence that Cue's block would work.

### A.2 Why most of the answer is already known

With scope "burst", a block of *b* on the 0.5 co-activation pattern gives a sphincter level of 0.5 × (1 − *b*) during bursts. That is exactly what Task 5 varied:

| Block on the `s0.5` pattern | Level during bursts | Task 5 result (15 seeds) |
|---|---|---|
| 0% | 0.5 | Nothing empties |
| 20–60% | 0.4–0.2 | Fails P1 in all 4 settings |
| **80%** | **0.1** | **Works in all 4 settings**; leftover volume rises |
| 100% | 0.0 | Works in all 4 settings |

So Part A does not repeat Task 5. It checks that the new mechanism reproduces Task 5 exactly, and probes what Task 5 could not show.

### A.3 Runs (closed loop)

The fixed Task 5 subset is used unchanged: detrusor 0.6 and 1.0, 5 s on / 5 s off, ceiling 55 cmH₂O, threshold 400 mL, maximum duration 60 s, 60 s ultrasound interval, sphincter ×1.0 and ×0.9 (4 settings). It is **POST-HOC and OPTIMISTIC**, as before. Seeds 42, 1 and 2. The base pattern is always the co-activation pattern `e{0.6,1.0}_s0.5_5on5off`.

| Group | Block | Scope | Fault | Runs | Judged how |
|---|---|---|---|---|---|
| A-check | 0.8 and 1.0 | burst | none | 24 | **Must equal** the Task 5 rows at levels 0.1 and 0.0 |
| A-check | 1.0 | burst | fails at 0 s | 12 | **Must equal** the Task 5 rows at level 0.5 |
| A-fault | 1.0 | burst | fails at 20 s | 12 | Descriptive |
| A-session | 0.8 and 1.0 | session | none | 24 | Descriptive |

- **"Must equal"** means every shared column of the run and session tables, compared file to file by value, except `runtime_s`, `group`, `stim_name` and the `reference` label. If any value differs, the claim "Task 5 applies to the block" is withdrawn and the difference is logged.
- **Invariants A2–A4** are recomputed from raw logs and must hold in 100% of the 72 runs.
- **Descriptive groups** report, per setting: P1, P2 and P3 values (Experiment 3 definitions, unchanged), sessions per run, leftover volume, which cutoff ended sessions, peak true p_D, and leak outside sessions. **They carry no "works" verdict:** 3 seeds give poor rates (E99). A 15-seed sweep would be a new frozen plan.

---

## Part B: the misalignment monitor (Experiment 8)

### B.1 What it is

Experiment 6 failed because it compared one estimate with the *highest* estimate of the last 15 minutes, using a fixed drop. The new `MisalignmentMonitor` (`devices/misalignment_monitor.py`) sees readings only, like the device, and uses two rules.

**Rule 1, level drop.** The bladder cannot shrink by itself between emptyings.
- Take the last 30 valid readings: the older 15 ("before") and the newer 15 ("after").
- change = mean(after) ÷ mean(before) − 1.
- noise = the scatter of one reading, measured from the jumps between neighbouring readings (last 120 jumps).
- Flag when the change is at most −*k* × noise × √(2/15), **and** at most −10%, **and** mean(before) is at least 100 mL.

**Rule 2, dropout rise.** Count missing readings among the last 20. Compare with the share that went missing before that (at least 120 earlier readings, nudged upward by two standard errors, never below 2%). Flag when a count this high would happen by luck less than 1 time in 10,000.

**Working together.** Once rule 2 has fired, rule 1 asks for less proof (*k* = 2.0 instead of 3.5).

**What the device does with a flag**
1. It raises `CHECK_PATCH`: the watch would ask the user to look at the patch.
2. **Correction:** if rule 1 fired, the device divides its estimate by the measured ratio mean(after) ÷ mean(before), until the user confirms the patch is back (`patch_reseated`). A wrong correction makes the estimate too high, so the alert comes early, not late.
3. Around a stimulation session the monitor is paused and then restarted from fresh readings, because emptying is a real fall.

| Value (all ASSUMED, fixed now) | Setting |
|---|---|
| Readings per group | 15 |
| *k*, and *k* after a dropout flag | 3.5, 2.0 |
| Smallest drop that can flag | 10% |
| Smallest "before" level | 100 mL (as in Experiment 6) |
| Jumps used for noise; noise floor | 120; 2% |
| Dropout window; earliest baseline; chance; floor | 20 readings; 120 readings; 1 in 10,000; 2% |

### B.2 Runs (open loop, like Experiments 2, 5 and 6)

- **Traces:** the 30 saved Experiment 2b ground-truth traces (15 inflow seeds × 2 sphincter strengths). Nothing changes the physiology.
- **Sensor seeds:** 10 per trace and scenario, new ones (`SeedSequence([1000, scenario number, scaling × 100, inflow seed, repeat])`). That gives **150 runs per scenario and sphincter strength**.
- **Thresholds:** 350, 400 and 450 mL, as in Experiment 5.
- **Device variants on the same readings:** monitor off; monitor on, flag only; monitor on with correction. The user never re-seats the patch (the worst case for the correction).

**Scenarios**

| Kind | Scenarios |
|---|---|
| Declared target | `misaligned_at_4h` from `config.py`: reads at ×0.7 from 4 h, with 30% extra missing readings |
| Target variants (built in the script) | ×0.5 and ×0.85 at 4 h; ×0.7 at 2 h and at 6 h; ×0.7 at 4 h **with no extra missing readings**; **extra missing readings only** (×1.0) at 4 h |
| No misalignment | All 14 other `config.SENSOR_SCENARIOS`: ideal, anchor_11pct, mre_20pct, mre_30pct, mre_40pct, gain_minus20, gain_plus20, drift_minus2ph, drift_plus2ph, delay_5min, delay_15min, missing_20pct, missing_50pct, combined_bad |

### B.3 Criteria

| ID | Criterion | Required |
|---|---|---|
| **M1** | `misaligned_at_4h`: no flag before 4 h, and the first flag within 30 min after 4 h (the Experiment 6 definition) | ≥ 90% of runs, at each sphincter strength |
| **M2** | Runs with any flag, in each of the 14 scenarios without misalignment | ≤ 5% of runs, for each scenario at each sphincter strength (28 cells) |
| **M4** | With the monitor and correction on, no scenario × threshold × sphincter-strength cell without misalignment changes from "Cue works" (C1–C3 of Experiment 2) to "does not work" | 0 cells |

**The flag works** only if M1 and M2 both pass. M1 and M2 are the frozen Experiment 6 criteria; M2 is applied to 14 scenarios instead of 7, which is stricter.

**M3, "less of a concern" (reported, with the claim rule fixed now).** For `misaligned_at_4h`, each of the 6 cells (3 thresholds × 2 strengths) is scored with C1–C3 of Experiment 2, with the monitor off, flag only, and with correction. Before Task 6, 0 of 6 work.
- A cell counts as rescued only if it passes C1, C2 and C3 with correction on.
- Misalignment is called "less of a concern" **only for the cells that are rescued**. Every cell that still fails is reported as still failing.
- A flag alone rescues nothing in this experiment, because no user acts on it here.

**Reported regardless**
- For every target variant: the M1-style rate at its own start time, which rule fired first, the time from misalignment to flag, the measured ratio against the true one, and the 6 C1–C3 cells in all three device variants.
- For the 14 other scenarios: the flag rate by rule, and C1–C3 with the monitor off and on.
- For all: late and missed alert rates, and the true volume at the first genuine alert.
- Rule 1 alone and rule 2 alone, so it is clear how much depends on the ASSUMED extra missing readings.

### B.4 Closed-loop probe (descriptive only)

To see the pause-and-restart around sessions in a real loop: pattern `e0.6_s0.0_5on5off`, ceiling 55, threshold 400, ×1.0 and ×0.9, seeds 42, 1, 2, for three cases: anchor sensor with the monitor on; `misaligned_at_4h` with the monitor off; `misaligned_at_4h` with the monitor and correction on. **18 runs.** Reported: flags per run and their times against session times, sessions, P1–P3 values, maximum true volume. Invariants A2–A4 must hold. No verdict (3 seeds).

---

## How it runs

- **Scripts:** `experiments/task6_block_check.py` (Parts A and B.4, 90 closed-loop runs, about 10–20 min) and `experiments/task6_experiment8.py` (Part B, open loop, a few minutes). Both write only to `results/task6/`.
- **Tests first:** `tests/test_task6.py` is written and run before either script, together with the whole fast suite, which must give the same passes and the same single known failure (E88) as on 8 Nov.
- **Truth stays on the evaluation side.** The monitor and the device see readings only; a test enforces this for the new file.
- **No void switch, no clinical parameters, nothing in the brain.**
- **Old results** are not touched. Errors and surprises go in §5 from **E104**.

## Declared limitations

- **Part A is a relabelling in this model.** A burst-scope block is mathematically the same as a lower co-activation level. The model cannot say whether a block is achievable, how fast it starts, or what it does to reflexes. Emptying still needs at least an 80% block of the 0.5 co-activation (Task 5), and leftover volume is already higher at 80%.
- **Three seeds** in the descriptive groups.
- **The monitor is tested on a synthetic sensor.** The step size, the extra missing readings and the noise shape are all ASSUMED. Real misalignment may be gradual, may come and go with posture, and may read high instead of low. **Rule 1 only looks for falls.** A patch that starts reading high gives early alerts and is not flagged.
- **The correction is a single ratio.** The ratio includes the filling that happened between the two groups of readings, so it under-corrects a little. If the patch moves back by itself, the estimate reads high until the user confirms.
- **Slow misalignment and small steps** (for example ×0.85) are not expected to be flagged. They are reported as found.
- **15 seeds are not proof** (E68). 150 runs per cell can show a 5% rate only roughly.
- **No user in Experiment 8.** Whether people would re-seat a patch when asked is not modelled.

## Change log
- **2026-11-10, before any Task 6 experiment was run (E104).** The first run of the unit tests showed that the correction used the ratio measured at the moment of the flag. Rule 1 fires as soon as the fall is clear, when the "after" group still holds readings from before the patch moved, so that ratio was too mild (0.90 measured for a true 0.70 on a made-up quiet signal). **Change:** after rule 1 fires, the ratio is re-measured against the same "before" average for the next 15 valid readings, then kept. No flag rule, criterion, scenario or value in the tables above changed. No experiment result existed when this was changed.
