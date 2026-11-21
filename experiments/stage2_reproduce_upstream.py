"""
STAGE 2: reproduce an existing upstream example, with the model UNMODIFIED.

What it does
------------
1. Runs the paper's Figure 2 simulation exactly as `paper_figures/figures.ipynb`
   (cell 4) does: 1 day, dT = 0.1 s, seed = 42, volume in mL, pressure in cmH2O.
2. Compares the first and last five rows with the numbers printed in the saved
   notebook output. Pandas printed them to 6 decimals, so a value "matches" if it
   is within 5e-7 of the printed number (half of the last printed digit).
3. Summarises the run (voids, capacity, voiding duration, peak flow, inflow) and
   saves a downsampled CSV and a figure in results/stage2/.
4. Optional (--baseline5d): repeats the 5-day sensitivity-analysis baseline from
   the notebook (cell 18) and compares its three printed metrics.

Nothing here changes the physiology. It only calls `LUT.process_neural_input`.

Usage:  python experiments/stage2_reproduce_upstream.py [--baseline5d]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # write PNG files without opening a window
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lut_upstream import load_upstream, PROJECT_ROOT, UPSTREAM_COMMIT  # noqa: E402

RESULTS_DIR = PROJECT_ROOT / "results" / "stage2"

COLUMNS = ["t", "V_B", "f_aD_s", "f_aS_s", "r_U", "Q", "p_D", "p_S",
           "Q_in", "w_e_s", "w_i_s", "w_s_s", "voiding"]

# Printed output of figures.ipynb cell 4 (upstream v1.3.0). Units: s, mL, cmH2O, mL/s.
EXPECTED_HEAD = [
    [0.0, 0.0, 0.004000, 0.250000, 0.0, 0.0, 0.178035, 30.051363, 0.0, 0.040000, 0.100000, 0.5, 0.0],
    [0.1, 0.0, 0.007560, 0.375000, 0.0, 0.0, 0.336485, 44.567187, 0.0, 0.040000, 0.100000, 0.5, 0.0],
    [0.2, 0.0, 0.010728, 0.437500, 0.0, 0.0, 0.477507, 51.825098, 0.0, 0.040000, 0.100000, 0.5, 0.0],
    [0.3, 0.0, 0.013548, 0.468750, 0.0, 0.0, 0.603016, 55.454054, 0.0, 0.040000, 0.100000, 0.5, 0.0],
    [0.4, 0.0, 0.016058, 0.484375, 0.0, 0.0, 0.714719, 57.268532, 0.0, 0.040000, 0.100000, 0.5, 0.0],
]
EXPECTED_TAIL = [
    [86399.5, 484.580062, 0.814345, 0.5, 0.0, 0.0, 53.061212, 59.083010, 0.028931, 0.948206, 0.164169, 0.5, 0.0],
    [86399.6, 484.582955, 0.814364, 0.5, 0.0, 0.0, 53.062329, 59.083010, 0.028931, 0.948221, 0.164159, 0.5, 0.0],
    [86399.7, 484.585848, 0.814384, 0.5, 0.0, 0.0, 53.063446, 59.083010, 0.028931, 0.948235, 0.164150, 0.5, 0.0],
    [86399.8, 484.588741, 0.814403, 0.5, 0.0, 0.0, 53.064563, 59.083010, 0.028931, 0.948249, 0.164140, 0.5, 0.0],
    [86399.9, 484.591634, 0.814422, 0.5, 0.0, 0.0, 53.065679, 59.083010, 0.028931, 0.948264, 0.164130, 0.5, 0.0],
]
PRINT_TOLERANCE = 5e-7

# Printed output of figures.ipynb cell 18: baseline row of the sensitivity analysis.
EXPECTED_BASELINE_5D = {"mean_intervoid_interval_hrs": 6.04,
                        "mean_peak_capacity_ml": 489.56,
                        "mean_voided_volume_ml": 489.56}


def run_upstream(days, dT=0.1, seed=42):
    """Run the unmodified model and return (DataFrame in mL / cmH2O, runtime in s)."""
    LUT_Model = load_upstream()
    lut = LUT_Model.LUT()
    start = time.perf_counter()
    data = lut.process_neural_input(days * 24 * 3600, dT, seed=seed, V_unit="ml", p_unit="cmH2O")
    return data, time.perf_counter() - start


def compare_rows(data, expected, label):
    """Return a table of |simulated - printed| for every column of the given rows."""
    sim = data[COLUMNS].to_numpy()[:len(expected)] if label == "head" else data[COLUMNS].to_numpy()[-len(expected):]
    diff = np.abs(sim - np.array(expected))
    table = pd.DataFrame(diff, columns=COLUMNS)
    table.insert(0, "rows", label)
    return table


def void_events(data):
    """Start and end row indices of each completed void (voiding goes 0 -> 1 -> 0)."""
    change = data["voiding"].astype(int).diff()
    starts = np.flatnonzero(change.to_numpy() == 1)
    ends = np.flatnonzero(change.to_numpy() == -1)
    ends = ends[ends > starts[0]] if len(starts) else ends
    n = min(len(starts), len(ends))
    return starts[:n], ends[:n], starts


def notebook_metrics(data):
    """Same three metrics as `calculate_metrics` in figures.ipynb cell 17."""
    change = data["voiding"].diff()
    v_starts = data[change == 1]
    v_ends = data[change == -1]
    intervals = np.diff(v_starts["t"])
    n = min(len(v_starts), len(v_ends))
    peaks = [data.iloc[v_starts.index[i]:v_ends.index[i]]["V_B"].max() for i in range(n)]
    voided = [v_starts["V_B"].iloc[i] - v_ends["V_B"].iloc[i] for i in range(n)]
    return {"mean_intervoid_interval_hrs": float(np.mean(intervals) / 3600) if len(intervals) else 0.0,
            "mean_peak_capacity_ml": float(np.mean(peaks)) if peaks else 0.0,
            "mean_voided_volume_ml": float(np.mean(voided)) if voided else 0.0}


def summarise(data, dT):
    """Plain-language summary of one run (all values are model outputs, not facts)."""
    starts, ends, all_starts = void_events(data)
    v = data["V_B"].to_numpy()
    return {
        "n_void_starts": int(len(all_starts)),
        "void_start_times_h": [round(float(data["t"].iloc[i]) / 3600, 3) for i in all_starts],
        "volume_at_void_start_ml": [round(float(v[i]), 2) for i in all_starts],
        "pressure_at_void_start_cmH2O": [round(float(data["p_D"].iloc[i]), 2) for i in all_starts],
        "volume_at_void_end_ml": [round(float(v[i]), 4) for i in ends],
        "void_durations_s": [round((e - s) * dT, 1) for s, e in zip(starts, ends)],
        "peak_flow_ml_per_s": round(float(data["Q"].max()), 3),
        "max_volume_ml": round(float(v.max()), 2),
        "max_p_D_cmH2O": round(float(data["p_D"].max()), 2),
        "mean_Q_in_ml_per_s": round(float(data["Q_in"].mean()), 5),
        "storage_closure_p_S_cmH2O_at_end": round(float(data["p_S"].iloc[-1]), 3),
    }


def plot_run(data, path):
    """Volume, pressure and neural drive vs time (same panels as paper Figure 2)."""
    d = data.iloc[::50]  # every 5 s is enough for a 1-day plot
    t_h = d["t"] / 3600
    fig, axs = plt.subplots(3, 1, sharex=True, figsize=(8, 6.5))
    axs[0].plot(t_h, d["p_D"], color="black", lw=0.8)
    axs[0].set_ylabel("p_D (cmH2O)")
    axs[1].plot(t_h, d["V_B"], color="black", lw=0.8)
    axs[1].set_ylabel("V_B (mL)")
    axs[2].plot(t_h, d["w_e_s"], lw=0.8, label="omega_e* (pelvic, excites detrusor)")
    axs[2].plot(t_h, d["w_i_s"], lw=0.8, label="omega_i* (hypogastric, inhibits detrusor)")
    axs[2].plot(t_h, d["w_s_s"], lw=0.8, label="omega_s* (pudendal, sphincter)")
    axs[2].set_ylabel("Neural drive (0-1)")
    axs[2].set_xlabel("Time (h)")
    axs[2].legend(fontsize=7, loc="upper left")
    fig.suptitle("Stage 2: upstream LUT model, unmodified (1 day, dT 0.1 s, seed 42)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--baseline5d", action="store_true", help="also check the 5-day sensitivity baseline")
    args = parser.parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print("Running upstream Figure 2 example: 1 day, dT 0.1 s, seed 42 ...")
    data, runtime = run_upstream(days=1)
    check = pd.concat([compare_rows(data, EXPECTED_HEAD, "head"), compare_rows(data, EXPECTED_TAIL, "tail")])
    worst = float(check[COLUMNS].to_numpy().max())
    passed = worst <= PRINT_TOLERANCE
    print(f"Runtime {runtime:.1f} s. Largest difference from notebook print: {worst:.2e} "
          f"(tolerance {PRINT_TOLERANCE:.0e}) -> {'MATCH' if passed else 'MISMATCH'}")

    report = {"upstream_commit": UPSTREAM_COMMIT, "numpy": np.__version__, "pandas": pd.__version__,
              "figure2_run": {"runtime_s": round(runtime, 1), "rows": len(data),
                              "max_abs_difference_vs_notebook": worst, "tolerance": PRINT_TOLERANCE,
                              "match": passed, "summary": summarise(data, 0.1),
                              "notebook_metrics": notebook_metrics(data)}}
    check.to_csv(RESULTS_DIR / "figure2_row_check.csv", index=False)
    data.iloc[::10].to_csv(RESULTS_DIR / "figure2_run_1day_1Hz.csv", index=False)  # 1 sample per second
    plot_run(data, RESULTS_DIR / "figure2_reproduction.png")

    if args.baseline5d:
        print("Running 5-day sensitivity baseline: dT 0.1 s, seed 42 ...")
        data5, runtime5 = run_upstream(days=5)
        metrics = notebook_metrics(data5)
        rounded = {k: round(v, 2) for k, v in metrics.items()}
        ok = rounded == EXPECTED_BASELINE_5D
        print(f"Runtime {runtime5:.1f} s. Metrics {rounded} vs notebook {EXPECTED_BASELINE_5D} -> "
              f"{'MATCH' if ok else 'MISMATCH'}")
        report["baseline_5day"] = {"runtime_s": round(runtime5, 1), "metrics": metrics,
                                   "metrics_rounded": rounded, "expected": EXPECTED_BASELINE_5D,
                                   "match": ok, "summary": summarise(data5, 0.1)}

    with open(RESULTS_DIR / "stage2_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
