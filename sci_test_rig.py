"""
sci_test_rig.py: the closed-loop Project Cue test rig.

One simulated person = upstream physiology (SCI condition) + synthetic ultrasound patch +
CustomTechDevice + watch + simulated user + safety controller + hypothetical stimulator +
synthetic implant pressure channel.

How it plugs into the UNMODIFIED upstream loop
----------------------------------------------
`ClosedLoopLUT` subclasses the Stage 3 `CueLUT`. Upstream calls `is_voiding()` once at
the start of every time step, so that is the hook: the rig takes sensor readings, the
device and controller update, and the stimulator is switched on or off. Upstream then asks
for the neural inputs; while a burst is ON the stimulator's values replace omega_e* and
omega_s*, otherwise the model's own values are returned untouched. `is_voiding()` still
returns False (SCI): the upstream void switch is never used, so any emptying has to come
out of the model's mechanics.

Information flow (who may see what)
  physiology (truth) --> ultrasound sensor --> device --> controller --> stimulator --> physiology
  physiology (truth) --> pressure channel ------------> controller
  device ALERT --> watch --> user --> button --> controller
Only the two sensors see truth; the device, user and controller never do. The rig itself
keeps a copy of the truth for the sensors' delay and for evaluation afterwards.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
from lut_upstream import M3_PER_ML, PA_PER_CMH2O  # noqa: E402
from cue_model import CueLUT, simulate  # noqa: E402
from sensors import SensorScenario, SyntheticUltrasoundSensor, PressureScenario, SyntheticImplantPressureChannel  # noqa: E402
from devices import (CustomTechDevice, UserScenario, SimulatedUser, BurstPattern,  # noqa: E402
                     HypotheticalStimulator, SafetyController, SessionGuard, SensorFusion)

STATE_CODES = {"MONITORING": 0, "WAITING_FOR_USER": 1, "STIMULATING": 2, "LOCKOUT": 3, "CATHETER_ONLY": 4}


class ClosedLoopLUT(CueLUT):
    def __init__(self, rig, **kwargs):
        super().__init__(**kwargs)
        if not self.sci_enabled:
            raise ValueError("The closed-loop rig only runs the SCI condition (no upstream void switch).")
        self.rig = rig

    def is_voiding(self):
        self.rig.on_step(self)            # sensors, device, user, controller, stimulator
        return super().is_voiding()       # always False under SCI

    def update_parasympathetic_input(self):
        own = super().update_parasympathetic_input()
        stim, _ = self.rig.stimulator.drive(self.t)
        return own if stim is None else stim

    def update_somatic_input(self):
        own = super().update_somatic_input()
        # Burst ON: the co-activation replaces the reflex value. A sphincter block (Task 6,
        # off by default) then cuts whatever the input is. With no block this is the old rule.
        return self.rig.stimulator.sphincter_input(self.t, own)


class CueRig:
    def __init__(self, case):
        """`case` is a plain dict (see default_case) so it can be sent to worker processes."""
        self.case = case
        dt = config.value(config.SIMULATION, "dt_s")
        self.dt = dt
        n = int(np.ceil(case["duration_s"] / dt)) + 2
        self.V = np.zeros(n)          # true volume at the start of each step (mL)
        self.P = np.zeros(n)          # true detrusor pressure at the start of each step (cmH2O)
        self.stim_active = np.zeros(n, dtype=bool)
        self.burst = np.zeros(n, dtype=bool)
        self.state = np.zeros(n, dtype=np.int8)
        self.i = 0
        self.sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict(case["sensor_name"], case["sensor"]),
                                                case["sensor_seed"])
        self.device = CustomTechDevice(case["threshold_ml"], **case["device"])
        self.user = SimulatedUser(UserScenario.from_dict(case["user_name"], case["user"]), case["user_seed"])
        self.stimulator = HypotheticalStimulator(BurstPattern.from_dict(case["stim_name"], case["stim"]))
        self.pressure = SyntheticImplantPressureChannel(PressureScenario.from_dict(case["pressure_name"],
                                                                                   case["pressure"]),
                                                        case["pressure_seed"])
        c = case["controller"]
        guard = SessionGuard(**case["guard"]) if case["guard"] else None     # Task 3; off by default
        self.controller = SafetyController(self.device, self.stimulator, c["max_duration_s"], c["volume_stop_ml"],
                                           c["pressure_ceiling_cmH2O"], c["lockout_s"], guard=guard)
        self.interval = case["ultrasound_interval_s"]
        self.stim_interval = case["ultrasound_interval_during_stim_s"]
        self.p_interval = c["pressure_sample_interval_s"]
        self.p_max_age = c["pressure_max_age_s"]
        self.next_read = self.interval
        self.next_p = 0.0
        self.last_p = None
        self.readings, self.alert_times = [], []
        # Task 8, off by default: an abstract second sensor B and a fusion rule. None = the old rig, exactly.
        f = case.get("fusion")
        self.fusion = SensorFusion(rule=f["rule"], **f.get("settings", {})) if f else None
        self.sensor_b = SyntheticUltrasoundSensor(SensorScenario.from_dict("sensor_b", f["sensor_b"]),
                                                  f["sensor_b_seed"]) if f else None
        self.readings_b, self.fusion_flags = [], []

    # truth lookups for the two sensors (they may look back in time for their delay)
    def _index(self, t_s):
        return min(max(int(round(t_s / self.dt)), 0), self.i)

    def true_volume_at(self, t_s):
        return float(self.V[self._index(t_s)])

    def true_pressure_at(self, t_s):
        return float(self.P[self._index(t_s)])

    def on_step(self, model):
        t, i = model.t, self.i
        self.V[i] = model.V_B / M3_PER_ML
        self.P[i] = model.p_D / PA_PER_CMH2O
        if self.stimulator.active and self.next_read > t + self.stim_interval:
            self.next_read = t + self.stim_interval          # sample faster while stimulating
        events = []
        if self.fusion is not None and self.stimulator.active != self.fusion._paused:
            if self.stimulator.active:                        # emptying: the comparison waits
                self.fusion.pause()
            else:
                self.fusion.resume()
        if t >= self.next_read - 1e-9:
            reading = self.sensor.read(t, self.true_volume_at)
            if self.fusion is not None:                       # sensor B reads at the same moment
                reading_b = self.sensor_b.read(t, self.true_volume_at)
                self.readings_b.append(reading_b)
                reading, fired = self.fusion.receive(reading, reading_b)
                if fired:
                    self.fusion_flags.append(t)
            self.readings.append(reading)
            events = self.device.receive(reading)
            self.next_read = t + (self.stim_interval if self.stimulator.active else self.interval)
        if t >= self.next_p - 1e-9:
            self.last_p = (t, self.pressure.read(t, self.true_pressure_at))
            self.next_p = t + self.p_interval
        p = self.last_p[1] if self.last_p is not None and t - self.last_p[0] <= self.p_max_age else None
        if self.controller.step(t, events, self.user.button_down(t), p):
            self.alert_times.append(t)
            self.user.feel_alert(t)                           # watch vibrates
        self.stim_active[i] = self.stimulator.active
        self.burst[i] = self.stimulator.burst_on(t)
        self.state[i] = STATE_CODES.get(self.controller.state, -1)
        self.i += 1


def default_case(**changes):
    """The Experiment 3 reference case; any field can be overridden."""
    sim, ctl = config.SIMULATION, config.CONTROLLER
    stim_name = config.REFERENCE_STIM.value
    sensor_name = config.value(config.EXPERIMENT3, "sensor_scenario")
    case = {
        "duration_s": config.value(config.EXPERIMENT3, "duration_s"), "phys_seed": 42, "sphincter_scaling": 1.0,
        "volume_ceiling_ml": config.value(config.SCI, "volume_ceiling_ml"),
        "sensor_name": sensor_name, "sensor": config.SENSOR_SCENARIOS.value[sensor_name], "sensor_seed": 1,
        "threshold_ml": config.value(config.EXPERIMENT3, "alert_threshold_ml"),
        "device": {k: config.value(config.DEVICE, k) for k in config.DEVICE},
        "user_name": "prompt", "user": config.USER_SCENARIOS.value["prompt"], "user_seed": 1,
        "stim_name": stim_name, "stim": config.STIM_PATTERNS.value[stim_name],
        "pressure_name": "ok", "pressure": config.PRESSURE_SCENARIOS.value["ok"], "pressure_seed": 1,
        "controller": {"max_duration_s": config.value(ctl, "max_duration_s"),
                       "volume_stop_ml": config.value(ctl, "volume_stop_ml"),
                       "pressure_ceiling_cmH2O": config.value(ctl, "reference_pressure_ceiling_cmH2O"),
                       "lockout_s": config.value(ctl, "lockout_s"),
                       "pressure_sample_interval_s": config.value(ctl, "pressure_sample_interval_s"),
                       "pressure_max_age_s": config.value(ctl, "pressure_max_age_s")},
        "ultrasound_interval_s": config.value(config.SENSOR, "sample_interval_s"),
        "ultrasound_interval_during_stim_s": config.value(ctl, "ultrasound_interval_during_stim_s")[0],
        "initial_volume_ml": config.value(sim, "initial_volume_ml"),
        "guard": None,
        "fusion": None,     # Task 8: {"rule", "sensor_b", "sensor_b_seed", optional "settings"}; None = off
    }
    for key, val in changes.items():
        if key in ("controller", "device") and isinstance(val, dict):
            case[key] = {**case[key], **val}
        else:
            case[key] = val
    return case


def run_closed_loop(case):
    """Simulate one person through the full Cue loop. Returns (data, rig)."""
    rig = CueRig(case)
    model = ClosedLoopLUT(rig, sci_enabled=True,
                          fullness_reference_ml=config.value(config.SCI, "fullness_reference_ml"),
                          volume_ceiling_ml=case["volume_ceiling_ml"], initial_volume_ml=case["initial_volume_ml"],
                          drive_above_reference=config.value(config.SCI, "drive_above_reference"),
                          overrides={"neural_args.somatic_a": CueLUT().neural_args["somatic_a"]
                                     * case["sphincter_scaling"]})
    with np.errstate(invalid="ignore", over="ignore"):
        data = simulate(model, case["duration_s"], config.value(config.SIMULATION, "dt_s"), case["phys_seed"],
                        config.value(config.SIMULATION, "inflow_noise"))
    n = len(data)
    data["stim_active"] = rig.stim_active[:n]
    data["burst_on"] = rig.burst[:n]
    data["controller_state"] = rig.state[:n]
    return data, rig


if __name__ == "__main__":
    data, rig = run_closed_loop(default_case())
    print(pd.DataFrame(rig.controller.sessions))
    for entry in rig.controller.log:
        print(entry)
