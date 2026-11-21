# Task 5 results: how much sphincter suppression during bursts the model needs before emptying works

Written 2026-11-08, after the sweep finished. Plan: `docs/TASK5_PLAN.md`, frozen before running and not changed since.

**Results are model predictions, not evidence for a device.**

- **Model only.** The levels are normalised model drives (0–1). They are **not** clinical stimulation parameters, and nothing here claims that any real device could reach them.
- **POST-HOC and OPTIMISTIC.** The four settings come from Experiment 3b working settings.
- **Levels are ASSUMED.** All six levels (0, 0.1, 0.2, 0.3, 0.4, 0.5) were fixed before running and never tuned.

## 1. Answer

**In all four settings, the highest level at which emptying still works is 0.1.**
- At 0.2 and above, no setting works.
- The working levels form one block from 0 upward everywhere (0 and 0.1), so there are no gaps.
- The step between 0.1 and 0.2 is the finest the frozen levels allow. The true boundary lies somewhere in that step, and it is **not** estimated: nothing is interpolated.

| Setting | Levels that work | Highest that works |
|---|---|---|
| Detrusor 0.6, sphincter ×1.0 | 0, 0.1 | **0.1** |
| Detrusor 0.6, sphincter ×0.9 | 0, 0.1 | **0.1** |
| Detrusor 1.0, sphincter ×1.0 | 0, 0.1 | **0.1** |
| Detrusor 1.0, sphincter ×0.9 | 0, 0.1 | **0.1** |

**What the levels mean:** the level **replaces** the sphincter's input drive while a burst is ON. Between bursts, the drive returns to the reflex level: 0.5 at ×1.0 and 0.45 at ×0.9. So level 0.5 means no suppression at ×1.0, and 0.1 means the drive is cut to a fifth of its resting value during bursts (E87).

## 2. How it ran

- **Runs:** 360 (4 settings × 6 levels × 15 seeds), with 2,612 sessions, 0 errors, and safety invariants A2–A4 holding in every run.
- **Before the sweep (Step 2):** the 24-run check passed. Levels 0 and 0.5 matched Task 4 exactly, and no level-0.5 session voided 10% or more.
- **After the sweep:** all 15 seeds at levels 0 and 0.5 match Task 4 exactly.
  - 120 of 120 runs (36 columns) and 761 of 761 sessions (26 columns) are identical.
  - 0 of 641 level-0.5 sessions voided 10% or more.
  - Source: `reproduction_15_seeds.json`.
- **One restart (E100):**
  - The first attempt stalled at run 150 of 360, when the laptop entered Modern Standby at 02:59.
  - With the user's OK, it was restarted at 09:06 from the 150 saved runs, and it finished at 09:39.
  - Every run is set by its seed, and the reproduction check above passed after the restart.
  - The first attempt's log is kept as `run_log_attempt1_stalled.txt`.
- **Scoring:** the unchanged Experiment 3 rule (`summarise_exp3`) is used. I cross-checked it independently from the raw CSVs: P1, session counts, residual medians and overflow counts all agree.

## 3. Results by level

**How to read the table**
- **P1:** sessions voiding at least 50%.
- **P2:** runs with no leak after the alert.
- **P3:** sessions in which true p_D stays within ceiling + 5 cmH₂O.
- **Leftover:** true volume 120 s after each session ends, as median [min–max] mL.
- **Emptying time:** the frozen 1 Hz definition, as median / max in s, over sessions that voided at least 10%.
- **Within 1 mL:** time to come within 1 mL of the lowest volume, as median / max in s.

### Detrusor 0.6, sphincter ×1.0

| Level | Works | P1 | P2 | P3 | Sessions per run | Leftover median [range] mL | Emptied sessions | Emptying time s | Within 1 mL s | Peak true p_D | Max volume mL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | yes | 1.000 | 1.0 | 1.0 | 2.00 | 2.2 [0.0–6.8] | 30 of 30 | 50 / 51 | 43 / 51 | 49.6 | 426.4 |
| 0.1 | yes | 0.968 | 1.0 | 1.0 | 2.07 | 91.0 [0.7–385.2] | 30 of 31 | 55 / 56 | 55 / 56 | 49.0 | 424.6 |
| 0.2 | no | 0.000 | 1.0 | 1.0 | 10.60 | 572.6 [322.7–830.4] | 0 of 159 | – | – | 55.8 | 851.7 |
| 0.3 | no | 0.000 | 1.0 | 1.0 | 10.67 | 633.5 [343.4–920.9] | 0 of 160 | – | – | 54.6 | 938.7 |
| 0.4 | no | 0.000 | 1.0 | 1.0 | 10.67 | 634.2 [343.4–920.9] | 0 of 160 | – | – | 54.5 | 940.4 |
| 0.5 | no | 0.000 | 1.0 | 1.0 | 10.67 | 634.2 [343.4–920.9] | 0 of 160 | – | – | 54.5 | 940.4 |

### Detrusor 0.6, sphincter ×0.9

| Level | Works | P1 | P2 | P3 | Sessions per run | Leftover median [range] mL | Emptied sessions | Emptying time s | Within 1 mL s | Peak true p_D | Max volume mL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | yes | 1.000 | 1.0 | 1.0 | 2.00 | 2.2 [0.0–6.8] | 30 of 30 | 50 / 51 | 43 / 51 | 46.3 | 426.4 |
| 0.1 | yes | 1.000 | 1.0 | 1.0 | 2.00 | 82.1 [0.7–170.1] | 30 of 30 | 55 / 56 | 55 / 56 | 47.0 | 424.6 |
| 0.2 | no | 0.000 | 0.0 | 1.0 | 10.67 | 469.3 [322.7–489.9] | 0 of 160 | – | – | 53.1 | 491.6 |
| 0.3 | no | 0.000 | 0.0 | 1.0 | 10.67 | 486.3 [343.4–490.3] | 0 of 160 | – | – | 54.4 | 491.6 |
| 0.4 | no | 0.000 | 0.0 | 1.0 | 10.67 | 486.4 [343.4–490.4] | 0 of 160 | – | – | 54.5 | 491.6 |
| 0.5 | no | 0.000 | 0.0 | 1.0 | 10.67 | 486.4 [343.4–490.4] | 0 of 160 | – | – | 54.5 | 491.6 |

### Detrusor 1.0, sphincter ×1.0

| Level | Works | P1 | P2 | P3 | Sessions per run | Leftover median [range] mL | Emptied sessions | Emptying time s | Within 1 mL s | Peak true p_D | Max volume mL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | yes | 1.000 | 1.0 | 1.0 | 2.00 | 62.3 [0.5–199.5] | 30 of 30 | 25 / 50 | 25 / 34 | 53.7 | 424.6 |
| 0.1 | yes | 0.903 | 1.0 | 1.0 | 2.07 | 116.2 [1.1–209.1] | 31 of 31 | 25 / 51 | 25 / 41 | 54.6 | 424.6 |
| 0.2 | no | 0.000 | 1.0 | 1.0 | 4.27 | 260.7 [201.8–330.5] | 64 of 64 | 35 / 56 | 35 / 56 | 56.6 | 439.4 |
| 0.3 | no | 0.000 | 1.0 | 1.0 | 10.67 | 607.0 [341.6–840.3] | 0 of 160 | – | – | 56.6 | 858.0 |
| 0.4 | no | 0.000 | 1.0 | 1.0 | 10.67 | 629.8 [343.3–907.4] | 0 of 160 | – | – | 56.5 | 936.7 |
| 0.5 | no | 0.000 | 1.0 | 1.0 | 10.67 | 632.1 [343.4–911.0] | 0 of 160 | – | – | 56.5 | 940.4 |

### Detrusor 1.0, sphincter ×0.9

| Level | Works | P1 | P2 | P3 | Sessions per run | Leftover median [range] mL | Emptied sessions | Emptying time s | Within 1 mL s | Peak true p_D | Max volume mL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | yes | 1.000 | 1.0 | 1.0 | 2.00 | 67.7 [1.5–188.4] | 30 of 30 | 25 / 50 | 25 / 34 | 53.7 | 424.6 |
| 0.1 | yes | 0.903 | 1.0 | 1.0 | 2.07 | 120.9 [1.1–204.3] | 31 of 31 | 25 / 51 | 25 / 41 | 54.6 | 424.6 |
| 0.2 | no | 0.032 | 1.0 | 1.0 | 4.20 | 257.9 [188.0–304.6] | 63 of 63 | 42 / 56 | 42 / 56 | 56.4 | 425.8 |
| 0.3 | no | 0.000 | 0.0 | 1.0 | 10.73 | 486.1 [341.6–490.4] | 0 of 161 | – | – | 55.4 | 491.6 |
| 0.4 | no | 0.000 | 0.0 | 1.0 | 10.73 | 486.3 [343.3–490.6] | 0 of 161 | – | – | 56.0 | 491.6 |
| 0.5 | no | 0.000 | 0.0 | 1.0 | 10.73 | 486.3 [343.4–490.8] | 0 of 161 | – | – | 56.2 | 491.6 |

Full table: `task5_by_level.csv`. Key numbers: `task5_key_numbers.json`.

## 4. How leftover volume and emptying time change with level

**Leftover volume rises sharply even at 0.1, the level that still works.**
- At detrusor 0.6, the median goes from 2.2 mL at level 0 to 82–91 mL at 0.1.
- At detrusor 1.0, it goes from 62–68 mL to 116–121 mL.
- At 0.1, one detrusor 0.6 ×1.0 session voided only 5%, leaving 385 mL (seed 4).
- P1 at detrusor 1.0 passes with little margin: 0.903 against the 0.80 line. Three sessions per scaling voided 46–50%.
- These are model leftovers, not post-void residuals. The model empties almost to zero, which is unrealistic (E35 and its correction).

**Above 0.1, emptying stops.**
- At detrusor 0.6, from 0.2 up, no session voids even 10%.
- At detrusor 1.0, level 0.2 gives only partial emptying:
  - Every session voids 10% or more.
  - The median voided is 33–34% and the maximum is 48–53%.
  - So only 0 of 64 sessions (×1.0) and 2 of 63 (×0.9) reach 50%.
  - The user then starts about twice as many sessions per run (4.2–4.3 against 2.0).
- At detrusor 1.0 from 0.3 up, no session voids 10%.
- Between 0.3 and 0.5 the results barely change, because the drive during bursts is then close to the resting drive.

**Emptying time grows only a little before emptying fails.**
- At detrusor 0.6, the median goes from 50 to 55 s (maximum 51 to 56 s). Almost every session there is ended by the 60 s maximum duration (97–100%), so the emptying time is close to that cutoff.
- At detrusor 1.0, the median stays at 25 s at level 0.1 (maximum 50 to 51 s). At 0.2 it is 35–42 s (maximum 56 s), but those sessions only empty partly.
- No emptying time exceeds 56 s.
- Flow stops within 2 s of stimulation stopping at every level.
- At detrusor 1.0, levels 0–0.2, most sessions end at the pressure ceiling (70–90%). No session at any level ends on the volume stop.

## 5. Caveats on the criteria

- **Only P1 separates the levels that work from those that don't.**
  - **P3** passes in all 24 setting × level cells. The highest peak true p_D is 56.6 cmH₂O, under the 60 cmH₂O limit (ceiling 55 + 5). The reason is that the model's storage pressure levels off near 56.6 (E18, E92).
  - **P2** only counts leaks after the alert (E63). At ×1.0, the levels that don't empty pass P2 (15 of 15) while the bladder fills up to 940 mL with no leak. At ×0.9, those levels fail P2: all 15 runs leak (up to 432 mL leaked after the alert). So "no leak" there means the bladder is over-full, not that it is managed.
- **The subset is narrow:** one ceiling (55), one threshold (400 mL), one maximum duration (60 s), one burst timing (5 s on / 5 s off) and two detrusor drives. The answer may differ elsewhere.
  - With a longer maximum duration, detrusor 0.6 sessions might empty more at 0.1, but that was not tested.
- **15 seeds are not proof.** Fifteen clean runs only show a rate of about 82% or more (E68).
- **Missing physiology.** The model has no dyssynergia, fatigue, fibre types or sacral anatomy. The level is a replaced model drive, not a recruitment level, so it does not say how much nerve block any real method would need.

## 6. Log entries

These are in §5 of `VALIDATION_AND_LIMITATIONS.md`:
- **E100:** the stalled first attempt and the restart.
- **E101:** the drop-off between 0.1 and 0.2, and the higher leftover at 0.1.
- **E102:** P2 and P3 do not separate the levels.
- **E103:** partial emptying at detrusor 1.0, level 0.2.
- The §2 row for the six levels is filled in.

## 7. Files in `results/task5/`

| File | Content |
|---|---|
| `task5_runs.csv`, `task5_sessions.csv` | All 360 runs and 2,612 sessions (no traces) |
| `task5_settings_summary.csv` | `summarise_exp3` output per setting × level |
| `task5_by_level.csv`, `task5_key_numbers.json` | Scoring by level (from `experiments/task5_analysis.py`) |
| `reproduction_15_seeds.json` | Levels 0 and 0.5 against Task 4, all 15 seeds |
| `parameters_used.csv`, `levels_used.csv` | Parameters and levels as run |
| `run_log.txt`, `sweep_started.txt` | Log of the restarted sweep (attempt 2) |
| `run_log_attempt1_stalled.txt`, `sweep_started_attempt1_stalled.txt` | Log of the first attempt, which stalled at 150 runs (E100) |
| `check/` | Step 2 check: 24 runs, passed |
