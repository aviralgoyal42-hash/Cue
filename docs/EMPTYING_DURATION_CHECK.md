# Emptying duration and sphincter timing: definitions (frozen before measuring)

Written 2026-11-07, before any duration was computed. Requested by the user. **Read-only analysis of existing files: no new simulation, no parameter changes.** All results are model predictions. The patterns without co-activation (`s0.0`) are **POST-HOC and OPTIMISTIC** (chosen after Stage 5 showed that they empty). This whole check is itself post-hoc: it was asked for after Experiments 3 and 4 had been run.

## Part A: emptying duration per session

**Data.** The only saved traces with stimulation in them are the 48 files `results/stage6/traces/exp3_*.csv`:
- one run per Experiment 3 `main` setting (8 patterns × 3 pressure ceilings × 2 ultrasound rates during stimulation), seed 42, sphincter ×1.0, alert threshold 400 mL, maximum duration 60 s;
- sampled at 1 Hz (every 10th model step), so every duration below is accurate to about ±1 s.

Not used:
- `exp4_*.csv` (2 files): byte-identical to `exp3_e1.0_s*_5on5off_55_60.csv`, so they would count the same sessions twice;
- `results/task4/traces`: still being written by the running 15-seed sweep;
- seeds 1 and 2, sphincter ×0.9, the threshold and max-duration groups, Experiment 3b, Experiment 7: no traces were saved for them. Their session tables hold the **stimulation** time (`duration_s`), not the flow time, so they cannot answer this question.

**Session.** A block of consecutive samples with `stim_active` true. Start = first such sample. Stimulation stop = last such sample + 1 s.

**Flowing second.** A second in which true volume `V_B_ml` falls by more than 0.1 mL. Inflow can only raise the volume (at most about 0.07 mL/s in the upstream kidney: up to 0.023 mL/s from the daily rhythm plus up to 0.05 mL/s noise), so any fall is outflow. Flow is **not** judged from `Q_ml_s`, because the model reports flow of about 8.9 mL/s when the bladder is already empty (E67). A `Q_ml_s > 0.1` version is reported beside it, only to show the size of that effect.

**Emptying episode.** Starts at session start. It takes in every flowing second from there on, and ends at the last flowing second that is followed by 30 s with no flow (30 s is longer than any OFF phase in the grid, which is at most 10 s), or at the next session start, or at the end of the trace, whichever comes first.

**Emptying duration** = end of the last flowing second in the episode − session start (s).

**Reported per setting** (only for settings with at least one session that voided 10% or more, using the existing `emptying` class of partial or complete): number of sessions, median and maximum emptying duration, flow seconds after stimulation stopped, and volume voided.

**Flag.** The user asked for runs where flow lasts "over 2–3 min". Both lines are reported: over 120 s and over 180 s. No pass or fail is attached. This is descriptive.

## Part B: does the model's sphincter respond faster than its bladder?

This is read-only. Post-stimulus voiding needs two things after a burst ends: (1) the sphincter relaxes faster than the detrusor, and (2) the sphincter actually relaxes, meaning its drive between bursts is lower than during the burst. The check:
1. Read from the upstream code the activation time constants (`tau_D`, `tau_S`) and the equations they enter (`f2`, `f3`). Read from `devices/stimulator.py` and `sci_test_rig.py` what drive the sphincter returns to when a burst is OFF.
2. Evaluate the model's own storage-phase drive formulas (no time stepping) to get the sphincter's OFF-phase target, and the detrusor's effective time constant, across urethral opening and bladder fullness.
3. Compare with flow that is already measured in OFF phases and after sessions: the Stage 5 map (`flow_fraction_burst_off`, `flow_after_session_ml`) and the 48 traces above.

## Change log
- 2026-11-07, after the first results: a **sensitivity column** was added, `within_1ml_of_lowest_s`. It is the time until true volume first comes within 1 mL of its lowest value before the next session. The reason: under the frozen rule, 3 sessions run on because later bursts push out about 0.12 mL of new urine from a bladder that is already empty (E85). The frozen definition is unchanged, and it is the one reported first. A second change was also added after seeing results: a count of where flow between bursts falls within the OFF phase.

---

# Results (2026-11-07)

Script: `experiments/emptying_duration_check.py`. Outputs: `results/emptying_check/` (`sessions.csv`, `settings_that_empty.csv`, `key_numbers.json`, and three Part B tables). The analysis was cross-checked with a separate script that reads the raw traces directly and uses a different definition. All of this is **model prediction**, for **one simulated person (seed 42), at the default sphincter strength (×1.0)**.

## Part A: how long each emptying episode lasts

- The 48 traces hold 313 sessions. All 313 match a row of `results/stage6/exp3_sessions.csv`.
- The table has 20 more sessions for these runs. None of them shows up in the traces, because every one lasted 0.5 s or less and fell between two 1 Hz samples. All 20 are co-activation sessions that voided nothing, so they do not change any result below.
- **67 sessions emptied** (voided 10% or more). Every one of them is in a pattern without co-activation, so **every duration below is POST-HOC and OPTIMISTIC**. They come from **24 settings**. None of the 24 co-activation settings emptied in any session.
- **Emptying duration across all 67: median 17 s, maximum 51 s.**
- **No session flowed for more than 120 s, and none for more than 180 s.** Nothing is flagged.
  - Flow never lasted more than 1 s after stimulation stopped, which is within the 1 Hz resolution.
  - So every episode is bounded by the 60 s maximum stimulation time.
- Sensitivity: if the last trickle of about 0.1 mL is ignored, the median stays at 17 s and the maximum falls to 44 s (E85).
- Judged from `Q_ml_s` instead of from volume, the maximum would be 61 s. That figure is not real flow: the model reports outflow from an empty bladder (E67).

Emptying duration by setting, in seconds. "n" is the number of sessions that emptied, out of one run per setting.

| Pattern (all POST-HOC, OPTIMISTIC) | Ceiling (cmH₂O) | 60 s sampling: n, median, max | 5 s sampling: n, median, max |
|---|---|---|---|
| e0.6_s0.0_5on5off | 40 | 2, 35.5, 36 | 2, 35.5, 36 |
| e0.6_s0.0_5on5off | 55 | 2, 47.5, 51 | 2, 43, 43 |
| e0.6_s0.0_5on5off | 70 | 2, 47.5, 51 | 2, 43, 43 |
| e0.6_s0.0_continuous | 40 | 2, 21, 22 | 2, 20.5, 22 |
| e0.6_s0.0_continuous | 55 | 2, 22, 22 | 2, 22, 22 |
| e0.6_s0.0_continuous | 70 | 2, 22, 22 | 2, 22, 22 |
| e1.0_s0.0_5on5off | 40 | 6, 4, 12 | 7, 5, 5 |
| e1.0_s0.0_5on5off | 55 | 2, 28.5, 32 | 2, 24.5, 25 |
| e1.0_s0.0_5on5off | 70 | 2, 41.5, 51 | 2, 32, 32 |
| e1.0_s0.0_continuous | 40 | 7, 4, 7 | 7, 5, 5 |
| e1.0_s0.0_continuous | 55 | 2, 14.5, 15 | 2, 15.5, 16 |
| e1.0_s0.0_continuous | 70 | 2, 17, 17 | 2, 17, 17 |

At ceiling 40 the episodes last only 4–12 s, and each voids only about 67–77 mL (median per setting). The pressure ceiling stops the session early, as reported in E44 and E63. These are partial voids, not quick complete ones.

**What this cannot show**
- The data cover one seed at ×1.0 only.
- No traces were saved for:
  - seeds 1 and 2;
  - sphincter ×0.9 (where the bladder dribbles continuously at baseline, Stage 3);
  - the threshold and max-duration groups;
  - Experiment 3b (sessions of up to 120 s);
  - Experiment 7.
- For the 120 s sessions in Experiment 3b, the 120 s flag could in principle be reached. It cannot be measured without traces.

## Part B: does the model's sphincter respond faster than its bladder?

**Yes, but that is not what decides post-stimulus voiding in this model.**

1. **Speed.** These are upstream values. Table S1 cites Bastiaanssen 1996, and the species is unconfirmed (E51).
   - Sphincter activation follows `f3`, with τ_S = **0.2 s**.
   - Detrusor activation follows `f2`, with τ_D = **1.0 s**. The sympathetic term also speeds its decay, so the effective detrusor time constant is τ_D / (1 + ω_i): **0.59–0.91 s** between 0 and 500 mL.
   - So the sphincter's activation changes about 3–5 times faster than the detrusor's.
   - Urethral opening has no lag of its own: it is solved fresh at every time step.

2. **Where the sphincter goes between bursts.** When a burst is OFF, the stimulator hands the sphincter back to the model's storage reflex, the upstream `update_somatic_input`. That reflex depends only on how open the urethra is:

   | Urethral opening (share of maximum) | 0–60% | 70% | 80% | 90% | 100% |
   |---|---|---|---|---|---|
   | Sphincter drive at ×1.0 | 0.500 | 0.494 | 0.432 | 0.197 | 0 |
   | Sphincter drive at ×0.9 | 0.450 | 0.445 | 0.389 | 0.177 | 0 |

   Post-stimulus voiding needs the sphincter to drop below its in-burst drive after the burst, while the detrusor is still active. In this model:
   - **Without co-activation (s0.0):** the sphincter is held at 0 during the burst, below its own storage drive of 0.5 (E87). When the burst ends, the fast sphincter goes **back up** to about 0.5 within about 0.2 s, while detrusor pressure is still falling. The faster sphincter **ends** flow, which is the opposite of post-stimulus voiding.
     - In the 33 burst sessions that emptied, there were 446 seconds of flow during bursts and 71 between bursts.
     - 68 of those 71 were in the first second after a burst ended, and the other 3 were in the second.
     - Example from the trace: 9.7 mL in the second after a burst ended, then only inflow (0.03 mL/s) until the next burst.
   - **Co-activation 0.5:** the in-burst drive equals the storage drive while the urethra is closed, so nothing changes at the end of a burst.
   - **Co-activation 1.0:** the sphincter does relax quickly at the end of a burst, but only down to 0.5. That level already holds against full detrusor drive, because `e1.0_s0.5` never empties.
   - The Stage 5 map agrees. Across 64 burst runs at co-activation 0.5 and 64 at 1.0, between-burst flow and flow after the session are both exactly 0.

3. **Conclusion (model prediction).** The time constants do favour the sphincter. But with drives of at most 1, between bursts the model's sphincter returns to its storage level of about 0.5 unless the urethra is already more than about 70% open. So post-stimulus voiding cannot appear.
   - This extends E34. What blocks it is the sphincter's level between bursts, not its speed.
   - The model has no muscle fatigue, no fast-versus-slow fibre types and no urethral lag, which are the features usually used to explain post-stimulus voiding. So it cannot test that rationale.
