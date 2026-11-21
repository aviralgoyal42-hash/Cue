"""
Evaluation for Experiment 2. This is the ONLY place where ground truth meets the
device's output. Definitions follow docs/EXPERIMENT2_SUCCESS_CRITERIA.md (frozen).
"""
import numpy as np

from devices import ALERT, SENSOR_STALE


def truth_lookup(truth):
    """Return f(t_s) -> true volume in mL, by linear interpolation of the 1 Hz trace."""
    t = truth["t"].to_numpy()
    v = truth["V_B_ml"].to_numpy()
    return lambda t_s: float(np.interp(t_s, t, v))


def adverse_event(truth, reference_volume_ml):
    """Earliest of: true volume first reaches V_ref, or leakage first starts. (time_s, kind)."""
    candidates = []
    reached = np.flatnonzero(truth["V_B_ml"].to_numpy() >= reference_volume_ml)
    if len(reached):
        candidates.append((float(truth["t"].iloc[reached[0]]), "reached_V_ref"))
    leaking = np.flatnonzero(((truth["Q_ml_s"] > 0) & (truth["voiding"] == 0)).to_numpy())
    if len(leaking):
        candidates.append((float(truth["t"].iloc[leaking[0]]), "leak_onset"))
    return min(candidates) if candidates else (None, "none")


def classify_alerts(alert_times_s, true_volume_at, t_adverse_s, false_below_ml):
    """Sort a run's alerts into false / useful / late / missed (see the criteria file)."""
    volumes = [true_volume_at(t) for t in alert_times_s]
    n_false = sum(v < false_below_ml for v in volumes)
    genuine = [(t, v) for t, v in zip(alert_times_s, volumes) if v >= false_below_ml]
    out = {"n_alerts": len(alert_times_s), "n_false_alerts": n_false, "any_false_alert": n_false > 0,
           "useful": False, "late": False, "missed": not genuine,
           "first_alert_t_h": alert_times_s[0] / 3600 if alert_times_s else None,
           "first_genuine_alert_t_h": None, "true_volume_at_genuine_alert_ml": None, "lead_time_min": None}
    if genuine:
        t, v = genuine[0]
        out["first_genuine_alert_t_h"] = t / 3600
        out["true_volume_at_genuine_alert_ml"] = v
        if t_adverse_s is None or t < t_adverse_s:
            out["useful"] = True
            if t_adverse_s is not None:
                out["lead_time_min"] = (t_adverse_s - t) / 60
        else:
            out["late"] = True
    return out


def sensor_errors(readings, true_volume_at, floor_ml):
    """Accuracy of the readings against true volume AT THE READING TIME (so delay counts as error)."""
    valid = [r for r in readings if r.valid]
    out = {"missing_fraction": 1 - len(valid) / len(readings) if readings else None}
    if not valid:
        return {**out, "mae_ml": None, "rmse_ml": None, "bias_ml": None, "mean_relative_error": None}
    m = np.array([r.volume_ml for r in valid])
    v = np.array([true_volume_at(r.t_s) for r in valid])
    err = m - v
    rel = np.abs(err[v >= floor_ml]) / v[v >= floor_ml]
    return {**out, "mae_ml": float(np.mean(np.abs(err))), "rmse_ml": float(np.sqrt(np.mean(err ** 2))),
            "bias_ml": float(np.mean(err)), "error_sd_ml": float(np.std(err)),
            "mean_relative_error": float(np.mean(rel)) if len(rel) else None}


def estimate_errors(history, true_volume_at):
    """Accuracy of the device's own estimate (after its median filter)."""
    rows = [h for h in history if h["estimate_ml"] is not None]
    if not rows:
        return {"estimate_mae_ml": None, "estimate_rmse_ml": None}
    err = np.array([h["estimate_ml"] - true_volume_at(h["t_s"]) for h in rows])
    return {"estimate_mae_ml": float(np.mean(np.abs(err))), "estimate_rmse_ml": float(np.sqrt(np.mean(err ** 2)))}


def stale_detection(readings, events, timeout_s):
    """Count gaps without valid readings lasting >= timeout, and how many the device flagged (C4)."""
    stale_times = [e.t_s for e in events if e.kind == SENSOR_STALE]
    gaps, flagged = 0, 0
    last_valid = readings[0].t_s if readings else 0.0
    gap_open = False
    for r in readings + [None]:                       # None marks the end of the run
        t = r.t_s if r is not None else readings[-1].t_s
        if r is None or r.valid:
            if gap_open:
                gaps += 1
                flagged += any(last_valid + timeout_s <= s <= t for s in stale_times)
            gap_open = False
            if r is not None:
                last_valid = r.t_s
        elif t - last_valid >= timeout_s:
            gap_open = True
    return gaps, flagged


def alert_events(events):
    return [e.t_s for e in events if e.kind == ALERT]
