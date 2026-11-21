"""
TASK 5 scoring (docs/TASK5_PLAN.md). Reads saved results only; never simulates.
Scores every setting x level with the unchanged Experiment 3 rule (A2-A4, P1, P2, P3) and reports,
per setting, the highest level that still works, plus leftover volume and emptying time by level.
All results are model predictions, POST-HOC and OPTIMISTIC (settings from Experiment 3b).

Usage: python experiments/task5_analysis.py           (the full sweep, results/task5/task5_*.csv)
       python experiments/task5_analysis.py --check   (dry run on the Step 2 files in results/task5/check/)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))
import stage6_experiments3_4 as s6                 # noqa: E402  (unchanged Experiment 3 scoring)
import task5_sphincter_levels as t5                # noqa: E402

EXACT = {"float_precision": "round_trip"}


def level_of(name):
    return float(name.split("_s")[1].split("_")[0])


def detrusor_of(name):
    return float(name.split("_")[0][1:])


def by_level(runs, sessions):
    summary = s6.summarise_exp3(runs, sessions)
    rows = []
    for _, st in summary.iterrows():
        key = (runs.stim_name == st.stim_name) & (runs.sphincter_scaling == st.sphincter_scaling)
        r = runs[key]
        s = sessions[(sessions.stim_name == st.stim_name) & (sessions.sphincter_scaling == st.sphincter_scaling)]
        emptied = s[s.emptying != "none"]
        q = lambda x, f: float(getattr(x, f)()) if len(x) else np.nan   # noqa: E731
        rows.append({
            "detrusor_drive": detrusor_of(st.stim_name), "sphincter_scaling": st.sphincter_scaling,
            "level": level_of(st.stim_name), "stim_name": st.stim_name, "n_runs": int(st.n_runs),
            "works": bool(st.full_loop_works), "A2_A3_A4_all_hold": bool(st.A2_A3_A4_all_hold),
            "P1": st.P1_sessions_voided_ge_50pct, "P2": st.P2_runs_without_overflow_after_alert,
            "P3": st.P3_sessions_within_ceiling_plus5, "P1_pass": bool(st.P1_pass), "P2_pass": bool(st.P2_pass),
            "P3_pass": bool(st.P3_pass), "sessions": len(s), "sessions_per_run": len(s) / len(r),
            "sessions_voided_lt_10pct": int((s.emptying == "none").sum()),
            "residual_median_ml": q(s.residual_ml, "median"), "residual_min_ml": q(s.residual_ml, "min"),
            "residual_max_ml": q(s.residual_ml, "max"),
            "emptied_sessions": len(emptied),
            "emptying_time_median_s": q(emptied.emptying_duration_s, "median"),
            "emptying_time_max_s": q(emptied.emptying_duration_s, "max"),
            "within_1ml_median_s": q(emptied.within_1ml_of_lowest_s, "median"),
            "within_1ml_max_s": q(emptied.within_1ml_of_lowest_s, "max"),
            "flow_s_after_stim_stop_max": q(s.flow_s_after_stim_stop, "max"),
            "cutoff_max_duration": st.cutoff_max_duration, "cutoff_volume_stop": st.cutoff_volume_stop,
            "cutoff_pressure_ceiling": st.cutoff_pressure_ceiling,
            "peak_true_p_D_cmH2O": st.max_true_p_D_during_stim_cmH2O,
            "runs_with_overflow": int(r.overflow_despite_alert.sum()),
            "leaked_after_alert_ml_max": float(r.leaked_after_alert_ml.max()),
            "max_volume_ml_max": float(r.max_volume_ml.max()),
        })
    return pd.DataFrame(rows).sort_values(["detrusor_drive", "sphincter_scaling", "level"],
                                          ascending=[True, False, True]).reset_index(drop=True)


def highest_levels(table):
    out = {}
    for (d, sc), g in table.groupby(["detrusor_drive", "sphincter_scaling"], sort=False):
        working = sorted(g[g.works].level.tolist())
        tried = sorted(g.level.tolist())
        block = working == tried[:len(working)]          # a single block starting at level 0?
        out[f"e{d}_x{sc}"] = {"levels_that_work": working, "highest_level_that_works": max(working) if working else None,
                              "working_levels_form_one_block_from_0": bool(block), "levels_tried": tried}
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    folder, label = (t5.CHECK, "check") if args.check else (t5.RESULTS, "task5")
    runs = pd.read_csv(folder / f"{label}_runs.csv", **EXACT)
    sessions = pd.read_csv(folder / f"{label}_sessions.csv", **EXACT)
    table = by_level(runs, sessions)
    key = {"runs": len(runs), "sessions": len(sessions),
           "errors": int(runs.error.fillna("").astype(str).ne("").sum()),
           "invariants_hold_all_runs": bool(runs[["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout",
                                                  "A4_sessions_within_max_duration"]].all().all()),
           "settings_x_levels": len(table), "working": int(table.works.sum()),
           "highest_working_level": highest_levels(table)}
    table.to_csv(folder / f"{label}_by_level.csv", index=False)
    (folder / f"{label}_key_numbers.json").write_text(json.dumps(key, indent=2, default=float))
    pd.set_option("display.width", 250)
    cols = ["detrusor_drive", "sphincter_scaling", "level", "works", "P1", "P2", "P3", "sessions_per_run",
            "residual_median_ml", "residual_max_ml", "emptied_sessions", "emptying_time_median_s",
            "emptying_time_max_s", "peak_true_p_D_cmH2O", "runs_with_overflow"]
    print(table[cols].round(3).to_string(index=False))
    print(json.dumps(key, indent=2, default=float))


if __name__ == "__main__":
    main()
