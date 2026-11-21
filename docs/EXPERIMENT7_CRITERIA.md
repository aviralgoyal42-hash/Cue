# Experiment 7: session cap and post-session check (frozen)

**Status: FROZEN, 2026-11-04, approved by the user with the three changes in the change log, before any code for the rule was written and before any run.** Any later change is logged at the bottom. The original text stays as it is.

This is a simulation of a design idea. All values are ASSUMED, the sensor is a synthetic experimental proxy, and passing says nothing about clinical safety.

## The problem

- **Stuck-high fault (E45):** the estimate stays at 450 mL whatever happens, so the user is invited to stimulate 12 times per 12 h run, even on a bladder that is already empty.
- **Genuine failed emptying:** the declared reference (co-activation 0.5) empties nothing, and the device has no way to notice.
- **A rule that blocks silently would be worse than no rule.** A person who relies on the device must always be told what to do instead.

## The proposed rule

It adds to the safety controller. It uses **device estimates only**, never true volume or pressure, and the button is still the only thing that can start stimulation.

**1. Session cap.** At most `session_cap` sessions per 12 h run. **The caps are per 12 h run, not per day**, because each simulated run lasts 12 h and nothing here tests a longer period. The Nth session runs normally. Only when the device next wants to invite another session does it send the catheter alert instead.

**2. Post-session check.** After every session, however it ended:
- `E_pre` = the device estimate when stimulation started.
- `E_post` = the device estimate once **5 new valid readings** have arrived after stimulation stopped. The estimate is a median of 5 readings, so this is the first estimate containing no reading from before or during the session. At one reading a minute that is about 5 minutes, inside the 30 min lockout.
- `drop` = (`E_pre` − `E_post`) / `E_pre`.
- **Pass** if `drop` ≥ `min_drop_fraction`. Monitoring continues as normal.
- **Fail** if `drop` is smaller, **or** if 5 valid readings have not arrived within 600 s. A check that cannot be completed counts as a failure.

**3. What failure does.** The device enters a new state, `CATHETER_ONLY`, until the end of the run:
- It sends a distinct alert at once: **"device fault suspected, use catheter"**.
- It no longer invites stimulation, and no session can start.
- It repeats the alert every 30 min.
- A button press does not start anything. It is logged and the alert is sent again straight away.

Reaching the cap leads to the same state with its own wording: **"session limit reached, use catheter"**. The action is the same, but a cap is not a fault.

**In short:** the only ways to stop stimulation being offered also tell the user to catheterise.

**Off by default.** With the rule off, the code path must give results identical to earlier experiments.

### New values

| Value | Setting | Label |
|---|---|---|
| `session_cap` | 2, 3, 4 per 12 h (swept) | ASSUMED, given by the user |
| `min_drop_fraction` | 0.20, 0.40 (swept) | ASSUMED, given by the user |
| Readings before the check | 5 | ASSUMED, equal to the median window so the estimate is all post-session |
| Check deadline | 600 s | ASSUMED, reuses the sensor stale timeout |
| Alert repeat | 1800 s | ASSUMED, reuses the lockout length |

Inflow during the 5 minute wait is about 6 mL (roughly 400 mL over 5.5 h), or about 1.5% of `E_pre`. This slightly favours a failed check, the safe direction.

## Grid

All 6 rule settings (3 caps × 2 fractions), both sphincter strengths (×1.0, ×0.9), 15 seeds (42 and 1–14). Fixed: anchor sensor (11.17%), prompt user, "ok" pressure channel, 60 s max duration, 55 cmH₂O ceiling, 100 mL volume stop, 30 min lockout, 12 h run.

| Group | Patterns | Threshold | Rule off ("before") | Rule on | Runs |
|---|---|---|---|---|---|
| **T1 Stuck-high fault** (450 mL from 5 h) | `e1.0_s0.5_5on5off`, `e1.0_s0.0_5on5off` | 400 mL | new, 15 seeds: 60 runs | 360 | 420 |
| **T2 Genuine failed emptying** | `e1.0_s0.5_5on5off` (declared reference), no sensor fault | 400 mL | new, 15 seeds: 30 runs | 180 | 210 |
| **T3 No fault, patterns that empty** | `e0.6_s0.0_5on5off`, `e1.0_s0.0_5on5off` | 350, 400, 450 mL | reused from Experiment 3b | 1,080 | 1,080 |

**Total: 1,710 runs, about 2.7 h** (68 s per run on 12 cores, measured in Experiment 3b).

T3 uses the patterns as POST-HOC and OPTIMISTIC, as in Experiment 3b. T1's second pattern is also post-hoc.

## How sessions are judged (evaluation only)

True volume is used here and nowhere in the rule. These are the existing P1 and emptying-class boundaries.

| True voided in the session | Meaning | What the rule should do |
|---|---|---|
| ≥ 50% | Emptied | Pass. A fault alert here is a **false alarm** |
| < 10% | Failed | Fail, and raise the fault alert |
| 10–50% | Partial | Either is acceptable. Reported, not judged |

## Criteria

With 15 runs per cell, "≥ 95% of runs" means **every** run.

**Must hold in 100% of runs, in every group and setting:**

| ID | Requirement |
|---|---|
| I1 | The existing invariants A2, A3 and A4 hold |
| I2 | No session starts, and no stimulation invitation is sent, after `CATHETER_ONLY` begins |
| I3 | **Never silent:** every entry to `CATHETER_ONLY`, and every press or device alert during it, has a catheter alert at that same moment. Alerts repeat on schedule until the run ends |
| I4 | **Estimates only:** a code test finds no ground-truth name in the rule's code, and its only volume input is the device estimate |

**T1, stuck-high, per setting, pattern and strength:**

| ID | Requirement | Before |
|---|---|---|
| T1a | Fault alert in ≥ 95% of runs | No such alert exists |
| T1b | Fault alert within 600 s of the end of the first session started after 5 h, in ≥ 95% of runs | — |
| T1c | At most 1 session started after 5 h, in ≥ 95% of runs | About 12 (3 seeds; 15-seed value to be measured) |
| T1d | Total sessions never above the cap, in all runs | 12 |

**T2, genuine failed emptying, per setting and strength:**

| ID | Requirement |
|---|---|
| T2a | Fault alert within 600 s of the end of the first failed session (< 10% voided), in ≥ 95% of runs |
| T2b | Fault alert before the first leak, in ≥ 95% of runs |
| T2c | At most 1 session after the first failed session, in ≥ 95% of runs |

**T3, no fault, per setting, pattern, threshold and strength (must not damage normal function):**

| ID | Requirement |
|---|---|
| T3a | False alarms (fault alert after a session with ≥ 50% voided) in at most 5% of runs |
| T3b | Session-limit alerts in at most 5% of runs |
| T3c | P1, P2 and P3 keep the verdict they had in Experiment 3b |
| T3d | In every run with no catheter alert, results match Experiment 3b exactly. The rule must do nothing until it acts |

**Verdict.** A rule setting **passes** only if I1–I4 and all T1, T2 and T3 items hold in all of its cells. If none passes, that is reported as the result. Values will not be changed to make one pass.

## Consistency checks (must pass)

- Rule off, seeds 42, 1 and 2: the stuck-high runs match Experiment 4, and the declared reference runs match Experiment 3, exactly.
- Rule off: the existing tests still pass, and the upstream `third_party` folder stays unchanged.
- Unit tests for the rule are written and passing **before** the sweep starts.

## Expected from data already seen

Stated now so it cannot be claimed as a discovery later.

- **Caps 2 and 3 are likely to fail T3b.** Without a fault, `e1.0_s0.0_5on5off` at 350 mL had a median of 3 and a maximum of 4 sessions per run in Experiment 3b. At 400 mL every run had 2 sessions.
- **That means a cap of 2 or 3 may fail for a reason that has nothing to do with faults.** Those extra sessions come from ceiling-55 noise stops (E62). The cap will not be raised and the criterion will not be relaxed in response.
- A 0.40 fraction may raise false alarms or grey-zone alerts where noise stops cut a session short.

## Before and after

Reported for each group, rule off against each rule setting: sessions per run, sessions after the fault, time to the catheter alert, true volume at the alert, leaked volume, maximum volume, peak true pressure, and sessions on a bladder below 100 mL. Old result folders are not touched. New results go to `results/task3/`.

## Declared limitations

- **Catheterisation is not modelled.** The simulated user does not act on the catheter alert, so the bladder keeps filling afterwards. This experiment can show that the alert arrives in time, **not** that the person ends up safe. Leak and volume after the alert describe someone who ignores it. P2 is therefore not applied to T1 and T2.
- **The first stimulation still happens.** The rule can only act after a session, so one session on a nearly empty bladder remains possible under stuck-high.
- **Faults it cannot catch.** A stuck-low estimate gives no alert and no session, so the check never runs (E46 remains). A fault that makes the estimate fall while the bladder does not, such as misalignment, could pass the check. Neither is tested here.
- **Not tested:** dead pressure channel with stuck-high (the 64.2 cmH₂O case), the ceiling-40 trap (E63), delayed users, and continuous patterns.
- **A latched alert ends the device's use for the run.** There is no reset in the simulation, and how a real device would be reset is an open design question.
- **A long sensor dropout can latch the device.** If 5 valid readings do not arrive within 600 s of a session, the check fails by timeout and the device stays in `CATHETER_ONLY` for the rest of the run, even if the session worked and the sensor recovers. A real device would need a reset path.
- 15 clean runs give a lower bound of about 82%, not 95% (E68).
- The rule was designed after seeing the stuck-high result, so this experiment is not a blind test of it.

## Change log
(empty)

- 2026-11-04, on approval and before freezing, three changes from the user: (1) T3 now also covers threshold 450 mL, so the grid grew from 1,350 to 1,710 runs (about 2.1 h to 2.7 h) and the declared limitation about leaving 450 out was removed; (2) a limitation was added on long sensor dropouts latching the device; (3) the text now states that session caps are per 12 h run, not per day.
