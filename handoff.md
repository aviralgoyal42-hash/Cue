# Project Cue: handoff for the next agent

**Rewritten 2026-11-10 so the work can move to a new session.** Nothing is running and nothing is pending.

- **Source of truth:** the documents and result files in this folder. This handoff summarises them and says where to look.
- **If a number here disagrees with a result file:** trust the file and log the mismatch (see "Rules", item 7).
- **Earlier version:** the handoff as it stood on 8 Nov, including the full step-by-step notes from the 15-seed rerun, is kept unchanged in `docs/HANDOFF_ARCHIVE_2026-11-08.md`.

---

## 0. First steps for a new session

1. Read this file, then §5 of `VALIDATION_AND_LIMITATIONS.md` from E83 onward. §5 runs from E1 to **E126**, so **the next entry is E127**.
2. Check that no Python sweep is still running, read-only: `Get-Process python`. None was running on 10 Nov.
3. Start every reply with **"Aviral"**. Keep replies short and in plain language.
4. Don't start any new experiment until Aviral asks. Then follow the rules in section 3: freeze the plan first, and write to a new results folder.

---

## 1. Status at a glance

| Item | State |
|---|---|
| Stages 1–7, Experiments 1–6 | Done and reported |
| Task 1: provenance of the upstream mechanical constants | Done: `docs/MECHANICAL_CONSTANT_PROVENANCE.md` |
| Task 2: Experiment 3b, 15 seeds, POST-HOC and OPTIMISTIC | Done and approved: `docs/EXPERIMENT3B_RESULTS.md` |
| Task 3: Experiment 7, session cap and post-session check | Done and approved by the user: `docs/EXPERIMENT7_RESULTS.md` |
| Task 4: Experiments 3 and 4 with 15 seeds | Done 7–8 Nov: `docs/EXPERIMENT3_4_15SEED_RESULTS.md`, `results/task4/`, §5 E93–E99. The old seeds reproduce exactly, and no verdict changed |
| Emptying-duration and sphincter-timing check (read-only) | Done 7 Nov: `docs/EMPTYING_DURATION_CHECK.md`, `results/emptying_check/`, §5 E84–E88 |
| Figure audit (read-only) | Done 7 Nov: `docs/FIGURE_AUDIT.md`, `results/figure_audit/`, §5 E35 correction and E89–E92 |
| **Task 5: sphincter level during bursts** (model only, POST-HOC, OPTIMISTIC) | **Done 8 Nov:** `docs/TASK5_PLAN.md`, `results/task5/SUMMARY.md`, §5 E100–E103. The highest level that works is **0.1 in all 4 settings**. See section 6 |
| **Task 6: sphincter block, and misalignment monitor (Experiment 8)** | **Done 10 Nov** (new session, model Fable 5.2): `docs/TASK6_PLAN.md`, `results/task6/SUMMARY.md`, §5 E104–E110. See section 6b |
| **Task 7: correction that allows for bladder filling (Experiment 9, POST-HOC)** | **Done 10 Nov**, approved by Aviral with a held-out addition (plan §7): `docs/TASK7_PLAN.md`, `results/task7/SUMMARY.md`, §5 E111–E116. See section 6c |
| **Task 8: a second independent volume signal, "sensor B" (Experiment 10)** | **Done 11 Nov:** `docs/TASK8_PLAN.md`, `docs/TASK8_REFERENCE_NOTES.md`, `results/task8/SUMMARY.md`, §5 E117–E125. See section 6d |
| **3D replay demo** | **Removed 21 Nov** at Aviral's request (no demo in the final submission). `demo/`, `experiments/demo_export_run.py` and the preview config were deleted. It held no result, so nothing else changed |
| **Final code review** | **Done 21 Nov:** `docs/FINAL_REVIEW.md`, §5 E126. Next entry is E127. Tests: 243 passed, 0 failed |
| Now | **Nothing running.** Wait for Aviral's next request |

**Checks as of 11 Nov:**
- **Document number check:** 1475 of 1475 match (Task 6, 7 and 8 blocks were added).
- **Fast test suite:** 243 passed and 1 failed. The failure is the known E88 one: the upstream `.git` folder is missing.
- **Slow tests:** not rerun since 4 Nov.
- **Task 6 tests:** 24 of 24 pass (`tests/test_task6.py`). **Task 7 tests:** 11 of 11 pass (`tests/test_task7.py`). **Task 8 tests:** 22 of 22 pass (`tests/test_task8.py`).

---

## 2. What the project is

Cue is a high-school concept (NYAS Junior Academy, Brain Tech Challenge) for people with spinal cord injury who cannot sense or control their bladder:

1. An ultrasound patch estimates fullness.
2. A watch vibrates when the bladder is full.
3. The user decides when to empty by pressing a button. **The device never starts emptying on its own.**
4. The press starts a hypothetical implanted sacral nerve-root stimulator.
5. Safety cutoffs end stimulation.

This folder is a **simulation-only** framework built on the unmodified upstream lower-urinary-tract model by Lister et al. 2025 (*R Soc Open Sci* 12:242062, MIT licence), in `third_party/lut-sim`.
- Nothing here is hardware, and every result is a model prediction.
- The team must understand and defend every part, so code and docs use plain language and readable comments.

---

## 3. Rules the user set (all still in force)

These come from the user's messages across the project. Treat them as hard rules.

**How to work with the user**
1. **Address the user as "Aviral" at the start of every response.**
   - Earlier agents used "Sumit", taken from the Windows account. On 2026-11-07 the user said their name is Aviral.
   - The `C:\Users\Sumit\...` folder paths are unchanged and correct.
2. **Never start or suggest a session compaction** unless the user explicitly asks. The user was upset when automatic compaction lost context.
3. **Never shut down, restart or change the computer**, and take no action outside the project folder, unless the user explicitly asks in that message.
   - Keeping the computer awake through the app's keep-awake hold was approved for past sweeps. Ask again for a new one.
   - The user chose to **leave the screen on** during sweeps, because turning it off risks Modern Standby.
4. Ask the user when a decision is genuinely theirs, and never make assumptions silently. Aviral often answers "use defaults": list your defaults clearly so that answer is usable.
5. **Freeze success criteria in `docs/` before running anything.** Never change frozen criteria after seeing results. If one must change, log it in that document's change log and in §5, and say why.
6. **Never tune an ASSUMED value** to make the baseline or Cue look better. If something behaves oddly, report it as a result and show how it changes across a range. Every ASSUMED value appears in the table in §2 of `VALIDATION_AND_LIMITATIONS.md`, with what was tried and what changed.
7. **Log every error, surprise, failed expectation or negative result in §5.**
   - Record what happened, how it was found, what changed, and the effect on conclusions.
   - **Never remove an entry.** Add corrections or notes beneath it, such as the "E47 correction" or "E100 note" rows.
8. Keep old results. New experiments write to a new `results/` subfolder.
9. Label every value SOURCED or ASSUMED. Never invent values, citations or accuracy figures. Check units carefully and convert explicitly.
10. **Every document you create goes inside `project-cue/`** (in `docs/`, `results/<task>/` or the root). List it in the README "Where to read" table and in this handoff. If you find a doc that isn't listed, add it.

**Science and safety**

11. The device must **never read ground-truth volume**. Only evaluation code compares with truth. Tests enforce this.
12. Never use the upstream void switch. Any emptying must come from the model's mechanics.
13. Give no clinical stimulation parameters. Stimulator inputs are normalised model drives. Never claim that a real device reaches any model level.
14. Never claim clinical safety or effectiveness. Call the sensor a "synthetic experimental proxy", never "validated".
15. The 11% mean relative error (Toymus et al. 2024, *Nat Commun*, 5 healthy volunteers lying on their backs) is only a labelled best-case anchor.
16. Pressure is **not** a fullness indicator.
17. **Keep the concept away from the brain:** no brain interfaces and no brain-signal recording, in code or in text. Nothing is placed in the brain.
18. **Label POST-HOC and OPTIMISTIC results as such.** This covers Experiment 3b, the patterns without co-activation (`s0.0`) and Task 5. Results documents carry the sentence "Results are model predictions, not evidence for a device."

---

## 4. Environment and how to run

- **Windows 11**, 12 logical cores, 15.3 GB of RAM. Memory can run low when other apps are open.
  - The laptop uses **Modern Standby**, so it can stand by when the screen turns off (E100).
- **Project folder:** `C:\Users\Sumit\Downloads\Project Cue\project-cue`. The parent folder `Project Cue` holds only this folder.
- **Python environment:** `%USERPROFILE%\.venvs\project-cue` (Python 3.12.10, with numpy 2.3.1, scipy 1.15.2, pandas 2.2.3, matplotlib 3.10.0 and pytest). It sits outside the project on purpose.
  - PowerShell: `& "$env:USERPROFILE\.venvs\project-cue\Scripts\python.exe" ...`
- **Tests:**
  - Command: `& "$env:USERPROFILE\.venvs\project-cue\Scripts\python.exe" -m pytest -q -p no:cacheprovider -W ignore`
  - Set `$env:CUE_RUN_SLOW="1"` to include the slow tests.
  - Last full fast run (8 Nov): 186 passed and 1 failed (E88).
- **Document number check:** `python experiments/check_doc_numbers.py` recomputes every number quoted in the docs from the result files, and writes `results/doc_number_check.csv`.
  - It is at 1475 of 1475.
  - Run it last, after any doc change. Add a block whenever a new doc quotes numbers.
- **Upstream:** `third_party/lut-sim` is at commit `bd8f2a072ef017b99dc051b24972333141f7d257`.
  - When the app moved the project to this folder, it did not copy the `.git` subfolder, so `git status` no longer works there.
  - The 19 source files are present, and the code reproduces old results exactly.
  - The project itself is not a git repository.

**Long sweeps: staying awake (learned the hard way, E83 and E100)**
- **The app's keep-awake hold:** `request_keep_awake` with `until: "session_idle"` **lets go about 5 minutes after the session goes idle**. In Task 5, the laptop then stood by at 02:59 and the sweep stalled for six hours.
  - The sweep processes stayed alive but did no work after waking.
  - The stall shows as no new log line and 0 CPU for the Python processes.
- **The in-process backup doesn't prevent it.** `SetThreadExecutionState` with system-required only, which `task5_sphincter_levels.py` uses, does not stop Modern Standby once the screen turns off.
- **What worked:** a Monitor that prints a progress or heartbeat line at least every 4 minutes. That keeps the session active, so the hold stays on. Re-arm it when it expires (30 minutes at most).
- **If a sweep stalls:**
  1. Back up the partial files.
  2. Stop the task and its Python processes, with the user's OK.
  3. Keep the old log under a new name.
  4. Start the same command again. The task 4 and task 5 runners resume from their partial files.
- **Never delete partial files by hand, and never treat them as the full grid.**
- `time.perf_counter()` keeps counting while the computer sleeps, so `runtime_s` is wrong for any run that spans a sleep (E83).

**Windows pitfalls already hit**
- Long paths are limited to 260 characters (E38). Keep file names short.
- **Line endings:** project text files are CRLF.
  - Edits can mix line endings. To normalise, read the bytes and replace `\r\n` with `\n`, then `\n` with `\r\n`.
  - Check afterwards that no bare LF is left.
- **Log encoding is not fixed.** PowerShell `*>` wrote UTF-16 logs in earlier runs, but UTF-8 with a BOM in the Task 5 run. Check the first bytes before parsing a log with other tools.
- **PowerShell 5.1 mangles quotes in `python -c "..."`.** Write the script to a file in the scratchpad and run that.
- **Renaming over files:** the temp-write-then-rename save fails if another reader holds the file open without delete sharing. To read a file that is being written, open it with `FileShare` ReadWrite|Delete, or copy it that way first.
- Use `Out-String -Width 200` for wide tables. `Select-Object -First` on a Python pipe can kill Python (exit 255).
- **Comparing CSV files exactly:**
  - Read with `float_precision="round_trip"`, and compare file to file, never a file against values in memory (E58).
  - Compare by value, not storage type: `same_values()` in `experiments/task3_experiment7.py` and `experiments/task5_sphincter_levels.py` does this, because `DataFrame.equals` fails on 2 against 2.0 (E73).

---

## 5. Code map

```
config.py                 every parameter, labelled SOURCED or ASSUMED; config.validate() checks them
lut_upstream.py           imports the unmodified upstream model (its package name is `model`, so never create one)
sci_test_rig.py           closed-loop rig: physiology + sensor + device + user + controller + stimulator + pressure
cue_model/                sci_lut.py (SCI subclass of the upstream model), metrics.py (ground-truth metrics)
sensors/                  ultrasound_sensor.py (synthetic proxy), pressure_channel.py (synthetic implant channel),
                          second_sensor.py (Task 8 abstract sensor B, off by default)
devices/                  custom_tech_device.py (sees readings only), user_model.py, stimulator.py (optional sphincter block),
                          safety_controller.py (state machine), session_guard.py (Experiment 7 rule, off by default),
                          misalignment_monitor.py (Task 6, off by default), sensor_fusion.py (Task 8, off by default)
evaluation/               closed_loop_metrics.py, experiment2_metrics.py, guard_metrics.py; the only place truth meets device output
experiments/              one script per stage or experiment (see README.md "How to run")
results/                  stage2, stage3, stage4, stage4b, stage5, stage6, extra, task2, task3, task4, task5, emptying_check, figure_audit
tests/                    pytest suite, one file per stage or task
docs/                     frozen criteria, stage reports, results documents, handoff archive; docs/sources holds source extracts
```

**Key mechanics**
- **Upstream model:** a lumped lower urinary tract, forward Euler, time step 0.1 s. It is unstable at 0.4 s or more.
- **Device:**
  - The estimate is the median of the last 5 valid readings, with one reading per 60 s.
  - It confirms an alert after 3 readings and re-arms with 50 mL hysteresis.
  - It treats readings as stale after 600 s.
- **Safety controller states:** MONITORING, FULL_DETECTED, ALERT_SENT, WAITING_FOR_USER, STIMULATING, CUTOFF, LOCKOUT (1,800 s), and CATHETER_ONLY (with the session guard only).
  - Stimulation starts **only** on a button press in WAITING_FOR_USER.
  - There are three independent cutoffs: maximum duration (60 s), volume stop (100 mL, device estimate only), and pressure ceiling (55 cmH₂O on the synthetic channel).
- **Invariants A2, A3 and A4** are recomputed from raw logs in every experiment:
  - A2: sessions start only after an alert and a press.
  - A3: no session starts during lockout.
  - A4: every session ends within the maximum duration.
- **Runs and seeds:** each run is one simulated person for 12 h. One seed value sets the inflow, sensor, user and pressure-channel random streams together.
- **The stimulator's sphincter level (co-activation)** replaces the sphincter's input drive while a burst is ON. It is not added to it.
  - Between bursts, the drive returns to the reflex level: 0.5 at ×1.0 and 0.45 at ×0.9.
  - So 0.5 means no suppression at ×1.0 (E87, `docs/FIGURE_AUDIT.md` §1).
- **Storage pressure** reaches 55 cmH₂O at about 491 mL, peaks at 56.6 near 502 mL, then falls (E18, E92).

---

## 6. The last task: Task 5 (finished 8 Nov)

**The user's request (8 Nov, paraphrased):**
- Find how much sphincter suppression during bursts the model needs before emptying works. Model only.
- Use levels 0, 0.1, 0.2, 0.3, 0.4 and 0.5, fixed and ASSUMED.
- Run them on a small fixed subset of Experiment 3b working settings with 15 seeds, in one sweep.
- Use the same P1, P2 and P3 as Experiment 3. Check first that level 0 reproduces the old results and that level 0.5 empties nothing.
- Report the highest level that works, plus leftover volume and emptying time by level.

**How it ran**
- **Plan:** frozen in `docs/TASK5_PLAN.md`.
  - Subset: detrusor 0.6 and 1.0, 5 s on / 5 s off, ceiling 55, threshold 400 mL, maximum duration 60 s, sphincter ×1.0 and ×0.9.
  - 4 settings × 6 levels × 15 seeds = 360 runs. The six levels are one row in the §2 ASSUMED table. `config.py` is untouched.
- **Code:**
  - Runner: `experiments/task5_sphincter_levels.py`. `--check` runs Step 2; `--sweep` refuses to run unless Step 2 passed.
  - Scoring: `experiments/task5_analysis.py`.
  - Tests: `tests/test_task5_levels.py`, 11 passing.
- **Step 2 (24 runs):** passed. It matched Task 4 exactly, and no level-0.5 session voided 10% or more.
- **Sweep:** the first attempt stalled at run 150 when the laptop stood by (E100). It was restarted from the saved runs with the user's OK and finished at 09:39 on 8 Nov.
  - 360 runs, 2,612 sessions, 0 errors, and the invariants held in every run.
  - All 15 seeds at levels 0 and 0.5 match Task 4 exactly, so the restart changed nothing.

**Results (model predictions only, POST-HOC and OPTIMISTIC)**
- **The highest level that works is 0.1 in all 4 settings.** Levels 0.2–0.5 fail P1 everywhere.
  - The real boundary lies between 0.1 and 0.2 and is not resolved.
- **Leftover volume already rises at 0.1.** The median goes from 2 to 82–91 mL at detrusor 0.6, and from 62–68 to 116–121 mL at detrusor 1.0.
  - P1 at detrusor 1.0 is only 0.903 (E101).
- **Emptying time barely changes before it fails.** At detrusor 0.6 the median goes from 50 to 55 s, close to the 60 s maximum duration. At detrusor 1.0 it stays at 25 s.
- **Only P1 separates the levels (E102).**
  - P3 passes in every cell (peak 56.6 cmH₂O).
  - At ×1.0, the levels that don't empty pass P2 while the bladder fills to 940 mL without leaking.
  - At ×0.9, those levels fail P2.
- **Detrusor 1.0 at level 0.2 empties only partly (E103):** about a third of the bladder per session.

The full tables are in `results/task5/SUMMARY.md`.

---

## 6b. Task 6 (finished 10 Nov)

**The user's request (10 Nov, paraphrased):** have a way to block the sphincter so it relaxes during a burst; make misalignment less of a concern and have a way to flag it. The user said more requests will follow.

**What was built (both off by default, so old results are unchanged; `config.py` untouched)**
- **Sphincter block:** `BurstPattern.sphincter_block` (0–1), `block_scope` ("burst" or "session") and the fault `block_fails_at_s`, in `devices/stimulator.py`. The rig calls `stimulator.sphincter_input()`.
- **Misalignment monitor:** `devices/misalignment_monitor.py`, owned by `CustomTechDevice` when `misalignment_monitor={...}` is passed. Two rules (level drop against measured noise; rise in missing readings). The device raises `CHECK_PATCH` and divides its estimate by the measured ratio until `patch_reseated()`. The safety controller pauses the monitor around sessions.
- **Scripts:** `experiments/task6_block_check.py` (90 closed-loop runs) and `experiments/task6_experiment8.py` (open loop; `--rescore` scores saved runs). **Tests:** `tests/test_task6.py`.

**Results (model predictions only; Part A is POST-HOC and OPTIMISTIC)**
- **Block during bursts = Task 5.** 36 runs and 176 sessions match Task 5 exactly. So emptying needs at least an 80% block of the 0.5 co-activation.
- **Block failing 20 s in, detrusor 1.0: peak 73.8 cmH₂O**, the highest in the project (E108). 3 seeds.
- **Whole-session block empties more** than a burst-only block (E110). 3 seeds, a lead only.
- **Flag: M1 and M2 pass.** 150 of 150 on time at both strengths; false flags at most 2.0%.
- **Correction: 2 of 6 cells rescued** (350 mL only). It under-corrects: measured ratio 0.818 for a true 0.70 (E106).
- Weak spots: a 15% fall, and misalignment at 2 h (E107).

**Not done, and would each need a new frozen plan and Aviral's go-ahead**
- A 15-seed sweep of the whole-session block and of block faults.
- A correction that removes the filling between the two groups of readings. **Done as Task 7, see section 6c.**
- A simulated user who re-seats the patch when asked.
- No keep-awake hold was requested for Task 6: the runs took about 20 minutes while the session was active.

---

## 6c. Task 7 (finished 10 Nov, POST-HOC)

**The user's request (10 Nov):** approved `docs/TASK7_PLAN.md` with one addition: also test the new correction on gains 0.5 and 0.85, report them separately and labelled held-out, and freeze that criterion before running. Keep-awake was approved for the closed-loop probe. New log entries from E111.

**What was built:** `MisalignmentMonitor(fill_adjust=True)` fits a straight line to up to 75 readings from before the fall and measures the ratio against that line. Off by default. The flag rules are untouched. Script: `experiments/task7_experiment9.py` (`--check`, `--run`, `--rescore`, `--probe`). Tests: `tests/test_task7.py` (11).

**Results (model predictions, POST-HOC)**
- **Reproduction check passed:** with the option off, Experiment 8's target rows come back exactly (300 flag rows, 2,700 alert rows).
- **All criteria pass:** F1 (flags unchanged), M1 (0.993 / 1.000), M2 (highest 4.0%, less margin than before, E112), R1 (ratio 0.700 / 0.706 for a true 0.70), M4 (0 of 84 harmed).
- **4 of 6 cells rescued**, against 2 for the Task 6 correction. The 450 mL threshold still fails, narrowly (E114).
- **Held-out:** ×0.5 passes H1 and goes from 2 to 4 cells. ×0.85 passes H2 but stays at 3 cells, because most runs get no correction (E115).
- **Costs:** the ratio is scattered, about 1 corrected run in 6 is over-corrected, and false alerts appear; at a 2 h misalignment they pass the 5% limit (E113). A correction is sometimes applied when only readings go missing (E116).
- **Closed-loop probe (3 seeds):** earlier alerts and no session above 453 mL; one run alerted early (sessions at 360–369 mL).

**Scoring mistake to know about (E111):** the first scoring said F1 failed. The scoring code compared the wrong column. It was corrected to the plan's definition and the saved runs were rescored; the first output is kept.

---

## 6d. Task 8 (finished 11 Nov)

**The user's request (11 Nov, paraphrased):** how good, and how independent from the patch, must a second signal be to fix misalignment? Model it abstractly as "sensor B". Planned 3 hours, hard stop 3.5 hours, keep-awake approved, no questions, errors from E117. It took about 1 hour.

**What was built (all off by default; `config.py` untouched)**
- `sensors/second_sensor.py`: settings for an abstract sensor B, with an independence setting (0 = a patch shift does not touch B; 1 = common-mode).
- `devices/sensor_fusion.py`: one disagreement test on the ratio A ÷ B, and three rules: flag, trust B, average.
- The rig takes an optional `fusion` entry in its case (`None` = the old rig, exactly).
- `experiments/task8_experiment10.py` (`--check`, `--timing`, `--physiology`, `--sweep main|heldout`, `--score`, `--probe`). Tests: `tests/test_task8.py` (22).
- 20 fresh physiology traces (inflow seeds 101–110) are in `results/task8/heldout/physiology/`.

**Results (model predictions)**
- **By the frozen criteria no sensor B fixes misalignment:** the disagreement test fails the 5% false-flag limit at every B error (worst cell 76%, E118). The test is the problem, not the idea of a second sensor.
- **Underneath that, the requirement is one grid point:** "trust B" passes all 6 target cells and all 6 early cells only at B error 0.1117 with independence 0. B error 0.20 gives 0 cells; independence 0.25 gives 2 (E120). Common-mode equals no sensor B.
- **Averaging never fixes it** and harms working cells (E122). **If B is the sensor that moves, "trust B" breaks a working system** (E121).
- **Held-out seeds and gain ×0.6 repeat the shape.** Held-out gain ×0.8 is not fixed (E123).
- Small falls (×0.85, ×0.8) are still not caught.

**How to read a requirement table here:** `results/task8/exp10_requirement.csv` has one row per scenario, rule, B error and independence, with every criterion. `exp10_curve.csv` is the curve. `-1` in the grid columns means "no sensor B".

**Not done; each would need a new frozen plan and Aviral's go-ahead:** a better disagreement test (logarithm of the ratio, fewer looks, a delay-tolerant comparison), which would be post-hoc; combining the two-sensor test with the Task 6 monitor; B error between 0.1117 and 0.20 and independence between 0 and 0.25; a rule that decides which sensor to trust.

**Still open from earlier tasks, each needing a new frozen plan and Aviral's go-ahead:** the 450 mL threshold; small falls (×0.85); early misalignment; the "less proof after a dropout flag" rule (E116); a simulated user who re-seats the patch; a 15-seed sweep of the whole-session sphincter block and of block faults.

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
| Emptying-duration check | Median emptying episode 17 s, maximum 51 s. Flow stops within 1 s of stimulation stopping, so there is no voiding after stimulation (E84–E87) | `docs/EMPTYING_DURATION_CHECK.md` |
| Figure audit | Co-activation explained. Leftover volume in working Experiment 3 sessions is 0.0–199.5 mL (median 2.5), not "0–3 mL". Quoted figures checked (E35 correction, E89–E92) | `docs/FIGURE_AUDIT.md` |
| Task 4: Experiments 3 and 4 with 15 seeds | Seeds 42, 1, 2 reproduce exactly. No verdict changed: 38 of 104 still work, and the invariants held in all 3,180 runs. Peaks rose: 60.2 cmH₂O in Experiment 3 and 67.2 in the dead-pressure worst case (E97). The 3-seed Experiment 4 rates were poor estimates (E99) | `docs/EXPERIMENT3_4_15SEED_RESULTS.md` |
| Task 5: sphincter level during bursts (POST-HOC, OPTIMISTIC) | The highest level that works is 0.1 in all 4 settings. Leftover volume rises already at 0.1. Only P1 separates the levels (E100–E103) | `results/task5/SUMMARY.md` |
| Task 6: sphincter block; Experiment 8, misalignment monitor | The block reproduces Task 5 exactly. A block failing mid-session gave 73.8 cmH₂O. The flag passes M1 and M2; the correction rescues 2 of 6 cells (E104–E110) | `docs/TASK6_PLAN.md`, `results/task6/SUMMARY.md` |
| Task 7: Experiment 9, correction that allows for filling (POST-HOC) | Measured ratio 0.700 for a true 0.70. 4 of 6 cells rescued; 450 mL still fails. Held-out ×0.5 gains cells, ×0.85 does not. Costs: scatter and some false alerts (E111–E116) | `docs/TASK7_PLAN.md`, `results/task7/SUMMARY.md` |
| Task 8: Experiment 10, a second volume signal ("sensor B") | No sensor B is a fix by the frozen criteria (false flags). Underneath: only B error about 11% with full independence passes all cells. Common-mode equals no B (E117–E125) | `docs/TASK8_PLAN.md`, `results/task8/SUMMARY.md` |

---

## 8. Open items (only if the user asks)

- The full text of Bastiaanssen 1996, to confirm the species of the mechanical constants.
- Primary sources for the DFree and SENS-U figures, sacral anterior-root stimulation, and McGuire et al. 1981.
- P2 cannot see over-filling without a leak (E63, E102). A volume limit would need the user's decision.
- Continuous stimulation patterns remain unswept at 15 seeds in Experiment 3b. Task 4 covered them at 15 seeds for the original Experiment 3 grid only.
- Experiment 7: catheterisation is not modelled, there is no reset path out of CATHETER_ONLY, and whether to keep the session cap is an open decision (E78).
- Task 5 was run on a narrow subset only:
  - The boundary between levels 0.1 and 0.2 is not resolved.
  - Other ceilings, longer maximum durations and other burst timings are untested. Any new level would be a new frozen plan, not a change to Task 5.
- E88: the upstream `.git` folder is missing, so the pin test fails. It was left as is.
- A copy of an older state exists at `C:\cue_share`. The user said not to refresh it.

---

## 9. Etiquette that worked with this user

- Report negative results plainly and early. The user values honesty over a good-looking result.
- If something the user says doesn't match what you find, such as a wrong next error number, stop and say so before continuing.
- Show proposals and criteria before running anything when the user asks for approval first. Ask all questions up front, before a long run, with clear defaults.
- Give realistic time estimates, and say so when one is wrong. The user notices.
- Keep replies short, in plain language, starting with "Aviral".
