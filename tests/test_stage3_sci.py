"""
Stage 3 tests: the SCI subclass changes only what it claims to change.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from lut_upstream import load_upstream, M3_PER_ML  # noqa: E402
from cue_model import CueLUT, simulate  # noqa: E402
from cue_model.metrics import leak_episodes, clipped_volume_ml, run_summary  # noqa: E402

LUT_Model = load_upstream()
SI_COLUMNS = ["t", "V_B", "f_aD_s", "f_aS_s", "r_U", "Q", "p_D", "p_S", "Q_in", "w_e_s", "w_i_s", "w_s_s", "voiding"]
NEAR_FULL_ML = 480.0   # start here so a healthy void happens within minutes


def upstream_run(initial_ml, seconds, seed=5):
    lut = LUT_Model.LUT()
    lut.V_B = initial_ml * M3_PER_ML
    return lut.process_neural_input(seconds, 0.1, seed=seed)


def test_initial_volume_is_converted_from_ml():
    assert CueLUT(initial_volume_ml=100.0).V_B == pytest.approx(1e-4)


def test_without_sci_and_at_500ml_ceiling_cue_model_equals_upstream_exactly():
    """Regression: the subclass is a no-op when SCI is off (includes a full void)."""
    expected = upstream_run(NEAR_FULL_ML, 1800)
    assert expected["voiding"].max() == 1, "test window must contain a void"
    model = CueLUT(sci_enabled=False, volume_ceiling_ml=500.0, initial_volume_ml=NEAR_FULL_ML)
    actual = model.process_neural_input(1800, 0.1, seed=5)
    pd.testing.assert_frame_equal(actual[SI_COLUMNS], expected[SI_COLUMNS], check_exact=True)


def test_sci_never_starts_a_void():
    model = CueLUT(sci_enabled=True, volume_ceiling_ml=1000.0, initial_volume_ml=NEAR_FULL_ML)
    data = simulate(model, 3600, 0.1, 5, 1.0)
    assert data["voiding"].max() == 0
    assert data["V_B_ml"].iloc[-1] > NEAR_FULL_ML      # filling continues


def test_neural_drive_uses_500ml_reference_not_the_ceiling():
    model = CueLUT(sci_enabled=True, volume_ceiling_ml=1000.0)
    model.V_B = 300 * M3_PER_ML
    reference = LUT_Model.LUT()
    reference.V_B = 300 * M3_PER_ML
    assert model.update_parasympathetic_input() == reference.update_parasympathetic_input()
    assert model.update_sympathetic_input() == reference.update_sympathetic_input()
    assert model.bladder_args["max_V_B"] == pytest.approx(1000 * M3_PER_ML)   # ceiling restored


def test_hold_freezes_drive_above_500ml_and_extrapolate_does_not():
    def drive(rule, volume_ml):
        m = CueLUT(volume_ceiling_ml=1000.0, drive_above_reference=rule)
        m.V_B = volume_ml * M3_PER_ML
        return m.update_parasympathetic_input(), m.update_sympathetic_input()
    assert drive("hold", 700.0) == drive("hold", 500.0)
    assert drive("extrapolate", 700.0) != drive("extrapolate", 500.0)
    with pytest.raises(ValueError):
        CueLUT(drive_above_reference="something else")


def test_volume_never_exceeds_ceiling_and_clip_is_measured():
    model = CueLUT(sci_enabled=True, volume_ceiling_ml=500.0, initial_volume_ml=495.0)
    data = simulate(model, 1800, 0.1, 5, 1.0)
    assert data["V_B_ml"].max() <= 500.0 + 1e-9
    clipped = clipped_volume_ml(data, 0.1, 495.0)
    produced_after_full = data["Q_in_ml_s"].sum() * 0.1 - (500.0 - 495.0)
    assert clipped.sum() == pytest.approx(produced_after_full, rel=1e-6)   # discarded inflow is accounted for


def test_no_clip_below_the_ceiling():
    data = simulate(CueLUT(sci_enabled=True, volume_ceiling_ml=1000.0), 3600, 0.1, 5, 1.0)
    assert np.abs(clipped_volume_ml(data, 0.1)).max() < 1e-9


def test_overrides_apply_and_unknown_keys_are_rejected():
    assert CueLUT(overrides={"neural_args.somatic_a": 0.4}).neural_args["somatic_a"] == 0.4
    with pytest.raises(KeyError):
        CueLUT(overrides={"neural_args.not_a_parameter": 1.0})


def test_leak_episode_detection_on_a_synthetic_trace():
    q = np.zeros(20)
    q[5:8] = 2.0      # 3 steps of 2 mL/s while not voiding -> one leak of 0.6 mL at dt 0.1 s
    data = pd.DataFrame({"t": np.arange(20) * 0.1, "Q": q * M3_PER_ML, "Q_ml_s": q, "voiding": 0,
                         "V_B_ml": 100.0, "p_D_cmH2O": 50.0})
    leaks = leak_episodes(data, 0.1)
    assert len(leaks) == 1
    assert leaks["leaked_ml"].iloc[0] == pytest.approx(0.6)


def test_healthy_void_is_not_counted_as_a_leak():
    model = CueLUT(sci_enabled=False, volume_ceiling_ml=500.0, initial_volume_ml=NEAR_FULL_ML)
    data = simulate(model, 1800, 0.1, 5, 1.0)
    summary = run_summary(data, 0.1, NEAR_FULL_ML, 500.0)
    assert summary["n_voluntary_voids"] == 1 and summary["n_leak_episodes"] == 0


def test_config_rejects_unstable_or_unimplemented_settings(monkeypatch):
    config.validate()   # the shipped configuration is valid
    monkeypatch.setitem(config.SIMULATION, "dt_s", config.Param(0.5, "s", config.ASSUMED, "test"))
    with pytest.raises(ValueError):
        config.validate()
    monkeypatch.setitem(config.SIMULATION, "dt_s", config.Param(0.1, "s", config.SOURCED, "test"))
    monkeypatch.setitem(config.SCI, "injury_level", config.Param("sacral", "-", config.ASSUMED, "test"))
    with pytest.raises(NotImplementedError):
        config.validate()


def test_every_config_parameter_is_labelled():
    for row in config.as_table():
        assert row["status"] in (config.SOURCED, config.ASSUMED)
        assert row["source"].strip()
