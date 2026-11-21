"""
CustomTechDevice: the Cue wearable's software.

RULE: the device only ever receives `Reading` objects from the sensor (a time and a
volume reading, or "missing"). It never receives, imports or computes the true
bladder volume or pressure. Its accuracy is measured afterwards by the evaluation code
(evaluation/experiment2_metrics.py), which is the only place ground truth is used.
The device also does not use pressure at all: in this model pressure falls when the
bladder over-fills, so it would be a misleading fullness signal.

What it does with each reading
------------------------------
1. Estimate:  median of the last `median_window` valid readings. A median ignores a single
              wild reading better than an average does.
2. Stale:     if no valid reading has arrived for `stale_timeout_s`, it raises SENSOR_STALE
              once (the device knows it is blind), and SENSOR_OK when readings return.
3. Alert:     when `confirm_n` consecutive valid estimates are at or above
              `alert_threshold_ml`, it raises ALERT (the watch would vibrate). It does not
              alert again until the estimate has fallen `rearm_hysteresis_ml` below the
              threshold (ALERT_CLEARED), so one full bladder gives one alert, not hundreds.
The device never starts emptying. In Stage 5 an alert only invites the user to press
the button.

Optional (Task 6, off by default): a MisalignmentMonitor (devices/misalignment_monitor.py).
4. Patch check: when the monitor sees the readings fall in a way the bladder cannot, or
              readings going missing more often, the device raises CHECK_PATCH (the watch
              would ask the user to look at the patch).
5. Correction: if the monitor measured the fall (say the patch now reads at 0.75 of what it
              did), the device divides its estimate by that ratio until the user confirms
              the patch is back in place (`patch_reseated`). A wrong correction makes the
              estimate too HIGH, so the alert comes early, not late.
"""
from collections import deque
from dataclasses import dataclass

import numpy as np

from .misalignment_monitor import MisalignmentMonitor

ALERT, ALERT_CLEARED, SENSOR_STALE, SENSOR_OK = "ALERT", "ALERT_CLEARED", "SENSOR_STALE", "SENSOR_OK"
POSSIBLE_MISALIGNMENT = "POSSIBLE_MISALIGNMENT"      # the Experiment 6 detector (kept as it was)
CHECK_PATCH, PATCH_RESEATED = "CHECK_PATCH", "PATCH_RESEATED"   # Task 6 monitor


@dataclass(frozen=True)
class DeviceEvent:
    t_s: float
    kind: str
    estimate_ml: float


class CustomTechDevice:
    def __init__(self, alert_threshold_ml, median_window=5, confirm_n=3, rearm_hysteresis_ml=50.0,
                 stale_timeout_s=600.0, misalignment_drop_fraction=None, misalignment_window_s=900.0,
                 misalignment_min_ml=100.0, misalignment_monitor=None):
        self.alert_threshold_ml = alert_threshold_ml
        self.confirm_n = confirm_n
        self.rearm_hysteresis_ml = rearm_hysteresis_ml
        self.stale_timeout_s = stale_timeout_s
        self._recent = deque(maxlen=median_window)   # last valid readings (mL)
        self._above = 0                              # consecutive valid estimates >= threshold
        self.alert_active = False
        self.stale = False
        self._last_valid_t = None
        self._first_t = None
        self.estimate_ml = None                      # current fullness estimate (None = no data yet)
        self.valid_readings = 0                      # valid readings received so far
        self.history = []                            # one row per reading received
        self.events = []
        # Optional misalignment detector (Experiment 6; off by default so earlier results are unchanged)
        self.misalignment_drop_fraction = misalignment_drop_fraction
        self.misalignment_window_s = misalignment_window_s
        self.misalignment_min_ml = misalignment_min_ml
        self._recent_estimates = deque()             # (t, estimate) within the window
        self.misalignment_flagged = False
        # Optional Task 6 monitor: None = off (earlier results unchanged), or a dict of its settings
        self.monitor = None if misalignment_monitor is None else MisalignmentMonitor(**misalignment_monitor)
        self.patch_checks = []                       # one dict per CHECK_PATCH (time, rule, ratio)

    @property
    def correction_ratio(self):
        """What the estimate is divided by. 1.0 unless the monitor measured a fall in the readings."""
        return 1.0 if self.monitor is None else self.monitor.ratio

    def receive(self, reading):
        """Process one sensor reading; return the list of events it caused."""
        new_events = []
        if self._first_t is None:
            self._first_t = reading.t_s
        rules = self.monitor.receive(reading) if self.monitor is not None else []
        if reading.valid:
            self._recent.append(reading.volume_ml)
            self.valid_readings += 1
            self.estimate_ml = float(np.median(self._recent)) / self.correction_ratio
            self._last_valid_t = reading.t_s
            if self.stale:
                self.stale = False
                new_events.append(DeviceEvent(reading.t_s, SENSOR_OK, self.estimate_ml))
            new_events += self._update_alert(reading.t_s)
            new_events += self._check_misalignment(reading.t_s)
        else:
            since = reading.t_s - (self._last_valid_t if self._last_valid_t is not None else self._first_t)
            if not self.stale and since >= self.stale_timeout_s:
                self.stale = True
                new_events.append(DeviceEvent(reading.t_s, SENSOR_STALE, self.estimate_ml))
        for rule in rules:                           # Task 6 monitor: ask the user to check the patch
            self.patch_checks.append({"t_s": reading.t_s, "rule": rule, "ratio": self.correction_ratio})
            new_events.append(DeviceEvent(reading.t_s, CHECK_PATCH, self.estimate_ml))
        self.history.append({"t_s": reading.t_s, "reading_ml": reading.volume_ml, "valid": reading.valid,
                             "estimate_ml": self.estimate_ml, "alert_active": self.alert_active,
                             "stale": self.stale})
        self.events += new_events
        return new_events

    def _update_alert(self, t_s):
        if self.estimate_ml >= self.alert_threshold_ml:
            self._above += 1
        else:
            self._above = 0
        if not self.alert_active and self._above >= self.confirm_n:
            self.alert_active = True
            return [DeviceEvent(t_s, ALERT, self.estimate_ml)]
        if self.alert_active and self.estimate_ml < self.alert_threshold_ml - self.rearm_hysteresis_ml:
            self.alert_active = False
            return [DeviceEvent(t_s, ALERT_CLEARED, self.estimate_ml)]
        return []

    def _check_misalignment(self, t_s):
        """Flag once if the estimate suddenly falls well below its recent peak (no emptying in monitoring)."""
        if self.misalignment_drop_fraction is None or self.misalignment_flagged:
            return []
        self._recent_estimates.append((t_s, self.estimate_ml))
        while self._recent_estimates and self._recent_estimates[0][0] < t_s - self.misalignment_window_s:
            self._recent_estimates.popleft()
        peak = max(e for _, e in self._recent_estimates)
        if peak >= self.misalignment_min_ml and self.estimate_ml < (1 - self.misalignment_drop_fraction) * peak:
            self.misalignment_flagged = True
            return [DeviceEvent(t_s, POSSIBLE_MISALIGNMENT, self.estimate_ml)]
        return []

    # ---- Task 6 monitor hooks. All three do nothing when the monitor is off.
    def session_started(self):
        """Called by the safety controller when stimulation starts: emptying is a real fall in
        volume, so the monitor must not look at it."""
        if self.monitor is not None:
            self.monitor.pause()

    def session_stopped(self):
        """Called by the safety controller when stimulation stops: the monitor starts again
        from fresh readings. A correction already in use stays (the patch has not moved back)."""
        if self.monitor is not None:
            self.monitor.resume()

    def patch_reseated(self, t_s):
        """The user confirms the patch is back in place: drop the correction, forget the readings
        taken while it was out of place, and let the monitor flag again."""
        if self.monitor is not None:
            self.monitor.reset()
            self._recent.clear()
            self._above = 0
            self.events.append(DeviceEvent(t_s, PATCH_RESEATED, self.estimate_ml))

    @property
    def last_valid_t(self):
        """Time of the last valid reading (None if there has been none)."""
        return self._last_valid_t

    def reset_alert(self):
        """Called by the safety controller after a lockout: forget the old alert so that a
        bladder that is still full can raise a new one (after confirm_n fresh estimates)."""
        self.alert_active = False
        self._above = 0

    def alert_times(self):
        return [e.t_s for e in self.events if e.kind == ALERT]
