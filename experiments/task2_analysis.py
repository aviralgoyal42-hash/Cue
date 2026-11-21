"""
Experiment 3b: read-only analysis of the saved results. Runs no simulation.

Looks behind the "works" count: which factors interact, how long sessions run, why each cutoff
fired, whether leakage comes before the first alert (P2 cannot see that), and whether 15 seeds
change any verdict from the 3 seeds of Experiment 3.

Writes results/task2/: exp3b_pairs.csv, exp3b_session_detail.csv, exp3b_leak_detail.csv,
exp3b_3_vs_15_seeds.csv, exp3b_key_numbers.json, and prints a short summary.
Usage: python experiments/task2_analysis.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "task2"
SETTING = ["stim_name", "sphincter_scaling", "max_duration_s", "threshold_ml", "pressure_ceiling_cmH2O"]


def pairs(s):
    """Settings that work, for each pair of factors (shows interactions the main effects hide)."""
    rows = []
    for a, b in [("stim_name", "pressure_ceiling_cmH2O"), ("stim_name", "max_duration_s"),
                 ("threshold_ml", "pressure_ceiling_cmH2O"), ("threshold_ml", "max_duration_s"),
                 ("max_duration_s", "pressure_ceiling_cmH2O"), ("sphincter_scaling", "pressure_ceiling_cmH2O")]:
        for (x, y), g in s.groupby([a, b]):
            rows.append({"factor_a": a, "level_a": x, "factor_b": b, "level_b": y, "settings": len(g),
                         "works": int(g.full_loop_works.sum())})
    return pd.DataFrame(rows)


def session_detail(z):
    """How long sessions ran, what ended them, and what the device estimate said at the end."""
    keys = ["stim_name", "max_duration_s", "pressure_ceiling_cmH2O"]
    rows = []
    for k, g in z.groupby(keys):
        rows.append({**dict(zip(keys, k)), "sessions": len(g),
                     "median_duration_s": g.duration_s.median(), "max_duration_seen_s": g.duration_s.max(),
                     "ended_by_max_duration": (g.cutoff == "max_duration").mean(),
                     "ended_by_pressure": g.cutoff.str.contains("pressure_ceiling").mean(),
                     "ended_by_volume_stop": g.cutoff.str.contains("volume_stop").mean(),
                     "pressure_stops_with_true_p_below_ceiling": int((g.cutoff.str.contains("pressure_ceiling")
                                                                      & (g.max_true_p_D_during_cmH2O < g.pressure_ceiling_cmH2O)).sum()),
                     "median_max_true_p_D": g.max_true_p_D_during_cmH2O.median(),
                     "median_estimate_at_start_ml": g.estimate_at_start_ml.median(),
                     "median_estimate_at_stop_ml": g.estimate_at_stop_ml.median(),
                     "median_residual_ml": g.residual_ml.median()})
    return pd.DataFrame(rows)


def leak_detail(r):
    """Leakage in each setting, split at the first alert. P2 only looks after the first alert."""
    rows = []
    for k, g in r.groupby(SETTING):
        rows.append({**dict(zip(SETTING, k)), "runs": len(g),
                     "runs_leaking_at_all": int((g.leaked_outside_sessions_ml > 0).sum()),
                     "runs_leaking_after_alert": int((g.leaked_after_alert_ml > 0).sum()),
                     "leaked_ml_mean": g.leaked_outside_sessions_ml.mean(), "leaked_ml_max": g.leaked_outside_sessions_ml.max(),
                     "leaked_after_alert_ml_max": g.leaked_after_alert_ml.max(),
                     "max_volume_ml_max": g.max_volume_ml.max(), "first_alert_h_median": g.first_alert_h.median(),
                     "sessions_per_run": g.n_sessions.mean()})
    return pd.DataFrame(rows)


def three_vs_fifteen(s):
    """The same settings as Experiment 3, judged on its 3 seeds and on these 15."""
    e3 = pd.read_csv(ROOT / "results" / "stage6" / "exp3_settings_summary.csv")
    e3 = e3[(e3.group == "main") & (e3.ultrasound_interval_during_stim_s == 60) & e3.stim_name.isin(s.stim_name.unique())]
    keys = ["stim_name", "pressure_ceiling_cmH2O", "sphincter_scaling"]
    b = s[(s.max_duration_s == 60) & (s.threshold_ml == 400)]
    cols = ["P1_sessions_voided_ge_50pct", "P2_runs_without_overflow_after_alert", "P3_sessions_within_ceiling_plus5",
            "full_loop_works"]
    return e3[keys + cols].merge(b[keys + cols], on=keys, suffixes=("_3seeds", "_15seeds"))


def key_numbers(s, r, z, l):
    """The figures quoted in docs/EXPERIMENT3B_RESULTS.md, checked by check_doc_numbers.py."""
    works = s[s.full_loop_works]
    stops = z[z.cutoff.str.contains("pressure_ceiling")]
    stops55 = stops[stops.pressure_ceiling_cmH2O == 55]
    over = z[z.ceiling_exceeded_gt5]
    short = over[over.duration_s < 1]
    z70 = z[z.pressure_ceiling_cmH2O == 70]
    trapped = (r.threshold_ml == 450) & (r.pressure_ceiling_cmH2O == 40)
    trap, rest = r[trapped & (r.sphincter_scaling == 1.0)], r[~trapped]
    return {"sessions": len(z), "settings_work": len(works), "error_rows": int(r.error.notna().sum()),
            "volume_stops": int(z.cutoff.str.contains("volume_stop").sum()),
            "stops_at_55": len(stops55),
            "stops_at_55_true_p_below_ceiling": int((stops55.max_true_p_D_during_cmH2O < 55).sum()),
            "sessions_at_70": len(z70), "stops_at_70": int(z70.cutoff.str.contains("pressure_ceiling").sum()),
            "peak_p_all": float(z.max_true_p_D_during_cmH2O.max()),
            "peak_p_working": float(works.max_true_p_D_during_stim_cmH2O.max()),
            "peak_p_full_sessions": float(z[z.duration_s >= 1].max_true_p_D_during_cmH2O.max()),
            "sessions_over_ceiling_plus5": len(over), "over_all_at_ceiling_40": bool((over.pressure_ceiling_cmH2O == 40).all()),
            "over_and_under_1s": len(short), "over_and_1s_or_longer": len(over) - len(short),
            "under_1s_median_volume_ml": float(short.true_volume_before_ml.median()),
            "under_1s_min_threshold_ml": float(short.threshold_ml.min()),
            "works_residual_le_10ml": int((works.median_residual_ml <= 10).sum()),
            "works_residual_gt_50ml": int((works.median_residual_ml > 50).sum()),
            "works_max_residual_ml": float(works.median_residual_ml.max()),
            "leak_settings": int((l.runs_leaking_at_all > 0).sum()),
            "leak_runs": int(l.runs_leaking_at_all.sum()), "leak_before_alert_runs": int((l.runs_leaking_at_all - l.runs_leaking_after_alert).sum()),
            "leak_max_ml": float(l.leaked_ml_max.max()),
            "leak_settings_max_volume_ml": float(l[l.runs_leaking_at_all > 0].max_volume_ml_max.max()),
            "over_and_ended_by_max_duration": int((over.cutoff == "max_duration").sum()),
            "trap_x1_runs_over_500ml": int((trap.max_volume_ml > 500).sum()), "trap_x1_runs": len(trap),
            "trap_x1_max_volume_ml": float(trap.max_volume_ml.max()),
            "trap_x1_leaked_ml": float(trap.leaked_outside_sessions_ml.max()),
            "highest_volume_other_settings_ml": float(rest.max_volume_ml.max()),
            "p2_lower_bound_15_of_15": 0.05 ** (1 / 15)}


def main():
    s = pd.read_csv(RESULTS / "exp3b_settings_summary.csv")
    r = pd.read_csv(RESULTS / "exp3b_runs.csv")
    z = pd.read_csv(RESULTS / "exp3b_sessions.csv")
    p, d, l, c = pairs(s), session_detail(z), leak_detail(r), three_vs_fifteen(s)
    with open(RESULTS / "exp3b_key_numbers.json", "w") as f:
        json.dump(key_numbers(s, r, z, l), f, indent=2)
    print(json.dumps(key_numbers(s, r, z, l), indent=1))
    p.to_csv(RESULTS / "exp3b_pairs.csv", index=False)
    d.to_csv(RESULTS / "exp3b_session_detail.csv", index=False)
    l.to_csv(RESULTS / "exp3b_leak_detail.csv", index=False)
    c.to_csv(RESULTS / "exp3b_3_vs_15_seeds.csv", index=False)

    pd.set_option("display.width", 230, "display.max_columns", 40, "display.max_rows", 200)
    print(f"runs {len(r)}; error rows {int(r.error.notna().sum())}; sessions {len(z)}; works {int(s.full_loop_works.sum())}/{len(s)}")
    print("invariants hold in every setting:", bool(s.A2_A3_A4_all_hold.all()))
    print("cutoff counts:", z.cutoff.value_counts().to_dict())
    print("highest true p_D:", z.max_true_p_D_during_cmH2O.max(), "; in working settings:", s[s.full_loop_works].max_true_p_D_during_stim_cmH2O.max())
    print(p.pivot_table(index=["factor_a", "level_a"], columns=["factor_b", "level_b"], values="works").fillna("").to_string())
    print(d.round(2).to_string())
    print("settings with any leak:", int((l.runs_leaking_at_all > 0).sum()), "; after alert:", int((l.runs_leaking_after_alert > 0).sum()))
    print(l[l.runs_leaking_at_all > 0].round(1).to_string())
    print("verdict changes 3 to 15 seeds:", int((c.full_loop_works_3seeds != c.full_loop_works_15seeds).sum()), "of", len(c))
    print(c.round(2).to_string())


if __name__ == "__main__":
    main()
