"""
Task 3 tests: the session cap and post-session check (docs/EXPERIMENT7_CRITERIA.md).

Written before the rule was built. The unit tests drive the real device and controller with
hand-made readings, so every timing is known exactly. The tests marked slow run whole 12 h
people through the rig and compare them with saved results; set CUE_RUN_SLOW=1 to run them.
"""
import ast
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config  # noqa: E402
from sensors import Reading  # noqa: E402
from devices import CustomTechDevice, BurstPattern, HypotheticalStimulator, SafetyController  # noqa: E402
from devices.safety_controller import CATHETER_ONLY, LOCKOUT, MONITORING, STIMULATING, WAITING  # noqa: E402
from devices.session_guard import (SessionGuard, FAULT_MESSAGE, LIMIT_MESSAGE, NO_DROP, TIMED_OUT,  # noqa: E402
                                   SESSION_LIMIT)
import sci_test_rig as rig_mod  # noqa: E402

READING_S = 60.0


class Bench:
    """A device and controller fed by hand, one reading a minute, as in the rig."""

    def __init__(self, cap=2, fraction=0.20, guard=True, deadline_s=600.0, repeat_s=1800.0, lockout_s=1800.0):
        self.device = CustomTechDevice(400.0, median_window=5, confirm_n=3)
        self.stim = HypotheticalStimulator(BurstPattern())
        self.guard = SessionGuard(session_cap=cap, min_drop_fraction=fraction, readings_needed=5,
                                  deadline_s=deadline_s, repeat_s=repeat_s) if guard else None
        self.ctl = SafetyController(self.device, self.stim, max_duration_s=60.0, volume_stop_ml=100.0,
                                    pressure_ceiling_cmH2O=55.0, lockout_s=lockout_s, guard=self.guard)
        self.t = 0.0
        self.vibrations = []

    def tick(self, volume_ml=None, read=True, press=False):
        """One step at the current time, with or without a sensor reading."""
        events = self.device.receive(Reading(self.t, volume_ml)) if read else []
        if self.ctl.step(self.t, events, press, None):
            self.vibrations.append(self.t)
        if press:                                     # release, so the next press is a new edge
            self.ctl.step(self.t, [], False, None)
        self.t += READING_S

    def until_alert(self, volume_ml=420.0):
        for _ in range(20):
            if self.ctl.state == WAITING:
                return
            self.tick(volume_ml)
        raise AssertionError("no alert")

    def session(self, volume_ml=420.0):
        """Alert, press, then run to the 60 s limit. Leaves the controller in lockout."""
        self.until_alert(volume_ml)
        self.tick(volume_ml, press=True)
        assert self.ctl.state == STIMULATING
        self.tick(volume_ml)
        assert self.ctl.state == LOCKOUT

    def after_lockout(self, volume_ml):
        while self.ctl.state == LOCKOUT:
            self.tick(volume_ml)


# ------------------------------------------------------------------ the post-session check
def test_a_session_that_empties_passes_and_monitoring_continues():
    b = Bench()
    b.session(420.0)
    b.after_lockout(30.0)
    assert b.ctl.state == MONITORING
    assert b.guard.latched_reason is None and b.guard.alerts == []
    assert b.guard.checks[0]["passed"] is True


def test_no_drop_latches_catheter_only_with_the_exact_message():
    b = Bench()
    b.session(420.0)
    b.after_lockout(420.0)
    assert b.ctl.state == CATHETER_ONLY
    assert b.guard.latched_reason == NO_DROP
    assert b.guard.alerts[0]["message"] == FAULT_MESSAGE == "device fault suspected, use catheter"


def test_estimate_going_up_also_fails():
    b = Bench()
    b.session(410.0)
    b.after_lockout(450.0)
    assert b.guard.latched_reason == NO_DROP


@pytest.mark.parametrize("fraction,after,passes", [(0.20, 400.0, True), (0.20, 401.0, False),
                                                   (0.40, 300.0, True), (0.40, 301.0, False)])
def test_the_drop_boundary_is_at_least_the_fraction(fraction, after, passes):
    b = Bench(fraction=fraction)
    b.session(500.0)
    b.after_lockout(after)
    assert b.guard.checks[0]["estimate_before_ml"] == 500.0
    assert b.guard.checks[0]["passed"] is passes


def test_the_check_waits_for_five_new_readings_and_not_one_more():
    b = Bench()
    b.session(420.0)
    stopped = b.ctl.sessions[0]["stop_s"]
    for i in range(1, 5):
        b.tick(420.0)
        assert b.guard.checks == [], f"checked after only {i} readings"
    b.tick(420.0)
    assert len(b.guard.checks) == 1
    assert b.guard.alerts[0]["t_s"] == stopped + 5 * READING_S


def test_the_estimate_it_judges_holds_no_reading_from_before_the_session():
    """Four high readings then one low would still pass a too-early check on a median."""
    b = Bench()
    b.session(420.0)
    for _ in range(5):
        b.tick(30.0)
    assert b.guard.checks[0]["estimate_after_ml"] == 30.0


def test_missing_readings_do_not_count_toward_the_five():
    b = Bench()
    b.session(420.0)
    for volume in [30.0, None, 30.0, None, 30.0, 30.0]:
        b.tick(volume)
    assert b.guard.checks == []
    b.tick(30.0)
    assert b.guard.checks[0]["passed"] is True


def test_a_dropout_fails_by_timeout_and_tells_the_user():
    """Declared limitation: this happens even if the session worked (a real device needs a reset)."""
    b = Bench()
    b.session(420.0)
    stopped = b.ctl.sessions[0]["stop_s"]
    while b.ctl.state == LOCKOUT:
        b.tick(None)
    assert b.ctl.state == CATHETER_ONLY
    assert b.guard.latched_reason == TIMED_OUT
    assert b.guard.alerts[0]["t_s"] == stopped + 600.0
    assert b.guard.alerts[0]["message"] == FAULT_MESSAGE


def test_four_readings_then_silence_still_times_out():
    b = Bench()
    b.session(420.0)
    for _ in range(4):
        b.tick(30.0)
    while b.ctl.state == LOCKOUT:
        b.tick(None)
    assert b.guard.latched_reason == TIMED_OUT


def test_readings_returning_after_the_timeout_do_not_clear_the_latch():
    b = Bench()
    b.session(420.0)
    while b.ctl.state == LOCKOUT:
        b.tick(None)
    for _ in range(50):
        b.tick(30.0)
    assert b.ctl.state == CATHETER_ONLY


def test_a_zero_starting_estimate_cannot_pass():
    g = SessionGuard(session_cap=2, min_drop_fraction=0.2, readings_needed=1, deadline_s=600.0, repeat_s=1800.0)
    g.session_started(0.0, 0.0)
    g.session_stopped(60.0, 10)
    assert g.check(120.0, 0.0, 11) == NO_DROP


def test_a_session_cut_short_is_still_checked():
    b = Bench()
    b.until_alert()
    b.tick(420.0, press=True)
    b.ctl.step(b.t, [], False, 60.0)                 # pressure ceiling stops it at once
    assert b.ctl.state == LOCKOUT
    b.after_lockout(420.0)
    assert b.guard.latched_reason == NO_DROP


# ------------------------------------------------------------------ never silent
def latched_bench():
    b = Bench()
    b.session(420.0)
    b.after_lockout(420.0)
    return b


def test_a_press_in_catheter_only_starts_nothing_and_resends_the_alert_at_once():
    b = latched_bench()
    before = len(b.guard.alerts)
    t = b.t
    b.tick(420.0, press=True)
    assert b.ctl.state == CATHETER_ONLY and not b.stim.active
    assert len(b.ctl.sessions) == 1
    assert len(b.guard.alerts) == before + 1
    assert b.guard.alerts[-1]["t_s"] == t and b.guard.alerts[-1]["because"] == "press"


def test_the_alert_repeats_every_30_minutes_until_the_end():
    b = latched_bench()
    end = b.t + 6 * 3600
    while b.t < end:
        b.tick(420.0)
    times = [a["t_s"] for a in b.guard.alerts]
    gaps = [y - x for x, y in zip(times, times[1:])]
    assert len(times) >= 12
    assert max(gaps) <= 1800.0 + READING_S
    assert b.t - times[-1] <= 1800.0 + READING_S


def test_no_stimulation_invitation_after_the_latch():
    b = latched_bench()
    before = list(b.vibrations)
    for _ in range(400):
        b.tick(450.0)
    assert b.vibrations == before


def test_a_new_device_alert_in_catheter_only_also_resends_the_alert():
    b = latched_bench()
    for _ in range(8):
        b.tick(100.0)                                # estimate falls, so the device re-arms
    assert b.device.alert_active is False
    before = len(b.guard.alerts)
    for _ in range(8):
        b.tick(450.0)
    assert b.device.alert_active is True
    assert [a for a in b.guard.alerts[before:] if a["because"] == "device_alert"]


# ------------------------------------------------------------------ session cap
def test_the_cap_acts_only_when_another_session_is_wanted():
    b = Bench(cap=2)
    for _ in range(2):
        b.session(420.0)
        b.after_lockout(30.0)
    assert b.ctl.state == MONITORING and b.guard.alerts == []     # at the cap, nothing wanted yet
    for _ in range(20):
        b.tick(30.0)
    assert b.guard.alerts == []


def test_the_next_alert_after_the_cap_is_the_session_limit_message_and_no_vibration():
    b = Bench(cap=2)
    for _ in range(2):
        b.session(420.0)
        b.after_lockout(30.0)
    vibrations = list(b.vibrations)
    for _ in range(20):
        b.tick(420.0)
    assert b.ctl.state == CATHETER_ONLY
    assert b.guard.latched_reason == SESSION_LIMIT
    assert b.guard.alerts[0]["message"] == LIMIT_MESSAGE == "session limit reached, use catheter"
    assert b.vibrations == vibrations
    assert len(b.ctl.sessions) == 2


@pytest.mark.parametrize("cap", [2, 3, 4])
def test_sessions_can_never_exceed_the_cap(cap):
    b = Bench(cap=cap)
    for _ in range(cap):
        b.session(420.0)
        b.after_lockout(30.0)
    for _ in range(50):
        b.tick(420.0, press=True)
    assert len(b.ctl.sessions) == cap


def test_a_failed_check_at_the_cap_reports_the_fault_not_the_limit():
    b = Bench(cap=1)
    b.session(420.0)
    b.after_lockout(420.0)
    assert b.guard.latched_reason == NO_DROP


# ------------------------------------------------------------------ the button rule and set-up
def test_the_rule_never_starts_stimulation_by_itself():
    b = Bench(cap=4)
    for _ in range(200):
        b.tick(450.0)
    assert b.ctl.sessions == [] and b.ctl.state == WAITING


def test_off_by_default_and_the_steps_match_a_guarded_controller_that_never_acts():
    """No guard, and a guard that never has to act, must take identical decisions."""
    plain, guarded = Bench(guard=False), Bench(cap=4)
    for b in (plain, guarded):
        b.session(420.0)
        b.after_lockout(30.0)
    assert plain.ctl.guard is None
    assert plain.ctl.log == guarded.ctl.log
    assert plain.ctl.sessions == guarded.ctl.sessions and plain.vibrations == guarded.vibrations


def test_a_deadline_longer_than_the_lockout_is_refused():
    """Otherwise a new session could be offered before the old one was checked."""
    with pytest.raises(ValueError):
        Bench(deadline_s=2000.0)


def test_config_holds_the_frozen_values():
    g = config.SESSION_GUARD
    assert config.value(g, "session_caps") == [2, 3, 4]
    assert config.value(g, "min_drop_fractions") == [0.20, 0.40]
    assert config.value(g, "readings_before_check") == config.value(config.DEVICE, "median_window") == 5
    assert config.value(g, "check_deadline_s") == 600.0
    assert config.value(g, "alert_repeat_s") == 1800.0
    assert all(p.status == config.ASSUMED for p in g.values())
    config.validate()


def test_the_guard_module_never_references_ground_truth():
    tree = ast.parse((ROOT / "devices" / "session_guard.py").read_text(encoding="utf8"))
    assert [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))] == []
    names = {getattr(n, "id", getattr(n, "attr", getattr(n, "arg", ""))) for n in ast.walk(tree)
             if isinstance(n, (ast.Name, ast.Attribute, ast.arg))}
    assert names
    for name in names:
        assert not any(bad in name.lower() for bad in ["v_b", "p_d", "true", "truth", "ground", "pressure"]), name


def test_the_controller_hands_the_guard_only_device_numbers():
    source = (ROOT / "devices" / "safety_controller.py").read_text(encoding="utf8")
    for line in source.splitlines():
        if "self.guard." in line and "(" in line and "alerts" not in line:
            assert "pressure" not in line, line


# ------------------------------------------------------------------ the sweep and its scoring
def test_the_grid_matches_the_frozen_criteria():
    import task3_experiment7 as t3
    cases = t3.cases()
    count = lambda test: sum(c["test"] == test for c in cases)  # noqa: E731
    assert (len(cases), count("T1"), count("T2"), count("T3")) == (1710, 420, 210, 1080)
    assert len(t3.SEEDS) == len(set(t3.SEEDS)) == 15
    assert all(c["guard"] is not None for c in cases if c["test"] == "T3")      # "before" comes from Experiment 3b
    assert {c["stim_name"] for c in cases if c["test"] == "T2"} == {"e1.0_s0.5_5on5off"}
    assert {c["threshold_ml"] for c in cases if c["test"] == "T3"} == {350.0, 400.0, 450.0}
    assert {c["sensor_name"] for c in cases if c["test"] == "T1"} == {"stuck_high_450ml_from_5h"}


def test_consistency_comparison_ignores_storage_type_but_not_values():
    import task3_experiment7 as t3
    a = pd.DataFrame({"n": [2, 3], "x": [1.5, None], "s": ["a", None]})
    b = pd.DataFrame({"n": [2.0, 3.0], "x": [1.5, None], "s": ["a", None]})
    assert t3.same_values(a, b, ["n", "x", "s"])
    b.loc[0, "x"] = 1.5 + 1e-12
    assert not t3.same_values(a, b, ["n", "x", "s"])


def scored_bench():
    from types import SimpleNamespace as Space
    b = latched_bench()
    for _ in range(120):
        b.tick(420.0)
    return Space(controller=b.ctl, alert_times=list(b.vibrations), device=b.device), b


def test_the_silence_check_passes_a_correct_run_and_catches_each_kind_of_failure():
    from evaluation import guard_metrics as gm
    rig, b = scored_bench()
    end = b.t - READING_S
    good = gm.never_silent(rig, READING_S, end)
    assert good["I2_nothing_offered_after_latch"] and good["I3_never_silent"]

    keep = list(b.guard.alerts)
    b.guard.alerts[:] = [a for a in keep if a["because"] != "repeat"]     # alerts stop repeating
    assert not gm.never_silent(rig, READING_S, end)["I3_never_silent"]
    b.guard.alerts[:] = keep[1:]                                          # the latch itself was silent
    assert not gm.never_silent(rig, READING_S, end)["I3_never_silent"]
    b.guard.alerts[:] = keep
    b.ctl.log.append((b.guard.latched_t_s + 7.0, "PRESS_IGNORED", "catheter only"))   # unanswered press
    assert not gm.never_silent(rig, READING_S, end)["I3_never_silent"]
    b.ctl.log.pop()
    rig.alert_times.append(b.guard.latched_t_s + 7.0)                     # stimulation offered after the latch
    assert not gm.never_silent(rig, READING_S, end)["I2_nothing_offered_after_latch"]


# ------------------------------------------------------------------ whole runs (slow)
def person(spec):
    data, rig = rig_mod.run_closed_loop(rig_mod.default_case(**spec))
    g = rig.controller.guard
    return {"max_volume_ml": float(data["V_B_ml"].max()), "final_volume_ml": float(data["V_B_ml"].iloc[-1]),
            "n_sessions": len(rig.controller.sessions), "reason": g.latched_reason if g else None,
            "alerts": len(g.alerts) if g else 0, "states": sorted(set(rig.state.tolist())),
            "checks": [c["passed"] for c in g.checks] if g else []}


STIM_R2 = {"stim_name": "e1.0_s0.0_5on5off", "stim": config.STIM_PATTERNS.value["e1.0_s0.0_5on5off"]}
SEED = {"phys_seed": 42, "sensor_seed": 42, "user_seed": 42, "pressure_seed": 42}
STUCK = {"sensor_name": "stuck_high_450ml_from_5h", "sensor": config.EXTRA_SENSOR_FAULTS.value["stuck_high_450ml_from_5h"]}
GUARD = {"session_cap": 4, "min_drop_fraction": 0.20, "readings_needed": 5, "deadline_s": 600.0, "repeat_s": 1800.0}


@pytest.fixture(scope="module")
def people():
    specs = {"plain": {**STIM_R2, **SEED}, "guarded": {**STIM_R2, **SEED, "guard": GUARD},
             "stuck_plain": {**STIM_R2, **SEED, **STUCK}, "stuck_guarded": {**STIM_R2, **SEED, **STUCK, "guard": GUARD}}
    with ProcessPoolExecutor(4) as pool:
        return dict(zip(specs, pool.map(person, specs.values())))


def saved(path, **where):
    t = pd.read_csv(ROOT / "results" / path, float_precision="round_trip")
    for key, val in where.items():
        t = t[t[key] == val]
    assert len(t) == 1
    return t.iloc[0]


slow = pytest.mark.skipif(os.environ.get("CUE_RUN_SLOW") != "1", reason="slow (12 h people); set CUE_RUN_SLOW=1")


@slow
def test_rule_off_still_reproduces_experiment_3b_exactly(people):
    row = saved("task2/exp3b_runs.csv", stim_name=STIM_R2["stim_name"], sphincter_scaling=1.0, max_duration_s=60.0,
                threshold_ml=400.0, pressure_ceiling_cmH2O=55.0, phys_seed=42)
    assert people["plain"]["max_volume_ml"] == row["max_volume_ml"]
    assert people["plain"]["final_volume_ml"] == row["final_volume_ml"]
    assert people["plain"]["n_sessions"] == row["n_sessions"]


@slow
def test_rule_off_still_reproduces_the_experiment_4_stuck_high_run_exactly(people):
    row = saved("stage6/exp4_runs.csv", group="estimate:stuck_high_450ml_from_5h", reference=STIM_R2["stim_name"],
                sphincter_scaling=1.0, phys_seed=42)
    assert people["stuck_plain"]["max_volume_ml"] == row["max_volume_ml"]
    assert people["stuck_plain"]["n_sessions"] == row["n_sessions"] == 12


@slow
def test_the_rule_does_nothing_to_a_healthy_run_until_it_acts(people):
    a, b = people["plain"], people["guarded"]
    assert b["reason"] is None and b["alerts"] == 0 and all(b["checks"])
    assert (a["max_volume_ml"], a["final_volume_ml"], a["n_sessions"]) == (b["max_volume_ml"], b["final_volume_ml"], b["n_sessions"])


@slow
def test_the_rule_catches_stuck_high_after_one_session_and_stays_loud(people):
    p = people["stuck_guarded"]
    assert p["reason"] == NO_DROP and p["n_sessions"] == 1 and p["alerts"] >= 2
    assert rig_mod.STATE_CODES[CATHETER_ONLY] in p["states"]
