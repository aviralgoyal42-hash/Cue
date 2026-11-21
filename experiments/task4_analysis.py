"""
Final experiment: compare the 15-seed rerun with the old 3-seed Experiments 3 and 4. Runs no
simulation. Criteria are the old ones, unchanged; see docs/EXPERIMENT3_4_15SEED_PLAN.md.

Writes results/task4/: exp3_verdict_compare.csv (all 104 settings), exp3_verdict_changes.csv,
exp4_cell_compare.csv (all 108 cells), exp4_line_crossings.csv, key_numbers.json, and the figures
exp3_P1_by_pattern_and_ceiling.png and exp4_fault_map.png.
Usage: python experiments/task4_analysis.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage6_experiments3_4 as s6  # noqa: E402
import task4_rerun_exp3_4 as t4  # noqa: E402

RESULTS, OLD = t4.RESULTS, t4.OLD
KEYS3 = t4.KEYS["exp3"][:-1]
KEYS4 = t4.KEYS["exp4"][:-1]
VERDICTS = ["P1_pass", "P2_pass", "P3_pass", "full_loop_works", "A2_A3_A4_all_hold"]
EXACT = {"float_precision": "round_trip"}
CO_ACTIVATION = "_s0.5_"
P1_LINE, P2_LINE, P3_LINE = 0.80, 0.95, 0.95


def compare_exp3(old, new):
    table = old.merge(new, on=KEYS3, suffixes=("_old", "_new"), how="outer", indicator=True)
    assert (table["_merge"] == "both").all(), "the old and new settings differ"
    table["changed"] = [", ".join(v for v in VERDICTS if row[f"{v}_old"] != row[f"{v}_new"])
                        for _, row in table.iterrows()]
    return table.drop(columns="_merge")


def compare_exp4(old, new):
    table = old.merge(new, on=KEYS4, suffixes=("_old", "_new"), how="outer", indicator=True)
    assert (table["_merge"] == "both").all(), "the old and new cells differ"
    table = table.drop(columns="_merge")
    tests = [("P1", "P1_sessions_voided_ge_50pct", lambda v: v >= P1_LINE),
             ("no overflow", "overflow_despite_alert_rate", lambda v: 1 - v >= P2_LINE),
             ("P3", "P3_sessions_within_ceiling_plus5", lambda v: v >= P3_LINE)]
    crossed = []
    for _, row in table.iterrows():
        marks = [name for name, col, ok in tests
                 if pd.notna(row[f"{col}_old"]) and pd.notna(row[f"{col}_new"]) and ok(row[f"{col}_old"]) != ok(row[f"{col}_new"])]
        crossed.append(", ".join(marks))
    table["crossed_line_descriptive"] = crossed
    return table


def cutoff_share(sessions, name):
    fired = sessions["cutoff"].str.contains(name)
    return int(fired.sum()), len(sessions)


def key_numbers(label, s3, r3, z3, s4, r4, z4):
    """The headline numbers of docs/STAGE6_EXPERIMENTS3_4.md, recomputed one way for both sets."""
    works = s3[s3.full_loop_works]
    fast = z3[z3.ultrasound_interval_during_stim_s == 5.0]
    usual = z3[z3.ultrasound_interval_during_stim_s == 60.0]
    no_co = z3[~z3.stim_name.str.contains(CO_ACTIVATION)]
    worst = s4[s4.group == "combo:dead_pressure+stuck_high_estimate"]
    stuck = s4[(s4.group == "estimate:stuck_high_450ml_from_5h")]
    reference = s3[(s3.stim_name == s6.config.REFERENCE_STIM.value)]
    return {"set": label, "exp3_runs": len(r3), "exp4_runs": len(r4), "exp3_sessions": len(z3), "exp4_sessions": len(z4),
            "exp3_errors": int(r3.error.fillna("").ne("").sum()), "exp4_errors": int(r4.error.fillna("").ne("").sum()),
            "settings": len(s3), "settings_work": int(s3.full_loop_works.sum()),
            "settings_work_with_co_activation": int(works.stim_name.str.contains(CO_ACTIVATION).sum()),
            "P1_pass": int(s3.P1_pass.sum()), "P2_pass": int(s3.P2_pass.sum()), "P3_pass": int(s3.P3_pass.sum()),
            "exp3_invariants_hold": bool(s3.A2_A3_A4_all_hold.all()), "exp4_invariants_hold": bool(s4.A2_A3_A4_all_hold.all()),
            "worst_case_all_max_duration": bool((worst.cutoff_max_duration == 1).all()),
            "volume_stop_60s": cutoff_share(usual, "volume_stop")[0], "sessions_60s": len(usual),
            "volume_stop_5s": cutoff_share(fast, "volume_stop")[0], "sessions_5s": len(fast),
            "peak_exp3": float(s3.max_true_p_D_during_stim_cmH2O.max()),
            "peak_exp3_working": float(works.max_true_p_D_during_stim_cmH2O.max()),
            "peak_exp4": float(s4.max_true_p_D_during_stim_cmH2O.max()),
            "peak_stuck_high_ok_channel": float(stuck.max_true_p_D_during_stim_cmH2O.max()),
            "max_exceed_of_ceiling_exp4": float(s4.max_exceed_of_ceiling_cmH2O.max()),
            "stuck_high_sessions_per_run_max": float(stuck.sessions_per_run.max()),
            "reference_P1_max": float(reference.P1_sessions_voided_ge_50pct.max()),
            "median_residual_working_min": float(works.median_residual_ml.min()),
            "median_residual_working_max": float(works.median_residual_ml.max()),
            "no_co_activation_sessions": len(no_co)}


def read_set(folder):
    return (pd.read_csv(folder / "exp3_settings_summary.csv", **EXACT), pd.read_csv(folder / "exp3_runs.csv", **EXACT),
            pd.read_csv(folder / "exp3_sessions.csv", **EXACT), pd.read_csv(folder / "exp4_fault_summary.csv", **EXACT),
            pd.read_csv(folder / "exp4_runs.csv", **EXACT), pd.read_csv(folder / "exp4_sessions.csv", **EXACT))


def main():
    old, new = read_set(OLD), read_set(RESULTS)
    verdicts = compare_exp3(old[0], new[0])
    verdicts.to_csv(RESULTS / "exp3_verdict_compare.csv", index=False)
    changes = verdicts[verdicts.changed != ""]
    changes.to_csv(RESULTS / "exp3_verdict_changes.csv", index=False)
    cells = compare_exp4(old[3], new[3])
    cells.to_csv(RESULTS / "exp4_cell_compare.csv", index=False)
    crossings = cells[cells.crossed_line_descriptive != ""]
    crossings.to_csv(RESULTS / "exp4_line_crossings.csv", index=False)
    keys = {"old_3_seeds": key_numbers("old", *old), "new_15_seeds": key_numbers("new", *new),
            "verdicts_changed": len(changes), "exp4_cells_crossing_a_line": len(crossings)}
    with open(RESULTS / "key_numbers.json", "w") as f:
        json.dump(keys, f, indent=2)
    s6.plot_exp3(new[0], RESULTS / "exp3_P1_by_pattern_and_ceiling.png")
    s6.plot_exp4(new[3], RESULTS / "exp4_fault_map.png")

    pd.set_option("display.width", 230, "display.max_columns", 40, "display.max_rows", 300, "display.max_colwidth", 60)
    print(json.dumps(keys, indent=1))
    show = ["group", "stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s", "threshold_ml",
            "max_duration_s", "sphincter_scaling", "P1_sessions_voided_ge_50pct_old", "P1_sessions_voided_ge_50pct_new",
            "P2_runs_without_overflow_after_alert_old", "P2_runs_without_overflow_after_alert_new",
            "P3_sessions_within_ceiling_plus5_old", "P3_sessions_within_ceiling_plus5_new", "changed"]
    print(changes[show].round(3).to_string(index=False))
    show = ["reference", "group", "sphincter_scaling", "P1_sessions_voided_ge_50pct_old", "P1_sessions_voided_ge_50pct_new",
            "overflow_despite_alert_rate_old", "overflow_despite_alert_rate_new", "P3_sessions_within_ceiling_plus5_old",
            "P3_sessions_within_ceiling_plus5_new", "max_true_p_D_during_stim_cmH2O_old", "max_true_p_D_during_stim_cmH2O_new",
            "crossed_line_descriptive"]
    print(crossings[show].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
