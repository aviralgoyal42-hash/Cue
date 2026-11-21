"""
Ultrasound bladder sensor: a SYNTHETIC EXPERIMENTAL PROXY.

Three different things could sit behind the word "sensor". Only the first exists here:
  1. SyntheticUltrasoundSensor  - a mathematical stand-in: true volume plus made-up
     (ASSUMED) error. It is NOT a validated ultrasound model and NOT a real device.
  2. ValidatedUltrasoundModel   - would turn simulated echoes into volume using a published,
     validated method. Not available: no validated model or SCI dataset was found
     (Kim & Kim 2026, Int Neurourol J 30:95-104: no prospective validation in adults with SCI).
  3. RealUltrasoundDevice       - real hardware. Not part of this project (no hardware).

The sensor is the ONLY Cue component allowed to see true volume, because a real patch
measures the real bladder. It passes on readings only; the device never sees the truth.

How a reading is made (all magnitudes come from config.SENSOR_SCENARIOS; ASSUMED except
the 11.17% best-case anchor from Toymus et al. 2024):

    v      = true volume at (t - delay)                  processing / transmission delay
    gain   = (1 + gain_error) x (1 + drift_per_hour x t_h) x misalignment_gain (after misalignment)
    e      ~ Normal(0, s), s = mean_relative_error x sqrt(pi / 2)
    reading = max(0, v x gain x (1 + e) + offset_ml)     or MISSING with probability p

Why s = MRE x sqrt(pi/2): for a normal error with standard deviation s, the average size
of the error is s x sqrt(2/pi). Choosing s this way makes the mean |relative error| equal
the target, e.g. 11.17%.
"""
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

SENSOR_KIND = "synthetic experimental proxy (not validated)"


@dataclass(frozen=True)
class Reading:
    """What the sensor sends to the device: a time and a volume estimate (or nothing)."""
    t_s: float
    volume_ml: Optional[float]          # None = missing reading

    @property
    def valid(self):
        return self.volume_ml is not None


@dataclass(frozen=True)
class SensorScenario:
    name: str = "ideal"
    mean_relative_error: float = 0.0     # target mean |relative error| of the random part
    gain_error: float = 0.0              # fixed calibration error (-0.2 = reads 20% low)
    offset_ml: float = 0.0               # fixed additive error
    drift_per_hour: float = 0.0          # gain changes by this fraction per hour
    delay_s: float = 0.0                 # reading reflects the bladder this long ago
    missing_probability: float = 0.0     # chance that a reading is lost
    misalignment_start_h: Optional[float] = None   # patch moves / posture changes at this time
    misalignment_gain: float = 1.0       # extra gain after misalignment (0.7 = reads 30% low)
    misalignment_missing_probability: float = 0.0  # extra chance of loss after misalignment
    stuck_from_h: Optional[float] = None # from this time the sensor repeats one value ...
    stuck_at_ml: Optional[float] = None  # ... this one (a frozen-output fault)

    @classmethod
    def from_dict(cls, name, values):
        return cls(name=name, **values)


class SyntheticUltrasoundSensor:
    kind = SENSOR_KIND

    def __init__(self, scenario: SensorScenario, seed: int):
        self.scenario = scenario
        # A private random generator: the sensor never touches numpy's global random
        # state, which the upstream physiology uses for its urine-production noise.
        self.rng = np.random.default_rng(seed)
        self.sigma = scenario.mean_relative_error * np.sqrt(np.pi / 2)

    def read(self, t_s: float, true_volume_at: Callable[[float], float]) -> Reading:
        """Take one reading at time t_s. `true_volume_at(t)` gives the true volume in mL."""
        sc = self.scenario
        t_h = t_s / 3600.0
        misaligned = sc.misalignment_start_h is not None and t_h >= sc.misalignment_start_h
        # Draw the random numbers first, always in the same order, so a run is reproducible.
        noise = self.rng.normal(0.0, self.sigma) if self.sigma > 0 else 0.0
        lost = self.rng.random() < sc.missing_probability
        lost_misaligned = self.rng.random() < (sc.misalignment_missing_probability if misaligned else 0.0)
        if lost or lost_misaligned:
            return Reading(t_s, None)
        if sc.stuck_from_h is not None and t_h >= sc.stuck_from_h:
            return Reading(t_s, sc.stuck_at_ml)
        v = true_volume_at(max(t_s - sc.delay_s, 0.0))
        gain = (1 + sc.gain_error) * (1 + sc.drift_per_hour * t_h) * (sc.misalignment_gain if misaligned else 1.0)
        return Reading(t_s, max(0.0, v * gain * (1 + noise) + sc.offset_ml))


class ValidatedUltrasoundModel:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("No validated ultrasound volume model for SCI exists in this project "
                                  "(see docs/STAGE1_REPOSITORY_REVIEW.md section 7).")


class RealUltrasoundDevice:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError("Project Cue has no hardware; only the synthetic proxy is available.")
