# Project Cue: Stage 5, user trigger, hypothetical stimulation and safety controller

Date: 2026-11-04 (overnight run). Criteria are frozen in `docs/STAGE5_EXPERIMENT3_4_CRITERIA.md`.

Everything here is a **model prediction**. The stimulator is hypothetical, and its inputs are normalised model drives, **not clinical stimulation parameters**. Nothing here shows clinical safety.

## What was built

| File | What it is |
|---|---|
| `sci_test_rig.py` | **The closed-loop rig.** `ClosedLoopLUT` subclasses the Stage 3 SCI model. The hook is upstream's per-step `is_voiding()` call: there, the rig runs the sensors, device, user, controller and stimulator. During a burst the stimulator's values **replace** ω\*e and ω\*s inside the original loop. The upstream void switch is never used: `is_voiding` still returns False, and the rig refuses to run with SCI off. |
| `devices/user_model.py` | The simulated user responds to the watch alert after a uniform random delay. Scenarios: prompt (0.5–5 min), delayed (30–90 min), no press, accidental presses with no alert, a second press during lockout, and a button held for 15 min. All ASSUMED. |
| `devices/stimulator.py` | The hypothetical burst stimulator: detrusor drive, sphincter co-activation drive, on/off timing. |
| `devices/safety_controller.py` | The state machine: MONITORING → FULL_DETECTED → ALERT_SENT → WAITING_FOR_USER → STIMULATING → CUTOFF → LOCKOUT → MONITORING. It starts stimulation only on a button press in WAITING_FOR_USER. It ignores presses with no alert pending, during stimulation and during lockout. Holding the button does nothing extra. It re-arms the device after lockout. |
| `sensors/pressure_channel.py` | The synthetic implant pressure channel, used only by the pressure ceiling. It has noise, gain error, delay, missing readings, a dead fault and a stuck fault. |
| `evaluation/closed_loop_metrics.py` | Session table, run summary, and the safety invariants **recomputed from the raw logs**. |

### The three independent cutoffs
1. **Maximum duration.** This is the primary cutoff and needs no sensor. Default 60 s (ASSUMED); 30, 60 and 120 s are swept in Experiment 3.
2. **Volume stop.** It uses only the **device estimate**, and only one made from a reading taken after stimulation started. Default 100 mL (ASSUMED).
3. **Pressure ceiling.** It uses the synthetic implant channel. Values 40, 55 and 70 cmH₂O are swept (ASSUMED).
   - 55 cmH₂O is close to this model's healthy-void peak of 54.7 cmH₂O.
   - 40 cmH₂O echoes the detrusor leak point pressure that McGuire et al. 1981 (*J Urol* 126:205–209) linked to upper-tract risk in children with myelodysplasia. I checked this through secondary sources only. It is a diagnostic measure in a different population, **not** a stimulation limit.

## Checks (Section A of the criteria)

| ID | Result |
|---|---|
| A1: stimulation off reproduces Stage 3 exactly | **PASS.** 24 h, seed 42, 1000 mL ceiling, user never presses: bit-identical to a fresh Stage 3 model. The maximum difference from the saved Stage 3 trace is 1.1 × 10⁻¹³ mL (float rounding in the CSV). One alert occurred and stimulation never ran (`results/stage5/stage5_A1_check.json`). |
| A2–A5 | Unit tests (`tests/test_stage5_closed_loop.py`):<br>• a press with no alert is ignored;<br>• alert, then press, starts stimulation;<br>• max duration stops it with **no sensor data at all**;<br>• a held button neither restarts nor extends it;<br>• volume stop ignores an estimate made before the session;<br>• the pressure ceiling stops it, and a missing channel cannot;<br>• presses in lockout are ignored and the device re-arms afterwards;<br>• a button held from before the alert does not start stimulation.<br>A short closed-loop run also passes the invariants recomputed from the logs. In Experiments 3 and 4, A2–A4 are checked on every run (see `docs/STAGE6_EXPERIMENTS3_4.md`). |

## Stimulation map (Section B)

Open-loop, from 450 mL:
- 4 detrusor drives × 4 sphincter co-activation levels × 5 timings × 2 session lengths × 2 sphincter strengths = 320 runs.
- Files: `results/stage5/stimulation_map.csv`, `stimulation_map_voided_fraction.png` and `stimulation_reference_trace.png`.

| Session | Complete (≥ 95%) | Partial | None |
|---|---|---|---|
| 60 s (each sphincter strength) | 15 | 6 | 59 |
| 120 s (each sphincter strength) | 21 | 1 | 58 |

### What the model does
1. **Sphincter co-activation decides everything.** Emptying is near-complete only with **no** sphincter co-activation (sphincter drive 0).
   - At co-activation 0.25 there is almost no emptying. The exceptions are detrusor drive 1.0 (0.13 voided after 60 s of continuous drive, complete after 120 s) and a 15% partial void with 10 s on / 5 s off for 120 s.
   - At co-activation 0.5 or 1.0 there is **no emptying at any drive, timing or duration**, at either sphincter strength. The sphincter wins.
   - The **declared reference pattern** (detrusor 1.0, co-activation 0.5, 5 s on / 5 s off) therefore empties **nothing** in this model.
2. **No post-stimulus voiding.** The clinical rationale for burst stimulation is that the sphincter relaxes faster than the detrusor between bursts. That pattern does not emerge here.
   - Flow happens during burst-ON time (flow in 90–100% of ON time). There is almost none between bursts (0–14% of OFF time).
   - Between bursts the model's own storage reflex puts the sphincter drive straight back to about 0.5 within τ_S = 0.2 s. With co-activation, the sphincter is closed during the bursts as well.
3. **Residual volume is unrealistically small** whenever emptying happens: 0.0–1.8 mL. This is the same built-in tendency to empty to zero that was found in Stage 1. It must not be read as proof of physiological emptying.
   - *Update 2026-11-07 (figure audit, E35 correction and E89):* the 0.0–1.8 mL range is too narrow. Complete sessions in the map leave 0.0–11.3 mL (median 0.2 mL). Only `e0.6_s0.0_2on2off`, 60 s, lies outside 1.8 mL (11.3 mL at ×1.0, 2.8 mL at ×0.9). Partial sessions leave 46–393 mL. See `docs/FIGURE_AUDIT.md`.
4. **Peak detrusor pressure** during stimulation from 450 mL was at most 53.8 cmH₂O in all 60 s sessions and in every run without co-activation. That is below the healthy-void peak. The highest in the whole map was **57.9 cmH₂O**, with detrusor 1.0 and co-activation 0.25, continuous for 120 s, which is above it.
5. Weaker sphincter (×0.9): almost identical, because the stimulator overrides the sphincter drive during bursts.

### What this means
- In this model the outcome of "stimulation" is set by an **unvalidated choice**: whether, and how strongly, stimulation also drives the sphincter.
- The model has **no dyssynergia and no sacral anatomy**. The co-activation levels are an ASSUMED set-up, not a representation of nerve-root recruitment.
- The model cannot tell us whether a real sacral stimulator would empty a bladder after SCI.

## Tests
`tests/test_stage5_closed_loop.py` has 14 tests. The full suite is 54 passed, plus 1 slow test that is skipped by default.
