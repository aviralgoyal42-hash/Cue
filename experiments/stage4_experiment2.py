"""
STAGE 4 / Experiment 2: SCI + Cue monitoring (sensor + device + alert, NO intervention).

Success criteria were fixed beforehand in docs/EXPERIMENT2_SUCCESS_CRITERIA.md.

Why the physiology is simulated once and reused: in Experiment 2 nothing the device does
changes the bladder (open loop). So each physiology run (sphincter strength x inflow
seed) is simulated once, and every sensor scenario / sensor seed / alert threshold is
replayed on that same ground-truth trace. Stage 5 (closed loop) cannot do this.

Phases:
  1. physiology  -> results/stage4/physiology/*.csv (1 Hz truth; reused if present)
  2. monitoring  -> sensor readings -> CustomTechDevice -> alerts
  3. evaluation  -> per-run metrics, aggregate table, pass/fail vs C1-C4, figures

Usage: python experiments/stage4_experiment2.py [--rerun-physiology]
       python experiments/stage4_experiment2.py --physiology-seeds 15 --out stage4b   (Experiment 2b)
"""
import argparse
import json
import os
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
from cue_model import CueLUT, simulate  # noqa: E402
from sensors import SensorScenario, SyntheticUltrasoundSensor  # noqa: E402
from devices import CustomTechDevice  # noqa: E402
from evaluation import experiment2_metrics as ev  # noqa: E402

# Output folder and seed list can be changed from the command line. They travel to the
# worker processes through environment variables, because each worker re-imports this file.
RESULTS = Path(__file__).resolve().parents[1] / "results" / os.environ.get("CUE_E2_OUT", "stage4")
PHYS_DIR = RESULTS / "physiology"
E2, DEV, SEN = config.EXPERIMENT2, config.DEVICE, config.SENSOR
C1_MIN_USEFUL, C2_MAX_FALSE, C3_MIN_LEAD_MIN = 0.95, 0.05, 30.0   # frozen criteria
POSTHOC_BAND_ML = (350.0, 450.0)   # POST-HOC metric only (docs/EXPERIMENT2B_RERUN_CRITERIA.md)


def physiology_seeds():
    n = int(os.environ.get("CUE_E2_N_SEEDS", "0"))
    return config.value(E2, "physiology_seeds") if n == 0 else [42] + list(range(1, n))


def physiology_name(scaling, seed):
    return f"somatic_x{scaling}_seed{seed}"


def run_physiology(args):
    """Simulate one SCI baseline (no Cue) and save the 1 Hz ground truth."""
    scaling, seed = args
    model = CueLUT(sci_enabled=True,
                   fullness_reference_ml=config.value(config.SCI, "fullness_reference_ml"),
                   volume_ceiling_ml=config.value(config.SCI, "volume_ceiling_ml"),
                   initial_volume_ml=config.value(config.SIMULATION, "initial_volume_ml"),
                   drive_above_reference=config.value(config.SCI, "drive_above_reference"),
                   overrides={"neural_args.somatic_a": CueLUT().neural_args["somatic_a"] * scaling})
    start = time.perf_counter()
    with np.errstate(invalid="ignore", over="ignore"):
        data = simulate(model, config.value(E2, "duration_s"), config.value(config.SIMULATION, "dt_s"), seed,
                        config.value(config.SIMULATION, "inflow_noise"))
    keep = ["t", "V_B_ml", "p_D_cmH2O", "p_S_cmH2O", "Q_ml_s", "Q_in_ml_s", "voiding"]
    data[keep].iloc[::10].to_csv(PHYS_DIR / f"{physiology_name(scaling, seed)}.csv", index=False)
    return physiology_name(scaling, seed), time.perf_counter() - start


def monitor(truth, scenario, sensor_seed, thresholds):
    """Replay one sensor stream through one device per threshold. Returns rows + example data."""
    v_ref = config.value(E2, "reference_volume_ml")
    true_at = ev.truth_lookup(truth)
    t_adverse, adverse_kind = ev.adverse_event(truth, v_ref)
    sensor = SyntheticUltrasoundSensor(scenario, sensor_seed)
    dt_read = config.value(SEN, "sample_interval_s")
    times = np.arange(dt_read, truth["t"].iloc[-1], dt_read)
    readings = [sensor.read(float(t), true_at) for t in times]
    sensor_stats = ev.sensor_errors(readings, true_at, config.value(E2, "relative_error_floor_ml"))
    rows, devices = [], {}
    for thr in thresholds:
        device = CustomTechDevice(thr, median_window=config.value(DEV, "median_window"),
                                  confirm_n=config.value(DEV, "confirm_n"),
                                  rearm_hysteresis_ml=config.value(DEV, "rearm_hysteresis_ml"),
                                  stale_timeout_s=config.value(DEV, "stale_timeout_s"))
        for r in readings:
            device.receive(r)
        alerts = ev.alert_events(device.events)
        cls = ev.classify_alerts(alerts, true_at, t_adverse, config.value(E2, "false_alert_fraction") * v_ref)
        gaps, flagged = ev.stale_detection(readings, device.events, config.value(DEV, "stale_timeout_s"))
        first = cls["first_genuine_alert_t_h"]
        p_at_alert = float(np.interp(first * 3600, truth["t"], truth["p_D_cmH2O"])) if first is not None else None
        rows.append({"threshold_ml": thr, "adverse_kind": adverse_kind,
                     "t_adverse_h": t_adverse / 3600 if t_adverse is not None else None,
                     **cls, "true_p_D_at_genuine_alert_cmH2O": p_at_alert, **sensor_stats,
                     **ev.estimate_errors(device.history, true_at), "stale_gaps": gaps, "stale_flagged": flagged})
        devices[thr] = device
    return rows, readings, devices


def run_scenario(args):
    """All physiology runs x sensor seeds x thresholds for one sensor scenario."""
    scen_index, (scen_name, scen_values) = args
    scenario = SensorScenario.from_dict(scen_name, scen_values)
    thresholds = config.value(E2, "alert_thresholds_ml")
    rows = []
    for scaling in config.value(E2, "sphincter_scalings"):
        for phys_seed in physiology_seeds():
            truth = pd.read_csv(PHYS_DIR / f"{physiology_name(scaling, phys_seed)}.csv")
            for rep in range(config.value(E2, "sensor_seeds_per_case")):
                # The sensor seed is derived from the case, so every run can be reproduced exactly.
                seed = np.random.SeedSequence([scen_index, int(scaling * 100), phys_seed, rep]).generate_state(1)[0]
                case_rows, _, _ = monitor(truth, scenario, int(seed), thresholds)
                for r in case_rows:
                    rows.append({"scenario": scen_name, "sphincter_scaling": scaling, "physiology_seed": phys_seed,
                                 "sensor_rep": rep, "sensor_seed": int(seed), **r})
    return rows


def aggregate(runs):
    def agg(g):
        lead = g["lead_time_min"].dropna()
        out = {"n_runs": len(g), "useful_rate": g["useful"].mean(), "false_alert_run_rate": g["any_false_alert"].mean(),
               "late_rate": g["late"].mean(), "missed_rate": g["missed"].mean(),
               "median_lead_min": lead.median() if len(lead) else np.nan,
               "median_true_volume_at_alert_ml": g["true_volume_at_genuine_alert_ml"].median(),
               "sensor_mae_ml": g["mae_ml"].mean(), "sensor_rmse_ml": g["rmse_ml"].mean(),
               "sensor_mean_relative_error": g["mean_relative_error"].mean(),
               "missing_fraction": g["missing_fraction"].mean(), "estimate_mae_ml": g["estimate_mae_ml"].mean(),
               "stale_gaps": g["stale_gaps"].sum(), "stale_flagged": g["stale_flagged"].sum()}
        v = g["true_volume_at_genuine_alert_ml"]
        in_band = g["useful"] & (v >= POSTHOC_BAND_ML[0]) & (v <= POSTHOC_BAND_ML[1])
        out["POSTHOC_band_350_450_rate"] = in_band.mean()   # post-hoc metric, NOT a criterion
        out["C1_useful>=95%"] = out["useful_rate"] >= C1_MIN_USEFUL
        out["C2_false<=5%"] = out["false_alert_run_rate"] <= C2_MAX_FALSE
        out["C3_lead>=30min"] = bool(out["median_lead_min"] >= C3_MIN_LEAD_MIN)
        out["cue_works_C1_C2_C3"] = out["C1_useful>=95%"] and out["C2_false<=5%"] and out["C3_lead>=30min"]
        return pd.Series(out)
    return runs.groupby(["sphincter_scaling", "scenario", "threshold_ml"]).apply(agg).reset_index()


def plot_example(truth, scenario_name, threshold, path, sensor_seed=7):
    scen = SensorScenario.from_dict(scenario_name, config.SENSOR_SCENARIOS.value[scenario_name])
    rows, readings, devices = monitor(truth, scen, sensor_seed, [threshold])
    dev = devices[threshold]
    t_adv = rows[0]["t_adverse_h"]
    true_at = ev.truth_lookup(truth)
    rt = np.array([r.t_s for r in readings]) / 3600
    rv = np.array([r.volume_ml if r.valid else np.nan for r in readings])
    est = np.array([h["estimate_ml"] if h["estimate_ml"] is not None else np.nan for h in dev.history])
    fig, axs = plt.subplots(2, 1, sharex=True, figsize=(9, 6.5), gridspec_kw={"height_ratios": [2, 1]})
    axs[0].plot(truth["t"] / 3600, truth["V_B_ml"], color="black", lw=1.2, label="true volume (evaluation only)")
    axs[0].plot(rt, rv, ".", ms=2.5, color="tab:blue", alpha=0.6, label="sensor readings (synthetic proxy)")
    axs[0].plot(rt, est, color="tab:orange", lw=1, label="device estimate (median of 5)")
    axs[0].axhline(threshold, color="tab:red", ls="--", lw=0.8, label=f"alert threshold {threshold:.0f} mL")
    for t in ev.alert_events(dev.events):
        axs[0].axvline(t / 3600, color="tab:red", lw=1.2)
    if t_adv is not None:
        axs[0].axvline(t_adv, color="purple", ls=":", lw=1.5, label=f"adverse event ({rows[0]['adverse_kind']})")
    axs[0].set_ylabel("Volume (mL)")
    axs[0].set_ylim(0, 1100)
    axs[0].legend(fontsize=7, loc="upper left")
    axs[1].plot(rt, rv - np.array([true_at(r.t_s) for r in readings]), ".", ms=2.5, color="tab:blue",
                label="reading - truth")
    axs[1].plot(rt, est - np.array([true_at(r.t_s) for r in readings]), color="tab:orange", lw=1,
                label="estimate - truth")
    axs[1].axhline(0, color="black", lw=0.6)
    axs[1].set_ylabel("Error (mL)")
    axs[1].set_xlabel("Time (h)")
    axs[1].legend(fontsize=7, loc="lower left")
    fig.suptitle(f"Experiment 2 example: sensor '{scenario_name}', threshold {threshold:.0f} mL "
                 f"(red lines = alerts; model predictions)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_tradeoff(summary, scaling, path):
    scenarios = list(config.SENSOR_SCENARIOS.value)
    fig, axs = plt.subplots(3, 5, sharex=True, sharey=True, figsize=(14, 8))
    for ax, name in zip(axs.flat, scenarios):
        s = summary[(summary["sphincter_scaling"] == scaling) & (summary["scenario"] == name)]
        ax.plot(s["threshold_ml"], s["useful_rate"], "o-", ms=3, color="tab:green", label="useful (before adverse)")
        ax.plot(s["threshold_ml"], s["false_alert_run_rate"], "s-", ms=3, color="tab:red", label="runs with false alert")
        ax.plot(s["threshold_ml"], s["late_rate"] + s["missed_rate"], "^-", ms=3, color="tab:purple",
                label="late or missed")
        ax.axhline(0.95, color="tab:green", lw=0.5, ls=":")
        ax.axhline(0.05, color="tab:red", lw=0.5, ls=":")
        ok = s[s["cue_works_C1_C2_C3"]]
        ax.scatter(ok["threshold_ml"], [1.05] * len(ok), marker="*", color="black", s=30)
        ax.set_title(name, fontsize=8)
        ax.set_ylim(-0.05, 1.12)
    axs[0, 0].legend(fontsize=6, loc="center left")
    for ax in axs[-1]:
        ax.set_xlabel("Alert threshold (mL)", fontsize=8)
    for ax in axs[:, 0]:
        ax.set_ylabel("Fraction of runs", fontsize=8)
    fig.suptitle(f"Experiment 2 trade-off, sphincter x{scaling} (star = C1, C2 and C3 all pass)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_pass_map(summary, path):
    fig, axs = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
    for ax, scaling in zip(axs, config.value(E2, "sphincter_scalings")):
        s = summary[summary["sphincter_scaling"] == scaling]
        grid = s.pivot(index="scenario", columns="threshold_ml", values="useful_rate")
        grid = grid.loc[list(config.SENSOR_SCENARIOS.value)]
        works = s.pivot(index="scenario", columns="threshold_ml", values="cue_works_C1_C2_C3").loc[grid.index]
        false = s.pivot(index="scenario", columns="threshold_ml", values="false_alert_run_rate").loc[grid.index]
        ax.imshow(grid.to_numpy(dtype=float), cmap="Greys", vmin=0, vmax=1, aspect="auto")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                mark = "PASS" if works.iat[i, j] else ""
                ax.text(j, i, f"{grid.iat[i, j]:.2f}\nF{false.iat[i, j]:.2f} {mark}", ha="center", va="center",
                        fontsize=6, color="tab:red" if grid.iat[i, j] > 0.5 else "black")
        ax.set_xticks(range(grid.shape[1]), [f"{c:.0f}" for c in grid.columns], fontsize=7)
        ax.set_yticks(range(grid.shape[0]), grid.index, fontsize=7)
        ax.set_xlabel("Alert threshold (mL)")
        ax.set_title(f"sphincter x{scaling}: useful-alert rate (F = false-alert run rate)", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun-physiology", action="store_true")
    parser.add_argument("--physiology-seeds", type=int, default=0, help="N seeds: 42 and 1..N-1 (0 = config)")
    parser.add_argument("--out", default="stage4", help="results sub-folder")
    args = parser.parse_args()
    if args.physiology_seeds or args.out != "stage4":
        # Re-launch with the settings in the environment so the worker processes see them too.
        os.environ["CUE_E2_N_SEEDS"], os.environ["CUE_E2_OUT"] = str(args.physiology_seeds), args.out
        globals().update(RESULTS=Path(__file__).resolve().parents[1] / "results" / args.out)
        globals().update(PHYS_DIR=RESULTS / "physiology")
    config.validate()
    PHYS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(config.as_table()).to_csv(RESULTS / "parameters_used.csv", index=False)

    todo = [(s, seed) for s in config.value(E2, "sphincter_scalings") for seed in physiology_seeds()
            if args.rerun_physiology or not (PHYS_DIR / f"{physiology_name(s, seed)}.csv").exists()]
    if todo:
        print(f"Phase 1: simulating {len(todo)} physiology runs ...", flush=True)
        with ProcessPoolExecutor() as pool:
            for name, rt in pool.map(run_physiology, todo):
                print(f"  {name}: {rt:.0f} s", flush=True)

    print("Phase 2: monitoring runs ...", flush=True)
    scenarios = list(enumerate(config.SENSOR_SCENARIOS.value.items()))
    with ProcessPoolExecutor() as pool:
        runs = pd.DataFrame([row for rows in pool.map(run_scenario, scenarios) for row in rows])
    runs.to_csv(RESULTS / "exp2_all_runs.csv", index=False)

    print("Phase 3: evaluation ...", flush=True)
    summary = aggregate(runs)
    summary.to_csv(RESULTS / "exp2_summary.csv", index=False)
    stale = runs.groupby("scenario")[["stale_gaps", "stale_flagged"]].sum()
    stale.to_csv(RESULTS / "exp2_stale_detection_C4.csv")
    for scaling in config.value(E2, "sphincter_scalings"):
        plot_tradeoff(summary, scaling, RESULTS / f"exp2_tradeoff_sphincter_x{scaling}.png")
        truth = pd.read_csv(PHYS_DIR / f"{physiology_name(scaling, 42)}.csv")
        for scen in ["anchor_11pct", "combined_bad"]:
            plot_example(truth, scen, 400.0, RESULTS / f"exp2_example_{scen}_sphincter_x{scaling}.png")
    plot_pass_map(summary, RESULTS / "exp2_pass_map.png")
    works = summary[summary["cue_works_C1_C2_C3"]]
    report = {"n_monitoring_runs": len(runs), "C4_stale": stale.to_dict(),
              "passing_combinations": works[["sphincter_scaling", "scenario", "threshold_ml"]].to_dict("records")}
    with open(RESULTS / "exp2_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"{len(runs)} monitoring runs; {len(works)} of {len(summary)} combinations pass C1-C3.")


if __name__ == "__main__":
    main()
