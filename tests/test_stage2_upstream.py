"""
Stage 2 tests: the upstream model is untouched, reproduces its own published
output, is deterministic with a fixed seed, and converts units the way we expect.

The full 1-day reproduction takes minutes, so it only runs when the environment
variable CUE_RUN_SLOW=1 is set. The quick tests run every time.
"""
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
from lut_upstream import load_upstream, UPSTREAM_DIR, UPSTREAM_COMMIT, M3_PER_ML, PA_PER_CMH2O  # noqa: E402
import stage2_reproduce_upstream as stage2  # noqa: E402

LUT_Model = load_upstream()


def run(max_time_s, dT=0.1, seed=42, **kwargs):
    return LUT_Model.LUT().process_neural_input(max_time_s, dT, seed=seed, **kwargs)


@pytest.mark.skipif(not (UPSTREAM_DIR / ".git").exists(),
                    reason="upstream copy has no .git folder, so its commit cannot be read (clone it as in README step 1)")
def test_upstream_clone_is_pinned_and_unmodified():
    head = subprocess.run(["git", "-C", str(UPSTREAM_DIR), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    changes = subprocess.run(["git", "-C", str(UPSTREAM_DIR), "status", "--porcelain"],
                             capture_output=True, text=True, check=True).stdout.strip()
    assert head == UPSTREAM_COMMIT
    assert changes == "", f"upstream files were modified:\n{changes}"


def test_first_rows_match_saved_notebook_output():
    data = run(0.5, V_unit="ml", p_unit="cmH2O")  # 5 steps: t = 0.0 ... 0.4 s
    diff = stage2.compare_rows(data, stage2.EXPECTED_HEAD, "head")
    assert diff[stage2.COLUMNS].to_numpy().max() <= stage2.PRINT_TOLERANCE


def test_same_seed_gives_identical_runs():
    a = run(600, seed=7)
    b = run(600, seed=7)
    pd.testing.assert_frame_equal(a, b)


def test_different_seed_changes_inflow_noise():
    a = run(600, seed=1)
    b = run(600, seed=2)
    assert not np.allclose(a["Q_in"], b["Q_in"])


def test_unit_conversion_matches_explicit_factors():
    si = run(120, seed=3)
    clinical = run(120, seed=3, V_unit="ml", p_unit="cmH2O")
    np.testing.assert_allclose(clinical["V_B"], si["V_B"] / M3_PER_ML, rtol=1e-12)
    np.testing.assert_allclose(clinical["Q_in"], si["Q_in"] / M3_PER_ML, rtol=1e-12)
    np.testing.assert_allclose(clinical["p_D"], si["p_D"] / PA_PER_CMH2O, rtol=1e-9)
    np.testing.assert_allclose(clinical["p_S"], si["p_S"] / PA_PER_CMH2O, rtol=1e-9)


def test_misspelt_unit_strings_are_silently_ignored_by_upstream():
    """Documents an upstream pitfall: 'mL' and 'cmh2o' leave values in m^3 and Pa.
    Project Cue therefore always runs in SI and converts with its own factors."""
    si = run(60, seed=3)
    misspelt = run(60, seed=3, V_unit="mL", p_unit="cmh2o")
    pd.testing.assert_frame_equal(si, misspelt)


def test_default_time_step_is_numerically_stable():
    data = run(600, dT=0.1, seed=1)
    assert np.isfinite(data.to_numpy(dtype=float)).all()
    assert data["f_aS_s"].between(0, 1).all() and data["f_aD_s"].between(0, 1).all()


def test_time_step_at_or_above_0p4_s_is_unstable():
    """Forward Euler with tau_S = 0.2 s diverges when dT > 2*tau_S. The Cue config
    must therefore refuse dT >= 0.4 s (and we use dT <= 0.2 s to avoid overshoot)."""
    with np.errstate(all="ignore"):
        data = run(600, dT=0.5, seed=1)
    assert np.nanmax(np.abs(data["f_aS_s"])) > 1e6


@pytest.mark.skipif(os.environ.get("CUE_RUN_SLOW") != "1", reason="slow (1 simulated day); set CUE_RUN_SLOW=1")
def test_full_day_matches_saved_notebook_output():
    data, _ = stage2.run_upstream(days=1)
    for expected, label in [(stage2.EXPECTED_HEAD, "head"), (stage2.EXPECTED_TAIL, "tail")]:
        diff = stage2.compare_rows(data, expected, label)
        assert diff[stage2.COLUMNS].to_numpy().max() <= stage2.PRINT_TOLERANCE
