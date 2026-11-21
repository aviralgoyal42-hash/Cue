"""Print the Experiment 3 and 4 summary tables to the console.
Usage: python experiments/stage6_print_summary.py [exp3|exp4]"""
import sys
from pathlib import Path

import pandas as pd

R = Path(__file__).resolve().parents[1] / "results" / "stage6"
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 300)


def exp3():
    s = pd.read_csv(R / "exp3_settings_summary.csv")
    r = pd.read_csv(R / "exp3_runs.csv")
    print("runs", len(r), "errors", int(r["error"].notna().sum()), "| invariants all hold:",
          bool(s["A2_A3_A4_all_hold"].all()), "| settings working:", int(s["full_loop_works"].sum()), "of", len(s))
    m = s[s.group == "main"]
    print(m.pivot_table(index="stim_name", columns=["sphincter_scaling", "ultrasound_interval_during_stim_s",
                                                    "pressure_ceiling_cmH2O"],
                        values="full_loop_works", aggfunc="sum").astype(int).to_string())
    c = ["stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s", "sphincter_scaling", "n_sessions",
         "P1_sessions_voided_ge_50pct", "P2_runs_without_overflow_after_alert", "P3_sessions_within_ceiling_plus5",
         "median_residual_ml", "max_true_p_D_during_stim_cmH2O", "cutoff_max_duration", "cutoff_volume_stop",
         "cutoff_pressure_ceiling", "max_volume_ml_mean", "leaked_after_alert_ml_mean"]
    short = {x: x.replace("sessions_", "").replace("ultrasound_interval_during_stim_s", "us_s")
             .replace("pressure_ceiling_cmH2O", "ceil").replace("sphincter_scaling", "sph") for x in c}
    print(m[m.ultrasound_interval_during_stim_s == 60][c].rename(columns=short).round(2).to_string(index=False))
    print(s[s.group != "main"][["group"] + c[3:]].rename(columns=short).round(2).to_string(index=False))


def exp4():
    s = pd.read_csv(R / "exp4_fault_summary.csv")
    print("errors", int(s["errors"].sum()), "| invariants hold everywhere:", bool(s["A2_A3_A4_all_hold"].all()))
    c = ["group", "sphincter_scaling", "sessions_per_run", "P1_sessions_voided_ge_50pct", "overflow_despite_alert_rate",
         "leaked_outside_sessions_ml_mean", "P3_sessions_within_ceiling_plus5", "max_true_p_D_during_stim_cmH2O",
         "max_exceed_of_ceiling_cmH2O", "cutoff_max_duration", "cutoff_volume_stop", "cutoff_pressure_ceiling",
         "median_residual_ml", "max_volume_ml_mean", "reached_ceiling_rate", "ignored_presses_mean"]
    short = {"sessions_per_run": "sess", "P1_sessions_voided_ge_50pct": "P1", "overflow_despite_alert_rate": "overflow",
             "leaked_outside_sessions_ml_mean": "leak_ml", "P3_sessions_within_ceiling_plus5": "P3",
             "max_true_p_D_during_stim_cmH2O": "maxP", "max_exceed_of_ceiling_cmH2O": "over", "cutoff_max_duration": "c_max",
             "cutoff_volume_stop": "c_vol", "cutoff_pressure_ceiling": "c_p", "median_residual_ml": "resid",
             "max_volume_ml_mean": "maxV", "reached_ceiling_rate": "ceil1000", "ignored_presses_mean": "ign",
             "sphincter_scaling": "sph"}
    for ref, g in s.groupby("reference"):
        print("=== reference", ref)
        print(g[c].rename(columns=short).round(2).to_string(index=False))


if __name__ == "__main__":
    {"exp3": exp3, "exp4": exp4}[sys.argv[1] if len(sys.argv) > 1 else "exp3"]()
