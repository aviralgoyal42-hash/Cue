"""
Safety controller (Stage 5): the state machine that decides when stimulation may start
and makes sure it always stops. This is CONTROL LOGIC ONLY. Its numbers (maximum duration,
volume stop, pressure ceiling, lockout) are ASSUMED and swept; none is a clinical setting.

States
  MONITORING        normal; the device estimates fullness
  FULL_DETECTED     the device raised ALERT                      (logged, passes straight on)
  ALERT_SENT        the watch vibrates                           (logged, passes straight on)
  WAITING_FOR_USER  nothing happens until the user presses the button
  STIMULATING       the hypothetical stimulator runs; three cutoffs are checked every step
  CUTOFF            stimulation stopped; the reason(s) are logged (passes straight on)
  LOCKOUT           no stimulation can start until `lockout_s` has passed
  CATHETER_ONLY     only with a SessionGuard (Task 3): stimulation is no longer offered, the
                    catheter alert is sent and repeated, and this lasts to the end of the run

Rules that can never be broken
  * Stimulation starts ONLY on a button press (the moment the button goes down) in
    WAITING_FOR_USER. The controller never starts it by itself.
  * A press with no pending alert, during stimulation or during lockout is ignored (logged).
    Holding the button down does not start, extend or restart anything.
  * Three INDEPENDENT cutoffs; any one of them stops stimulation:
      1. max_duration   time since start >= max_duration_s. Needs no sensor; always works.
      2. volume_stop    the DEVICE ESTIMATE (never true volume) <= volume_stop_ml, using only
                        an estimate made from a reading taken after stimulation started.
      3. pressure_ceiling  the synthetic implant pressure reading >= ceiling. A missing or
                        dead channel simply cannot fire; the other two still can.
  * With a SessionGuard, stimulation is never withheld silently: entering CATHETER_ONLY, and
    every press or device alert during it, sends the catheter alert in that same step.
    A catheter alert is not a vibration: it never invites the user to press the button.
"""
from .session_guard import SESSION_LIMIT

MONITORING, FULL_DETECTED, ALERT_SENT, WAITING = "MONITORING", "FULL_DETECTED", "ALERT_SENT", "WAITING_FOR_USER"
STIMULATING, CUTOFF, LOCKOUT = "STIMULATING", "CUTOFF", "LOCKOUT"
CATHETER_ONLY = "CATHETER_ONLY"


class SafetyController:
    def __init__(self, device, stimulator, max_duration_s, volume_stop_ml, pressure_ceiling_cmH2O, lockout_s,
                 guard=None):
        if guard is not None and guard.deadline_s > lockout_s:
            raise ValueError("The check deadline must end inside the lockout, or a new session "
                             "could be offered before the last one was checked.")
        self.guard = guard                               # optional SessionGuard (Task 3); None = off
        self.device = device
        self.stimulator = stimulator
        self.max_duration_s = max_duration_s
        self.volume_stop_ml = volume_stop_ml
        self.pressure_ceiling_cmH2O = pressure_ceiling_cmH2O
        self.lockout_s = lockout_s
        self.state = MONITORING
        self._was_down = False
        self._lockout_end = None
        self._start = None
        self.log = []          # (t_s, event, detail)
        self.sessions = []     # one dict per stimulation session

    def _note(self, t, event, detail=""):
        self.log.append((t, event, detail))

    def _catheter_only(self, t_s, reason):
        self.state = CATHETER_ONLY
        self.guard.latch(t_s, reason)
        self._note(t_s, CATHETER_ONLY, reason)

    def step(self, t_s, device_events, button_down, pressure_cmH2O):
        """Advance one time step. Returns True if the watch should vibrate now."""
        vibrate = False
        press = button_down and not self._was_down       # press edge only
        self._was_down = button_down
        alert_now = any(e.kind == "ALERT" for e in device_events)

        if self.guard is not None and self.state == LOCKOUT:
            failed = self.guard.check(t_s, self.device.estimate_ml, self.device.valid_readings)
            if failed is not None:
                self._catheter_only(t_s, failed)

        if self.state == MONITORING:
            if alert_now and self.guard is not None and self.guard.cap_reached:
                self._catheter_only(t_s, SESSION_LIMIT)
            elif alert_now:
                self._note(t_s, FULL_DETECTED)
                self._note(t_s, ALERT_SENT)
                self.state, vibrate = WAITING, True
            elif press:
                self._note(t_s, "PRESS_IGNORED", "no alert pending")
        elif self.state == WAITING:
            if press:
                self.state, self._start = STIMULATING, t_s
                self.stimulator.start(t_s)
                self.device.session_started()        # Task 6 monitor pauses (no effect when it is off)
                self._note(t_s, STIMULATING, "started by button press")
                self.sessions.append({"start_s": t_s, "estimate_at_start_ml": self.device.estimate_ml})
                if self.guard is not None:
                    self.guard.session_started(t_s, self.device.estimate_ml)
        elif self.state == STIMULATING:
            if press:
                self._note(t_s, "PRESS_IGNORED", "already stimulating")
            reasons = []
            if t_s - self._start >= self.max_duration_s:
                reasons.append("max_duration")
            fresh = self.device.last_valid_t is not None and self.device.last_valid_t > self._start
            if fresh and self.device.estimate_ml is not None and self.device.estimate_ml <= self.volume_stop_ml:
                reasons.append("volume_stop")
            if pressure_cmH2O is not None and pressure_cmH2O >= self.pressure_ceiling_cmH2O:
                reasons.append("pressure_ceiling")
            if reasons:
                self.stimulator.stop(t_s)
                self.device.session_stopped()        # Task 6 monitor starts again from fresh readings
                self._note(t_s, CUTOFF, "+".join(reasons))
                self.sessions[-1].update({"stop_s": t_s, "cutoff": "+".join(reasons),
                                          "estimate_at_stop_ml": self.device.estimate_ml,
                                          "pressure_reading_at_stop_cmH2O": pressure_cmH2O})
                self.state, self._lockout_end = LOCKOUT, t_s + self.lockout_s
                self._note(t_s, LOCKOUT, f"until {self._lockout_end:.0f} s")
                if self.guard is not None:
                    self.guard.session_stopped(t_s, self.device.valid_readings)
        elif self.state == LOCKOUT:
            if press:
                self._note(t_s, "PRESS_IGNORED", "lockout")
            if t_s >= self._lockout_end:
                self.state = MONITORING
                self.device.reset_alert()   # so a still-full bladder can raise a new alert
                self._note(t_s, MONITORING, "lockout over")
        elif self.state == CATHETER_ONLY:
            if press:
                self._note(t_s, "PRESS_IGNORED", "catheter only")
                self.guard.send(t_s, "press")
            if alert_now:
                self.guard.send(t_s, "device_alert")
            if self.guard.repeat_due(t_s):
                self.guard.send(t_s, "repeat")
        return vibrate
