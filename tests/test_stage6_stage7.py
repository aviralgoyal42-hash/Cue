"""
Stage 6 and 7 tests: saved Experiment 3 and 4 results obey the safety rules, the worst-case
fault still ends at maximum duration, labels are complete, and the misalignment detector works.
Result-file tests are skipped when the experiments have not been run yet.
"""
import ast
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
from sensors import Reading  # noqa: E402
from devices import CustomTechDevice  # noqa: E402
from devices.custom_tech_device import POSSIBLE_MISALIGNMENT  # noqa: E402

STAGE6 = ROOT / "results" / "stage6"
INVARIANTS = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
has_results = pytest.mark.skipif(not (STAGE6 / "exp4_runs.csv").exists(), reason="run Stage 6 first")


@has_results
@pytest.mark.parametrize("name, n_runs", [("exp3_runs.csv", 312), ("exp4_runs.csv", 324)])
def test_every_saved_run_obeys_the_safety_rules(name, n_runs):
    runs = pd.read_csv(STAGE6 / name)
    assert len(runs) == n_runs and runs["error"].isna().all()
    assert runs[INVARIANTS].all().all()


@has_results
def test_sessions_never_exceed_max_duration():
    for name in ["exp3_sessions.csv", "exp4_sessions.csv"]:
        s = pd.read_csv(STAGE6 / name)
        assert (s["duration_s"] <= s["max_duration_s"] + 0.1 + 1e-6).all()


@has_results
def test_worst_case_fault_always_ends_at_max_duration():
    s = pd.read_csv(STAGE6 / "exp4_sessions.csv")
    worst = s[s["group"] == "combo:dead_pressure+stuck_high_estimate"]
    assert len(worst) and worst["cutoff"].eq("max_duration").all()


@has_results
def test_no_press_scenario_never_stimulates():
    r = pd.read_csv(STAGE6 / "exp4_runs.csv")
    assert (r[r["group"].isin(["user:no_press", "user:accidental_no_alert"])]["n_sessions"] == 0).all()


def test_every_parameter_section_is_labelled_sourced_or_assumed():
    rows = config.as_table()
    names = {r["name"] for r in rows}
    assert {"max_duration_s", "volume_stop_ml", "lockout_s", "median_window"} <= names
    assert all(r["status"] in (config.SOURCED, config.ASSUMED) for r in rows)


def test_stage5_modules_do_not_read_truth_directly():
    """The controller and user model take no physiology import; only the sensors see truth."""
    for name in ["safety_controller.py", "user_model.py", "stimulator.py"]:
        tree = ast.parse((ROOT / "devices" / name).read_text(encoding="utf8"))
        mods = {getattr(n, "module", None) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        mods |= {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not any(str(m).startswith(("cue_model", "lut_upstream", "model", "evaluation", "sensors")) for m in mods)


def feed(device, values):
    for i, v in enumerate(values):
        device.receive(Reading(60.0 * (i + 1), v))
    return [e.kind for e in device.events]


def test_misalignment_detector_is_off_by_default():
    device = CustomTechDevice(1000.0, median_window=1)
    assert POSSIBLE_MISALIGNMENT not in feed(device, [400, 400, 200, 200])


def test_misalignment_detector_flags_a_sudden_fall_once():
    device = CustomTechDevice(1000.0, median_window=1, misalignment_drop_fraction=0.25)
    kinds = feed(device, [400, 410, 420, 280, 280, 200])
    assert kinds.count(POSSIBLE_MISALIGNMENT) == 1


def test_misalignment_detector_ignores_a_steady_rise_and_low_volumes():
    device = CustomTechDevice(1000.0, median_window=1, misalignment_drop_fraction=0.25)
    assert feed(device, [100, 150, 200, 250, 300]) == []
    low = CustomTechDevice(1000.0, median_window=1, misalignment_drop_fraction=0.25)
    assert feed(low, [50, 20, 50, 20]) == []
