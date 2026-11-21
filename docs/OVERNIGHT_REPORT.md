# Overnight report (unattended run, started 2026-11-04)

Status: COMPLETE. All eight items were done. The user came back partway through and made two decisions (D13, D14). **No shutdown was run**, by the user's choice.

> **Warning.** Everything below is a model prediction from a synthetic sensor, a hypothetical stimulator and a synthetic pressure channel. It proves nothing clinically.

## The three most important findings

1. **Whether Cue empties the bladder depends entirely on one unvalidated assumption.** With no sphincter co-activation, one or two sessions control the bladder. With co-activation of 0.5 or more, stimulation empties nothing, at any drive, timing or duration: volume climbs to about 900 mL, or about 390 mL overflows with the weaker sphincter. The pattern declared in advance as the reference is one of those that fails. The model has no dyssynergia and no sacral anatomy, so it cannot tell us which case is real. The clinical idea of voiding between bursts does not appear in this model.
2. **The safety logic held everywhere, but safe logic is not a working device.** In all 636 closed-loop runs, stimulation started only after an alert and a press, never during lockout, and always ended within the maximum duration, even with no working sensors. However, a stuck-high estimate gave 12 sessions per run, and with a dead pressure channel true pressure reached 64.2 cmH₂O. A low or noisy pressure ceiling stopped emptying altogether (P1 0.15 with the noisy channel). The volume stop fired in 0 of 1,236 sessions at normal sampling.
3. **The alert works only near the sensor's best case, in a threshold window that depends on the sensor's error.** With the 11% anchor, alerts at 350–450 mL pass. No threshold passes every fault (at best 10 of 14 scenarios with 15 seeds). Misalignment defeats the alert, and neither device settings (0 of 60 cells) nor a simple detector (fails at every value) rescue it. An alert alone changes nothing if nobody responds.

## What was completed

| Item | Result | Document |
|---|---|---|
| 1. Experiment 2b, 15 seeds | 54,000 runs. 69 of 180 combinations pass; 7 results flipped. Post-hoc band metric and lead-time caveat added. | `docs/STAGE4B_EXPERIMENT2_RERUN.md` |
| 2–4. Stage 5 | User model, stimulator, safety controller, pressure channel, closed-loop rig (`sci_test_rig.py`). A1 passes bit-for-bit. Stimulation map: 320 runs. | `docs/STAGE5_TRIGGER_STIMULATION_SAFETY.md` |
| 5. Stage 6 | Experiment 3: 312 runs, 38 of 104 settings work, all without co-activation. Experiment 4: 324 runs. Comparison CSV and PNGs. | `docs/STAGE6_EXPERIMENTS3_4.md` |
| 6. Stage 7 | Tests, validation document and README completed. | `VALIDATION_AND_LIMITATIONS.md`, `README.md` |
| 7. Extras | Experiment 5: no device setting changes the picture. Experiment 6: the misalignment detector fails. | `docs/EXPERIMENT5_6_RESULTS.md` |
| 8. Consistency check | 48 quoted numbers recomputed from the CSVs. 1 mismatch found and fixed (E50). | `results/doc_number_check.csv` |

**Tests:** 65 passed, including the slow full-day reproduction. The upstream clone is unchanged.

## What was skipped or not done, and why

- **ESM Table S1** of the upstream paper was still not read, so the species and primary source of each mechanical constant remain unconfirmed. This has been open since Stage 1.
- **Primary sources** for DFree, SENS-U, sacral anterior-root stimulation and McGuire 1981 were not read. Secondary sources only, and they are labelled that way.
- **Max-duration and threshold sweeps** ran only on the declared reference, which never empties, so they say little (E47). They were not rerun, because the grid was frozen.
- **Only 3 inflow seeds per cell** in Experiments 3 and 4, so rates move in steps of 33%.
- **Injury levels other than suprasacral** are not implemented, and neurogenic detrusor overactivity and dyssynergia are not modelled.

## Failures during the run

Full entries are in `VALIDATION_AND_LIMITATIONS.md` §5.
- E38: Experiment 4 crashed on the Windows path limit. Fixed and rerun. Experiment 3 was unaffected.
- E39: a rerun was started before the fix had actually been applied. Stopped and restarted.
- E40: a banned phrase was briefly in the README. Removed.
- E41: the saved parameter table left out the Stage 5–6 values. Fixed.
- E50: one quoted number was wrong. Corrected.

No test failure was left unresolved, and no work was built on top of a failing test.

## Decisions made while unattended
Each decision is ASSUMED unless stated otherwise. The alternatives that were rejected are listed with it.

| # | Decision | Rejected alternatives | Why |
|---|---|---|---|
| D1 | Experiment 2b uses inflow seeds 42 and 1–14 and keeps the 20 sensor seeds | Increasing the number of sensor seeds instead | The request asked for about 15 physiology seeds. Sensor seeds were already 20. |
| D2 | A button press with no pending alert is **ignored**. Accidental presses never start stimulation. | Allowing on-demand stimulation whenever the user presses | This is the most conservative option. It means a user cannot choose to empty before an alert (a usability cost, logged). |
| D3 | Only the moment the button goes down counts. Holding it, or a button already held when the alert arrives, does nothing. | Treating "button held" as a request to start or continue | Conservative: a stuck or held button can never start or prolong stimulation. |
| D4 | While WAITING_FOR_USER, the controller waits indefinitely. There are no reminder alerts. | Repeating the alert every N minutes | No source exists for a reminder interval. The cost (no reminder for a missed alert) is reported in Experiment 4. |
| D5 | After lockout the device's alert is reset, so a bladder that is still full alerts again | Keeping the old alert state, so a failed emptying would never re-alert | Without the reset, a failed session would leave the user with no further warning. |
| D6 | Volume stop uses only an estimate made after stimulation started | Using whatever estimate exists | An old, pre-session estimate says nothing about emptying. Using only fresh estimates means it can only fire if new readings arrive. |
| D7 | Stimulation replaces ω\*e and ω\*s only during burst-ON; ω\*i is never stimulated; between bursts the model's own values return | Adding the stimulus on top of the reflex drive; also driving ω\*i | The instruction was to replace the inputs. Sacral roots do not carry the hypogastric (sympathetic) outflow. |
| D8 | Stimulation-map grid, Experiment 3 grid and the reference pattern were declared before running. The reference has co-activation 0.5. | Choosing the reference after seeing the map | Prevents tuning. When the declared reference turned out to empty nothing, a second reference (no co-activation) was **added**, and it is labelled post-map. |
| D9 | Flow up to 120 s after a session counts as that session's emptying, not as leakage | 0 s or 60 s windows | It covers the tail of the post-session flow seen in the map. ASSUMED. |
| D10 | Emptying classes: complete if ≥ 95% of the pre-session volume is voided, partial if ≥ 10%, otherwise none | Absolute residual-volume cut-offs | No sourced definition was used. A fraction works at any starting volume. ASSUMED. |
| D11 | Pressure ceilings 40, 55 and 70 cmH₂O, reference 55 | A single value | The value is ASSUMED, so it is swept, as requested. |
| D13 | **(User decision after returning.)** No computer shutdown at the end of the work. | Running the authorised shutdown /s /t 300 | The user came back during the run and chose this. |
| D14 | **(User decision after returning.)** Experiment 4 keeps both references: the declared one, and the post-map one without co-activation (see D8). | The declared reference only | Confirmed by the user. |
| D12 | Experiment 3 uses the 400 mL alert threshold (plus 350 and 450 at the reference pattern) | Only 400 mL | 400 mL is the middle of the band where the anchor sensor passed in Experiments 2 and 2b. This choice was made after those results, so it is logged here. |

## Update 2026-11-08: rerun with 15 seeds

This report is kept as written. Experiments 3 and 4 were rerun with 15 seeds (42 and 1 to 14) on the same grid and criteria. Seeds 42, 1 and 2 reproduced these results exactly, and no verdict changed: 38 of 104 settings still work, and the invariants held in all 3,180 runs. Some descriptive figures moved: the highest Experiment 3 peak is 60.2 cmH₂O (58.5 here), the dead-pressure worst case is 67.2 cmH₂O (64.2 here), and several 3-seed Experiment 4 rates were poor estimates. See `docs/EXPERIMENT3_4_15SEED_RESULTS.md` and `VALIDATION_AND_LIMITATIONS.md` §5, E93–E99.
