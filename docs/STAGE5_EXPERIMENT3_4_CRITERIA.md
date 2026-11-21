# Stage 5 and Experiments 3–4: criteria (frozen)

**Written 2026-11-04, after one smoke-test run of the rig on the reference case, and before the stimulation map, Experiment 3 and Experiment 4 were run.**

That smoke test (reference case, seed 42) showed that the 55 cmH₂O ceiling can stop a session within 1–2 s. These criteria were written knowing that. They were not shaped to pass or fail it, and they are not changed afterwards. Any change is logged at the bottom.

All values are ASSUMED. Everything here is about the model. Nothing shows clinical safety.

## A. Stage 5 checks (must be exact or 100%)

| ID | Check | Required |
|---|---|---|
| A1 | With stimulation never started (user never presses), the closed-loop model reproduces the Stage 3 SCI baseline (24 h, seed 42, 1000 mL ceiling) **bit-for-bit** | Exact |
| A2 | Every stimulation session starts at a press edge while the controller is WAITING_FOR_USER | 100% |
| A3 | No session starts during LOCKOUT, and no press without an alert starts one | 100% |
| A4 | Every session ends within max_duration_s + one time step, even with no working sensor | 100% |
| A5 | Each cutoff can fire on its own: max duration (sensors dead), volume stop (estimate low), pressure ceiling (pressure high) | Each shown in a test |

## B. Stimulation map (Stage 5 characterisation: no pass or fail)

Open-loop stimulation from 450 mL, over the grid in `config.STIM_MAP_GRID`. For each run we report:
- volume before and after;
- **residual volume**, measured 120 s after the session ends;
- the voided fraction, classed as **complete** (≥ 0.95), **partial** (≥ 0.10) or **none**;
- peak true p_D;
- flow during burst-ON versus burst-OFF time, which shows whether flow happens only between bursts;
- the share of burst-ON time in which the urethra stays closed (sphincter "fighting" the detrusor).

The model has no dyssynergia and no sacral anatomy. The sphincter co-activation values are an ASSUMED, unvalidated set-up.

## C. Experiment 3 (full loop, prompt user, anchor sensor)

The grid is declared in `config.STIM_PATTERNS`, `CONTROLLER` and `EXPERIMENT3`:
- 8 stimulation patterns × 3 pressure ceilings × 2 ultrasound rates during stimulation (60 s and 5 s) × 2 sphincter strengths × 3 inflow seeds, at a 400 mL threshold;
- plus, at the reference pattern only: thresholds of 350 and 450 mL, and maximum durations of 30 and 120 s.

Safety invariants A2–A4 must hold in **100%** of runs.

Performance, for each setting (pattern × ceiling × ultrasound rate × sphincter strength):

| ID | Criterion | Required |
|---|---|---|
| P1 | Sessions that void ≥ 50% of the pre-session true volume | ≥ 80% of sessions |
| P2 | Runs with **no** leakage outside sessions after the first alert ("overflow despite alert") | ≥ 95% of runs |
| P3 | Sessions in which true p_D never exceeds the configured ceiling by more than 5 cmH₂O while stimulating | ≥ 95% of sessions |

"Full loop works" for a setting means P1, P2 and P3 all pass.

Always reported:
- which cutoff ended each session;
- residual volume;
- maximum true p_D during stimulation;
- the number of sessions per run;
- leaked and clipped volumes.

## D. Experiment 4 (faults)

The reference setting is: reference pattern, 55 cmH₂O ceiling, 60 s rate during stimulation, 400 mL threshold, prompt user, anchor sensor, "ok" pressure channel. Each fault is applied **one at a time**, for both sphincter strengths and 3 inflow seeds:
- each Experiment 2 sensor scenario;
- the stuck-high and stuck-low estimate faults;
- each user scenario (delayed, no press, accidental with no alert, press in lockout, held button);
- each pressure-channel scenario (noisy, reads 30% low, stuck low, dead).

Required under **every** fault:
- A2–A4 hold in 100% of runs;
- when the pressure channel is dead or stuck low and the estimate is stuck high, every session still ends at max duration.

Reported as results, not pass or fail:
- overflow despite an alert;
- which cutoff ended stimulation;
- residual volume;
- whether true p_D went above the ceiling, and by how much;
- the change in P1–P3 relative to the reference.

## Change log
- 2026-11-04, after the stimulation map and before Experiments 3–4: **one addition, no criterion changed.** The declared reference pattern (`e1.0_s0.5_5on5off`) produces **no emptying at all** in the stimulation map. A fault study on top of a reference that never empties would show little. Experiment 4 is therefore run for the declared reference (unchanged, still reported) **and** for a second reference, `e1.0_s0.0_5on5off` (the same pattern without sphincter co-activation). The second reference was chosen after seeing the map. It is labelled as such everywhere and is not presented as the planned reference.
