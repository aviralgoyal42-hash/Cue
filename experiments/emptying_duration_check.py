"""
Emptying duration per session, and whether the model's sphincter responds faster than its
bladder. READ-ONLY: no new simulation, no parameter changes.

Definitions were frozen first in docs/EMPTYING_DURATION_CHECK.md. In short:
  * data: the 48 saved 1 Hz traces results/stage6/traces/exp3_*.csv (seed 42, sphincter x1.0,
    threshold 400 mL, max duration 60 s). exp4_*.csv are byte-identical copies, so are skipped.
  * a "flowing second" is one in which TRUE volume falls by more than 0.1 mL. Flow is not judged
    from Q_ml_s, because the model reports flow when the bladder is already empty (E67).
  * an emptying episode starts at session start and ends at the last flowing second that is
    followed by 30 s with no flow (or at the next session, or the end of the trace).
  * emptying duration = end of that last flowing second - session start.

Part B only reads constants from the upstream model and evaluates its storage-phase drive
formulas at fixed states. Nothing is stepped in time.

Writes to results/emptying_check/ (a new folder; old results are not touched).
Evaluation code: it reads ground truth (V_B_ml), which is allowed only on the evaluation side.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config                                  # noqa: E402
from cue_model.sci_lut import CueLUT           # noqa: E402
from lut_upstream import M3_PER_ML             # noqa: E402

TRACES = ROOT / "results" / "stage6" / "traces"
OUT = ROOT / "results" / "emptying_check"

FLOW_DROP_ML = 0.1      # a fall in true volume larger than this in 1 s counts as flow
Q_FLOW_ML_S = 0.1       # the Q-based version, shown only to size the E67 effect
GAP_S = 30.0            # an episode ends after 30 s with no flow
FLAG_LINES_S = (120.0, 180.0)   # the user's "over 2-3 min"


def pattern_timing(stim_name):
    p = config.STIM_PATTERNS.value[stim_name]
    return p["on_s"], p["off_s"]


def episode(t, flowing, i0, i_limit):
    """Last flowing second of the episode that starts at sample i0.

    flowing[i] means "flow happened between sample i and sample i+1".
    Returns (end time of the last flowing second, list of flowing sample indices)."""
    last_end = t[i0]                      # no flow yet: the episode is 0 s long
    used = []
    for i in range(i0, i_limit):
        if t[i] >= last_end + GAP_S:      # 30 s with no flow: the episode is over
            break
        if flowing[i]:
            last_end = t[i + 1]
            used.append(i)
    return last_end, used


def sessions_in_trace(path, tag_parts, table):
    d = pd.read_csv(path)
    t = d["t"].to_numpy()
    v = d["V_B_ml"].to_numpy()
    q = d["Q_ml_s"].to_numpy()
    active = d["stim_active"].to_numpy().astype(bool)
    n = len(t)
    # flowing[i]: true volume fell between sample i and i+1 (last sample has no "next")
    v_flow = np.zeros(n, dtype=bool)
    v_flow[:-1] = (v[:-1] - v[1:]) > FLOW_DROP_ML
    q_flow = np.zeros(n, dtype=bool)
    q_flow[:-1] = q[:-1] > Q_FLOW_ML_S

    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    stops = np.flatnonzero(active & ~np.r_[active[1:], False])      # last active sample
    stim_name, ceiling, rate = tag_parts
    on_s, off_s = pattern_timing(stim_name)
    rows = []
    for k, (i0, i_last) in enumerate(zip(starts, stops)):
        i_limit = starts[k + 1] if k + 1 < len(starts) else n - 1
        exact_start = None
        # the session table holds the exact (0.1 s) start; match it to this trace session
        match = table[(table.start_h * 3600 - t[i0]).abs() <= 1.0]
        if len(match) == 1:
            exact_start = float(match.start_h.iloc[0] * 3600)
            cls = match.emptying.iloc[0]
            table_vf = float(match.voided_fraction.iloc[0])
            stim_s = float(match.duration_s.iloc[0])
            cutoff = match.cutoff.iloc[0]
        else:
            cls, table_vf, stim_s, cutoff = "unmatched", np.nan, np.nan, ""
        stim_stop = t[i_last] + 1.0
        end_v, used_v = episode(t, v_flow, i0, i_limit)
        end_q, _ = episode(t, q_flow, i0, i_limit)
        before = v[i0 - 1] if i0 > 0 else v[i0]
        after = v[min(int(np.searchsorted(t, end_v)), n - 1)]
        # where did the flow happen: burst ON, burst OFF (between bursts), or after the session?
        on_n = off_n = post_n = 0
        off_pos = []                     # whole seconds since the burst ended, for OFF-phase flow
        for i in used_v:
            mid = t[i] + 0.5
            if mid >= stim_stop:
                post_n += 1
            elif off_s > 0 and exact_start is not None and (mid - exact_start) % (on_s + off_s) >= on_s:
                off_n += 1
                off_pos.append(int((mid - exact_start) % (on_s + off_s) - on_s))
            else:
                on_n += 1
        dur = end_v - t[i0]
        # Sensitivity (added after the first results, see the doc's change log): time until true
        # volume first comes within 1 mL of the lowest volume before the next session (or 600 s).
        # Unlike the frozen definition, it ignores the ~0.1 mL of new urine that later bursts
        # push out of a bladder that is already empty.
        w_end = min(i_limit, int(np.searchsorted(t, t[i0] + 600.0)))
        v_low = v[i0:w_end + 1].min()
        i_reach = i0 + int(np.flatnonzero(v[i0:w_end + 1] <= v_low + 1.0)[0])
        near_empty_dur = t[i_reach] - t[i0]
        rows.append({
            "stim_name": stim_name, "pressure_ceiling_cmH2O": ceiling, "us_interval_s": rate,
            "session": k + 1, "start_s": t[i0], "stim_s": stim_s, "cutoff": cutoff, "emptying": cls,
            "table_voided_fraction": table_vf, "true_volume_before_ml": before,
            "true_volume_at_flow_stop_ml": after, "voided_ml": before - after,
            "emptying_duration_s": dur, "q_based_duration_s": end_q - t[i0],
            "within_1ml_of_lowest_s": near_empty_dur,
            "flow_s_total": len(used_v), "flow_s_burst_on": on_n, "flow_s_burst_off": off_n,
            "off_flow_positions": ";".join(map(str, off_pos)),
            "flow_s_after_stim_stop": post_n, "flow_stop_minus_stim_stop_s": end_v - stim_stop,
            **{f"over_{x:.0f}s": dur > x for x in FLAG_LINES_S},
        })
    return rows


def part_a():
    sess = pd.read_csv(ROOT / "results" / "stage6" / "exp3_sessions.csv", float_precision="round_trip")
    sess = sess[(sess.group == "main") & (sess.phys_seed == 42) & (sess.sphincter_scaling == 1.0)]
    # exp4 traces are exact copies of two exp3 traces: confirm, then skip them
    h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    dupes = {f.name: h(f) == h(TRACES / f"exp3_{f.stem[5:]}_55_60.csv") for f in sorted(TRACES.glob("exp4_*.csv"))}
    rows = []
    files = sorted(TRACES.glob("exp3_*.csv"))
    for f in files:
        parts = f.stem[5:].rsplit("_", 2)            # e1.0_s0.0_5on5off, 55, 60
        stim_name, ceiling, rate = parts[0], float(parts[1]), float(parts[2])
        table = sess[(sess.stim_name == stim_name) & (sess.pressure_ceiling_cmH2O == ceiling)
                     & (sess.ultrasound_interval_during_stim_s == rate)]
        rows += sessions_in_trace(f, (stim_name, ceiling, rate), table)
    df = pd.DataFrame(rows)
    df["post_hoc_optimistic"] = df.stim_name.str.contains("_s0.0_")    # no co-activation
    emptied = df[df.emptying.isin(["partial", "complete"])]
    keys = ["stim_name", "pressure_ceiling_cmH2O", "us_interval_s"]
    settings = emptied.groupby(keys).agg(
        sessions_that_emptied=("session", "size"), median_duration_s=("emptying_duration_s", "median"),
        max_duration_s=("emptying_duration_s", "max"), max_q_based_duration_s=("q_based_duration_s", "max"),
        max_within_1ml_of_lowest_s=("within_1ml_of_lowest_s", "max"),
        max_flow_s_after_stim_stop=("flow_s_after_stim_stop", "max"),
        median_voided_ml=("voided_ml", "median"), post_hoc_optimistic=("post_hoc_optimistic", "first"),
    ).reset_index()
    return df, settings, dupes, len(files)


def part_b():
    """Constants and storage-phase drive targets, read from the upstream model (no time stepping)."""
    m = CueLUT()
    ba, na = m.bladder_args, m.neural_args
    out = {"tau_D_s": ba["tau_D"], "tau_S_s": ba["tau_S"],
           "somatic_a_x1.0": na["somatic_a"], "somatic_w_voiding": na["somatic_w_voiding"]}
    # Sphincter: OFF-phase target = the model's own storage drive, which depends only on
    # urethral opening (openness = r_U / r_U_max). Evaluated at fixed openings.
    sph = []
    for scaling in (1.0, 0.9):
        m2 = CueLUT(overrides={"neural_args.somatic_a": na["somatic_a"] * scaling})
        for openness in (0.0, 0.25, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
            m2.r_U = openness * ba["r_U_max"]
            sph.append({"sphincter_scaling": scaling, "openness": openness,
                        "off_phase_sphincter_target": m2.update_somatic_input()})
    # Detrusor: activation obeys d f/dt = (w_e - f - w_i f) / tau_D, so its effective time
    # constant is tau_D / (1 + w_i) and it relaxes toward w_e / (1 + w_i) when a burst ends.
    det = []
    for vol in (0.0, 100.0, 200.0, 300.0, 400.0, 450.0, 500.0):
        m.V_B = vol * M3_PER_ML
        w_e, w_i = m.update_parasympathetic_input(), m.update_sympathetic_input()
        det.append({"volume_ml": vol, "w_e": w_e, "w_i": w_i,
                    "effective_tau_D_s": ba["tau_D"] / (1 + w_i), "off_phase_detrusor_target": w_e / (1 + w_i)})
    # Already-measured OFF-phase and after-session flow in the Stage 5 map (Q-based there)
    smap = pd.read_csv(ROOT / "results" / "stage5" / "stimulation_map.csv")
    burst = smap[smap.off_s > 0]
    by_s = burst.groupby("sphincter_drive").agg(
        n=("emptying", "size"), n_emptying=("emptying", lambda x: int((x != "none").sum())),
        max_flow_fraction_burst_off=("flow_fraction_burst_off", "max"),
        max_flow_after_session_ml=("flow_after_session_ml", "max")).reset_index()
    out["all_map_flow_after_session_ml_max"] = float(smap.flow_after_session_ml.max())
    return out, pd.DataFrame(sph), pd.DataFrame(det), by_s


def main():
    OUT.mkdir(exist_ok=True)
    df, settings, dupes, n_files = part_a()
    df.to_csv(OUT / "sessions.csv", index=False)
    settings.to_csv(OUT / "settings_that_empty.csv", index=False)
    b, sph, det, by_s = part_b()
    sph.to_csv(OUT / "sphincter_off_targets.csv", index=False)
    det.to_csv(OUT / "detrusor_off_targets.csv", index=False)
    by_s.to_csv(OUT / "stage5_off_phase_flow.csv", index=False)

    emptied = df[df.emptying.isin(["partial", "complete"])]
    bursts = emptied[emptied.stim_name.str.contains("on") & ~emptied.stim_name.str.contains("continuous")]
    positions = [int(x) for s in bursts.off_flow_positions.fillna("").astype(str) for x in s.split(";") if x]
    key = {
        "traces_used": n_files, "exp4_traces_identical_to_exp3": dupes,
        "sessions_in_traces": len(df), "sessions_unmatched": int((df.emptying == "unmatched").sum()),
        "sessions_that_emptied": len(emptied),
        "sessions_that_emptied_post_hoc": int(emptied.post_hoc_optimistic.sum()),
        "settings_that_empty": len(settings),
        "median_emptying_duration_s": float(emptied.emptying_duration_s.median()),
        "max_emptying_duration_s": float(emptied.emptying_duration_s.max()),
        "max_emptying_duration_any_session_s": float(df.emptying_duration_s.max()),
        "max_q_based_duration_s": float(df.q_based_duration_s.max()),
        "sessions_over_120s": int(df.over_120s.sum()), "sessions_over_180s": int(df.over_180s.sum()),
        "median_within_1ml_of_lowest_s": float(emptied.within_1ml_of_lowest_s.median()),
        "max_within_1ml_of_lowest_s": float(emptied.within_1ml_of_lowest_s.max()),
        "max_flow_s_after_stim_stop": int(df.flow_s_after_stim_stop.max()),
        "burst_sessions_emptied": len(bursts),
        "burst_flow_s_on": int(bursts.flow_s_burst_on.sum()), "burst_flow_s_off": int(bursts.flow_s_burst_off.sum()),
        "burst_flow_s_after_stop": int(bursts.flow_s_after_stim_stop.sum()),
        "burst_off_flow_s_by_seconds_after_burst_end": pd.Series(positions, dtype=int).value_counts().sort_index().to_dict(),
        "max_stim_s": float(df.stim_s.max()), **b,
    }
    (OUT / "key_numbers.json").write_text(json.dumps(key, indent=2, default=float))
    pd.set_option("display.width", 200)
    print(json.dumps(key, indent=2, default=float))
    print("\nSettings that empty (seed 42, sphincter x1.0; s0.0 = POST-HOC, OPTIMISTIC):")
    print(settings.round(1).to_string(index=False))
    print("\nSphincter OFF-phase target:\n", sph.round(3).to_string(index=False))
    print("\nDetrusor after a burst:\n", det.round(3).to_string(index=False))
    print("\nStage 5 map, burst patterns, by sphincter drive:\n", by_s.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
