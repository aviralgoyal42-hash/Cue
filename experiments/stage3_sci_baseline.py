"""
STAGE 3 / Experiment 1: baseline SCI, no Cue device.

Runs the simplified SCI condition (config.SCI) and a healthy control, then checks how
the result depends on every value we could not source. Nothing is tuned: each
ASSUMED value is swept over a range and every run is reported.

Runs (all 24 h, dT and noise from config unless stated):
  control                    healthy upstream model (no SCI), 500 mL clip = upstream
  ceiling_<x>                SCI with volume ceiling x mL (ASSUMED; sweep)
  seed_<n>                   SCI, default ceiling, other random seeds (stochastic spread)
  somatic_a_x<f> etc.        SCI, default ceiling, one upstream neural strength scaled by f.
                             These are SOURCED upstream values, but the paper says they lack
                             empirical ranges, so the SCI result is checked against them.
  default_48h                SCI, default ceiling, two days (is 24 h long enough?)

Outputs: results/stage3/ (1 Hz CSVs, summary CSV/JSON, figures, parameter table).
Usage:   python experiments/stage3_sci_baseline.py
"""
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
from cue_model import CueLUT, simulate  # noqa: E402
from cue_model.metrics import run_summary, leak_episodes  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results" / "stage3"
DAY_S = 24 * 3600


def make_cases():
    """Every run of this experiment as a plain dict (so it can go to a worker process)."""
    sim, sci = config.SIMULATION, config.SCI
    base = {"sci": True, "ceiling_ml": config.value(sci, "volume_ceiling_ml"), "seed": config.value(sim, "seed"),
            "duration_s": config.value(sim, "duration_s"), "overrides": dict(config.PHYSIOLOGY_OVERRIDES),
            "drive": config.value(sci, "drive_above_reference")}
    cases = {"control": {**base, "sci": False, "ceiling_ml": 500.0, "drive": "extrapolate"}}
    upstream_neural = CueLUT().neural_args
    for drive in ["extrapolate", "hold"]:      # both ASSUMED rules for drives above 500 mL
        tag = "" if drive == "extrapolate" else "hold_"
        d = {**base, "drive": drive}
        for c in config.CEILING_SWEEP_ML.value:
            cases[f"{tag}ceiling_{int(c)}"] = {**d, "ceiling_ml": c}
        for s in [1, 2, 3, 4]:
            cases[f"{tag}seed_{s}"] = {**d, "seed": s}
        for name, factors in [("somatic_a", [0.75, 0.9, 1.1, 1.25]),
                              ("parasympathetic_a", [0.75, 1.25]),
                              ("sympathetic_a", [0.75, 1.25])]:
            for f in factors:
                cases[f"{tag}{name}_x{f}"] = {**d, "overrides": {**d["overrides"],
                                                                f"neural_args.{name}": upstream_neural[name] * f}}
        cases[f"{tag}default_48h"] = {**d, "duration_s": 2 * DAY_S}
    return cases


def run_case(item):
    """Run one case; save its 1 Hz trace; return (name, summary, leak table, runtime)."""
    name, case = item
    dt = config.value(config.SIMULATION, "dt_s")
    start = time.perf_counter()
    model = CueLUT(sci_enabled=case["sci"], fullness_reference_ml=config.value(config.SCI, "fullness_reference_ml"),
                   volume_ceiling_ml=case["ceiling_ml"],
                   initial_volume_ml=config.value(config.SIMULATION, "initial_volume_ml"),
                   overrides=case["overrides"], drive_above_reference=case["drive"])
    with np.errstate(invalid="ignore", over="ignore"):
        data = simulate(model, case["duration_s"], dt, case["seed"], config.value(config.SIMULATION, "inflow_noise"))
    summary = run_summary(data, dt, config.value(config.SIMULATION, "initial_volume_ml"), case["ceiling_ml"])
    summary["all_values_finite"] = bool(np.isfinite(data.drop(columns="voiding").to_numpy(dtype=float)).all())
    leaks = leak_episodes(data, dt)
    keep = ["t", "V_B_ml", "p_D_cmH2O", "p_S_cmH2O", "Q_ml_s", "Q_in_ml_s", "r_U_mm",
            "f_aD_s", "f_aS_s", "w_e_s", "w_i_s", "w_s_s", "voiding"]
    data[keep].iloc[::10].to_csv(RESULTS_DIR / f"trace_{name}_1Hz.csv", index=False)
    return name, {**case, **summary}, leaks, time.perf_counter() - start


def plot_control_vs_sci(control, sci, path):
    fig, axs = plt.subplots(4, 1, sharex=True, figsize=(9, 9))
    for label, d, style in [("healthy control", control, dict(color="grey", lw=0.8)),
                            ("SCI (no Cue)", sci, dict(color="black", lw=0.9))]:
        t = d["t"] / 3600
        axs[0].plot(t, d["V_B_ml"], label=label, **style)
        axs[1].plot(t, d["p_D_cmH2O"], label=f"p_D {label}", **style)
        axs[2].plot(t, d["Q_ml_s"], label=label, **style)
    axs[1].plot(sci["t"] / 3600, sci["p_S_cmH2O"], color="tab:red", lw=0.8, ls="--", label="p_S (sphincter) SCI")
    t = sci["t"] / 3600
    axs[3].plot(t, sci["w_e_s"], lw=0.8, label="omega_e* (detrusor excitation)")
    axs[3].plot(t, sci["w_i_s"], lw=0.8, label="omega_i* (detrusor inhibition)")
    axs[3].plot(t, sci["w_s_s"], lw=0.8, label="omega_s* (sphincter)")
    labels = ["Volume (mL)", "Pressure (cmH2O)", "Outflow (mL/s)", "SCI neural drive"]
    for ax, lab in zip(axs, labels):
        ax.set_ylabel(lab)
        ax.legend(fontsize=7, loc="upper left")
    axs[3].set_xlabel("Time (h)")
    fig.suptitle("Experiment 1: baseline SCI vs healthy control (model predictions, default ceiling)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_ceiling_sweep(traces, path):
    fig, axs = plt.subplots(2, 1, sharex=True, figsize=(9, 6))
    for name, d in traces.items():
        t = d["t"] / 3600
        axs[0].plot(t, d["V_B_ml"], lw=0.9, label=name)
        axs[1].plot(t, d["p_D_cmH2O"], lw=0.9, label=name)
    axs[0].set_ylabel("Volume (mL)")
    axs[1].set_ylabel("p_D (cmH2O)")
    axs[1].set_xlabel("Time (h)")
    axs[0].legend(fontsize=7)
    fig.suptitle("SCI baseline: effect of the ASSUMED volume ceiling", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    config.validate()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(config.as_table()).to_csv(RESULTS_DIR / "parameters_used.csv", index=False)
    cases = make_cases()
    print(f"Running {len(cases)} cases in parallel ...")
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(run_case, cases.items()))
    summaries, all_leaks = [], []
    for name, summary, leaks, runtime in results:
        summaries.append({"case": name, "runtime_s": round(runtime, 1), **summary})
        if len(leaks):
            all_leaks.append(leaks.assign(case=name))
        print(f"  {name:28s} {runtime:6.1f} s  leaks={summary['n_leak_episodes']:3d} "
              f"max V={summary['max_volume_ml']:7.1f} mL  max p_D={summary['max_p_D_cmH2O']:6.1f} cmH2O")
    table = pd.DataFrame(summaries)
    table.to_csv(RESULTS_DIR / "summary_all_cases.csv", index=False)
    if all_leaks:
        pd.concat(all_leaks).to_csv(RESULTS_DIR / "leak_episodes_all_cases.csv", index=False)
    with open(RESULTS_DIR / "summary_all_cases.json", "w") as f:
        json.dump(summaries, f, indent=2, default=str)

    read = lambda n: pd.read_csv(RESULTS_DIR / f"trace_{n}_1Hz.csv")  # noqa: E731
    default = f"ceiling_{int(config.value(config.SCI, 'volume_ceiling_ml'))}"
    plot_control_vs_sci(read("control"), read(default), RESULTS_DIR / "exp1_control_vs_sci.png")
    plot_control_vs_sci(read("control"), read("hold_" + default), RESULTS_DIR / "exp1_control_vs_sci_hold.png")
    for tag in ["", "hold_"]:
        plot_ceiling_sweep({n: read(n) for n in table["case"] if n.startswith(f"{tag}ceiling_")},
                           RESULTS_DIR / f"exp1_{tag}ceiling_sweep.png")


if __name__ == "__main__":
    main()
