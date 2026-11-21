# Figure audit (7 Nov 2026)

The user asked for four things to be checked straight from the data. This audit is **read-only**: no new simulation, no parameter changes. Script: `experiments/figure_audit.py`. Outputs: `results/figure_audit/` (`key_numbers.json`, `exp2_passes_by_threshold.csv`, `exp2b_passes_by_threshold.csv`, `pressure_vs_volume_no_stimulation.csv`). Every number is a **model prediction**. Results for patterns without co-activation (`s0.0`) are **POST-HOC and OPTIMISTIC**. Mismatches are logged in §5 of `VALIDATION_AND_LIMITATIONS.md` (E35 correction, E89–E92).

## 1. What co-activation 0, 0.5 and 1.0 mean, as implemented

While a burst is ON, the hypothetical stimulator **replaces** the model's sphincter input with the co-activation value. That input is the somatic (pudendal) drive, ω_s, a dimensionless number from 0 to 1, not a current. The stimulator does not add to the model's own value. The sphincter's activation then follows the new value with a 0.2 s time constant. When a burst is OFF, and between sessions, the sphincter goes back to the model's own storage reflex. That reflex gives 0.5 while the urethra is closed (0.45 at the weaker ×0.9 strength), and only falls once the urethra is more than about 70% open (see `docs/EMPTYING_DURATION_CHECK.md`).

- **Co-activation 0:** the stimulator switches the sphincter drive fully off during each burst. That is below its resting 0.5, and below the 0.1 the upstream model uses during a healthy void.
- **Co-activation 0.5:** holds the drive at its resting level (exactly at ×1.0, slightly above it at ×0.9). The drive is fixed, so the reflex cannot ease off as the urethra starts to open.
- **Co-activation 1.0:** doubles the drive to the maximum the model allows.

The ×0.9 strength changes only the reflex, never the stimulated value. None of these numbers corresponds to a real stimulation setting.

## 2. Leftover (residual) volume

Residual is the **true** volume 120 s after a session ends, so it includes about 2 mL of new urine made during those 120 s. "Working settings" are those that pass every frozen criterion.

| Where | Sessions | Median (mL) | Range (mL) | Share ≤ 3 mL |
|---|---|---|---|---|
| Stage 5 map, complete sessions (one fixed session from 453 mL) | 72 | 0.2 | 0.0–11.3 | 99% |
| Experiment 3 (3 seeds), all sessions in the 38 working settings | 228 | 2.5 | 0.0–199.5 | 58% |
| Experiment 3, complete sessions only (any setting) | 175 | 1.9 | 0.0–17.8 | 78% |
| Experiment 3b (15 seeds), all sessions in the 75 working settings | 2,380 | 5.1 | 0.0–251.1 | 33% |
| Experiment 3b, complete sessions only (any setting) | 1,470 | 2.5 | 0.0–21.2 | 57% |
| Experiment 7, normal use (T3), passing rule `cap4_drop0.40`, sessions that emptied | 370 | 3.9 | 0.0–240.9 | 38% |

Medians per working setting:
- Experiment 3: 1.3–97.5 mL.
- Experiment 3b: 1.9–156.4 mL.

**"0 to 3 mL" is not confirmed as a range.** It describes a typical complete session, not what is left over in settings that work.
- In Experiment 3 working settings, 96 of 228 sessions left more than 3 mL, and 42 left more than 50 mL.
- In Experiment 3b, 1,597 of 2,380 left more than 3 mL, and 868 left more than 50 mL.

The large leftovers come from sessions that the pressure ceiling stopped early:
- **Experiment 3:** median 60.8 mL, up to 199.5 mL.
- **Experiment 3b:** median 92.6 mL, up to 207.2 mL.

Sessions that ended on the maximum duration or the volume stop leave 0.0–6.3 mL in Experiment 3.

The model's tendency to empty almost to zero is not realistic (E35), so even the small numbers must not be read as a real post-void residual.

**Mismatch (E35 correction, E89):** the Stage 5 report and E35 say the residual is 0.0–1.8 mL whenever emptying happens. For complete sessions the true range is **0.0–11.3 mL**. The 11.3 mL comes from `e0.6_s0.0_2on2off`, 60 s, at ×1.0, and the same pattern at ×0.9 leaves 2.8 mL. The other 70 complete sessions are 0.0–1.8 mL. Partial sessions (14) leave 46–393 mL.

## 3. Quoted figures

| Figure | From the data | Verdict |
|---|---|---|
| 636 closed-loop runs | 312 Experiment 3 + 324 Experiment 4 runs (3 seeds), 0 errors, invariants A2–A4 hold in all 636 | **Confirmed, but only as "Experiment 3 and 4 runs".** Experiment 3b (1,620) and Experiment 7 (1,710) are closed-loop runs too, so 636 is not the project total (E91). |
| Best alert threshold passes 10 of 14 sensor scenarios | 15 seeds (Experiment 2b, 300 runs per cell): **10 of 14** at 400 mL at both sphincter strengths; at ×1.0, 450 mL also gives 10. With 3 seeds (Experiment 2, 60 runs per cell): **11 of 14** (×1.0) and **9 of 14** (×0.9), both at 400 mL. | **Confirmed for 15 seeds only.** Quote it as "10 of 14 with 15 seeds" (E91). |
| 75 of 108 settings work in Experiment 3b | 75 of 108; recomputing invariants + P1 + P2 + P3 from the summary flags gives 75, with 0 disagreements | **Confirmed.** POST-HOC, OPTIMISTIC. Must not be quoted alone (E68). |
| Stuck-high sessions fall from 12 to 1 in Experiment 7 | Test T1 (estimate stuck at 450 mL from 5 h): rule off, 60 runs, 12 sessions in every run; rule on, 360 runs, exactly 1 session in every run | **Confirmed.** |

**The 14 sensor scenarios** are every Experiment 2 scenario except `ideal`, which is a reference only. "11%" is the Toymus 2024 best-case anchor, 11.17% mean relative error. Every magnitude other than that anchor is ASSUMED.
1. `anchor_11pct`: 11% error.
2. `mre_20pct`: 20% error.
3. `mre_30pct`: 30% error.
4. `mre_40pct`: 40% error.
5. `gain_minus20`: reads 20% low.
6. `gain_plus20`: reads 20% high.
7. `drift_minus2ph`: drifts 2% per hour low.
8. `drift_plus2ph`: drifts 2% per hour high.
9. `delay_5min`: readings 5 min late.
10. `delay_15min`: readings 15 min late.
11. `missing_20pct`: 20% of readings missing.
12. `missing_50pct`: 50% of readings missing.
13. `misaligned_at_4h`: from 4 h, reads 30% low and 30% of readings are missing.
14. `combined_bad`: 30% error, drifts 2% per hour low, 30% missing and 5 min late.

Scenarios 5–13 also carry the 11% error.

**Which scenarios fail at the best threshold**
- **15 seeds, 400 mL, both strengths:** `gain_minus20`, `misaligned_at_4h`, `mre_30pct`, `mre_40pct`.
- **15 seeds, 450 mL, ×1.0:** `combined_bad`, `drift_minus2ph`, `gain_minus20`, `misaligned_at_4h`.

**The pass rule** (frozen in `docs/EXPERIMENT2_SUCCESS_CRITERIA.md`) is applied per scenario, threshold and sphincter strength. A combination "works" when C1, C2 and C3 all pass:
- **C1:** at least 95% of runs have a useful alert. A useful alert is the first alert at or above 300 mL true volume that comes before the adverse event. The adverse event is reaching 500 mL, or with the weaker sphincter, the start of leaking.
- **C2:** at most 5% of runs have any false alert, meaning an alert below 300 mL.
- **C3:** the median lead time before the adverse event is at least 30 min.

## 4. Bladder pressure against volume, with no stimulation

These come from the saved Stage 3 traces: seed 42, the first 12 h, 1 Hz. The SCI ×1.0 case is the configured one (ceiling 1,000 mL, drive extrapolated above 500 mL). All three cases follow the same curve until something stops the filling.

| Volume (mL) | 0–50 | 200–250 | 350–400 | 400–450 | 450–500 | 500–550 | 550–600 | 650–700 | 850–900 |
|---|---|---|---|---|---|---|---|---|---|
| SCI ×1.0, median p_D (cmH₂O) | 6.9 | 8.9 | 9.0 | 17.2 | 51.5 | 50.1 | 25.0 | 13.3 | 14.1 |
| SCI ×1.0, max p_D | 7.8 | 9.2 | 11.5 | 32.4 | 56.5 | 56.6 | 39.0 | 13.4 | 14.4 |

- **The curve is flat, then steep, then falling.**
  - Pressure stays at about 7–9.4 cmH₂O (median per 50 mL band) up to about 400 mL.
  - It then rises steeply: 11.6 at 400 mL, 32.5 at 450 mL.
  - It first reaches 40 cmH₂O at 461 mL and 55 cmH₂O at 491 mL.
  - It peaks at **56.6 cmH₂O at 502 mL** (7.2 h).
  - Above that it **falls**, to about 13–14 cmH₂O from 650 mL up to the 909 mL reached in 12 h (E18).
  - Pressure therefore says little about fullness below 400 mL, and nothing reliable above 500 mL. It is not a fullness indicator.
- **Yes, storage pressure alone reaches the 55 cmH₂O ceiling**, once the bladder passes about 490 mL.
  - **SCI ×1.0:** it stays at or above 55 for 1,269 s (21 min) on the way through.
  - **SCI ×0.9:** it reaches 55.1 at 491 mL. The urethra then opens and the bladder dribbles (420 mL leaked in 12 h), which holds the pressure just below 55 (only 36 s at or above it).
  - **Healthy control:** it voids at its 54.7 cmH₂O trigger and never reaches 55.
  - In Stage 3, 30 of 34 SCI cases peaked at or above 55. The SCI peaks range from 45.2 to 57.3.
- **In the closed-loop runs, the same thing happened whenever the bladder over-filled.** This counts the highest true pressure outside sessions and outside the 120 s after each session:

  | Experiment | Runs at or above 55 cmH₂O | Without co-activation | Notes |
  |---|---|---|---|
  | Experiment 3 | 119 of 312 | 0 | |
  | Experiment 4 | 129 of 324 | 21 | |
  | Experiment 3b | 40 of 1,620 | 40 | all at ceiling 40, the E63 trap |
  | Experiment 7 | 412 of 1,710 | 104 | |

  - Every one of these runs reached at least 490.7 mL.
  - The highest storage pressure in any run is 56.6 cmH₂O.
- **What this means (E92):** the 55 cmH₂O ceiling sits below the model's own resting peak. A session started on a bladder above about 490 mL begins above the ceiling and stops at once (E36). In this model the ceiling only works if the alert comes well before 490 mL.
