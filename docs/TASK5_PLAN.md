# Task 5: how much sphincter suppression during bursts the model needs before emptying works

**Frozen 2026-11-08, before anything for Task 5 was run.** This plan does not change after results are seen. Any change goes in the change log at the bottom and in §5 of `VALIDATION_AND_LIMITATIONS.md`, with the reason.

**Results are model predictions, not evidence for a device.**

This is a model-only question. The numbers below are normalised model drives (0–1). They are **not** clinical stimulation parameters, and nothing here claims that any real device could reach these levels.

## 1. What is varied

**Sphincter level during bursts** (the co-activation value): **0, 0.1, 0.2, 0.3, 0.4, 0.5**.
- All six are **ASSUMED**. They are fixed now and will never be changed or tuned after results are seen.
- Levels 0 and 0.5 are the existing references: the `s0.0` and `s0.5` patterns of Experiment 3.
- What a level means, as implemented (`docs/FIGURE_AUDIT.md` §1, E87):
  - While a burst is ON, the level **replaces** the sphincter's input drive. It is not added to the drive.
  - Between bursts, the sphincter returns to the model's own reflex level: 0.5 while the urethra is closed at ×1.0, and 0.45 at ×0.9.
  - So 0.5 equals the resting drive at ×1.0 (slightly above it at ×0.9), and lower levels mean stronger suppression during bursts.

The new patterns `e{0.6,1.0}_s{0.1,0.2,0.3,0.4}_5on5off` are built inside the Task 5 script. They copy the existing `s0.0` 5 s on / 5 s off pattern and change only the sphincter level. `config.py` is **not** edited, because adding patterns to `config.STIM_PATTERNS` would also add them to the Experiment 3 grid. The six levels are added as one row to the §2 table of ASSUMED values.

## 2. Fixed subset of working settings (chosen before running)

The subset comes from the Experiment 3b working settings, so it is **POST-HOC and OPTIMISTIC**: these settings were picked because the patterns without co-activation empty there. All four settings below work in Experiment 3b and in the 15-seed Experiment 3 rerun (Task 4) at level 0.

| Factor | Value |
|---|---|
| Detrusor drive, burst timing | 0.6 and 1.0; 5 s on / 5 s off |
| Pressure ceiling | 55 cmH₂O |
| Alert threshold | 400 mL |
| Maximum duration | 60 s |
| Ultrasound interval during stimulation | 60 s |
| Sphincter strength | ×1.0 and ×0.9 |
| User, sensor, pressure channel | prompt, `anchor_11pct`, ok (the Experiment 3 defaults) |
| Seeds | 42 and 1–14 (15). One seed sets all four random streams, as before |

That gives 4 settings × 6 levels × 15 seeds = **360 runs, in one sweep**.

**Estimated run time: 30–80 min.** It is based on measured Experiment 3 run times with 12 workers (`results/stage6/exp3_runs.csv`, ceiling 55, 60 s sampling):
- about 50–67 s per run when the bladder empties;
- about 64–73 s per run at ×1.0 when it does not;
- about 243–277 s per run at ×0.9 when it does not, because the leak keeps the urethra solver busy (E21).

The low end assumes every level empties; the high end assumes no level above 0 does. Either way it is under 5 h, so the subset is not shrunk.

## 3. Success criteria (the same as Experiment 3)

These come from `docs/STAGE5_EXPERIMENT3_4_CRITERIA.md` §C and are scored with the unchanged `summarise_exp3`. Each setting × level is scored separately:

| ID | Criterion | Required |
|---|---|---|
| A2–A4 | Safety invariants recomputed from raw logs | 100% of runs |
| P1 | Sessions that void ≥ 50% of the pre-session true volume | ≥ 80% of sessions |
| P2 | Runs with no leakage outside sessions after the first alert | ≥ 95% of runs (all 15 of 15) |
| P3 | Sessions in which true p_D never exceeds the ceiling by more than 5 cmH₂O while stimulating | ≥ 95% of sessions |

A setting × level **works** when A2–A4, P1, P2 and P3 all pass.

**Reported for each setting**
- The **highest level at which it still works**. If the levels that work are not a single block from 0 upward, every level is reported as found. Nothing is interpolated, smoothed or extrapolated.
- How **leftover volume** changes with level. This is the true volume 120 s after each session ends, given as median and range.
- How **emptying time** changes with level. This uses the frozen definition in `docs/EMPTYING_DURATION_CHECK.md`, applied to 1 Hz samples of the true volume (±1 s), together with the "within 1 mL of the lowest volume" measure. It is given as median and maximum over sessions that voided at least 10%, plus the count of sessions that voided less.
- P1, P2 and P3 values, sessions per run, which cutoff ended each session, peak true p_D, leaked volume and maximum volume.

## 4. Step 2: the check before the sweep

This runs 4 settings × levels {0, 0.5} × seeds {42, 1, 2} = **24 runs**, with output in `results/task5/check/`.
- **Level 0** must reproduce the Task 4 rows (`results/task4/exp3_runs.csv` and `exp3_sessions.csv`, group `main`) **exactly**, in every shared column except `runtime_s` and the group label.
- **Level 0.5** must do the same, **and** show no session that voids 10% or more, as before.

If either check fails, the sweep does not start: the failure is logged in §5 and reported.

After the sweep, all 15 seeds at levels 0 and 0.5 are compared with Task 4 in the same way, and the result is reported.

## 5. How it runs

- **Script:** `experiments/task5_sphincter_levels.py`. It reuses the unchanged rig, device, controller, `closed_loop_metrics` and `summarise_exp3`, and writes only to `results/task5/`.
- **Truth stays on the evaluation side.** The device never reads true volume (unchanged device code). Emptying time is computed on the evaluation side.
- **No void switch.** The upstream void switch is never used: under SCI, `is_voiding` is always False.
- **No traces.** Full traces are not saved.
- **Saving as it goes.** Partial files are saved every 25 runs by writing a temporary file and renaming it. The sweep resumes from them if restarted. Partial files are never deleted by hand and never treated as the full grid. Final files are written only after all 360 runs.
- **Staying awake.** The app's keep-awake hold is on (approved by the user). As a backup, approved by the user, the sweep process asks Windows to stay awake (`SetThreadExecutionState`, system-required only). That request ends when the process exits, and no setting changes. The screen stays on, by the user's choice.
- **Tests and freezes.** `tests/test_task5_levels.py` is written and run before Step 2. No code is edited while the sweep runs.
- **Old results.** `results/task4/` and older result folders are not touched.
- **Log entries.** Errors and surprises go in §5 from **E100**: E93–E99 are taken by the 15-seed rerun, and the "old results unchanged: False" item is E94 with its 8 Nov note.

## 6. Declared limitations

- **The subset is narrow:** one ceiling (55), one threshold, one maximum duration and one burst timing. The answer may differ elsewhere, for example at ceiling 40 (E63).
- **15 seeds are not proof.** Fifteen clean runs only show a rate of about 82% or more, not 95% (E68).
- **Missing physiology.** The model has no dyssynergia, no fatigue, no fibre types and no sacral anatomy. The sphincter level is a replaced model drive, not a recruitment level.
- **Unrealistic leftovers.** The model empties almost to zero, which is unrealistic (E35 and its correction), so the leftover volumes are model numbers, not post-void residuals.
- **Timing resolution.** Emptying time is measured at 1 Hz (±1 s).
- **All POST-HOC and OPTIMISTIC.** Every result is POST-HOC and OPTIMISTIC, because the settings come from Experiment 3b.

## Change log
- (none)
