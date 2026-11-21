"""
Stage 4 tests: synthetic sensor, CustomTechDevice (never sees truth) and Experiment 2 scoring.
"""
import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
from sensors import (Reading, SensorScenario, SyntheticUltrasoundSensor, ValidatedUltrasoundModel,  # noqa: E402
                     RealUltrasoundDevice, SENSOR_KIND)
from devices import CustomTechDevice, ALERT, ALERT_CLEARED, SENSOR_STALE, SENSOR_OK  # noqa: E402
from evaluation import experiment2_metrics as ev  # noqa: E402


def constant(v):
    return lambda t: v


def readings(scenario, n=4000, volume=400.0, seed=1, interval=60.0):
    sensor = SyntheticUltrasoundSensor(scenario, seed)
    return [sensor.read(i * interval, constant(volume)) for i in range(1, n + 1)]


# ------------------------------------------------------------------ sensor
def test_sensor_is_labelled_a_synthetic_proxy_and_others_do_not_exist():
    assert "synthetic" in SENSOR_KIND and "not validated" in SENSOR_KIND
    with pytest.raises(NotImplementedError):
        ValidatedUltrasoundModel()
    with pytest.raises(NotImplementedError):
        RealUltrasoundDevice()


def test_ideal_sensor_returns_truth():
    assert all(r.volume_ml == 400.0 for r in readings(SensorScenario(), n=50))


def test_mean_relative_error_matches_target():
    for target in [0.1117, 0.30]:
        rs = readings(SensorScenario(mean_relative_error=target), n=20000)
        mre = np.mean([abs(r.volume_ml - 400.0) / 400.0 for r in rs])
        assert mre == pytest.approx(target, rel=0.05)


def test_same_seed_same_readings_and_seed_changes_them():
    sc = SensorScenario(mean_relative_error=0.2, missing_probability=0.3)
    assert readings(sc, n=200, seed=3) == readings(sc, n=200, seed=3)
    assert readings(sc, n=200, seed=3) != readings(sc, n=200, seed=4)


def test_sensor_does_not_touch_numpys_global_random_state():
    np.random.seed(123)
    before = np.random.get_state()[1].copy()
    readings(SensorScenario(mean_relative_error=0.3, missing_probability=0.2), n=100)
    assert np.array_equal(np.random.get_state()[1], before)


def test_missing_probability():
    rs = readings(SensorScenario(missing_probability=0.5), n=20000)
    assert np.mean([not r.valid for r in rs]) == pytest.approx(0.5, abs=0.02)


def test_gain_drift_delay_and_misalignment():
    ramp = lambda t: t / 60.0     # noqa: E731  (1 mL per minute)
    assert SyntheticUltrasoundSensor(SensorScenario(gain_error=-0.2), 0).read(600, ramp).volume_ml == pytest.approx(8.0)
    drift = SyntheticUltrasoundSensor(SensorScenario(drift_per_hour=0.02), 0).read(3600 * 5, constant(100.0))
    assert drift.volume_ml == pytest.approx(110.0)
    assert SyntheticUltrasoundSensor(SensorScenario(delay_s=300), 0).read(900, ramp).volume_ml == pytest.approx(10.0)
    mis = SensorScenario(misalignment_start_h=1.0, misalignment_gain=0.7)
    s = SyntheticUltrasoundSensor(mis, 0)
    assert s.read(1800, constant(100.0)).volume_ml == pytest.approx(100.0)
    assert s.read(7200, constant(100.0)).volume_ml == pytest.approx(70.0)


def test_readings_are_never_negative():
    rs = readings(SensorScenario(mean_relative_error=0.4), n=5000, volume=5.0)
    assert min(r.volume_ml for r in rs) >= 0.0


def test_all_configured_scenarios_build():
    for name, values in config.SENSOR_SCENARIOS.value.items():
        SensorScenario.from_dict(name, values)


# ------------------------------------------------------------------ device
def test_device_module_never_references_ground_truth():
    """The device file may not import the physiology, the sensor's truth input or the
    evaluation code, and no identifier in its code (docstrings excluded) may refer to truth."""
    tree = ast.parse((ROOT / "devices" / "custom_tech_device.py").read_text())
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    modules = {a.name for n in imports for a in n.names} | {getattr(n, "module", None) for n in imports}
    assert not any(str(m).startswith(("cue_model", "lut_upstream", "model", "evaluation", "sensors"))
                   for m in modules)
    identifiers = {getattr(n, "id", None) or getattr(n, "attr", None) or getattr(n, "arg", None)
                   for n in ast.walk(tree) if isinstance(n, (ast.Name, ast.Attribute, ast.arg))}
    identifiers.discard(None)
    for name in identifiers:
        assert not any(bad in name.lower() for bad in ["v_b", "p_d", "true", "truth", "ground"]), name


def test_device_api_accepts_only_readings():
    device = CustomTechDevice(400.0)
    with pytest.raises(AttributeError):
        device.receive(400.0)          # a bare number (e.g. a true volume) is not a Reading


def feed(device, values, start=60.0, step=60.0):
    for i, v in enumerate(values):
        device.receive(Reading(start + i * step, v))
    return [e.kind for e in device.events]


def test_alert_needs_confirm_n_consecutive_estimates_and_fires_once():
    device = CustomTechDevice(400.0, median_window=1, confirm_n=3)
    kinds = feed(device, [390, 410, 420, 380, 410, 420, 430, 440, 450])
    assert kinds == [ALERT]
    assert device.alert_times() == [60.0 + 6 * 60.0]


def test_alert_rearms_only_after_hysteresis():
    device = CustomTechDevice(400.0, median_window=1, confirm_n=1, rearm_hysteresis_ml=50)
    kinds = feed(device, [410, 370, 410, 340, 410])
    assert kinds == [ALERT, ALERT_CLEARED, ALERT]


def test_median_ignores_a_single_spike():
    device = CustomTechDevice(400.0, median_window=5, confirm_n=1)
    assert feed(device, [100, 100, 900, 100, 100]) == []


def test_missing_readings_do_not_count_towards_confirmation():
    device = CustomTechDevice(400.0, median_window=1, confirm_n=3)
    assert feed(device, [410, None, 410, None]) == []
    assert feed(device, [410]) == [ALERT]


def test_device_flags_when_it_is_blind_and_when_readings_return():
    device = CustomTechDevice(400.0, stale_timeout_s=600)
    kinds = feed(device, [100] + [None] * 12 + [100])
    assert kinds == [SENSOR_STALE, SENSOR_OK]


# ------------------------------------------------------------------ evaluation
def test_alert_classification():
    true_at = lambda t: t / 60.0       # noqa: E731  volume in mL = minutes elapsed
    useful = ev.classify_alerts([400 * 60.0], true_at, t_adverse_s=500 * 60.0, false_below_ml=300)
    assert useful["useful"] and useful["lead_time_min"] == pytest.approx(100)
    false_then_useful = ev.classify_alerts([100 * 60.0, 450 * 60.0], true_at, 500 * 60.0, 300)
    assert false_then_useful["any_false_alert"] and false_then_useful["useful"]
    late = ev.classify_alerts([520 * 60.0], true_at, 500 * 60.0, 300)
    assert late["late"] and not late["useful"]
    assert ev.classify_alerts([], true_at, 500 * 60.0, 300)["missed"]


def test_adverse_event_is_the_earlier_of_leak_and_reference_volume():
    t = np.arange(0, 1000.0)
    truth = pd.DataFrame({"t": t, "V_B_ml": t, "Q_ml_s": np.where(t >= 300, 0.05, 0.0), "voiding": 0})
    assert ev.adverse_event(truth, 500.0) == (300.0, "leak_onset")
    truth["Q_ml_s"] = 0.0
    assert ev.adverse_event(truth, 500.0) == (500.0, "reached_V_ref")


def test_sensor_error_metrics_on_known_errors():
    rs = [Reading(60.0, 110.0), Reading(120.0, 90.0), Reading(180.0, None)]
    stats = ev.sensor_errors(rs, constant(100.0), floor_ml=50)
    assert stats["mae_ml"] == pytest.approx(10.0) and stats["rmse_ml"] == pytest.approx(10.0)
    assert stats["mean_relative_error"] == pytest.approx(0.1) and stats["missing_fraction"] == pytest.approx(1 / 3)


def test_stale_detection_counts_every_long_gap():
    rs = [Reading(60.0 * i, None if 2 <= i <= 14 else 100.0) for i in range(1, 30)]
    device = CustomTechDevice(400.0, stale_timeout_s=600)
    for r in rs:
        device.receive(r)
    assert ev.stale_detection(rs, device.events, 600) == (1, 1)
