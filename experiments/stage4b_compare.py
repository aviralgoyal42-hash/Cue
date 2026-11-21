"""
STAGE 4 follow-up: compare Experiment 2 (3 inflow seeds) with Experiment 2b (15 seeds).
Writes results/stage4b/exp2b_vs_exp2_comparison.csv and prints the key tables.
Usage: python experiments/stage4b_compare.py
"""
from pathlib import Path

import pandas as pd

R = Path(__file__).resolve().parents[1] / "results"
KEY = ["sphincter_scaling", "scenario", "threshold_ml"]


def main():
    a = pd.read_csv(R / "stage4" / "exp2_summary.csv")
    b = pd.read_csv(R / "stage4b" / "exp2_summary.csv")
    m = a[KEY + ["useful_rate", "false_alert_run_rate", "median_lead_min", "cue_works_C1_C2_C3"]].merge(
        b[KEY + ["n_runs", "useful_rate", "false_alert_run_rate", "median_lead_min", "cue_works_C1_C2_C3",
                 "POSTHOC_band_350_450_rate"]], on=KEY, suffixes=("_3seeds", "_15seeds"))
    m["pass_changed"] = m["cue_works_C1_C2_C3_3seeds"] != m["cue_works_C1_C2_C3_15seeds"]
    m.to_csv(R / "stage4b" / "exp2b_vs_exp2_comparison.csv", index=False)
    real = m[m["scenario"] != "ideal"]
    for col in ["cue_works_C1_C2_C3_3seeds", "cue_works_C1_C2_C3_15seeds"]:
        print(f"--- non-ideal scenarios passing per threshold ({col})")
        print(real.groupby(["sphincter_scaling", "threshold_ml"])[col].sum().unstack().to_string())
    print("--- combinations whose pass/fail changed:")
    print(m[m["pass_changed"]][KEY + ["useful_rate_3seeds", "useful_rate_15seeds", "false_alert_run_rate_15seeds",
                                      "median_lead_min_15seeds", "cue_works_C1_C2_C3_15seeds"]].round(3).to_string(index=False))
    print("--- anchor_11pct, 15 seeds")
    print(m[m["scenario"] == "anchor_11pct"][KEY + ["useful_rate_15seeds", "false_alert_run_rate_15seeds",
                                                     "median_lead_min_15seeds", "POSTHOC_band_350_450_rate",
                                                     "cue_works_C1_C2_C3_15seeds"]].round(3).to_string(index=False))
    print("--- POST-HOC band rate at 400 mL, 15 seeds")
    print(m[m["threshold_ml"] == 400].pivot(index="scenario", columns="sphincter_scaling",
                                             values="POSTHOC_band_350_450_rate").round(3).to_string())


if __name__ == "__main__":
    main()
