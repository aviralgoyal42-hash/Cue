"""
Evaluation of the session cap and post-session check (Experiment 7). Uses ground truth, so it
belongs to the evaluation side only; the rule itself never sees any of this. Definitions follow
docs/EXPERIMENT7_CRITERIA.md.
"""
import numpy as np

from devices.session_guard import NO_DROP, TIMED_OUT, SESSION_LIMIT

FAULT_REASONS = (NO_DROP, TIMED_OUT)
FAILED_BELOW = 0.10         # the existing "none" emptying class
EMPTIED_FROM = 0.50         # the existing P1 boundary


def check_rows(rig):
    """The check that followed each session, in session order (empty with the rule off)."""
    guard = rig.controller.guard
    return list(guard.checks) if guard else []


def add_checks_to_sessions(session_rows, rig):
    checks = check_rows(rig)
    for i, row in enumerate(session_rows):
        c = checks[i] if i < len(checks) else {}
        row.update({"check_estimate_before_ml": c.get("estimate_before_ml"), "check_estimate_after_ml": c.get("estimate_after_ml"),
                    "check_drop": c.get("drop"), "check_passed": c.get("passed"), "check_reason": c.get("reason")})
    return session_rows


def first_leak_s(data, rig, post_window_s):
    t = data["t"].to_numpy()
    in_session = np.zeros(len(t), dtype=bool)
    for s in rig.controller.sessions:
        in_session |= (t >= s["start_s"]) & (t <= s.get("stop_s", t[-1]) + post_window_s)
    leak = (data["Q_ml_s"].to_numpy() > 0) & ~in_session
    return float(t[leak.argmax()]) if leak.any() else None


def never_silent(rig, dt_s, end_s):
    """I2 and I3, recomputed from the raw logs rather than trusted from the controller."""
    guard = rig.controller.guard
    if guard is None or guard.latched_reason is None:
        return {"I2_nothing_offered_after_latch": True, "I3_never_silent": True, "presses_while_latched": 0}
    latched, alerts = guard.latched_t_s, [a["t_s"] for a in guard.alerts]
    log = rig.controller.log
    i2 = (not any(s["start_s"] > latched for s in rig.controller.sessions)
          and not any(t > latched for t in rig.alert_times)
          and not any(e in ("STIMULATING", "ALERT_SENT") and t > latched for t, e, _ in log))
    presses = [t for t, e, d in log if e == "PRESS_IGNORED" and d == "catheter only"]
    device_alerts = [e.t_s for e in rig.device.events if e.kind == "ALERT" and e.t_s > latched]
    gaps = np.diff(alerts + [end_s])
    i3 = (latched in alerts and all(t in alerts for t in presses) and all(t in alerts for t in device_alerts)
          and bool((gaps <= guard.repeat_s + 2 * dt_s + 1e-6).all()))
    return {"I2_nothing_offered_after_latch": bool(i2), "I3_never_silent": bool(i3), "presses_while_latched": len(presses)}


def guard_summary(data, rig, session_rows, fault_onset_s, dt_s, post_window_s):
    """Run-level results for one person. `session_rows` must come from closed_loop_metrics."""
    guard = rig.controller.guard
    t, v = data["t"].to_numpy(), data["V_B_ml"].to_numpy()
    sessions = rig.controller.sessions
    leak_s = first_leak_s(data, rig, post_window_s)
    reason = guard.latched_reason if guard else None
    latched = guard.latched_t_s if guard else None
    out = {"catheter_reason": reason or "", "catheter_alert_h": latched / 3600 if latched is not None else np.nan,
           "n_catheter_alerts": len(guard.alerts) if guard else 0,
           "fault_alert": reason in FAULT_REASONS, "session_limit_alert": reason == SESSION_LIMIT,
           "true_volume_at_catheter_alert_ml": float(np.interp(latched, t, v)) if latched is not None else np.nan,
           "first_leak_h": leak_s / 3600 if leak_s is not None else np.nan,
           "fault_alert_before_first_leak": reason in FAULT_REASONS and (leak_s is None or latched < leak_s),
           "sessions_below_100ml": sum(s["true_volume_before_ml"] < 100.0 for s in session_rows),
           "checks_done": len(check_rows(rig)), "checks_failed": sum(not c["passed"] for c in check_rows(rig)),
           **never_silent(rig, dt_s, float(t[-1]))}

    # The session whose check raised the fault alert
    trigger = session_rows[len(check_rows(rig)) - 1] if reason in FAULT_REASONS else None
    out["trigger_voided_fraction"] = trigger["voided_fraction"] if trigger else np.nan
    out["false_alarm"] = bool(trigger is not None and trigger["voided_fraction"] >= EMPTIED_FROM)

    # T1: sessions after the sensor fault began
    after = [s for s in sessions if fault_onset_s is not None and s["start_s"] >= fault_onset_s]
    out["sessions_after_fault_onset"] = len(after)
    stop = after[0].get("stop_s") if after else None
    out["alert_s_after_first_session_after_onset"] = (latched - stop if stop is not None and reason in FAULT_REASONS
                                                      else np.nan)

    # T2: the first session that failed, judged on the true volume
    failed = next((i for i, s in enumerate(session_rows) if s["voided_fraction"] < FAILED_BELOW), None)
    out["first_failed_session"] = failed if failed is not None else -1
    out["sessions_after_first_failed"] = len(sessions) - failed - 1 if failed is not None else 0
    stop = sessions[failed].get("stop_s") if failed is not None else None
    out["alert_s_after_first_failed"] = latched - stop if stop is not None and reason in FAULT_REASONS else np.nan
    return out
