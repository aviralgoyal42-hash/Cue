# Experiment 3b results: POST-HOC, OPTIMISTIC

**Read this first.** The two patterns were chosen after we saw that they empty, and neither has any sphincter co-activation. That is the favourable case. The declared reference pattern (co-activation 0.5) still empties nothing, and that remains the planned result. Continuous stimulation was dropped from this grid (E57), so **nothing here describes it**. Everything below is a model prediction. No setting here is recommended, is a clinical parameter, or becomes a new default.

Criteria were frozen first in `docs/EXPERIMENT3B_CRITERIA.md`. Results are in `results/task2/`.

## Result

**75 of 108 settings meet P1, P2 and P3.** In all 1,620 runs (5,123 sessions) there were no crashes and the safety invariants A2, A3 and A4 held. Those invariants are facts about the simulation code, not about any device.

**Consistency check: passed.** All 36 shared runs and 104 shared sessions match Experiment 3 exactly, in every shared column (31 for runs, 22 for sessions). The first automatic check wrongly said they did not (E58).

**15 seeds against 3:** none of the 12 settings shared with Experiment 3 changed verdict.

## Answer to E47: which sweeps matter on a pattern that empties

| Factor | Settings that work | What it shows |
|---|---|---|
| Pressure ceiling | 40: **7**/36. 55: 34/36. 70: 34/36 | By far the strongest factor. |
| Max duration | 30 s: 23/36. 60 s: 26/36. 120 s: 26/36 | 30 s often stops early. Going from 60 to 120 s changes no verdict. |
| Alert threshold | 350: 27/36. 400: 28/36. 450: 20/36 | 350 and 400 are about equal. 450 is worse. |
| Sphincter strength | ×0.9: 40/54. ×1.0: 35/54 | Weak on its own. See the trap below. |
| Pattern | Drive 0.6: 39/54. Drive 1.0: 36/54 | The two patterns fail in different places. |

**Interactions the table hides**

| Pair | Settings that work (ceiling 40 / 55 / 70, 12 or 18 settings per cell) |
|---|---|
| Drive 0.6 | 7 / 16 / 16 of 18 |
| Drive 1.0 | **0** / 18 / 18 of 18 |
| Threshold 350 | 3 / 12 / 12 of 12 |
| Threshold 400 | 4 / 12 / 12 of 12 |
| Threshold 450 | **0** / 10 / 10 of 12 |

- At drive 1.0, a 40 ceiling fails every setting: P1 is 0.00 and the median session lasts 3 s. Stopped sessions then repeat, up to about 11 per run at threshold 350.
- All four failures at ceilings 55 and 70 are one combination: drive 0.6, 30 s, 450 mL (P1 0.66–0.69). 30 s is too short for that volume at that drive.
- Going from 60 to 120 s rescues no setting. The median residual is 3.9 mL at 60 s and 3.5 mL at 120 s, against 129.7 mL at 30 s.

**The 7 working settings at ceiling 40** (all at drive 0.6; `exp3b_ceiling40_working.csv`):

| Threshold | Sphincter | Max duration | P1 | P2 | P3 | Median residual |
|---|---|---|---|---|---|---|
| 350 mL | ×0.9 | 30 s | 0.976 | 1.00 | 0.976 | 86.1 mL |
| 350 mL | ×0.9 | 60 s | 0.971 | 1.00 | 1.000 | 4.7 mL |
| 350 mL | ×0.9 | 120 s | 0.971 | 1.00 | 1.000 | 4.1 mL |
| 400 mL | ×0.9 | 30 s | 1.000 | 1.00 | 1.000 | 146.6 mL |
| 400 mL | ×0.9 | 60 s | 1.000 | 1.00 | 0.967 | 5.8 mL |
| 400 mL | ×0.9 | 120 s | 1.000 | 1.00 | 0.967 | 6.9 mL |
| 400 mL | ×1.0 | 30 s | 1.000 | 1.00 | 1.000 | 154.3 mL |

At threshold 350, ceiling 40, drive 0.6, the three ×1.0 settings do not work: they fail P3 (0.81–0.83).

The count of 75 was rechecked after the user counted 74 on the heatmap: the summary column, P1–P3 recomputed from the raw tables, and the WORKS labels on the figure all give 75 (E70, `experiments/task2_recount.py`).

Every setting, pass or fail, is in `exp3b_settings_summary.csv`, including sessions, residual, cutoffs, peak pressure, overflow and volume. `exp3b_works_map.png` shows the grid, and `exp3b_pairs.csv` has every factor pair.

## Why "works" should not be read as "safe" or "good"

**1. A low ceiling can trap a full bladder.** At threshold 450 with ceiling 40, 202 sessions lasted under 1 s, starting from a median of 487 mL. Storage pressure was already over the ceiling, so stimulation stopped almost at once, and the bladder kept filling.
- ×0.9 sphincter: all 30 leaking runs in the experiment are here (6 settings). Up to 429.5 mL leaked, and maximum volume was 491 mL.
- ×1.0 sphincter: 29 of 90 runs passed 500 mL, up to 661 mL, with no leak. **P2 calls these runs clean.** No setting outside this combination went above 478 mL.

**2. No ceiling was truly tested by high pressure.** Pressure never went above 56.6 cmH₂O, or 53.7 in any working setting. These patterns do not drive the sphincter, so pressure levels off once the urethra opens. The ceilings were not holding pressure down:
- 70 never fired, in 1,109 sessions.
- 55 fired 376 times, and in **all 376** true pressure was below 55. They were triggered by the ASSUMED 2 cmH₂O noise on a single reading. At drive 1.0 with 60 or 120 s, those stops raised the median residual from about 2.5 mL to about 57–66 mL.

**3. A real pressure spike can slip past the ceiling.** 255 sessions passed the ceiling by more than 5 cmH₂O, all at ceiling 40. 202 are the trap above. The other 53 lasted longer, and 22 of them ended on max duration, meaning the ceiling never fired even though true pressure passed 45.

A traced example (seed 1, two sessions) shows why. When flow stops at the end of a burst, it drops from about 22 mL/s to 0 in one step, and pressure jumps from about 20 to 45–47 cmH₂O for 0.2–0.3 s. That falls between the 0.5 s samples. Peaks stayed at 43–51 cmH₂O at time steps of 0.1, 0.05 and 0.025 s, so this is how the model behaves when the outlet shuts, not just a time-step effect. Whether real bladders do this is unknown. **Only seed 1 was traced**, so the 53 are not all confirmed as this mechanism.

**4. The volume stop never fired: 0 of 5,123 sessions.** The device estimate is the median of 5 readings at one per minute. It needs 3 low readings, so about 3 minutes, which is longer than the longest session. At 120 s the median estimate at the stop was 349 mL, with about 2.5 mL truly left. So in the 120 s sessions at ceiling 55 and 70 at drive 0.6, every session ran to the full limit, about 60 s or more with the bladder near empty. In the traced example emptying finished at about 42–44 s. The model has no tissue-harm term, so it cannot say what that costs.

**5. "Works" is a low bar.** P1 only asks for 50% voided. Of the 75 working settings, 42 have a median residual of 10 mL or less, and 27 have more than 50 mL (up to 156 mL). Residuals of 2–3 mL are themselves unrealistically low (see the Stage 5 report).

**6. 15 runs cannot show 95%.** A setting with 15 of 15 clean runs has a one-sided 95% lower bound of about 82%. P2 passing means "no failure seen in 15 runs".

## Limits

- POST-HOC and OPTIMISTIC, as stated at the top.
- Continuous patterns were not tested (E57).
- Best-case sensor, prompt user, working pressure channel. Experiment 4 shows faults make things worse.
- The model has no detrusor overactivity, no dyssynergia and no tissue harm.
- Every ceiling, duration, threshold and drive is ASSUMED.
- `voided_in_sessions_ml` is overstated and should not be quoted (E67). P1 does not use it.

## Reproduce

```bash
python experiments/task2_experiment3b.py
```

```bash
python experiments/task2_analysis.py
```

```bash
python experiments/task2_overshoot_diagnostic.py
```

The first takes about 2.5 h. `python experiments/task2_experiment3b.py --recheck` repeats only the consistency check.
