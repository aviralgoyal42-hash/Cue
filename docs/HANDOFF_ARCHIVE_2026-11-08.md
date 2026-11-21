# Project Cue: handoff for the next agent

Written 2026-11-07, while the final experiment (the 15-seed rerun of Experiments 3 and 4) was running. **The documents and result files in this folder are the source of truth.** This handoff summarises them and says where to look. If a number here disagrees with a result file, trust the file, and log the mismatch (see "Rules", item 7).

---

## 1. Status at a glance

| Item | State |
|---|---|
| Stages 1–7, Experiments 1–6 | Done and reported |
| Task 1: provenance of the upstream mechanical constants | Done: `docs/MECHANICAL_CONSTANT_PROVENANCE.md` |
| Task 2: Experiment 3b, 15 seeds, POST-HOC and OPTIMISTIC | Done and approved: `docs/EXPERIMENT3B_RESULTS.md` |
| Task 3: Experiment 7, session cap and post-session check | Done and approved by the user: `docs/EXPERIMENT7_RESULTS.md` |
| **Final experiment: Experiments 3 and 4 with 15 seeds** | **Done 7–8 Nov:** `docs/EXPERIMENT3_4_15SEED_RESULTS.md`, `results/task4/`, §5 E93–E99. Old seeds reproduce exactly; no verdict changed. See section 6 |
| Emptying-duration and sphincter-timing check (read-only, 7 Nov) | Done: `docs/EMPTYING_DURATION_CHECK.md`, `results/emptying_check/`, §5 E84–E88 |
| Figure audit (read-only, 7 Nov) | Done: `docs/FIGURE_AUDIT.md`, `results/figure_audit/`, §5 E35 correction and E89–E92 |
| Task 5: sphincter level during bursts (model only, POST-HOC, OPTIMISTIC) | **Done 8 Nov:** `docs/TASK5_PLAN.md`, `results/task5/SUMMARY.md`, §5 E100–E103. The highest level that works is 0.1 in all 4 settings |
| After that | Nothing pending. Stop and report |

Update 2026-11-08: section 5 now runs from E1 to **E99**. The next entry is **E100**. The 15-seed rerun is finished and its entries are E93–E99. *(Superseded by the Task 5 line below.)*

Update 2026-11-08 (Task 5): the sweep is finished, with 360 runs and 0 errors. The first attempt stalled at run 150 when the laptop went into Modern Standby. It was restarted from the saved runs with the user's OK and finished at 09:39 (E100). Levels 0 and 0.5 match Task 4 exactly for all 15 seeds. The highest sphincter level during bursts at which emptying works is **0.1 in all 4 settings**, and 0.2–0.5 fail P1. Leftover volume already rises at 0.1. P2 and P3 do not separate the levels (E101–E103). These are model predictions, not evidence for a device. Section 5 now runs to **E103**, and the next entry is **E104**. To keep a long sweep awake, a progress monitor keeps the session active, because the app's keep-awake hold lets go after about 5 idle minutes.

*(Superseded line from 7 Nov, corrected 2026-11-08: it said the log ran to E92 and the next entry was E93. The update line above is the current one.)* Note E88: the upstream pin test now fails because `.git` is missing, so expect 1 failure in the suite.

---

## 2. What the project is

Cue is a high-school concept (NYAS Junior Academy, Brain Tech Challenge) for people with spinal cord injury who cannot sense or control their bladder:

1. An ultrasound patch estimates fullness.
2. A watch vibrates when the bladder is full.
3. The user decides when to empty by pressing a button. **The device never starts emptying on its own.**
4. The press starts a hypothetical implanted sacral nerve-root stimulator.
5. Safety cutoffs end stimulation.

This folder is a **simulation-only** framework built on the unmodified upstream lower-urinary-tract model by Lister et al. 2025 (*R Soc Open Sci* 12:242062, MIT licence), in `third_party/lut-sim`. Nothing here is hardware. Every result is a model prediction. The team must understand and defend every part, so code and docs use plain language and readable comments.

---

## 3. Rules the user set (all still in force)

These come from the user's messages across the project. Treat them as hard rules.

**How to work with the user**
1. **Address the user as "Aviral" at the start of every response.** The user asked to be called by name. Earlier agents used "Sumit", taken from the Windows account; on 2026-11-07 the user said their name is Aviral. The `C:\Users\Sumit\...` folder paths are unchanged and correct.
2. **Never start or suggest a session compaction** unless the user explicitly asks. The user was upset when automatic compaction lost context, and has set `/autocompact` to a 1 million token window.
3. **Never shut down, restart or change the computer**, and take no action outside the project folder, unless the user explicitly asks in that message. The user did approve keeping the computer awake for the current sweep, through the app's keep-awake hold.
4. Ask the user when a decision is genuinely theirs, and never make assumptions silently.
5. **Freeze success criteria in `docs/` before running anything.** Never change frozen criteria after seeing results. If one must change, log it in that document's change log and in §5, and say why.
6. **Never tune an ASSUMED value** to make the baseline or Cue look better. If something behaves oddly, report it as a result and show how it changes across a range. Every ASSUMED value appears in the table in §2 of `VALIDATION_AND_LIMITATIONS.md`, with what was tried and what changed.
7. **Log every error, surprise, failed expectation or negative result in §5**, recording what happened, how it was found, what changed, and the effect on conclusions. **Never remove an entry.** Add corrections beneath it, such as the "E47 correction" row.
8. Keep old results. New experiments write to a new `results/` subfolder.
9. Label every value SOURCED or ASSUMED. Never invent values, citations or accuracy figures. Check units carefully and convert explicitly.

**Science and safety**

10. The device must **never read ground-truth volume**. Only evaluation code compares with truth. Tests enforce this.
11. Never use the upstream void switch. Any emptying must come from the model's mechanics.
12. Give no clinical stimulation parameters. Stimulator inputs are normalised model drives.
13. Never claim clinical safety or effectiveness. Call the sensor a "synthetic experimental proxy", never "validated".
14. The 11% mean relative error (Toymus et al. 2024, *Nat Commun*, 5 healthy volunteers lying on their backs) is only a labelled best-case anchor.
15. Pressure is **not** a fullness indicator.
16. **Keep the concept away from the brain:** no brain interfaces and no brain-signal recording, in code or in text. Nothing is placed in the brain.
17. Label POST-HOC and OPTIMISTIC results as such. This covers Experiment 3b and the patterns without co-activation, which were chosen after seeing that they empty.

---

## 4. Environment and how to run

- **Windows 11**, 12 logical cores, 15.3 GB of RAM. Memory can run low when other apps are open.
- The project lives at `C:\Users\Sumit\Downloads\Project Cue\project-cue`.
- **Python environment:** `%USERPROFILE%\.venvs\project-cue` (Python 3.12.10, with numpy 2.3.1, scipy 1.15.2, pandas 2.2.3, matplotlib 3.10.0 and pytest). It sits outside the project on purpose.
  - PowerShell: `& "$env:USERPROFILE\.venvs\project-cue\Scripts\python.exe" ...`
- **Tests:**
  - `& "$env:USERPROFILE\.venvs\project-cue\Scripts\python.exe" -m pytest -q -p no:cacheprovider -W ignore`
  - Set `$env:CUE_RUN_SLOW="1"` to include the slow tests. The last full run with them passed 172 tests on 4 Nov, before the 9 tests in `tests/test_task4_rerun.py` were added. Those 9 pass on their own, so expect 181. *Update 2026-11-08: the last full run (8 Nov) gave 180 passed and 1 failed, the known E88 failure.*
- **Document number check:** `python experiments/check_doc_numbers.py` recomputes every number quoted in the docs from the result files. It was at 192 of 192 checks matching. *Update 2026-11-08: now 587 of 587.* *Update 2026-11-08, after Task 5: now 903 of 903, including the Task 5 block (T5).* Run it last, after any doc change.
- **Upstream:** `third_party/lut-sim` is at commit `bd8f2a072ef017b99dc051b24972333141f7d257`. When the app moved the project to this folder it did not copy the `.git` subfolder, so `git status` no longer works there. The 19 source files are present, and the code reproduces old results exactly.

**Windows pitfalls already hit**
- Long paths are limited to 260 characters (E38). Keep file names short.
- Python's `read_text`/`write_text` on Windows turns line endings into CRLF. All project files are CRLF now. Edits can mix line endings. To normalise, read the bytes and replace `\r\n` with `\n`, then `\n` with `\r\n`.
- In PowerShell, `*>` writes UTF-16 log files. `Get-Content` reads them fine.
- Use `Out-String -Width 200` for wide tables. `Select-Object -First` on a Python pipe can kill Python (exit 255).
- `time.perf_counter()` keeps counting while the computer sleeps, so `runtime_s` is wrong for any run that spans a sleep (E83).
- **Comparing CSV files exactly:** read with `float_precision="round_trip"` and compare file to file, never a file against values in memory (E58). Compare by value, not storage type: `same_values()` in `experiments/task3_experiment7.py` does this, because `DataFrame.equals` fails on 2 against 2.0 (E73).

---

## 5. Code map

```
config.py                 every parameter, labelled SOURCED or ASSUMED; config.validate() checks them
lut_upstream.py           imports the unmodified upstream model (its package name is `model`, so never create one)
sci_test_rig.py           closed-loop rig: physiology + sensor + device + user + controller + stimulator + pressure
cue_model/                sci_lut.py (SCI subclass of the upstream model), metrics.py (ground-truth metrics)
sensors/                  ultrasound_sensor.py (synthetic proxy), pressure_channel.py (synthetic implant channel)
devices/                  custom_tech_device.py (sees readings only), user_model.py, stimulator.py,
                          safety_controller.py (state machine), session_guard.py (Experiment 7 rule, off by default)
evaluation/               closed_loop_metrics.py, experiment2_metrics.py, guard_metrics.py; the only place truth meets device output
experiments/              one script per stage or experiment (see README.md)
results/                  stage2, stage3, stage4, stage4b, stage5, stage6, extra, task2, task3, task4, task5, emptying_check, figure_audit
tests/                    pytest suite, one file per stage or task
docs/                     frozen criteria, stage reports, results documents; docs/sources holds source extracts
```

**Key mechanics**
- Upstream model: lumped lower urinary tract, forward Euler, time step 0.1 s. It is unstable at 0.4 s or more.
- Device: the estimate is the median of the last 5 valid readings, one reading per 60 s. It confirms an alert after 3 readings, re-arms with 50 mL hysteresis, and treats readings as stale after 600 s.
- Safety controller states: MONITORING, FULL_DETECTED, ALERT_SENT, WAITING_FOR_USER, STIMULATING, CUTOFF, LOCKOUT (1,800 s), and CATHETER_ONLY (with the session guard only).
  - Stimulation starts **only** on a button press in WAITING_FOR_USER.
  - Three independent cutoffs: maximum duration (60 s), volume stop (100 mL, device estimate only), and pressure ceiling (55 cmH₂O on the synthetic channel).
- Invariants A2, A3 and A4 are recomputed from raw logs in every experiment:
  - A2: sessions start only after an alert and a press.
  - A3: no session starts during lockout.
  - A4: every session ends within the maximum duration.
- Each run is one simulated person for 12 h. One seed value sets the inflow, sensor, user and pressure-channel random streams together.

---

## 6. Current work: the 15-seed rerun of Experiments 3 and 4

**Update 2026-11-08: finished.** The sweep ended at 22:33 on 7 Nov: 3,180 runs, 0 errors. The steps below were all done. Results are in `docs/EXPERIMENT3_4_15SEED_RESULTS.md` and §5 E93–E99. The text below is kept as written on 7 Nov.

**The user's request (7 Nov, paraphrased):** "Rerun Experiments 3 and 4 with 15 inflow seeds per cell (42 and 1 to 14) on the same grid, with the same criteria. Do not change criteria or any ASSUMED value. Freeze the plan in docs/ first, including an estimated run time based on the Experiment 7 rate. Check that seeds 42, 1 and 2 reproduce the old Experiments 3 and 4 exactly. Keep the old results, put new ones in a new folder, report which verdicts changed and log every change in section 5. Never shut down or restart the computer. Do not start or suggest a session compaction. Stop and report when finished."

**Already done**
- Plan frozen: `docs/EXPERIMENT3_4_15SEED_PLAN.md`. The grid is 3,180 runs: Experiment 3 has 1,560 (104 settings) and Experiment 4 has 1,620 (108 cells). The estimate was 8.7 h, with a range of 7 to 9 h.
- Runner: `experiments/task4_rerun_exp3_4.py`.
  - It calls the old grid functions in `stage6_experiments3_4.py`, swapping only the seed list. `config.py` is untouched.
  - It sends traces to `results/task4/traces`.
  - It saves `*_runs_partial.csv` and `*_sessions_partial.csv` every 25 runs, and resumes from them automatically when started again.
  - It hashes every old result file before the sweep (`old_results_manifest.csv`) and compares them afterwards (`old_results_check.json`). It then writes `reproduction.json`.
  - `--recheck` repeats only the reproduction check.
- Tests: `tests/test_task4_rerun.py`, 9 passing.
- Pilot: 12 cases at seed 42 matched the old rows with 0 differences.
- Scoring script: `experiments/task4_analysis.py`. Its output has not been checked against new results yet. In a dry run on the old results alone it reproduced the old headline numbers (38 of 104 settings work, 0 of 1,236 volume stops at 60 s, 87 of 978 at 5 s, peaks of 53.8, 58.5 and 64.2 cmH₂O), and comparing the old results with themselves gave 0 changes.
- **E83:** the first attempt ran from 4 to 6 Nov. The computer slept for long periods, and then a restart started from the Start menu killed the sweep at 825 of 1,560 Experiment 3 runs. The saved runs were checked: they are complete and in order, and all 165 old-seed rows match. The sweep was resumed on 7 Nov. The first log is `results/task4/run_log_part1_stopped_by_restart.txt`.

**Running now:** a background job runs `python -W ignore experiments\task4_rerun_exp3_4.py *> results\task4\run_log.txt`. It had reached 900 of 1,560 Experiment 3 runs when this file was written, with 1,620 Experiment 4 runs to follow, so about 6 h of awake time is left.
- Progress: `Get-Content results\task4\run_log.txt -Tail 3`.
- If it stops for any reason, check the partial files the same way E83 did, rename the log so it is kept, and start the same command again. It continues from the saved runs.
- Never delete the partial files while the job is running.

**Remaining steps, in order**
1. When the job ends, read `results/task4/run_log.txt`.
   - Count real errors with `runs.error.fillna("").ne("").sum()`.
   - Confirm `reproduction.json` has `"reproduces": true`, and `old_results_check.json` has `"old_results_unchanged": true`.
   - Confirm no `*_partial.csv` files remain.
   - If reproduction fails, report that as a result and investigate. Do not present the new verdicts as an extension of the old ones until the cause is known (frozen plan).
2. Run `python experiments/task4_analysis.py > results\task4\analysis_output.txt`. Fix analysis bugs only; never change criteria. It writes:
   - `exp3_verdict_compare.csv` and `exp3_verdict_changes.csv`
   - `exp4_cell_compare.csv` and `exp4_line_crossings.csv`. These marks are descriptive only, because Experiment 4 has no pass or fail beyond the invariants and the worst-case cutoff.
   - `key_numbers.json`, with old against new headline numbers
   - figures `exp3_P1_by_pattern_and_ceiling.png` and `exp4_fault_map.png`. Open and look at both figures.
3. Cross-check the key findings directly from the raw CSV files, not only through the analysis script. That is how Experiment 7's narrow margins were found.
4. Write `docs/EXPERIMENT3_4_15SEED_RESULTS.md`:
   - every verdict that changed, whichever way it moved;
   - old against new headline numbers;
   - the reproduction result;
   - the expectations stated in the plan, and whether they held;
   - the declared limitations.
   Label everything as model predictions, and keep the POST-HOC label on the second reference and the patterns without co-activation.
5. Add §5 entries from E93 (E84–E92 went to the emptying-duration check and the figure audit): **one per changed verdict** (the user asked for every change to be logged), plus any errors or surprises. The plan already predicts that the peak on the stuck-high reference rises from 58.6 to 59.4 cmH₂O (E80), and that the 38 of 104 count may fall because P2 now needs all 15 runs.
6. Do not edit the old reports (`docs/STAGE6_EXPERIMENTS3_4.md`, `docs/OVERNIGHT_REPORT.md`). If a headline there changes, add a dated update note pointing to the new results, as earlier updates did in §6. Update §4 of `VALIDATION_AND_LIMITATIONS.md` if a stated prediction changes, add the new run and documents to `README.md`, and add §6 notes.
7. Add a block for the rerun to `experiments/check_doc_numbers.py` covering every number quoted in the new doc, then run it until every check matches.
8. Run the full test suite with `CUE_RUN_SLOW=1`.
9. Report to Aviral: which verdicts changed, whether the old seeds reproduced, the run time (and that `runtime_s` is unreliable because of sleep), and the negative results. **Then stop.** No more experiments.

---

## 7. History and headline results

These are short summaries. The documents named are authoritative.

| Stage or experiment | Headline | Document |
|---|---|---|
| Stage 1 | Audit of the upstream code and science. The model was validated against one rat cystometry recording, on shape only | `docs/STAGE1_REPOSITORY_REVIEW.md` |
| Stage 2 | Upstream output reproduced exactly. Stable only at time steps up to 0.2 s | `docs/STAGE2_REPRODUCTION.md` |
| Stage 3, Experiment 1 | The simplified SCI bladder fills to whatever ceiling is set. Peak pressure is about 56.6 cmH₂O near 500 mL. With a weaker sphincter (×0.9) it dribbles continuously. It cannot show detrusor overactivity or dyssynergia | `docs/STAGE3_SCI_BASELINE.md` |
| Stage 4, Experiments 2 and 2b | Sensor and alert performance under faults. No threshold works for all faults, and misalignment defeats the alert | `docs/STAGE4_EXPERIMENT2.md`, `docs/STAGE4B_EXPERIMENT2_RERUN.md` |
| Stage 5 | Stimulation map: with sphincter co-activation of 0.5 or more, nothing empties. Without it, one session empties. The planned reference pattern `e1.0_s0.5_5on5off` therefore never empties, so a second reference `e1.0_s0.0_5on5off` was added, POST-HOC | `docs/STAGE5_TRIGGER_STIMULATION_SAFETY.md` |
| Stage 6, Experiment 3 (3 seeds) | 38 of 104 settings work, none of them with co-activation. The volume stop fired in 0 of 1,236 sessions at 60 s sampling. Peak pressures were 53.8 cmH₂O in working settings and 58.5 overall | `docs/STAGE6_EXPERIMENTS3_4.md` |
| Stage 6, Experiment 4 (3 seeds) | The invariants held under every fault. Stuck-high estimate: 12 sessions per run. Stuck-low: no alert. Dead pressure channel plus stuck-high estimate: 64.2 cmH₂O | same |
| Experiments 5 and 6 | Device parameters move pass counts by at most 1. The misalignment detector fails at every value tried | `docs/EXPERIMENT5_6_RESULTS.md` |
| Experiment 3b (15 seeds, POST-HOC, OPTIMISTIC) | 75 of 108 settings work. The pressure ceiling matters most. There is a trap at ceiling 40 with a 450 mL threshold. 15 clean runs only prove about 82%, not 95% (E68) | `docs/EXPERIMENT3B_RESULTS.md` |
| Experiment 7 | 1 of 6 rule settings passes (cap 4, drop 0.40), with thin margins. The cap caught no fault. If the catheter alert is ignored, a person can end up worse off. The first session's peak pressure is unchanged (E75–E81) | `docs/EXPERIMENT7_RESULTS.md` |
| Final: Experiments 3 and 4 with 15 seeds | Seeds 42, 1, 2 reproduce exactly. No verdict changed: 38 of 104 still work, and the invariants held in all 3,180 runs. Peaks rose: 60.2 cmH₂O in Experiment 3 and 67.2 in the dead-pressure worst case (E97). The 3-seed Experiment 4 rates were poor estimates (E99) | `docs/EXPERIMENT3_4_15SEED_RESULTS.md` |

---

## 8. Open items (only if the user asks)

- The full text of Bastiaanssen 1996, to confirm the species of the mechanical constants.
- Primary sources for the DFree and SENS-U figures, sacral anterior-root stimulation, and McGuire et al. 1981.
- P2 cannot see over-filling without a leak (E63). A volume limit would need the user's decision.
- Continuous stimulation patterns remain unswept at 15 seeds in Experiment 3b. The current rerun covers them at 15 seeds for the original Experiment 3 grid only.
- Experiment 7: catheterisation is not modelled, there is no reset path out of CATHETER_ONLY, and whether to keep the session cap is an open decision (E78).
- A copy of an older state exists at `C:\cue_share`. The user said not to refresh it.

---

## 9. Etiquette that worked with this user

- Report negative results plainly and early. The user values honesty over a good-looking result.
- Show proposals and criteria before running anything when the user asks for approval first. This time the user asked for the plan to be frozen and the sweep run, not for approval.
- Give realistic time estimates, and say so when one is wrong. The user notices.
- Keep replies short, in plain language, starting with "Aviral".
