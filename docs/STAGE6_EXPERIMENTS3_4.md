# Project Cue: Stage 6, Experiment 3 (full loop) and Experiment 4 (faults)

Date: 2026-11-04. Criteria: `docs/STAGE5_EXPERIMENT3_4_CRITERIA.md`, including its logged addition of a second reference.

All numbers are **model predictions** from a synthetic sensor, a hypothetical stimulator and a synthetic pressure channel. Each cell has only 3 inflow seeds, so rates move in steps of 33%. Nothing here shows clinical safety or effectiveness.

Outputs in `results/stage6/`:
- `exp3_runs.csv`, `exp3_sessions.csv`, `exp3_settings_summary.csv`
- `exp4_runs.csv`, `exp4_sessions.csv`, `exp4_fault_summary.csv`
- `comparison_exp1_to_exp4.csv` and `.png`
- `exp3_P1_by_pattern_and_ceiling.png`, `exp4_fault_map.png`

## Experiment 3: full loop (312 runs, no crashes)

Anchor sensor (best case), prompt user, 12 h.

**Safety rules (A2–A4) held in all 312 runs,** recomputed from the raw logs: stimulation started only after an alert and a press, never during lockout, and every session ended within the maximum duration.

**38 of 104 settings meet P1, P2 and P3. All 38 have no sphincter co-activation.**

| Stimulation pattern (normalised drive) | Ceiling 40 | Ceiling 55 | Ceiling 70 |
|---|---|---|---|
| Detrusor 0.6, co-activation 0, continuous | works (all 4 cases) | works | works |
| Detrusor 0.6, co-activation 0, 5 on / 5 off | works with ×0.9, **fails with default sphincter** (P3) | works | works |
| Detrusor 1.0, co-activation 0, continuous or 5 on / 5 off | **fails** (P1) | works | works |
| Any pattern with co-activation 0.5 | **fails** | **fails** | **fails** |

"Cases" are the two sphincter strengths × the two ultrasound rates during stimulation.

### Main findings
1. **The declared reference pattern (co-activation 0.5) never empties the bladder.** P1 is 0%. There are about 10.7 futile sessions per 12 h run, and a median residual of 486 mL (×0.9) to 641 mL (default). With the default sphincter, volume keeps rising to about 900 mL by 12 h, and the alert does nothing useful. With the weaker sphincter, every run overflows after the alert, leaking about 390 mL. Changing the threshold (350 or 450 mL) or the maximum duration (30 or 120 s) does not help (P1 stays 0%).
2. **Without co-activation, one or two sessions keep the bladder under control.** Maximum volume is about 400–421 mL, there is no overflow after the alert, and median residual in the working settings is 1.3–97 mL. This is an **idealised stimulator that drives only the detrusor**. Sacral roots carry both kinds of fibre, so this is the optimistic case, not a prediction for real stimulation.
3. **A ceiling that is too low defeats the emptying.** At 40 cmH₂O with detrusor drive 1.0, the ceiling ended every session early. The median residual was about 323–329 mL, with 22–23 sessions in 3 runs. The ceiling protects against pressure, but here it also prevents emptying. This trade-off is a result, not a tuning opportunity.
4. **At 40 cmH₂O the pressure "exceeded" is partly the full bladder itself.** With co-activation, P3 falls to 0.19 (×0.9) and 0.78–0.88 (default), because storage pressure near full is already well above 40 before any stimulation.
5. **Volume stop almost never helps.** At the normal 60 s sampling it fired in **0 of 1,236 sessions**, because the median estimate cannot update within a 60 s session. At 5 s sampling during stimulation it fired in 87 of 978 sessions, all without co-activation. So the volume cutoff depends on a faster sampling rate than the alert needs. The maximum-duration cutoff is what actually bounds stimulation.
6. **Highest true pressure during stimulation:** 53.8 cmH₂O in the working settings, and 58.5 cmH₂O across all Experiment 3 settings (threshold 350, co-activation). The model's healthy-void peak is 54.7 cmH₂O. No claim of safety follows from this.

## Experiment 4: faults (324 runs, no crashes)

Each fault was applied one at a time on two references:
- **R1:** the declared reference (co-activation 0.5);
- **R2:** added after the stimulation map (no co-activation).

Both use a 55 cmH₂O ceiling, 400 mL threshold, prompt user and anchor sensor, for both sphincter strengths and 3 inflow seeds. Full table: `exp4_fault_summary.csv`.

**Safety rules (A2–A4) held in all 324 runs, under every fault.** With the pressure channel dead and the estimate stuck high, every session still ended at maximum duration. This is the required worst case for the cutoffs.

| Fault (on R2 unless stated) | What happened |
|---|---|
| Estimate stuck **high** (450 mL from 5 h) | The device keeps alerting and the prompt user keeps pressing: **12 sessions per run**, so the bladder is stimulated repeatedly at low volume. Nothing stops this except the lockout and the user. With a dead pressure channel as well, on R1, true pressure reached **64.2 cmH₂O**, 9.2 above the ceiling. This is the highest pressure in Experiment 4. |
| Estimate stuck **low** (50 mL from 3 h) | **No alert at all.** Default sphincter: volume reaches about 900 mL. ×0.9: about 412 mL leaks with no warning. The "overflow despite alert" metric reads 0 here because no alert was sent, so that metric understates this failure. |
| Misaligned patch | Default: volume reaches about 565 mL before action. ×0.9: only 0.33 sessions per run and about 274 mL leaked. |
| Gain −20%, combined bad sensor | Late alerts. Sessions start at higher volumes, so the 55 cmH₂O ceiling cuts some short. P1 falls to 0.71–0.83, and with ×0.9, 67% of runs overflow (22–37 mL). |
| Noisy sensors (20–40%), gain +20%, drift +2%/h | Alerts come early, sessions are more frequent (2.7–3.3 per run) and residual is higher (about 95–120 mL). Still safe by the invariants. |
| Delay, missing readings | Little change. |
| User delayed (30–90 min) | P1 falls to 0.60–0.75. With ×0.9, 33% of runs overflow (about 38 mL). Peak pressure 56.7 cmH₂O, 1.7 above the ceiling. |
| User never presses | No stimulation, as designed. The outcome is the SCI baseline: about 900 mL, or overflow of about 412 mL with ×0.9. **The alert alone changes nothing without a response.** |
| Accidental presses, no alert | Both presses per run were ignored. No stimulation. |
| Second press in lockout | Ignored (2 per run on R2, 10.7 on R1). |
| Button held 15 min | Identical to the no-fault run. |
| Pressure channel noisy (±10 cmH₂O) | **False ceiling trips.** Every session was cut short. P1 falls to 0.15, residual is about 300 mL, and there are 4.3 sessions per run. Safe in the narrow sense, but emptying fails. |
| Pressure channel dead, stuck low or reading 30% low | The ceiling cannot fire. Maximum duration ended every session. True pressure stayed at or below 53.8 cmH₂O on R2 from this starting volume, but only because the bladder was emptying. On R1 it reached up to 57.3 cmH₂O, and 64.2 in the worst combination above. |

## Comparison across Experiments 1–4

`comparison_exp1_to_exp4.png` and `.csv` show the same simulated person (default sphincter, inflow seed 42), and the CSV also covers ×0.9. In the figure, Experiments 1 and 2 share one physiology, and they overlap with Experiment 3 at co-activation 0.5, because that stimulation removes nothing. Experiment 3 without co-activation and the Experiment 4 no-fault run are the same case.

## What this does and does not show

- **Shows:** in this model, the safety logic held under every fault tested, and the maximum-duration cutoff works without sensors.
- **Does not show:**
  - that the concept empties a bladder. That result depends entirely on the ASSUMED co-activation value, and the model has no dyssynergia and no sacral anatomy;
  - that any pressure value is safe;
  - that any setting would work in a person.

## Update 2026-11-08: rerun with 15 seeds

This report is kept as written. Experiments 3 and 4 were rerun with 15 seeds (42 and 1 to 14) on the same grid and criteria. Seeds 42, 1 and 2 reproduced these results exactly, and no verdict changed: 38 of 104 settings still work, and the invariants held in all 3,180 runs. Some descriptive figures moved: the highest Experiment 3 peak is 60.2 cmH₂O (58.5 here), the dead-pressure worst case is 67.2 cmH₂O (64.2 here), and several 3-seed Experiment 4 rates were poor estimates. See `docs/EXPERIMENT3_4_15SEED_RESULTS.md` and `VALIDATION_AND_LIMITATIONS.md` §5, E93–E99.
