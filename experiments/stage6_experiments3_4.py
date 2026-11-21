"""
STAGE 6: Experiment 3 (full Cue loop) and Experiment 4 (faults), both sphincter strengths.
Criteria frozen in docs/STAGE5_EXPERIMENT3_4_CRITERIA.md (including its change log).

Every run is one simulated person for 12 h through sci_test_rig.py. Results:
  results/stage6/exp3_runs.csv, exp3_sessions.csv, exp3_settings_summary.csv
  results/stage6/exp4_runs.csv, exp4_sessions.csv, exp4_fault_summary.csv
  figures exp3_*.png, exp4_*.png, comparison_exp1_to_exp4.png
Usage: python experiments/stage6_experiments3_4.py [--only exp3|exp4|figures]
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
import sci_test_rig as rig_mod  # noqa: E402
from evaluation import closed_loop_metrics as cm  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results" / "stage6"
DT = config.value(config.SIMULATION, "dt_s")
POST = config.value(config.CONTROLLER, "post_stimulus_window_s")
SEEDS = config.value(config.EXPERIMENT3, "physiology_seeds")
SCALINGS = [1.0, 0.9]
SECOND_REFERENCE = "e1.0_s0.0_5on5off"     # added after the stimulation map (see criteria change log)


def stim(name):
    return {"stim_name": name, "stim": config.STIM_PATTERNS.value[name]}


def exp3_cases():
    cases = []
    ceilings = config.value(config.CONTROLLER, "pressure_ceilings_cmH2O")
    rates = config.value(config.CONTROLLER, "ultrasound_interval_during_stim_s")
    for name in config.STIM_PATTERNS.value:
        for ceiling in ceilings:
            for rate in rates:
                for scaling in SCALINGS:
                    for seed in SEEDS:
                        cases.append({"group": "main", **stim(name), "controller": {"pressure_ceiling_cmH2O": ceiling},
                                      "ultrasound_interval_during_stim_s": rate, "sphincter_scaling": scaling,
                                      "phys_seed": seed, "sensor_seed": seed, "user_seed": seed, "pressure_seed": seed})
    ref = config.REFERENCE_STIM.value
    for scaling in SCALINGS:
        for seed in SEEDS:
            common = {**stim(ref), "sphincter_scaling": scaling, "phys_seed": seed, "sensor_seed": seed,
                      "user_seed": seed, "pressure_seed": seed}
            for thr in [350.0, 450.0]:
                cases.append({"group": f"threshold_{thr:.0f}", **common, "threshold_ml": thr})
            for dur in [30.0, 120.0]:
                cases.append({"group": f"max_duration_{dur:.0f}", **common, "controller": {"max_duration_s": dur}})
    return cases


def exp4_cases():
    faults = [("reference", {})]
    for name, values in config.SENSOR_SCENARIOS.value.items():
        if name != config.value(config.EXPERIMENT3, "sensor_scenario"):
            faults.append((f"sensor:{name}", {"sensor_name": name, "sensor": values}))
    for name, values in config.EXTRA_SENSOR_FAULTS.value.items():
        faults.append((f"estimate:{name}", {"sensor_name": name, "sensor": values}))
    for name, values in config.USER_SCENARIOS.value.items():
        if name != "prompt":
            faults.append((f"user:{name}", {"user_name": name, "user": values}))
    for name, values in config.PRESSURE_SCENARIOS.value.items():
        if name != "ok":
            faults.append((f"pressure:{name}", {"pressure_name": name, "pressure": values}))
    # Worst combination for the cutoffs: no pressure channel and an estimate stuck high.
    faults.append(("combo:dead_pressure+stuck_high_estimate",
                   {"pressure_name": "dead", "pressure": config.PRESSURE_SCENARIOS.value["dead"],
                    "sensor_name": "stuck_high_450ml_from_5h",
                    "sensor": config.EXTRA_SENSOR_FAULTS.value["stuck_high_450ml_from_5h"]}))
    cases = []
    for reference in [config.REFERENCE_STIM.value, SECOND_REFERENCE]:
        for fault, change in faults:
            for scaling in SCALINGS:
                for seed in SEEDS:
                    cases.append({"group": fault, "reference": reference, **stim(reference), **change,
                                  "sphincter_scaling": scaling, "phys_seed": seed, "sensor_seed": seed,
                                  "user_seed": seed, "pressure_seed": seed})
    return cases


def run_one(spec):
    """Run one case; return (run row, session rows). Never raises: failures become rows."""
    meta = {k: spec[k] for k in ("group", "stim_name", "sphincter_scaling", "phys_seed") if k in spec}
    meta["reference"] = spec.get("reference", "")
    changes = {k: v for k, v in spec.items() if k not in ("group", "reference")}
    case = rig_mod.default_case(**changes)
    meta.update({"sensor_name": case["sensor_name"], "user_name": case["user_name"],
                 "pressure_name": case["pressure_name"], "threshold_ml": case["threshold_ml"],
                 "pressure_ceiling_cmH2O": case["controller"]["pressure_ceiling_cmH2O"],
                 "max_duration_s": case["controller"]["max_duration_s"],
                 "ultrasound_interval_during_stim_s": case["ultrasound_interval_during_stim_s"]})
    start = time.perf_counter()
    try:
        data, rig = rig_mod.run_closed_loop(case)
    except Exception as exc:          # logged as a result, not hidden
        return {**meta, "error": repr(exc)}, []
    ceiling = case["controller"]["pressure_ceiling_cmH2O"]
    sessions = cm.session_table(data, rig, DT, ceiling, POST)
    row = {**meta, "error": "", "runtime_s": round(time.perf_counter() - start, 1),
           **cm.run_summary(data, rig, DT, ceiling, POST),
           **cm.invariants(rig, DT, case["controller"]["max_duration_s"])}
    if sessions:
        s = pd.DataFrame(sessions)
        row.update({"sessions_voided_ge_50pct": float(s["voided_ge_50pct"].mean()),
                    "sessions_ceiling_exceeded_gt5": float(s["ceiling_exceeded_gt5"].mean()),
                    "max_true_p_D_during_stim_cmH2O": float(s["max_true_p_D_during_cmH2O"].max()),
                    "median_residual_ml": float(s["residual_ml"].median()),
                    "cutoffs": ";".join(sorted(set(s["cutoff"]))),
                    "n_complete": int((s["emptying"] == "complete").sum()),
                    "n_partial": int((s["emptying"] == "partial").sum()),
                    "n_none": int((s["emptying"] == "none").sum())})
    sessions = [{**meta, **x} for x in sessions]
    if meta["phys_seed"] == 42 and meta["sphincter_scaling"] == 1.0 and meta["group"] in ("main", "reference"):
        # keep a few full traces (1 Hz) for the comparison figure
        # short names: Windows paths are limited to 260 characters (error E38)
        tag = f"exp4_{meta['stim_name']}" if meta["group"] == "reference" else \
            f"exp3_{meta['stim_name']}_{ceiling:.0f}_{case['ultrasound_interval_during_stim_s']:.0f}"
        cols = ["t", "V_B_ml", "p_D_cmH2O", "Q_ml_s", "stim_active", "controller_state"]
        data[cols].iloc[::10].to_csv(RESULTS / "traces" / f"{tag}.csv", index=False)
    return row, sessions


def run_all(cases, label):
    print(f"{label}: {len(cases)} runs ...", flush=True)
    rows, sessions = [], []
    with ProcessPoolExecutor() as pool:
        for i, (row, sess) in enumerate(pool.map(run_one, cases, chunksize=1)):
            rows.append(row)
            sessions += sess
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(cases)} done", flush=True)
                pd.DataFrame(rows).to_csv(RESULTS / f"{label}_runs_partial.csv", index=False)  # save as we go
    runs = pd.DataFrame(rows)
    runs.to_csv(RESULTS / f"{label}_runs.csv", index=False)
    pd.DataFrame(sessions).to_csv(RESULTS / f"{label}_sessions.csv", index=False)
    (RESULTS / f"{label}_runs_partial.csv").unlink(missing_ok=True)
    return runs, pd.DataFrame(sessions)


def summarise_exp3(runs, sessions):
    keys = ["group", "stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s", "threshold_ml",
            "max_duration_s", "sphincter_scaling"]
    def agg(g):
        s = sessions.merge(g[["phys_seed"] + keys], on=["phys_seed"] + keys)
        out = {"n_runs": len(g), "n_sessions": len(s),
               "A2_A3_A4_all_hold": bool(g[["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout",
                                            "A4_sessions_within_max_duration"]].all().all()),
               "P1_sessions_voided_ge_50pct": s["voided_ge_50pct"].mean() if len(s) else np.nan,
               "P2_runs_without_overflow_after_alert": 1 - g["overflow_despite_alert"].mean(),
               "P3_sessions_within_ceiling_plus5": 1 - s["ceiling_exceeded_gt5"].mean() if len(s) else np.nan,
               "median_residual_ml": s["residual_ml"].median() if len(s) else np.nan,
               "max_true_p_D_during_stim_cmH2O": s["max_true_p_D_during_cmH2O"].max() if len(s) else np.nan,
               "cutoff_max_duration": (s["cutoff"].str.contains("max_duration")).mean() if len(s) else np.nan,
               "cutoff_volume_stop": (s["cutoff"].str.contains("volume_stop")).mean() if len(s) else np.nan,
               "cutoff_pressure_ceiling": (s["cutoff"].str.contains("pressure_ceiling")).mean() if len(s) else np.nan,
               "leaked_after_alert_ml_mean": g["leaked_after_alert_ml"].mean(),
               "max_volume_ml_mean": g["max_volume_ml"].mean()}
        out["P1_pass"] = bool(out["P1_sessions_voided_ge_50pct"] >= 0.80)
        out["P2_pass"] = bool(out["P2_runs_without_overflow_after_alert"] >= 0.95)
        out["P3_pass"] = bool(out["P3_sessions_within_ceiling_plus5"] >= 0.95)
        out["full_loop_works"] = out["P1_pass"] and out["P2_pass"] and out["P3_pass"] and out["A2_A3_A4_all_hold"]
        return pd.Series(out)
    return runs.groupby(keys).apply(agg).reset_index()


def summarise_exp4(runs, sessions):
    keys = ["reference", "group", "sphincter_scaling"]
    def agg(g):
        s = sessions.merge(g[["phys_seed"] + keys], on=["phys_seed"] + keys)
        return pd.Series({
            "n_runs": len(g), "n_sessions": len(s), "errors": int((g["error"] != "").sum()),
            "A2_A3_A4_all_hold": bool(g[["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout",
                                         "A4_sessions_within_max_duration"]].all().all()),
            "sessions_per_run": len(s) / len(g),
            "P1_sessions_voided_ge_50pct": s["voided_ge_50pct"].mean() if len(s) else np.nan,
            "overflow_despite_alert_rate": g["overflow_despite_alert"].mean(),
            "leaked_outside_sessions_ml_mean": g["leaked_outside_sessions_ml"].mean(),
            "P3_sessions_within_ceiling_plus5": 1 - s["ceiling_exceeded_gt5"].mean() if len(s) else np.nan,
            "max_true_p_D_during_stim_cmH2O": s["max_true_p_D_during_cmH2O"].max() if len(s) else np.nan,
            "max_exceed_of_ceiling_cmH2O": s["exceeded_ceiling_by_cmH2O"].max() if len(s) else np.nan,
            "cutoff_max_duration": (s["cutoff"].str.contains("max_duration")).mean() if len(s) else np.nan,
            "cutoff_volume_stop": (s["cutoff"].str.contains("volume_stop")).mean() if len(s) else np.nan,
            "cutoff_pressure_ceiling": (s["cutoff"].str.contains("pressure_ceiling")).mean() if len(s) else np.nan,
            "median_residual_ml": s["residual_ml"].median() if len(s) else np.nan,
            "max_volume_ml_mean": g["max_volume_ml"].mean(), "reached_ceiling_rate": g["reached_ceiling"].mean(),
            "ignored_presses_mean": g["n_ignored_presses"].mean()})
    return runs.groupby(keys).apply(agg).reset_index()


def plot_exp3(summary, path):
    main = summary[(summary.group == "main") & (summary.ultrasound_interval_during_stim_s == 60.0)]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, scaling in zip(axs, SCALINGS):
        m = main[main.sphincter_scaling == scaling]
        grid = m.pivot(index="stim_name", columns="pressure_ceiling_cmH2O", values="P1_sessions_voided_ge_50pct")
        works = m.pivot(index="stim_name", columns="pressure_ceiling_cmH2O", values="full_loop_works").loc[grid.index]
        cut = m.pivot(index="stim_name", columns="pressure_ceiling_cmH2O", values="cutoff_pressure_ceiling").loc[grid.index]
        ax.imshow(grid.to_numpy(dtype=float), cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                ax.text(j, i, f"P1 {grid.iat[i, j]:.2f}\nceil-cut {cut.iat[i, j]:.2f}" + ("\nWORKS" if works.iat[i, j] else ""),
                        ha="center", va="center", fontsize=6.5, color="white" if grid.iat[i, j] > 0.6 else "black")
        ax.set_xticks(range(grid.shape[1]), [f"{c:.0f}" for c in grid.columns])
        ax.set_yticks(range(grid.shape[0]), grid.index, fontsize=7)
        ax.set_xlabel("Pressure ceiling (cmH2O)")
        ax.set_title(f"Experiment 3, sphincter x{scaling}: share of sessions voiding >= 50%", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_exp4(summary, path):
    cols = ["P1_sessions_voided_ge_50pct", "overflow_despite_alert_rate", "P3_sessions_within_ceiling_plus5",
            "cutoff_max_duration", "cutoff_volume_stop", "cutoff_pressure_ceiling", "reached_ceiling_rate"]
    fig, axs = plt.subplots(1, 2, figsize=(16, 10), sharey=True)
    for ax, ref in zip(axs, [config.REFERENCE_STIM.value, SECOND_REFERENCE]):
        s = summary[(summary.reference == ref) & (summary.sphincter_scaling == 1.0)].set_index("group")
        grid = s[cols].astype(float)
        ax.imshow(np.nan_to_num(grid.to_numpy(), nan=-0.2), cmap="Greys", vmin=-0.2, vmax=1, aspect="auto")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                v = grid.iat[i, j]
                ax.text(j, i, "-" if np.isnan(v) else f"{v:.2f}", ha="center", va="center", fontsize=6.5,
                        color="tab:red" if (not np.isnan(v) and v > 0.5) else "black")
        ok = s["A2_A3_A4_all_hold"]
        ax.set_yticks(range(len(s)), [g + ("" if ok[g] else "  INVARIANT FAILED") for g in s.index], fontsize=7)
        ax.set_xticks(range(len(cols)), [c.replace("_", "\n") for c in cols], fontsize=6)
        ax.set_title(f"Experiment 4 faults, reference {ref}, sphincter x1.0", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_comparison(path):
    """Experiments 1-4 side by side for the same simulated person (default sphincter, seed 42)."""
    root = Path(__file__).resolve().parents[1] / "results"
    traces = {"Exp 1: SCI baseline, no Cue": pd.read_csv(root / "stage3" / "trace_ceiling_1000_1Hz.csv")}
    e2 = pd.read_csv(root / "stage4b" / "physiology" / "somatic_x1.0_seed42.csv")
    traces["Exp 2: monitoring only (same physiology)"] = e2
    tdir = RESULTS / "traces"
    pick = {"Exp 3: declared reference (co-activation 0.5), ceiling 55": f"exp3_{config.REFERENCE_STIM.value}_55_60.csv",
            "Exp 3: no co-activation, ceiling 55": f"exp3_{SECOND_REFERENCE}_55_60.csv",
            "Exp 4: no co-activation, no fault": f"exp4_{SECOND_REFERENCE}.csv"}
    for label, fname in pick.items():
        if (tdir / fname).exists():
            traces[label] = pd.read_csv(tdir / fname)
    fig, axs = plt.subplots(2, 1, sharex=True, figsize=(10, 7))
    for label, d in traces.items():
        d = d[d["t"] <= 12 * 3600]
        axs[0].plot(d["t"] / 3600, d["V_B_ml"], lw=0.9, label=label)
        axs[1].plot(d["t"] / 3600, d["p_D_cmH2O"], lw=0.9, label=label)
    axs[0].set_ylabel("True volume (mL)")
    axs[1].set_ylabel("True p_D (cmH2O)")
    axs[1].set_xlabel("Time (h)")
    axs[0].legend(fontsize=7)
    fig.suptitle("Experiments 1-4 compared (default sphincter, inflow seed 42; model predictions)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["exp3", "exp4", "figures"], default=None)
    args = parser.parse_args()
    config.validate()
    (RESULTS / "traces").mkdir(parents=True, exist_ok=True)
    if args.only in (None, "exp3"):
        runs, sessions = run_all(exp3_cases(), "exp3")
        summarise_exp3(runs, sessions).to_csv(RESULTS / "exp3_settings_summary.csv", index=False)
    if args.only in (None, "exp4"):
        runs, sessions = run_all(exp4_cases(), "exp4")
        summarise_exp4(runs, sessions).to_csv(RESULTS / "exp4_fault_summary.csv", index=False)
    s3 = pd.read_csv(RESULTS / "exp3_settings_summary.csv")
    plot_exp3(s3, RESULTS / "exp3_P1_by_pattern_and_ceiling.png")
    if (RESULTS / "exp4_fault_summary.csv").exists():
        plot_exp4(pd.read_csv(RESULTS / "exp4_fault_summary.csv"), RESULTS / "exp4_fault_map.png")
    plot_comparison(RESULTS / "comparison_exp1_to_exp4.png")
    print(json.dumps({"exp3_settings": len(s3), "exp3_full_loop_works": int(s3["full_loop_works"].sum())}))


if __name__ == "__main__":
    main()
