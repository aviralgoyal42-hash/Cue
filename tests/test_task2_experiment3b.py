"""
Experiment 3b: the grid must match the frozen criteria, and the saved results must be complete,
clean, and consistent with Experiment 3. Result checks skip if the results are not on disk.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import task2_experiment3b as t2  # noqa: E402

RESULTS = ROOT / "results" / "task2"
needs_results = pytest.mark.skipif(not (RESULTS / "exp3b_runs.csv").exists(), reason="results not on disk")


def test_grid_matches_the_frozen_criteria():
    cases = t2.cases()
    assert len(cases) == 1620
    assert len(t2.SEEDS) == 15 and len(set(t2.SEEDS)) == 15
    keys = {(c["stim_name"], c["controller"]["max_duration_s"], c["threshold_ml"],
             c["controller"]["pressure_ceiling_cmH2O"], c["sphincter_scaling"], c["phys_seed"]) for c in cases}
    assert len(keys) == 1620


def test_no_pattern_has_sphincter_coactivation_or_is_continuous():
    for name in t2.PATTERNS:
        assert "_s0.0_" in name and name.endswith("5on5off")


@needs_results
def test_consistency_check_passes_on_copies_and_catches_a_tiny_change(tmp_path, monkeypatch):
    """A check that once failed falsely (E58) must still fail when a number really differs."""
    for name in ["exp3b_runs.csv", "exp3b_sessions.csv"]:
        (tmp_path / name).write_bytes((RESULTS / name).read_bytes())
    monkeypatch.setattr(t2, "RESULTS", tmp_path)
    assert t2.check_against_exp3()["reproduces"] is True

    runs = pd.read_csv(tmp_path / "exp3b_runs.csv", float_precision="round_trip")
    pick = (runs.max_duration_s == 60) & (runs.threshold_ml == 400) & (runs.phys_seed == 42)
    runs.loc[runs[pick].index[0], "max_volume_ml"] += 1e-9
    runs.to_csv(tmp_path / "exp3b_runs.csv", index=False)
    assert t2.check_against_exp3()["reproduces"] is False


@needs_results
def test_saved_results_are_complete_and_clean():
    runs = pd.read_csv(RESULTS / "exp3b_runs.csv")
    summary = pd.read_csv(RESULTS / "exp3b_settings_summary.csv")
    assert len(runs) == 1620 and runs["error"].notna().sum() == 0     # the error column is empty (E59)
    assert len(summary) == 108 and (summary.n_runs == 15).all()
    assert summary["A2_A3_A4_all_hold"].all()


@needs_results
def test_shared_runs_reproduce_experiment_3_exactly():
    assert json.load(open(RESULTS / "exp3b_reproduces_exp3.json"))["reproduces"] is True


@needs_results
def test_full_loop_works_really_needs_all_three_criteria():
    s = pd.read_csv(RESULTS / "exp3b_settings_summary.csv")
    assert (s.full_loop_works == (s.P1_pass & s.P2_pass & s.P3_pass & s.A2_A3_A4_all_hold)).all()
