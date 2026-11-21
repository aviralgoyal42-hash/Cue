"""
Simulated user and watch button (Stage 5). Every behaviour here is ASSUMED: there are no
data on how people with SCI respond to a bladder-fullness alert.

The user only ever feels the watch alert; they never see any volume. Each press holds the
button down for `hold_s` seconds. The safety controller reacts only to the moment the button
goes DOWN (a press edge), so holding it does nothing extra.

Scenarios (config.USER_SCENARIOS):
  prompt / delayed    press once, after a delay drawn uniformly from [delay_min_s, delay_max_s]
                      after each alert
  no_press            never responds
  accidental          presses at fixed times whatever the device says (e.g. with no alert)
  press_in_lockout    responds promptly, then presses again `second_press_after_s` after the
                      first press, which lands inside the lockout after a short session
  held_button         responds promptly but holds the button down for a long time
"""
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class UserScenario:
    name: str = "prompt"
    responds_to_alert: bool = True
    delay_min_s: float = 30.0
    delay_max_s: float = 300.0
    hold_s: float = 0.5
    accidental_press_times_s: tuple = field(default_factory=tuple)
    second_press_after_s: float = None

    @classmethod
    def from_dict(cls, name, values):
        values = dict(values)
        if "accidental_press_times_s" in values:
            values["accidental_press_times_s"] = tuple(values["accidental_press_times_s"])
        return cls(name=name, **values)


class SimulatedUser:
    def __init__(self, scenario: UserScenario, seed: int):
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)
        self.presses = [(t, t + scenario.hold_s) for t in scenario.accidental_press_times_s]  # (down, up)
        self.alerts_felt = []

    def feel_alert(self, t_s):
        """The watch vibrated at t_s. Decide whether and when to press."""
        self.alerts_felt.append(t_s)
        sc = self.scenario
        if not sc.responds_to_alert:
            return
        delay = self.rng.uniform(sc.delay_min_s, sc.delay_max_s)
        self.presses.append((t_s + delay, t_s + delay + sc.hold_s))
        if sc.second_press_after_s is not None:
            t2 = t_s + delay + sc.second_press_after_s
            self.presses.append((t2, t2 + 0.5))

    def button_down(self, t_s):
        return any(down <= t_s < up for down, up in self.presses)
