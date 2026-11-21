"""Tests for Task 7 (misalignment correction that allows for bladder filling). Plan: docs/TASK7_PLAN.md."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config  # noqa: E402
from sensors import Reading  # noqa: E402
from devices import CustomTechDevice, MisalignmentMonitor  # noqa: E402
from devices.misalignment_monitor import LEVEL_DROP  # noqa: E402
import task6_experiment8 as e8  # noqa: E402
import task7_experiment9 as e9  # noqa: E402


def feed(target, values, start=60.0, step=60.0):
    out = []
    for i, v in enumerate(values):
        out += target.receive(Reading(start + i * step, v))
    return out


def filling(n, start_ml=200.0, per_reading=1.5, wobble=6.0, first=0):
    """A bladder filling at a steady rate, with a little scatter."""
    return [start_ml + per_reading * i + (i % 2) * wobble for i in range(first, first + n)]


def moved_patch(gain, monitor_settings, n_before=150, n_after=40):
    monitor = MisalignmentMonitor(**monitor_settings)
    feed(monitor, filling(n_before))
    fired = feed(monitor, [v * gain for v in filling(n_after, first=n_before)], start=60.0 * (n_before + 1))
    return monitor, fired


def test_settings_are_the_frozen_ones():
    assert e9.OLD == e8.MONITOR
    assert e9.NEW == {**e8.MONITOR, "fill_adjust": True, "fill_history_n": 90, "fill_min_n": 30, "ratio_floor": 0.40}
    assert e9.SEED_PREFIX == 2000 and e9.R1_BAND == (0.65, 0.75) and e9.OVER_CORRECTED_BY == 0.05
    assert e9.HELD_OUT == {"mis_x0.5_at_4h": (0.45, 0.55), "mis_x0.85_at_4h": (0.80, 0.90)}
    assert [v for v, _ in e9.VARIANTS] == ["monitor_off", "old_correction", "new_correction"]
    assert e9.OUT.name == "task7" and e9.TASK6.name == "task6"
    assert len(e8.scenarios()) == 21 and set(e9.HELD_OUT) <= {n for n, _, _ in e8.scenarios()}
    assert len(config.SENSOR_SCENARIOS.value) == 15                    # config.py is left alone


def test_the_option_is_off_by_default():
    m = MisalignmentMonitor()
    assert m.fill_adjust is False and m.line_kind == ""
    assert CustomTechDevice(400.0, misalignment_monitor={}).monitor.fill_adjust is False


def test_filling_no_longer_hides_part_of_the_fall():
    old, fired_old = moved_patch(0.70, e9.OLD)
    new, fired_new = moved_patch(0.70, e9.NEW)
    assert fired_old == fired_new == [LEVEL_DROP]
    assert new.line_kind == "line"
    assert new.ratio == pytest.approx(0.70, abs=0.01)                  # the true ratio
    assert old.ratio > 0.74                                            # the Task 6 ratio is too mild


def test_the_flags_do_not_depend_on_the_option():
    for gain in (0.5, 0.7, 0.85, 1.0):
        old, _ = moved_patch(gain, e9.OLD)
        new, _ = moved_patch(gain, e9.NEW)
        assert old.flags == new.flags and old.fired == new.fired


def test_a_bladder_that_is_not_filling_gives_the_same_ratio_either_way():
    def run(settings):
        monitor = MisalignmentMonitor(**settings)
        level = [300.0 + (i % 2) * 6.0 for i in range(150)]
        feed(monitor, level)
        feed(monitor, [v * 0.7 for v in level[:40]], start=60.0 * 151)
        return monitor.ratio
    assert run(e9.NEW) == pytest.approx(run(e9.OLD), abs=0.01) == pytest.approx(0.70, abs=0.01)


def test_too_few_readings_falls_back_to_the_task6_correction():
    def run(settings):
        monitor = MisalignmentMonitor(**settings)
        feed(monitor, filling(35))                                     # 35 readings: 20 older than the newest 15
        feed(monitor, [v * 0.6 for v in filling(40, first=35)], start=60.0 * 36)
        return monitor
    old, new = run(e9.OLD), run(e9.NEW)
    assert LEVEL_DROP in new.fired and new.line_kind == "flat_few_readings"
    assert new.ratio == pytest.approx(old.ratio)


def test_a_line_that_slopes_down_is_made_flat():
    monitor = MisalignmentMonitor(**e9.NEW)
    feed(monitor, [400.0 - 0.3 * i + (i % 2) * 6.0 for i in range(150)])       # slow fall: no flag, but slope < 0
    feed(monitor, [(400.0 - 0.3 * i) * 0.6 for i in range(150, 190)], start=60.0 * 151)
    assert LEVEL_DROP in monitor.fired and monitor.line_kind == "flat_negative_slope"


def test_ratio_is_kept_between_the_limits():
    low, _ = moved_patch(0.2, e9.NEW)
    assert low.ratio == 0.40                                           # never multiplies the estimate by more than 2.5
    assert 0.40 <= moved_patch(0.85, e9.NEW)[0].ratio <= 1.0


def test_device_estimate_with_the_new_correction_is_near_the_real_level():
    plain, old, new = (CustomTechDevice(900.0, misalignment_monitor=m) for m in (None, e9.OLD, e9.NEW))
    for d in (plain, old, new):
        feed(d, filling(150))
        feed(d, [v * 0.7 for v in filling(40, first=150)], start=60.0 * 151)
    real = filling(1, first=187)[0] + 3.0                              # about where the bladder really is
    assert plain.estimate_ml == pytest.approx(real * 0.7, abs=8)
    assert new.estimate_ml == pytest.approx(real, abs=10)
    assert abs(new.estimate_ml - real) < abs(old.estimate_ml - real)


def test_reset_and_resume_forget_the_remembered_readings():
    monitor, _ = moved_patch(0.7, e9.NEW)
    monitor.resume()
    assert len(monitor._history) == 0 and monitor.ratio < 0.8          # the correction in use stays
    monitor.reset()
    assert monitor.ratio == 1.0 and monitor.fill_adjust is True and monitor.line_kind == ""


def test_probe_grid_matches_the_plan():
    cases = e9.probe_cases()
    assert len(cases) == 12 and e9.PROBE_SEEDS == [42, 1, 2]
    assert all(c["device"]["misalignment_monitor"] == e9.NEW for c in cases)
    assert {c["probe"] for c in cases} == {"anchor_new_correction", "misaligned_new_correction"}
