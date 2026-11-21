# Final code review before submission (21 Nov 2026)

A whole-project quality audit ("ponytail-audit") made before the NYAS Junior Academy submission.
**Rule for this review:** nothing that could change a simulation result was edited. Problems in
simulation code are reported here only.

## What the project is

A Python simulation of the Cue concept: the unmodified Lister et al. 2025 bladder model, run as a
spinal-cord-injury case, with a synthetic ultrasound patch, the device software, a simulated user,
a safety controller and a hypothetical stimulator. Expected load: one person running scripts on one
PC, so "scale" here means run time, not many users.

## What was read

All of `sci_test_rig.py`, `cue_model/`, `sensors/`, `devices/` (the monitor in part), `lut_upstream.py`,
the README, the handoff, `requirements.txt`, `pytest.ini` and the Stage 2 tests. Not read line by line:
the 29 experiment scripts, `evaluation/`, `config.py` and the other test files. The test suite and the
document-number check were run.

## Changes made (safe, no result can change)

| Change | Why |
|---|---|
| Deleted `demo/`, `experiments/demo_export_run.py` and the demo preview config; removed the demo from the README and handoff | Aviral decided there is no demo in the final submission. The demo held no result |
| `tests/test_stage2_upstream.py`: the "upstream is pinned and unmodified" test now **skips** when `third_party/lut-sim` has no `.git` folder | That copy has no `.git`, so the test always failed (known issue E88). It now says why it skipped. With a fresh clone (README step 1) it runs as before |
| `requirements.txt`: `pytest` pinned to `9.2.0` | Every other package was pinned; an unpinned pytest could break the tests later |

After the changes: **243 tests passed, 0 failed** (6 slow tests skipped as designed), and the
document-number check gives **1475 of 1475**.

## Findings (reported, NOT fixed, because they touch simulation code)

**Must fix:** none found. The control logic, sensors and metrics do what their docstrings say.

**Should fix (only if experiments are ever re-run):**

1. **A second press always lasts 0.5 s** (`devices/user_model.py`, `feel_alert`). The first press uses the
   scenario's `hold_s`, but the second press is fixed at 0.5 s. No result changes, because the
   controller only reacts to the moment the button goes down. Fix: use `sc.hold_s`.
2. **The rig reads a private field of the fusion object** (`sci_test_rig.py`, `on_step`, `self.fusion._paused`).
   It works, but if that name changes, sensor B would stop pausing during emptying without any error. Fix: a
   public `paused` property.
3. **The time arrays have a fixed length** (`sci_test_rig.py`, `CueRig.__init__`, `ceil(duration/dt) + 2`). If the
   upstream loop ever took more steps, the run would crash with an IndexError rather than give a wrong
   number, so it is safe, just fragile.

**Nice to have:**

4. `SensorFusion._disagreement` re-adds all stored readings on every reading (about 110 at the
   default settings). It is fast enough at this size.

**Verdict:** healthy for a research prototype. Nothing needs fixing before submission.
