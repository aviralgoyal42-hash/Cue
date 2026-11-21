# Experiments 3 and 4 rerun with 15 seeds: results

**Run 4–7 Nov 2026, analysed 8 Nov 2026.** Plan: `docs/EXPERIMENT3_4_15SEED_PLAN.md`, frozen 4 Nov, unchanged. Its SHA-256 still begins 4C4DC185, and its change log is empty. This is the last experiment in the project.

All values are ASSUMED or carried over unchanged. The sensor is a synthetic experimental proxy, the stimulator is hypothetical, and nothing here shows clinical safety or effectiveness. Every pattern that empties uses no co-activation, so those results are **POST-HOC and OPTIMISTIC** (E87).

Files: `results/task4/`. Scripts: `experiments/task4_rerun_exp3_4.py` (sweep) and `experiments/task4_analysis.py` (comparison). The old results in `results/stage6/` were read and never written.

## Headline

- **Seeds 42, 1 and 2 reproduce the old Experiments 3 and 4 exactly.** That covers every run row and every session row, in every shared column except `runtime_s`.
- **No verdict changed.** None of the 104 Experiment 3 settings changed P1, P2, P3, "full loop works" or the A2–A4 result. Both Experiment 4 requirements still hold.
- **38 of 104 settings still work.** As before, none of them uses co-activation.
- **The worst pressures rose with more seeds**, as the plan expected for Experiment 3. The dead-pressure worst case in Experiment 4 rose from 64.2 to 67.2 cmH₂O, 12.2 above the ceiling. The plan did not predict that.

## What was run

| Part | Runs | Sessions | Errors |
|---|---|---|---|
| Experiment 3 (104 settings × 15 seeds) | 1,560 | 11,105 | 0 |
| Experiment 4 (108 cells × 15 seeds) | 1,620 | 9,379 | 0 |
| **Total** | **3,180** | **20,484** | **0** |

The seeds were 42 and 1 to 14. One seed sets all four random streams, as in the original runs.

## Reproduction check: passed

| Table | Old rows | Matching new rows | Columns compared | Identical |
|---|---|---|---|---|
| Experiment 3 runs | 312 | 312 | 37 | yes |
| Experiment 3 sessions | 2,214 | 2,214 | 27 | yes |
| Experiment 4 runs | 324 | 324 | 37 | yes |
| Experiment 4 sessions | 1,889 | 1,889 | 27 | yes |

The files were compared to each other with exact number reading (E58), by value rather than by storage type (E73). No old column is missing from the new files. Source: `results/task4/reproduction.json`.

## Old results: unchanged, but the automatic check said False

`results/task4/old_results_check.json` reports `old_results_unchanged: false`. **No old file changed.** All 214 files hashed before the sweep are still present and byte-identical.

The check compares the whole list of files, so new files also make it fail. During the sweep, another session added 10 files in two new folders: `results/emptying_check/` (6 files, 18:43 on 7 Nov) and `results/figure_audit/` (4 files, 19:18). Those belong to the emptying-duration check and the figure audit (E84–E92), not to this rerun. Logged as E94.

## Experiment 3: verdicts

| Count of 104 settings | 3 seeds | 15 seeds |
|---|---|---|
| P1 passes (≥80% of sessions void ≥50%) | 40 | 40 |
| P2 passes (≥95% of runs without overflow after alert) | 76 | 76 |
| P3 passes (≥95% of sessions within ceiling + 5 cmH₂O) | 86 | 86 |
| Full loop works | 38 | 38 |
| Working settings using co-activation | 0 | 0 |
| A2–A4 hold in every run | yes | yes |
| Settings with any verdict changed | – | **0** |

I recounted all of these from the raw run and session files with a separate script that uses none of the project's scoring code. It gave the same counts and found 0 changes.

### Why nothing moved

The verdicts are far from their lines, except for P3:

| Criterion | Lowest among passing settings | Highest among failing settings | Line |
|---|---|---|---|
| P1 | 0.933 | 0.000 | 0.80 |
| P2 | 1.000 (every run) | 0.000 (every run overflowed) | 0.95 |
| P3 | 0.967 | 0.881 | 0.95 |

A setting either empties in almost every session or in none. It either never overflows or always overflows. More seeds cannot flip results like these, so this rerun was a weaker test than it looks (E95). The largest moves were:
- **P1:** up to 0.067.
- **P3:** up to 0.267, in e0.6_s0.0_5on5off at ceiling 40, 60 s, ×1.0. It went from 0.500 to 0.767 and still fails.

The plan expected that the count of 38 "may fall" (E93). It did not. Every one of the 38 working settings had 15 of 15 runs without overflow.

### Other headline numbers

| Number | 3 seeds | 15 seeds |
|---|---|---|
| Highest session peak, any setting | 58.47 cmH₂O | **60.18 cmH₂O** |
| Highest session peak, working settings | 53.83 | 53.83 |
| Sessions over ceiling + 5 cmH₂O | 261 of 2,214 | 1,306 of 11,105 |
| Volume stop fired, 60 s ultrasound | 0 of 1,236 | 0 of 6,193 |
| Volume stop fired, 5 s ultrasound | 87 of 978 | 440 of 4,912 |
| Median residual across working settings | 1.33–97.48 mL | 1.84–98.76 mL |
| Declared reference, best P1 | 0.000 | 0.000 |

**The new 60.18 cmH₂O peak** is in the declared reference (e1.0_s0.5_5on5off) with a 350 mL threshold, seed 4. The session started at 315.9 mL, and the pressure ceiling stopped it after 1.8 s, with pressure 5.18 cmH₂O over the ceiling. That setting already failed P1. Its P3 went from 1.000 to 0.994, so it still passes P3 (E96).

## Experiment 4: requirements

| Requirement | 3 seeds | 15 seeds |
|---|---|---|
| A2–A4 hold in every run, under every fault | yes (324 runs) | **yes (1,620 runs)** |
| Dead pressure + estimate stuck high: every session ends at maximum duration | yes | **yes (720 of 720 sessions, all 60.0 s)** |

Both requirements still hold.

### Descriptive results (not criteria)

| Number | 3 seeds | 15 seeds |
|---|---|---|
| Highest peak, any cell | 64.21 cmH₂O | **67.17 cmH₂O** |
| Largest overshoot of the ceiling | 9.21 | **12.17** |
| Peak, estimate stuck high, pressure channel working | 58.65 | 59.44 |
| Sessions per run, estimate stuck high (maximum) | 12 | 12 |
| Sessions over ceiling + 5 cmH₂O | 2 of 1,889 | 24 of 9,379 |
| Cells with any overflow after alert | 32 | 33, all at ×0.9 |

- **The dead-pressure worst case got worse (E97).** The 67.17 cmH₂O peak is in the co-activation reference with seed 14, at ×0.9 (67.16 at ×1.0). With no pressure channel, only the 60 s maximum duration ends the session. That requirement still held, but the peak is 12.2 cmH₂O over the ceiling. In that cell, P3 went from 0.972 to 0.961.
- **The pressure ceiling overshoots even when the channel works (E98).** 10 of the 24 sessions over the margin were on a working pressure channel, in faults sensor:mre_30pct, sensor:mre_40pct and sensor:gain_plus20. The ceiling stopped them after 1.5–1.8 s, with peaks of 60.18 to 61.38 cmH₂O. They started at 296–316 mL, so they were not late, full-bladder sessions. The other 14 were in the dead-pressure combination.
- **The stuck-high peak rose from 58.65 to 59.44 cmH₂O**, as the plan predicted from Experiment 7 (E80).

### Cells that crossed a line (descriptive only)

As frozen in the plan, these marks are reported and not scored. All 6 are in the second reference, e1.0_s0.0_5on5off.

| Fault | Sphincter | Line crossed | 3 seeds | 15 seeds |
|---|---|---|---|---|
| sensor:combined_bad | ×0.9 | P1 | 0.714 | 0.933 |
| sensor:combined_bad | ×1.0 | P1 | 0.750 | 0.879 |
| sensor:drift_minus2ph | ×0.9 | no overflow | overflow rate 0.000 | 0.467 |
| sensor:gain_minus20 | ×0.9 | P1 | 0.833 | 0.633 |
| sensor:misaligned_at_4h | ×1.0 | P1 | 0.750 | 0.833 |
| user:delayed | ×0.9 | P1 | 0.750 | 0.957 |

**The 3-seed estimates of fault rates were poor (E99).** The largest move in an overflow rate was 0.467, for sensor:drift_minus2ph at ×0.9: no overflow in 3 runs, but 7 of 15 with 15 seeds. The largest P1 move was 0.219, for sensor:combined_bad at ×0.9. Other overflow rates also moved a lot, for example user:delayed at ×0.9, from 0.333 to 0.733. So no 3-seed Experiment 4 rate should be quoted as a rate.

## Expectations frozen in the plan, checked

| Expectation | Result |
|---|---|
| The count of 38 working settings may fall | **Did not happen.** Still 38 |
| The stuck-high peak rises from 58.6 to 59.4 cmH₂O | Happened: 59.44 |
| Other Experiment 3 peaks may rise above 58.5 cmH₂O | Happened: 60.18 |
| The declared reference still fails everywhere | Happened: best P1 0.000 |

## Run time

The plan estimated about 8.7 h, with a range of 7 to 9 h.
- **Experiment 3:** after the restart, the resumed part (runs 826 to 1,560) ran at 11.0 s of wall time per run.
- **Experiment 4:** ran at 8.7 s per run (18:39 to 22:33 on 7 Nov).
- **Total:** at those rates, the sweep would have taken about 8.7 h without interruption.

It actually took from 19:53 on 4 Nov to 22:33 on 7 Nov, because the computer slept and was restarted (E83). `runtime_s` in this rerun counts sleep and must not be used.

## Checks after the run

- **Number check:** `experiments/check_doc_numbers.py` recomputes every number quoted here from the result files. All 587 checks match, 128 of them added for this rerun.
- **Tests:** the full suite with slow tests (`CUE_RUN_SLOW=1`) gave 180 passed and 1 failed, out of 181. The failure is `test_upstream_clone_is_pinned_and_unmodified`, already logged as E88: `third_party/lut-sim/.git` was not copied in the move, so git cannot check the upstream pin. The exact reproduction of seeds 42, 1 and 2 is further evidence that the upstream model is unchanged. Log: `results/task4/full_test_log.txt`.

## Limitations

These carry over from the plan:
- **Seeds are matched across cells.** The same seed gives the same inflow everywhere, so one unusual seed (seed 4 here) can affect several cells at once.
- **15 clean runs give a lower bound of about 82%, not 95% (E68).**
- **The rerun is not blind.** 3 of the 15 seeds are the old ones, and Experiments 3b and 7 had been seen.
- **The sensor and stimulator are a proxy and a hypothesis.** The model has no dyssynergia and no sacral anatomy.
- **All working patterns assume no co-activation**, which in this model means the stimulator switches off the sphincter's own reflex tone (E87).

## Files

| File | What it holds |
|---|---|
| `exp3_runs.csv`, `exp3_sessions.csv`, `exp3_settings_summary.csv` | Experiment 3, 15 seeds |
| `exp4_runs.csv`, `exp4_sessions.csv`, `exp4_fault_summary.csv` | Experiment 4, 15 seeds |
| `reproduction.json` | Seeds 42, 1, 2 against `results/stage6/` |
| `old_results_manifest.csv`, `old_results_check.json` | Hashes of old result files, before and after (see E94) |
| `exp3_verdict_compare.csv`, `exp3_verdict_changes.csv` | All 104 settings, old against new (the changes file is empty) |
| `exp4_cell_compare.csv`, `exp4_line_crossings.csv` | All 108 cells, old against new, and the 6 crossings |
| `key_numbers.json`, `analysis_output.txt` | Headline numbers for both seed sets |
| `exp3_P1_by_pattern_and_ceiling.png`, `exp4_fault_map.png` | The Stage 6 figures redrawn with 15 seeds |
| `run_log.txt`, `run_log_part1_stopped_by_restart.txt` | Sweep logs, after and before the restart |
| `traces/` | 1 Hz traces for seed 42, ×1.0, as in Stage 6 |
