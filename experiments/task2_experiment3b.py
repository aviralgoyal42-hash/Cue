"""
Experiment 3b: POST-HOC, OPTIMISTIC sweep of max duration, alert threshold and pressure ceiling
on the two burst patterns WITHOUT sphincter co-activation (they empty; see the stimulation map).
Grid and criteria frozen in docs/EXPERIMENT3B_CRITERIA.md. The continuous patterns were dropped
from this grid to keep it near 2 hours (declared limitation).

Writes results/task2/: exp3b_runs.csv, exp3b_sessions.csv, exp3b_settings_summary.csv,
exp3b_main_effects.csv, exp3b_reproduces_exp3.json, exp3b_works_map.png.
Usage: python experiments/task2_experiment3b.py [--recheck]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage6_experiments3_4 as s6  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results" / "task2"
STAGE6 = RESULTS.parent / "stage6"
PATTERNS = ["e0.6_s0.0_5on5off", "e1.0_s0.0_5on5off"]
DURATIONS = [30.0, 60.0, 120.0]
THRESHOLDS = [350.0, 400.0, 450.0]
CEILINGS = [40.0, 55.0, 70.0]
SCALINGS = [1.0, 0.9]
SEEDS = [42] + list(range(1, 15))
FACTORS = ["stim_name", "max_duration_s", "threshold_ml", "pressure_ceiling_cmH2O", "sphincter_scaling"]


def cases():
    out = []
    for name in PATTERNS:
        for duration in DURATIONS:
            for threshold in THRESHOLDS:
                for ceiling in CEILINGS:
                    for scaling in SCALINGS:
                        for seed in SEEDS:
                            out.append({"group": "posthoc", **s6.stim(name), "threshold_ml": threshold,
                                        "controller": {"max_duration_s": duration, "pressure_ceiling_cmH2O": ceiling},
                                        "sphincter_scaling": scaling, "phys_seed": seed, "sensor_seed": seed,
                                        "user_seed": seed, "pressure_seed": seed})
    return out


def check_against_exp3():
    """Same setting and seed as Experiment 3 must give the same numbers, in every shared column of
    the run and session tables. Compares file to file with the exact float parser: the default
    parser is out by about 1e-14, which once made this check fail falsely (error E58)."""
    exact = {"float_precision": "round_trip"}
    keys = ["stim_name", "pressure_ceiling_cmH2O", "sphincter_scaling", "phys_seed"]
    skip = keys + ["group", "runtime_s", "error"]
    out = {}
    for label in ["runs", "sessions"]:
        e3 = pd.read_csv(STAGE6 / f"exp3_{label}.csv", **exact)
        e3 = e3[(e3.group == "main") & (e3.ultrasound_interval_during_stim_s == 60) & e3.stim_name.isin(PATTERNS)]
        b = pd.read_csv(RESULTS / f"exp3b_{label}.csv", **exact)
        b = b[(b.max_duration_s == 60) & (b.threshold_ml == 400) & b.phys_seed.isin([42, 1, 2])]
        order = keys + (["start_h"] if label == "sessions" else [])
        e3, b = e3.sort_values(order).reset_index(drop=True), b.sort_values(order).reset_index(drop=True)
        cols = [c for c in e3.columns if c in b.columns and c not in skip]
        out[label] = {"rows_exp3": len(e3), "rows_exp3b": len(b), "columns_compared": len(cols),
                      "identical": len(e3) == len(b) and e3[cols].fillna(-1).equals(b[cols].fillna(-1))}
    out["reproduces"] = out["runs"]["rows_exp3"] == 36 and out["runs"]["identical"] and out["sessions"]["identical"]
    return out


def main_effects(s):
    rows = []
    for factor in FACTORS:
        for level, g in s.groupby(factor):
            rows.append({"factor": factor, "level": level, "settings": len(g), "works": int(g["full_loop_works"].sum()),
                         "mean_P1": g["P1_sessions_voided_ge_50pct"].mean(),
                         "mean_P2": g["P2_runs_without_overflow_after_alert"].mean(),
                         "mean_P3": g["P3_sessions_within_ceiling_plus5"].mean(),
                         "median_residual_ml": g["median_residual_ml"].median(),
                         "max_p_D_cmH2O": g["max_true_p_D_during_stim_cmH2O"].max(),
                         "cut_max_duration": g["cutoff_max_duration"].mean(),
                         "cut_volume_stop": g["cutoff_volume_stop"].mean(),
                         "cut_pressure_ceiling": g["cutoff_pressure_ceiling"].mean()})
    return pd.DataFrame(rows)


def plot_map(s, path):
    fig, axs = plt.subplots(len(PATTERNS) * len(SCALINGS), len(DURATIONS), figsize=(11, 11), sharex=True, sharey=True)
    for r, (name, scaling) in enumerate([(p, x) for p in PATTERNS for x in SCALINGS]):
        for c, duration in enumerate(DURATIONS):
            ax = axs[r, c]
            m = s[(s.stim_name == name) & (s.sphincter_scaling == scaling) & (s.max_duration_s == duration)]
            grid = m.pivot(index="threshold_ml", columns="pressure_ceiling_cmH2O", values="P1_sessions_voided_ge_50pct")
            works = m.pivot(index="threshold_ml", columns="pressure_ceiling_cmH2O", values="full_loop_works")
            resid = m.pivot(index="threshold_ml", columns="pressure_ceiling_cmH2O", values="median_residual_ml")
            ax.imshow(grid.to_numpy(dtype=float), cmap="Blues", vmin=0, vmax=1, origin="lower", aspect="auto")
            for i in range(3):
                for j in range(3):
                    ax.text(j, i, f"P1 {grid.iat[i, j]:.2f}\nres {resid.iat[i, j]:.0f}" + ("\nWORKS" if works.iat[i, j] else ""),
                            ha="center", va="center", fontsize=7, color="white" if grid.iat[i, j] > 0.6 else "black")
            ax.set_xticks(range(3), [f"{x:.0f}" for x in grid.columns])
            ax.set_yticks(range(3), [f"{x:.0f}" for x in grid.index])
            ax.set_title(f"{name}, sph x{scaling}, max {duration:.0f} s", fontsize=7)
            if r == 3:
                ax.set_xlabel("Ceiling (cmH2O)", fontsize=8)
            if c == 0:
                ax.set_ylabel("Threshold (mL)", fontsize=8)
    fig.suptitle("Experiment 3b: POST-HOC, OPTIMISTIC (no sphincter co-activation; model predictions)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def recheck():
    """Compare the saved results with Experiment 3. Needs no new simulation."""
    check = check_against_exp3()
    with open(RESULTS / "exp3b_reproduces_exp3.json", "w") as f:
        json.dump(check, f, indent=2)
    print(json.dumps(check))


def main():
    s6.config.validate()
    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(s6.config.as_table()).to_csv(RESULTS / "parameters_used.csv", index=False)
    s6.RESULTS = RESULTS                  # run_all saves here; workers never write traces for this group
    runs, sessions = s6.run_all(cases(), "exp3b")
    summary = s6.summarise_exp3(runs, sessions)
    summary.to_csv(RESULTS / "exp3b_settings_summary.csv", index=False)
    main_effects(summary).to_csv(RESULTS / "exp3b_main_effects.csv", index=False)
    recheck()
    plot_map(summary, RESULTS / "exp3b_works_map.png")
    print(f"{len(runs)} runs; errors {int((runs['error'] != '').sum())}; "
          f"{int(summary['full_loop_works'].sum())} of {len(summary)} settings work; "
          f"invariants all hold: {bool(summary['A2_A3_A4_all_hold'].all())}")


if __name__ == "__main__":
    recheck() if "--recheck" in sys.argv else main()
