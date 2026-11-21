"""Tests for Task 6 (sphincter block, misalignment monitor). Plan: docs/TASK6_PLAN.md."""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config  # noqa: E402
from sensors import Reading  # noqa: E402
from devices import (CustomTechDevice, BurstPattern, HypotheticalStimulator, SafetyController,  # noqa: E402
                     MisalignmentMonitor, CHECK_PATCH, PATCH_RESEATED, ALERT)
from devices.custom_tech_device import DeviceEvent  # noqa: E402
from devices.misalignment_monitor import LEVEL_DROP, DROPOUT_RISE, chance_of_at_least  # noqa: E402
import task5_sphincter_levels as t5  # noqa: E402
import task6_block_check as t6  # noqa: E402
import task6_experiment8 as e8  # noqa: E402


# ------------------------------------------------------------------ sphincter block
def started(**pattern):
    stim = HypotheticalStimulator(BurstPattern(detrusor_drive=0.6, sphincter_drive=0.5, on_s=5, off_s=5, **pattern))
    stim.start(100.0)
    return stim


def test_no_block_is_exactly_the_old_behaviour():
    stim = started()
    assert stim.drive(102.0) == (0.6, 0.5) and stim.drive(107.0) == (None, None)
    assert stim.sphincter_input(102.0, 0.45) == 0.5          # burst ON: co-activation replaces the reflex
    assert stim.sphincter_input(107.0, 0.45) == 0.45         # burst OFF: the model's own value, untouched
    assert not stim.block_on(102.0)


def test_burst_block_cuts_only_the_coactivation():
    stim = started(sphincter_block=0.8)
    assert stim.sphincter_input(102.0, 0.45) == 0.1          # exactly the Task 5 level, not 0.0999...
    assert stim.drive(102.0) == (0.6, 0.1)
    assert stim.sphincter_input(107.0, 0.45) == 0.45         # between bursts the reflex is left alone
    assert started(sphincter_block=1.0).sphincter_input(102.0, 0.45) == 0.0


def test_session_block_also_cuts_the_reflex_between_bursts():
    stim = started(sphincter_block=0.8, block_scope="session")
    assert stim.sphincter_input(102.0, 0.45) == 0.1
    assert stim.sphincter_input(107.0, 0.45) == pytest.approx(0.09)


def test_block_never_acts_outside_a_session():
    stim = HypotheticalStimulator(BurstPattern(sphincter_drive=0.5, sphincter_block=1.0, block_scope="session"))
    assert stim.sphincter_input(5.0, 0.5) == 0.5             # not started
    stim.start(10.0)
    stim.stop(20.0)
    assert stim.sphincter_input(25.0, 0.5) == 0.5 and not stim.block_on(25.0)


def test_block_fault_gives_the_coactivation_back():
    stim = started(sphincter_block=1.0, block_fails_at_s=20.0)
    assert stim.sphincter_input(112.0, 0.45) == 0.0          # 12 s in: still blocked
    assert stim.sphincter_input(122.0, 0.45) == 0.5          # 22 s in: the block has failed
    assert started(sphincter_block=1.0, block_fails_at_s=0.0).sphincter_input(102.0, 0.45) == 0.5


def test_bad_block_settings_are_refused():
    for bad in ({"sphincter_block": 1.2}, {"sphincter_block": -0.1}, {"block_scope": "always"},
                {"block_fails_at_s": -1.0}):
        with pytest.raises(ValueError):
            BurstPattern(**bad)


def test_block_grid_matches_the_plan_and_config_is_left_alone():
    cases = t6.cases()
    groups = {g: sum(c["group"] == g for c in cases) for g in ("A-check", "A-fault", "A-session", "B-probe")}
    assert groups == {"A-check": 36, "A-fault": 12, "A-session": 24, "B-probe": 18} and len(cases) == 90
    assert t6.SEEDS == [42, 1, 2] and t6.BLOCKS == (0.8, 1.0) and t6.FAULT_AT_S == 20.0
    assert len(config.STIM_PATTERNS.value) == 8
    assert all(c["stim"].get("sphincter_block", 0.0) == 0.0 for c in cases if c["group"] == "B-probe")
    assert t6.RESULTS.name == "task6" and t6.TASK5.name == "task5"


def test_check_cases_have_the_right_task5_twins():
    assert t6.block_pattern(0.6, 0.8)[2] == "e0.6_s0.1_5on5off"
    assert t6.block_pattern(1.0, 1.0)[2] == "e1.0_s0.0_5on5off"
    assert t6.block_pattern(0.6, 1.0, fails_at_s=0.0)[2] == "e0.6_s0.5_5on5off"
    assert t6.block_pattern(0.6, 1.0, fails_at_s=20.0)[2] is None
    assert t6.block_pattern(0.6, 0.8, scope="session")[2] is None
    for c in t6.cases():
        if c["group"] == "A-check":                           # only the pattern differs from the Task 5 case
            assert c["task5_twin"] in {t5.pattern(d, lv)[0] for d in t5.DETRUSOR for lv in (0.0, 0.1, 0.5)}
            assert c["controller"] == {"pressure_ceiling_cmH2O": t5.CEILING_CMH2O}


# ------------------------------------------------------------------ misalignment monitor
def feed(target, values, start=60.0, step=60.0):
    out = []
    for i, v in enumerate(values):
        out += target.receive(Reading(start + i * step, v))
    return out


def test_monitor_file_never_references_ground_truth():
    tree = ast.parse((ROOT / "devices" / "misalignment_monitor.py").read_text())
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    modules = {a.name for n in imports for a in n.names} | {getattr(n, "module", None) for n in imports}
    assert modules <= {"math", "collections", "deque", None}
    identifiers = {getattr(n, "id", None) or getattr(n, "attr", None) or getattr(n, "arg", None)
                   for n in ast.walk(tree) if isinstance(n, (ast.Name, ast.Attribute, ast.arg))}
    identifiers.discard(None)
    for name in identifiers:
        assert not any(bad in name.lower() for bad in ["v_b", "p_d", "true", "truth", "ground"]), name


def test_settings_in_both_scripts_are_the_frozen_ones():
    frozen = {"window_n": 15, "k_noise": 3.5, "k_noise_after_dropout": 2.0, "min_drop_fraction": 0.10,
              "min_ml": 100.0, "noise_n": 120, "noise_floor": 0.02, "dropout_slots": 20,
              "dropout_baseline_slots": 120, "dropout_chance": 1e-4, "dropout_floor": 0.02, "compensate": True}
    assert e8.MONITOR == frozen and t6.MONITOR == frozen
    m = MisalignmentMonitor()                                 # the class defaults are the same values
    assert (m.window_n, m.k_noise, m.k_noise_after_dropout, m.min_drop_fraction, m.min_ml) == (15, 3.5, 2.0, 0.10, 100.0)
    assert e8.THRESHOLDS == [350.0, 400.0, 450.0] and e8.SENSOR_REPS == 10 and len(e8.SEEDS) == 15


def test_experiment8_scenarios_match_the_plan():
    sc = e8.scenarios()
    kinds = [k for _, k, _ in sc]
    assert sc[0][0] == "misaligned_at_4h" and kinds.count("target") == 1
    assert kinds.count("variant") == 6 and kinds.count("none") == 14 and len(sc) == 21
    assert "misaligned_at_4h" not in e8.VARIANTS and len(config.SENSOR_SCENARIOS.value) == 15
    assert e8.OUT.name == "task6" and e8.PHYS.parent.name == "stage4b"


def test_a_steady_rise_is_never_flagged():
    monitor = MisalignmentMonitor()
    assert feed(monitor, [50.0 + 1.4 * i for i in range(600)]) == []
    assert monitor.ratio == 1.0


def test_a_clear_fall_is_flagged_and_measured():
    monitor = MisalignmentMonitor()
    values = [300.0 + (i % 2) * 6.0 for i in range(150)]      # steady readings with a little scatter
    assert feed(monitor, values) == []
    fired = feed(monitor, [v * 0.7 for v in values[:40]], start=60.0 * 151)
    assert fired == [LEVEL_DROP]                              # once only
    assert monitor.ratio == pytest.approx(0.7, abs=0.08)


def test_a_small_fall_or_a_low_level_is_not_flagged():
    values = [300.0 + (i % 2) * 6.0 for i in range(150)]
    small = MisalignmentMonitor()
    feed(small, values)
    assert feed(small, [v * 0.95 for v in values[:40]], start=60.0 * 151) == []      # under the 10% minimum
    low = MisalignmentMonitor()
    feed(low, [v / 5 for v in values])
    assert feed(low, [v / 5 * 0.7 for v in values[:40]], start=60.0 * 151) == []     # "before" is under 100 mL


def test_a_noisier_sensor_needs_a_bigger_fall():
    quiet, noisy = MisalignmentMonitor(), MisalignmentMonitor()
    feed(quiet, [300.0 + (i % 2) * 6.0 for i in range(150)])
    feed(noisy, [300.0 + (i % 2) * 150.0 for i in range(150)])
    assert noisy.noise() > 5 * quiet.noise()
    assert feed(quiet, [255.0 + (i % 2) * 6.0 for i in range(40)], start=60.0 * 151) == [LEVEL_DROP]   # -15%
    assert feed(noisy, [255.0 + (i % 2) * 150.0 for i in range(40)], start=60.0 * 151) == []


def test_dropout_rise_is_flagged_against_the_devices_own_rate():
    monitor = MisalignmentMonitor()
    assert feed(monitor, [300.0] * 200) == []
    fired = feed(monitor, [None if i % 3 == 0 else 300.0 for i in range(30)], start=60.0 * 201)
    assert fired == [DROPOUT_RISE]
    used_to_it = MisalignmentMonitor()                        # a sensor that always loses 1 in 3
    assert feed(used_to_it, [None if i % 3 == 0 else 300.0 for i in range(600)]) == []


def test_chance_of_at_least():
    assert chance_of_at_least(0, 20, 0.3) == pytest.approx(1.0)
    assert chance_of_at_least(20, 20, 0.5) == pytest.approx(0.5 ** 20)
    assert chance_of_at_least(5, 20, 0.02) < 1e-4 < chance_of_at_least(4, 20, 0.02)


def test_after_a_dropout_flag_the_level_rule_needs_less_proof():
    def run(with_dropout):
        monitor = MisalignmentMonitor()
        feed(monitor, [300.0 + (i % 2) * 60.0 for i in range(200)])          # noisy enough that -12% is not clear
        if with_dropout:
            feed(monitor, [None] * 8, start=60.0 * 201)
        return feed(monitor, [264.0 + (i % 2) * 53.0 for i in range(40)], start=60.0 * 220), monitor
    alone, _ = run(False)
    together, monitor = run(True)
    assert LEVEL_DROP not in alone
    assert LEVEL_DROP in together and DROPOUT_RISE in monitor.fired


def test_device_raises_check_patch_and_corrects_its_estimate():
    values = [300.0 + (i % 2) * 6.0 for i in range(150)]
    device = CustomTechDevice(400.0, misalignment_monitor={})
    plain = CustomTechDevice(400.0)
    for d in (device, plain):
        feed(d, values)
        feed(d, [v * 0.7 for v in values[:60]], start=60.0 * 151)
    assert [e.kind for e in device.events] == [CHECK_PATCH]
    assert device.patch_checks[0]["rule"] == LEVEL_DROP
    assert plain.estimate_ml == pytest.approx(212.1, abs=3) and plain.correction_ratio == 1.0
    assert device.estimate_ml == pytest.approx(303.0, abs=30)                # back near the real level
    assert device.estimate_ml == pytest.approx(plain.estimate_ml / device.correction_ratio)


def test_flag_only_mode_does_not_change_the_estimate():
    values = [300.0 + (i % 2) * 6.0 for i in range(150)]
    device = CustomTechDevice(400.0, misalignment_monitor={"compensate": False})
    feed(device, values)
    feed(device, [v * 0.7 for v in values[:60]], start=60.0 * 151)
    assert [e.kind for e in device.events] == [CHECK_PATCH] and device.correction_ratio == 1.0


def test_monitor_off_leaves_the_device_exactly_as_before():
    values = [100.0 + 2.0 * i + (i % 3) * 20.0 for i in range(300)] + [None] * 5
    old, new = CustomTechDevice(400.0), CustomTechDevice(400.0, misalignment_monitor=None)
    feed(old, values)
    feed(new, values)
    assert new.monitor is None and old.history == new.history and old.events == new.events
    new.session_started()
    new.session_stopped()
    new.patch_reseated(1.0)                                   # all three do nothing when the monitor is off
    assert old.events == new.events


def test_patch_reseated_drops_the_correction_and_lets_it_flag_again():
    values = [300.0 + (i % 2) * 6.0 for i in range(150)]
    device = CustomTechDevice(400.0, misalignment_monitor={})
    feed(device, values)
    feed(device, [v * 0.7 for v in values[:60]], start=60.0 * 151)
    assert device.correction_ratio < 0.8
    device.patch_reseated(60.0 * 212)
    assert device.correction_ratio == 1.0 and device.events[-1].kind == PATCH_RESEATED
    feed(device, values, start=60.0 * 213)
    assert device.estimate_ml == pytest.approx(303.0, abs=4)
    feed(device, [v * 0.7 for v in values[:60]], start=60.0 * 364)
    assert [e.kind for e in device.events].count(CHECK_PATCH) == 2


def test_emptying_in_a_session_is_not_mistaken_for_misalignment():
    """The controller pauses the monitor at the start of a session and restarts it afterwards."""
    full = [420.0 + (i % 2) * 6.0 for i in range(150)]
    empty = [20.0 + 1.4 * i for i in range(200)]

    def run(tell_the_device):
        device = CustomTechDevice(400.0, misalignment_monitor={})
        stim = HypotheticalStimulator(BurstPattern())
        controller = SafetyController(device, stim, max_duration_s=60.0, volume_stop_ml=100.0,
                                      pressure_ceiling_cmH2O=55.0, lockout_s=1800.0)
        if not tell_the_device:
            device.session_started = device.session_stopped = lambda: None
        t = 0.0
        for v in full:
            t += 60.0
            controller.step(t, device.receive(Reading(t, v)), False, None)
        assert controller.state == "WAITING_FOR_USER"
        controller.step(t + 1.0, [], True, None)             # button press: stimulation starts
        controller.step(t + 62.0, [], False, None)           # maximum duration: it stops
        assert controller.state == "LOCKOUT" and len(stim.sessions) == 1
        t += 120.0
        for v in empty:
            t += 60.0
            controller.step(t, device.receive(Reading(t, v)), False, None)
        return [e.kind for e in device.events]
    assert CHECK_PATCH not in run(tell_the_device=True)
    assert CHECK_PATCH in run(tell_the_device=False)          # shows the pause is what prevents it


def test_alert_still_fires_once_with_the_monitor_on():
    device = CustomTechDevice(400.0, misalignment_monitor={})
    kinds = feed(device, [100.0 + 1.4 * i for i in range(300)])
    assert [e.kind for e in kinds] == [ALERT] if kinds and isinstance(kinds[0], DeviceEvent) else True
    assert [e.kind for e in device.events] == [ALERT]
