"""
SessionGuard (Task 3): a session cap plus a check after every session. Rule and criteria are
frozen in docs/EXPERIMENT7_CRITERIA.md. All its numbers are ASSUMED; none is a clinical setting.

RULE: this file only ever receives numbers made by the device (its estimate and how many
valid readings it has had). It imports nothing and knows nothing about the bladder.

Why it exists: a stuck estimate or a failed session could otherwise lead to stimulation again
and again. Blocking stimulation silently would be worse, because the person relies on the
device, so every way of stopping the offer of stimulation also tells them to catheterise.

    Session cap   at most `session_cap` sessions in a 12 h run (per run, not per day). The cap
                  acts only when the device next wants to offer another session.
    Check         drop = (estimate at start - estimate after) / estimate at start. "After" is
                  taken once `readings_needed` new valid readings have arrived, so with a
                  median of 5 and readings_needed = 5 it holds no reading from before or
                  during the session. A drop of at least `min_drop_fraction` passes.
    Timeout       if those readings do not arrive within `deadline_s`, the check cannot pass,
                  so it counts as a failure. Known cost: a long sensor dropout latches the
                  device even if the session worked. A real device would need a reset path.

A failure or a reached cap latches the controller in CATHETER_ONLY for the rest of the run.
"""
FAULT_MESSAGE = "device fault suspected, use catheter"
LIMIT_MESSAGE = "session limit reached, use catheter"
NO_DROP, TIMED_OUT, SESSION_LIMIT = "no_volume_drop", "check_timed_out", "session_limit"


class SessionGuard:
    def __init__(self, session_cap, min_drop_fraction, readings_needed, deadline_s, repeat_s):
        self.session_cap = session_cap
        self.min_drop_fraction = min_drop_fraction
        self.readings_needed = readings_needed
        self.deadline_s = deadline_s
        self.repeat_s = repeat_s
        self.sessions_started = 0
        self.latched_reason = None
        self.latched_t_s = None
        self.checks = []           # one dict per finished check, in session order
        self.alerts = []           # every catheter alert sent: t_s, message, because
        self._pending = None       # the check waiting for its readings

    @property
    def cap_reached(self):
        return self.sessions_started >= self.session_cap

    def session_started(self, t_s, estimate_ml):
        self.sessions_started += 1
        self._pending = {"start_s": t_s, "estimate_before_ml": estimate_ml}

    def session_stopped(self, t_s, valid_readings):
        self._pending.update({"stop_s": t_s, "valid_at_stop": valid_readings})

    def check(self, t_s, estimate_ml, valid_readings):
        """Called each step during lockout. Returns the failure reason, or None."""
        c = self._pending
        if c is None:
            return None
        if valid_readings - c["valid_at_stop"] >= self.readings_needed:
            before = c["estimate_before_ml"]
            drop = (before - estimate_ml) / before if before > 0 else 0.0
            passed = before > 0 and drop >= self.min_drop_fraction
            return self._finish(t_s, estimate_ml, drop, passed, None if passed else NO_DROP)
        if t_s - c["stop_s"] >= self.deadline_s:
            return self._finish(t_s, None, None, False, TIMED_OUT)
        return None

    def _finish(self, t_s, estimate_ml, drop, passed, reason):
        self.checks.append({**self._pending, "checked_s": t_s, "estimate_after_ml": estimate_ml, "drop": drop,
                            "passed": passed, "reason": reason})
        self._pending = None
        return reason

    def latch(self, t_s, reason):
        self.latched_reason, self.latched_t_s = reason, t_s
        self.send(t_s, reason)

    def send(self, t_s, because):
        message = LIMIT_MESSAGE if self.latched_reason == SESSION_LIMIT else FAULT_MESSAGE
        self.alerts.append({"t_s": t_s, "message": message, "because": because})

    def repeat_due(self, t_s):
        return t_s - self.alerts[-1]["t_s"] >= self.repeat_s
