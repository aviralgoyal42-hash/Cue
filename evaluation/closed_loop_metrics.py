"""
Evaluation of closed-loop runs (Stage 5, Experiments 3 and 4). Uses ground truth, so it
belongs to the evaluation side only. Definitions follow docs/STAGE5_EXPERIMENT3_4_CRITERIA.md.
"""
import numpy as np

import config


def emptying_class(voided_fraction):
    c = config.EMPTYING_CLASSES.value
    if voided_fraction >= c["complete_min_fraction"]:
        return "complete"
    if voided_fraction >= c["partial_min_fraction"]:
        return "partial"
    return "none"


def session_table(data, rig, dt_s, ceiling_cmH2O, post_window_s):
    """One row per stimulation session, measured on the true model state."""
    t = data["t"].to_numpy()
    v = data["V_B_ml"].to_numpy()
    p = data["p_D_cmH2O"].to_numpy()
    q = data["Q_ml_s"].to_numpy()
    rows = []
    for s in rig.controller.sessions:
        if "stop_s" not in s:                 # still running when the simulation ended
            s = {**s, "stop_s": t[-1], "cutoff": "run_ended"}
        i0 = int(round(s["start_s"] / dt_s))
        i1 = int(round(s["stop_s"] / dt_s))
        i2 = min(int(round((s["stop_s"] + post_window_s) / dt_s)), len(t) - 1)
        before = v[max(i0 - 1, 0)]
        residual = v[i2]
        frac = (before - residual) / before if before > 0 else 0.0
        during = slice(i0, max(i1, i0 + 1))
        burst = data["burst_on"].to_numpy()[during]
        flow = q[during] > 0
        rows.append({
            "start_h": s["start_s"] / 3600, "duration_s": s["stop_s"] - s["start_s"], "cutoff": s["cutoff"],
            "true_volume_before_ml": before, "residual_ml": residual, "voided_fraction": frac,
            "emptying": emptying_class(frac), "voided_ge_50pct": frac >= 0.5,
            "max_true_p_D_during_cmH2O": float(p[during].max()),
            "exceeded_ceiling_by_cmH2O": float(max(p[during].max() - ceiling_cmH2O, 0.0)),
            "ceiling_exceeded_gt5": bool(p[during].max() > ceiling_cmH2O + 5.0),
            "flow_fraction_burst_on": float(flow[burst].mean()) if burst.any() else np.nan,
            "flow_fraction_burst_off": float(flow[~burst].mean()) if (~burst).any() else np.nan,
            "estimate_at_start_ml": s.get("estimate_at_start_ml"), "estimate_at_stop_ml": s.get("estimate_at_stop_ml"),
        })
    return rows


def invariants(rig, dt_s, max_duration_s):
    """Safety checks A2-A4, recomputed from the raw logs rather than trusted from the controller."""
    log = rig.controller.log
    starts = [t for t, e, _ in log if e == "STIMULATING"]
    presses = [down for down, _ in rig.user.presses]
    # A2: each start coincides (within one step) with a press edge, and an alert was sent before it
    alerts = [t for t, e, _ in log if e == "ALERT_SENT"]
    a2 = all(any(abs(st - pr) <= dt_s + 1e-9 for pr in presses) and any(a <= st for a in alerts) for st in starts)
    # A3: no start inside a lockout window
    lockouts = [(t, float(d.split()[1])) for t, e, d in log if e == "LOCKOUT"]
    a3 = all(not (lo < st < hi) for st in starts for lo, hi in lockouts)
    # A4: every finished session lasted at most max_duration + one step
    a4 = all(s.get("stop_s", np.inf) - s["start_s"] <= max_duration_s + dt_s + 1e-9
             for s in rig.controller.sessions if "stop_s" in s)
    return {"A2_start_only_after_press_and_alert": a2, "A3_no_start_in_lockout": a3,
            "A4_sessions_within_max_duration": a4, "n_presses": len(presses),
            "n_ignored_presses": sum(e == "PRESS_IGNORED" for _, e, _ in log)}


def run_summary(data, rig, dt_s, ceiling_cmH2O, post_window_s):
    """Run-level outcome: leakage outside sessions, overflow despite alert, pressure, volume."""
    t = data["t"].to_numpy()
    q = data["Q_ml_s"].to_numpy()
    in_session = np.zeros(len(t), dtype=bool)
    for s in rig.controller.sessions:
        stop = s.get("stop_s", t[-1])
        in_session |= (t >= s["start_s"]) & (t <= stop + post_window_s)
    leak = (q > 0) & ~in_session
    first_alert = rig.alert_times[0] if rig.alert_times else None
    after_alert = leak & (t >= first_alert) if first_alert is not None else np.zeros(len(t), dtype=bool)
    outside = data["p_D_cmH2O"].to_numpy()[~in_session]
    return {
        "n_alerts": len(rig.alert_times), "first_alert_h": first_alert / 3600 if first_alert else None,
        "n_sessions": len(rig.controller.sessions),
        "leaked_outside_sessions_ml": float((q[leak]).sum() * dt_s),
        "overflow_despite_alert": bool(after_alert.any()),
        "leaked_after_alert_ml": float((q[after_alert]).sum() * dt_s),
        "voided_in_sessions_ml": float((q[in_session]).sum() * dt_s),
        "max_true_p_D_outside_sessions_cmH2O": float(outside.max()) if len(outside) else np.nan,
        "max_volume_ml": float(data["V_B_ml"].max()), "final_volume_ml": float(data["V_B_ml"].iloc[-1]),
        "reached_ceiling": bool(data["V_B_ml"].max() >= config.value(config.SCI, "volume_ceiling_ml") - 1e-6),
    }
