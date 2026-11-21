"""
Stage 5 tests: user model, stimulator, pressure channel, safety controller and the closed-loop rig.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from cue_model import CueLUT, simulate  # noqa: E402
from sensors import Reading, PressureScenario, SyntheticImplantPressureChannel  # noqa: E402
from devices import (CustomTechDevice, UserScenario, SimulatedUser, BurstPattern, HypotheticalStimulator,  # noqa: E402
                     SafetyController)
from devices.custom_tech_device import DeviceEvent  # noqa: E402
import sci_test_rig as rig_mod  # noqa: E402
from evaluation import closed_loop_metrics as cm  # noqa: E402

SI = ["t", "V_B", "f_aD_s", "f_aS_s", "r_U", "Q", "p_D", "p_S", "Q_in", "w_e_s", "w_i_s", "w_s_s", "voiding"]
ALERT_EVENT = [DeviceEvent(0.0, "ALERT", 450.0)]


# ------------------------------------------------------------------ user, stimulator, pressure channel
def test_user_delay_is_within_the_configured_range_and_no_press_never_presses():
    user = SimulatedUser(UserScenario(delay_min_s=30, delay_max_s=300), seed=3)
    user.feel_alert(1000.0)
    (down, up), = user.presses
    assert 1030.0 <= down <= 1300.0 and up == pytest.approx(down + 0.5)
    silent = SimulatedUser(UserScenario(responds_to_alert=False), seed=3)
    silent.feel_alert(1000.0)
    assert silent.presses == [] and not silent.button_down(1100.0)


def test_accidental_presses_happen_without_any_alert():
    user = SimulatedUser(UserScenario.from_dict("acc", config.USER_SCENARIOS.value["accidental_no_alert"]), 1)
    assert user.button_down(3600.2) and not user.button_down(3601.0)


def test_burst_timing_and_continuous_mode():
    stim = HypotheticalStimulator(BurstPattern(detrusor_drive=0.8, sphincter_drive=0.3, on_s=5, off_s=5))
    assert stim.drive(1.0) == (None, None)            # not started
    stim.start(100.0)
    assert stim.drive(102.0) == (0.8, 0.3) and stim.drive(107.0) == (None, None) and stim.drive(111.0) == (0.8, 0.3)
    stim.stop(120.0)
    assert stim.drive(121.0) == (None, None) and stim.sessions == [(100.0, 120.0)]
    cont = HypotheticalStimulator(BurstPattern(on_s=1, off_s=0))
    cont.start(0.0)
    assert all(cont.burst_on(t) for t in np.arange(0, 50, 0.7))


def test_pressure_channel_faults():
    true_p = lambda t: 50.0      # noqa: E731
    assert SyntheticImplantPressureChannel(PressureScenario(dead_from_s=10.0), 1).read(5.0, true_p) == 50.0
    assert SyntheticImplantPressureChannel(PressureScenario(dead_from_s=10.0), 1).read(11.0, true_p) is None
    assert SyntheticImplantPressureChannel(PressureScenario(stuck_at_cmH2O=5.0), 1).read(11.0, true_p) == 5.0
    noisy = SyntheticImplantPressureChannel(PressureScenario(noise_sd_cmH2O=10.0), 1)
    values = [noisy.read(i, true_p) for i in range(5000)]
    assert np.std(values) == pytest.approx(10.0, rel=0.05)


# ------------------------------------------------------------------ safety controller (unit level)
def make_controller(**kw):
    device = CustomTechDevice(400.0, median_window=1, confirm_n=1)
    stim = HypotheticalStimulator(BurstPattern())
    args = dict(max_duration_s=60.0, volume_stop_ml=100.0, pressure_ceiling_cmH2O=55.0, lockout_s=1800.0)
    args.update(kw)
    return SafetyController(device, stim, **args), device, stim


def test_press_without_alert_is_ignored():
    ctl, _, stim = make_controller()
    ctl.step(0.0, [], True, None)
    assert not stim.active and ctl.log[-1][1] == "PRESS_IGNORED"


def test_alert_then_press_starts_and_max_duration_stops_with_no_sensors_at_all():
    ctl, _, stim = make_controller()
    assert ctl.step(0.0, ALERT_EVENT, False, None) is True          # watch vibrates
    ctl.step(10.0, [], True, None)
    assert stim.active and ctl.state == "STIMULATING"
    ctl.step(69.9, [], True, None)                                   # held: no restart, no stop yet
    assert stim.active
    ctl.step(70.0, [], False, None)                                  # no device estimate, no pressure
    assert not stim.active and ctl.sessions[-1]["cutoff"] == "max_duration"


def test_volume_stop_uses_only_a_fresh_device_estimate():
    ctl, device, stim = make_controller()
    device.receive(Reading(0.0, 50.0))                               # low estimate BEFORE the session
    ctl.step(0.0, ALERT_EVENT, False, None)
    ctl.step(1.0, [], True, None)
    ctl.step(2.0, [], False, None)
    assert stim.active                                               # old estimate must not stop it
    device.receive(Reading(3.0, 80.0))
    ctl.step(3.0, [], False, None)
    assert not stim.active and ctl.sessions[-1]["cutoff"] == "volume_stop"


def test_pressure_ceiling_stops_and_dead_channel_cannot():
    ctl, _, stim = make_controller()
    ctl.step(0.0, ALERT_EVENT, False, None)
    ctl.step(1.0, [], True, None)
    ctl.step(2.0, [], False, None)                                   # pressure missing: keeps going
    assert stim.active
    ctl.step(3.0, [], False, 56.0)
    assert not stim.active and ctl.sessions[-1]["cutoff"] == "pressure_ceiling"


def test_lockout_blocks_presses_and_then_rearms_the_device():
    ctl, device, stim = make_controller(lockout_s=100.0)
    device.receive(Reading(0.0, 450.0))                              # device alert active
    ctl.step(0.0, ALERT_EVENT, False, None)
    ctl.step(1.0, [], True, None)
    ctl.step(61.0, [], False, None)                                  # max duration -> lockout
    ctl.step(62.0, [], True, None)                                   # press in lockout
    assert not stim.active and ctl.log[-1][1] == "PRESS_IGNORED"
    ctl.step(161.0, [], False, None)
    assert ctl.state == "MONITORING" and device.alert_active is False


def test_button_held_through_the_alert_does_not_start_stimulation():
    ctl, _, stim = make_controller()
    ctl.step(0.0, [], True, None)                                    # already held before the alert
    ctl.step(1.0, ALERT_EVENT, True, None)
    ctl.step(2.0, [], True, None)
    assert not stim.active and ctl.state == "WAITING_FOR_USER"


# ------------------------------------------------------------------ closed-loop rig
def test_rig_refuses_the_upstream_void_switch():
    with pytest.raises(ValueError):
        rig_mod.ClosedLoopLUT(rig=None, sci_enabled=False)


def test_with_no_press_the_closed_loop_model_equals_the_stage3_model_exactly():
    case = rig_mod.default_case(duration_s=2 * 3600, initial_volume_ml=380.0,
                                user_name="no_press", user=config.USER_SCENARIOS.value["no_press"])
    data, rig = rig_mod.run_closed_loop(case)
    assert rig.alert_times, "an alert must happen inside the test window"
    plain = CueLUT(sci_enabled=True, volume_ceiling_ml=case["volume_ceiling_ml"], initial_volume_ml=380.0)
    expected = simulate(plain, case["duration_s"], config.value(config.SIMULATION, "dt_s"), case["phys_seed"],
                        config.value(config.SIMULATION, "inflow_noise"))
    pd.testing.assert_frame_equal(data[SI], expected[SI], check_exact=True)
    assert not data["stim_active"].any()


def test_closed_loop_session_obeys_the_safety_invariants():
    case = rig_mod.default_case(duration_s=1800, initial_volume_ml=420.0)
    data, rig = rig_mod.run_closed_loop(case)
    assert rig.controller.sessions, "a session must happen inside the test window"
    inv = cm.invariants(rig, 0.1, case["controller"]["max_duration_s"])
    assert inv["A2_start_only_after_press_and_alert"] and inv["A3_no_start_in_lockout"]
    assert inv["A4_sessions_within_max_duration"]
    on = data["burst_on"].to_numpy()
    assert np.allclose(data["w_e_s"].to_numpy()[on], case["stim"]["detrusor_drive"])
    assert np.allclose(data["w_s_s"].to_numpy()[on], case["stim"]["sphincter_drive"])


def test_emptying_classes():
    assert cm.emptying_class(0.97) == "complete" and cm.emptying_class(0.5) == "partial"
    assert cm.emptying_class(0.05) == "none"
