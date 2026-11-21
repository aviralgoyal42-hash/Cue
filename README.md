# Project Cue: simulation and testing framework

Cue is a student concept for people with spinal cord injury (SCI) who cannot sense or control their bladder:
1. An ultrasound patch estimates fullness.
2. A watch vibrates when the bladder is full.
3. The user decides when to empty by pressing a button. The device never starts emptying on its own.
4. The button press starts a hypothetical implanted sacral nerve-root stimulator.
5. A safety cutoff ends stimulation.

This repository is an early-stage research prototype for education and the NYAS Junior Academy Brain Tech Challenge. **Nothing here is hardware, and nothing here shows clinical safety or effectiveness.** All results are model predictions. The sensor is a synthetic experimental proxy, and the stimulator is hypothetical.

**This project treats errors, failures and negative results as data and reports them openly in `VALIDATION_AND_LIMITATIONS.md` §5.**

Physiology comes from the open-source lower-urinary-tract simulator by Lister et al. 2025 (*R Soc Open Sci* 12:242062, doi:10.1098/rsos.242062, MIT licence), used unmodified from `third_party/lut-sim`.

## Reproduce everything from scratch

You need Windows, macOS or Linux, Python 3.11–3.13 (tested with 3.12.10) and git. On Windows, keep the project in a short folder path, because long paths are limited to 260 characters by default.

**1. Get the upstream model at the exact commit used:**
```bash
git clone https://github.com/MoveR-Digital-Health-and-Care-Hub/lower-urinary-tract-sim.git third_party/lut-sim
git -C third_party/lut-sim checkout bd8f2a072ef017b99dc051b24972333141f7d257
```
Skip this step if `third_party/lut-sim` is already present.

**2. Create an environment and install the packages:**
```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
```
On macOS or Linux, the activate line is `source .venv/bin/activate`.

**3. Run the tests:**
```bash
python -m pytest
```
Set the environment variable `CUE_RUN_SLOW=1` to include the full-day reproduction test.

**4. Run the experiments, in this order.** Times are for a 12-core PC.

| Step | Command | Time | Output |
|---|---|---|---|
| Stage 2: reproduce upstream | `python experiments/stage2_reproduce_upstream.py --baseline5d` | 5 min | `results/stage2/` |
| Stage 2: diagnostics | `python experiments/stage2_upstream_diagnostics.py` | 5 min | console |
| Stage 3: Experiment 1, SCI baseline | `python experiments/stage3_sci_baseline.py` | 15 min | `results/stage3/` |
| Stage 4: Experiment 2 | `python experiments/stage4_experiment2.py` | 10 min | `results/stage4/` |
| Stage 4: Experiment 2b (15 seeds) | `python experiments/stage4_experiment2.py --physiology-seeds 15 --out stage4b` | 40 min | `results/stage4b/` |
| Stage 4: comparison | `python experiments/stage4b_compare.py` | 1 min | `results/stage4b/` |
| Check quoted numbers (run last) | `python experiments/check_doc_numbers.py` | 1 min | `results/doc_number_check.csv` |
| Stage 5: stimulation map and A1 check | `python experiments/stage5_stimulation_map.py` | 5 min | `results/stage5/` |
| Stage 6: Experiments 3 and 4 | `python experiments/stage6_experiments3_4.py` | 1–2 h | `results/stage6/` |
| Stage 6: comparison table | `python experiments/stage6_comparison_table.py` | 1 min | `results/stage6/` |
| Extra: Experiments 5 and 6 | `python experiments/extra_experiments5_6.py` | 15 min | `results/extra/` |
| Task 2: Experiment 3b (POST-HOC, OPTIMISTIC) | `python experiments/task2_experiment3b.py` | 2.5 h | `results/task2/` |
| Task 2: analysis of saved results | `python experiments/task2_analysis.py` | 1 min | `results/task2/` |
| Task 2: pressure-spike diagnostic | `python experiments/task2_overshoot_diagnostic.py` | 3 min | `results/task2/` |
| Task 2: recount of working settings | `python experiments/task2_recount.py` | 1 min | `results/task2/` |
| Task 3: Experiment 7 | `python experiments/task3_experiment7.py` | 3.8 h | `results/task3/` |
| Task 3: scoring of saved results | `python experiments/task3_analysis.py` | 1 min | `results/task3/` |
| Emptying duration and sphincter timing (read-only, saved traces) | `python experiments/emptying_duration_check.py` | 1 min | `results/emptying_check/` |
| Figure audit (read-only, saved results) | `python experiments/figure_audit.py` | 2 min | `results/figure_audit/` |
| Final: Experiments 3 and 4 with 15 seeds | `python experiments/task4_rerun_exp3_4.py` | about 8.7 h awake | `results/task4/` |
| Final: old against new comparison | `python experiments/task4_analysis.py` | 1 min | `results/task4/` |
| Task 5: sphincter level during bursts (POST-HOC, OPTIMISTIC) | `python experiments/task5_sphincter_levels.py --check`, then `--sweep` | 4 min, then about 35–60 min awake | `results/task5/` |
| Task 5: scoring of saved results | `python experiments/task5_analysis.py` | 1 min | `results/task5/` |
| Task 6: sphincter block check and probes (POST-HOC, OPTIMISTIC) | `python experiments/task6_block_check.py` | about 20 min | `results/task6/` |
| Task 6: Experiment 8, misalignment monitor | `python experiments/task6_experiment8.py` (add `--rescore` to score saved runs only) | 5 min | `results/task6/` |
| Task 7: Experiment 9, correction that allows for filling (POST-HOC) | `python experiments/task7_experiment9.py --check`, then `--run`, then `--probe` (`--rescore` scores saved runs only) | 2 min, 3 min, 5 min | `results/task7/` |
| Task 8: Experiment 10, a second volume signal and fusion rules | `python experiments/task8_experiment10.py --check`, `--timing`, `--physiology`, `--sweep main`, `--sweep heldout`, `--score`, `--probe` (in this order; sweeps resume from their job files) | 2, 1, 5, 27, 8, 1 and 4 min | `results/task8/` |

All random seeds are fixed, so reruns give the same numbers on the same package versions. Run a single closed-loop person with `python sci_test_rig.py`.

**Large raw outputs are not in the GitHub copy.** 77 raw output files over 3 MB each (listed in `.gitignore`) are left out to keep the repository small. Running the step in the table above rebuilds each one. Every summary, and every file that `check_doc_numbers.py` reads, is included, so the tests and the number check pass on a fresh copy.

## Where to read

| Document | Content |
|---|---|
| `docs/OVERNIGHT_REPORT.md` | Summary of Stages 5–7, decisions, failures, top findings |
| `VALIDATION_AND_LIMITATIONS.md` | Component table, every ASSUMED value and what was tried, predictions vs facts, errors log |
| `docs/STAGE1_REPOSITORY_REVIEW.md` | Audit of the upstream code and science |
| `docs/STAGE2_REPRODUCTION.md` | Exact reproduction of upstream, time-step limit |
| `docs/STAGE3_SCI_BASELINE.md` | SCI condition and Experiment 1 |
| `docs/EXPERIMENT2_SUCCESS_CRITERIA.md`, `docs/STAGE4_EXPERIMENT2.md`, `docs/EXPERIMENT2B_RERUN_CRITERIA.md`, `docs/STAGE4B_EXPERIMENT2_RERUN.md` | Sensor, device and alert experiments |
| `docs/STAGE5_EXPERIMENT3_4_CRITERIA.md`, `docs/STAGE5_TRIGGER_STIMULATION_SAFETY.md`, `docs/STAGE6_EXPERIMENTS3_4.md` | User trigger, stimulation, safety controller, full loop, faults |
| `docs/EXPERIMENT3B_CRITERIA.md`, `docs/EXPERIMENT3B_RESULTS.md` | POST-HOC, OPTIMISTIC sweep of duration, threshold and ceiling on patterns that empty |
| `docs/EXPERIMENT5_6_CRITERIA.md`, `docs/EXPERIMENT5_6_RESULTS.md` | Device parameters and misalignment detector |
| `docs/EXPERIMENT7_CRITERIA.md`, `docs/EXPERIMENT7_RESULTS.md` | Session cap and post-session check, before and after |
| `docs/EMPTYING_DURATION_CHECK.md` | How long each emptying episode lasts, and why the model shows no post-stimulus voiding |
| `docs/FIGURE_AUDIT.md` | Co-activation as implemented, leftover volume, quoted headline figures, pressure against volume |
| `docs/EXPERIMENT3_4_15SEED_PLAN.md`, `docs/EXPERIMENT3_4_15SEED_RESULTS.md` | Final experiment: Experiments 3 and 4 with 15 seeds. Old seeds reproduce exactly and no verdict changed |
| `docs/TASK5_PLAN.md`, `results/task5/SUMMARY.md` | Task 5: how much sphincter suppression during bursts the model needs before emptying works. The highest level that works is 0.1 in all 4 settings. Model predictions only |
| `docs/TASK6_PLAN.md`, `results/task6/SUMMARY.md` | Task 6: a sphincter block during bursts, and a misalignment monitor with correction (Experiment 8). The block reproduces Task 5 exactly; the flag passes M1 and M2; the correction rescues 2 of 6 cells. Model predictions only |
| `docs/TASK7_PLAN.md`, `results/task7/SUMMARY.md` | Task 7 (Experiment 9, POST-HOC): a misalignment correction that allows for bladder filling. Measured ratio 0.700 for a true 0.70; rescues 4 of 6 cells against 2; held-out gains ×0.5 and ×0.85 reported separately. Model predictions only |
| `docs/TASK8_PLAN.md`, `results/task8/SUMMARY.md` | Task 8 (Experiment 10): an abstract second volume signal ("sensor B") and three fusion rules. By the frozen criteria no sensor B fixes misalignment (too many false flags). Underneath, all target cells pass only with B error about 11% and full independence from the patch. Model predictions only |
| `docs/TASK8_REFERENCE_NOTES.md` | Task 8 background reading on near-infrared, implanted and bioimpedance bladder sensing. Reference only, from summaries, not used to set any value |
| `docs/FINAL_REVIEW.md` | Final code review before submission (21 Nov): what was checked, the safe changes made, and small issues reported but not fixed |
| `docs/MECHANICAL_CONSTANT_PROVENANCE.md` | Task 1: where the upstream mechanical constants come from |
| `handoff.md` | Handoff for another agent: rules, environment, code map, history. Rewritten 2026-11-10 for a new session |
| `docs/HANDOFF_ARCHIVE_2026-11-08.md` | The handoff as it stood on 8 Nov, kept unchanged (includes the full 15-seed rerun steps) |

## Layout

```
config.py            every parameter, labelled SOURCED or ASSUMED
lut_upstream.py      imports the unmodified upstream model (package name `model`)
sci_test_rig.py      the closed-loop rig: physiology + sensors + device + user + controller + stimulator
cue_model/           SCI subclass of the upstream model, ground-truth metrics
sensors/             synthetic ultrasound proxy, synthetic implant pressure channel, abstract sensor B (optional)
devices/             CustomTechDevice (sees readings only), user model, stimulator (with optional sphincter block),
                     safety controller, misalignment monitor (optional), two-sensor fusion (optional)
evaluation/          scoring against ground truth (the only place truth meets device output)
experiments/         one script per stage or experiment
results/             CSV and PNG outputs
tests/               pytest suite
docs/                stage reports and frozen success criteria
third_party/lut-sim  unmodified upstream clone (MIT licence)
```

Our code must not create a package called `model`, because the upstream package already uses that name.

## Rules this project follows

- Success criteria are written in `docs/` before each experiment, and changes are logged.
- ASSUMED values are swept or listed, never tuned to make Cue look better.
- The device never reads true volume. Only the evaluation code compares with ground truth.
- The upstream void switch is never used by Cue. Any emptying has to come out of the model's mechanics.
- No clinical stimulation parameters are given. Stimulator inputs are normalised model drives.

## Citations

Please cite the upstream work if you reuse it: Lister E, McConnell-Trevillion A, Jabbari M, Erfanian A, Nazarpour K. An open-source neurodynamic model of the lower urinary tract. *R Soc Open Sci* 2025;12(10):242062. Software: Zenodo 10.5281/zenodo.16961553. The upstream licence (MIT) is in `third_party/lut-sim/LICENSE`.
