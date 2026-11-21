"""
Measurements on a finished run. These read ground truth, so they belong to the
EVALUATION side only. The Cue device must never call them.
"""
import numpy as np
import pandas as pd


def _runs(mask):
    """(start, end_exclusive) index pairs of consecutive True values."""
    m = np.asarray(mask, dtype=int)
    edges = np.diff(np.concatenate([[0], m, [0]]))
    return list(zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1)))


def leak_episodes(data, dt_s):
    """Outflow while NO void is active = involuntary leakage (model prediction).

    Leaked volume is outflow x time step, summed over the episode.
    """
    rows = []
    for start, end in _runs((data["Q"] > 0) & (data["voiding"] == 0)):
        ep = data.iloc[start:end]
        before = data["V_B_ml"].iloc[start - 1] if start > 0 else data["V_B_ml"].iloc[0]
        rows.append({
            "start_h": data["t"].iloc[start] / 3600,
            "duration_s": (end - start) * dt_s,
            "leaked_ml": float((ep["Q_ml_s"] * dt_s).sum()),
            "volume_before_ml": float(before),
            "volume_after_ml": float(ep["V_B_ml"].iloc[-1]),
            "peak_p_D_cmH2O": float(ep["p_D_cmH2O"].max()),
            "peak_flow_ml_s": float(ep["Q_ml_s"].max()),
        })
    return pd.DataFrame(rows, columns=["start_h", "duration_s", "leaked_ml", "volume_before_ml",
                                       "volume_after_ml", "peak_p_D_cmH2O", "peak_flow_ml_s"])


def clipped_volume_ml(data, dt_s, initial_volume_ml=0.0):
    """Volume the upstream clip removed (positive = inflow discarded at the ceiling).

    Upstream step i does V[i] = clip(V[i-1] + dt * (Q_in[i] - Q[i-1])). Whatever the clip
    takes away is the difference between that unclipped value and the stored V[i].
    """
    v = data["V_B_ml"].to_numpy()
    q_in = data["Q_in_ml_s"].to_numpy()
    q_prev = np.concatenate([[0.0], data["Q_ml_s"].to_numpy()[:-1]])
    v_prev = np.concatenate([[initial_volume_ml], v[:-1]])
    unclipped = v_prev + dt_s * (q_in - q_prev)
    return unclipped - v   # per-step, mL


def run_summary(data, dt_s, initial_volume_ml=0.0, ceiling_ml=None):
    """Headline numbers of one run (model outputs, not facts)."""
    clip = clipped_volume_ml(data, dt_s, initial_volume_ml)
    leaks = leak_episodes(data, dt_s)
    voids = _runs(data["voiding"] == 1)
    t_h = data["t"] / 3600
    out = {
        "duration_h": float(t_h.iloc[-1] + dt_s / 3600),
        "urine_produced_ml": float((data["Q_in_ml_s"] * dt_s).sum()),
        "n_voluntary_voids": len(voids),
        "voided_ml": float(sum((data["Q_ml_s"].iloc[s:e] * dt_s).sum() for s, e in voids)),
        "n_leak_episodes": len(leaks),
        "leaked_ml": float(leaks["leaked_ml"].sum()) if len(leaks) else 0.0,
        "first_leak_h": float(leaks["start_h"].iloc[0]) if len(leaks) else None,
        "max_volume_ml": float(data["V_B_ml"].max()),
        "final_volume_ml": float(data["V_B_ml"].iloc[-1]),
        "max_p_D_cmH2O": float(data["p_D_cmH2O"].max()),
        "final_p_D_cmH2O": float(data["p_D_cmH2O"].iloc[-1]),
        "max_flow_ml_s": float(data["Q_ml_s"].max()),
        "discarded_at_ceiling_ml": float(clip[clip > 0].sum()),
        "max_numerical_clip_at_zero_ml": float(-clip[clip < 0].min()) if (clip < 0).any() else 0.0,
    }
    if ceiling_ml is not None:
        at_ceiling = data["V_B_ml"] >= ceiling_ml - 1e-9
        out["hours_at_ceiling"] = float(at_ceiling.sum() * dt_s / 3600)
    for threshold in (400, 500):
        reached = np.flatnonzero(data["V_B_ml"].to_numpy() >= threshold)
        out[f"first_reach_{threshold}ml_h"] = float(t_h.iloc[reached[0]]) if len(reached) else None
    return out
