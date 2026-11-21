"""
Synthetic IMPLANTED pressure channel: a hypothetical sensor used ONLY by the safety
controller's pressure-ceiling cutoff. It does not exist in Cue's hardware concept, has no
published accuracy, and every error value is ASSUMED.

Like the ultrasound proxy, it is allowed to see the true model pressure (a real implant
would sit in the real bladder) and passes on readings only.

    reading = true p_D(t - delay) x (1 + gain_error) + offset + Normal(0, noise_sd)
    faults:  missing with probability p; 'dead' from a given time (no readings at all);
             'stuck' at a constant value (reads the same number whatever happens).
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class PressureScenario:
    name: str = "ok"
    noise_sd_cmH2O: float = 0.0
    gain_error: float = 0.0
    offset_cmH2O: float = 0.0
    delay_s: float = 0.0
    missing_probability: float = 0.0
    dead_from_s: Optional[float] = None       # no readings at all from this time on
    stuck_at_cmH2O: Optional[float] = None    # always returns this value

    @classmethod
    def from_dict(cls, name, values):
        return cls(name=name, **values)


class SyntheticImplantPressureChannel:
    kind = "synthetic hypothetical implant pressure channel (not validated, not part of Cue hardware)"

    def __init__(self, scenario: PressureScenario, seed: int):
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)   # private: never touches numpy's global state

    def read(self, t_s, true_pressure_at):
        """Return a pressure reading in cmH2O, or None if there is no reading."""
        sc = self.scenario
        noise = self.rng.normal(0.0, sc.noise_sd_cmH2O) if sc.noise_sd_cmH2O > 0 else 0.0
        lost = self.rng.random() < sc.missing_probability
        if (sc.dead_from_s is not None and t_s >= sc.dead_from_s) or lost:
            return None
        if sc.stuck_at_cmH2O is not None:
            return sc.stuck_at_cmH2O
        p = true_pressure_at(max(t_s - sc.delay_s, 0.0))
        return p * (1 + sc.gain_error) + sc.offset_cmH2O + noise
