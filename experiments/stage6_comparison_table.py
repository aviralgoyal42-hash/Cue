"""
Comparison of Experiments 1-4 over the first 12 h (inflow seed 42, both sphincter strengths).
Experiment 1 = SCI baseline. Experiment 2 changes nothing in the bladder, so it has the same
physiology plus an alert. Experiments 3 and 4 come from the closed-loop runs.
Writes results/stage6/comparison_exp1_to_exp4.csv and comparison_exp1_to_exp4_bars.png.
Usage: python experiments/stage6_comparison_table.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1] / "results"
DT_1HZ = 1.0
R1, R2 = "e1.0_s0.5_5on5off", "e1.0_s0.0_5on5off"


def baseline_row(label, scaling):
    d = pd.read_csv(ROOT / "stage4b" / "physiology" / f"somatic_x{scaling}_seed42.csv")
    return {"experiment": label, "sphincter_scaling": scaling, "alerts": np.nan, "sessions": 0,
            "max_volume_ml": d.V_B_ml.max(), "final_volume_ml": d.V_B_ml.iloc[-1],
            "leaked_outside_sessions_ml": float((d.Q_ml_s * DT_1HZ).sum()), "max_true_p_D_cmH2O": d.p_D_cmH2O.max()}


def closed_row(label, r):
    assert len(r) == 1, label
    r = r.iloc[0]
    return {"experiment": label, "sphincter_scaling": r.sphincter_scaling, "alerts": r.n_alerts, "sessions": r.n_sessions,
            "max_volume_ml": r.max_volume_ml, "final_volume_ml": r.final_volume_ml,
            "leaked_outside_sessions_ml": r.leaked_outside_sessions_ml,
            "max_true_p_D_cmH2O": np.nanmax([r.max_true_p_D_outside_sessions_cmH2O, r.get("max_true_p_D_during_stim_cmH2O", np.nan)])}


def main():
    e3 = pd.read_csv(ROOT / "stage6" / "exp3_runs.csv")
    e4 = pd.read_csv(ROOT / "stage6" / "exp4_runs.csv")
    rows = []
    for s in (1.0, 0.9):
        rows.append(baseline_row("Exp 1: SCI baseline", s))
        rows.append({**baseline_row("Exp 2: monitoring only (alert, no action)", s), "alerts": 1})
        pick = lambda d, q: d[(d.sphincter_scaling == s) & (d.phys_seed == 42) & q(d)]  # noqa: E731
        main3 = lambda d: (d.group == "main") & (d.pressure_ceiling_cmH2O == 55) & (d.ultrasound_interval_during_stim_s == 60)  # noqa: E731
        rows.append(closed_row("Exp 3: co-activation 0.5", pick(e3, lambda d: main3(d) & (d.stim_name == R1))))
        rows.append(closed_row("Exp 3: no co-activation", pick(e3, lambda d: main3(d) & (d.stim_name == R2))))
        rows.append(closed_row("Exp 4: no co-activation, user delayed",
                               pick(e4, lambda d: (d.reference == R2) & (d.group == "user:delayed"))))
        rows.append(closed_row("Exp 4: no co-activation, estimate stuck low",
                               pick(e4, lambda d: (d.reference == R2) & (d.group == "estimate:stuck_low_50ml_from_3h"))))
    t = pd.DataFrame(rows)
    t.to_csv(ROOT / "stage6" / "comparison_exp1_to_exp4.csv", index=False)
    print(t.round(1).to_string(index=False))
    fig, axs = plt.subplots(1, 3, figsize=(14, 5), sharey=True)
    labels = list(t[t.sphincter_scaling == 1.0].experiment)
    y = np.arange(len(labels))
    for ax, col, title in zip(axs, ["max_volume_ml", "leaked_outside_sessions_ml", "max_true_p_D_cmH2O"],
                              ["Maximum true volume (mL)", "Leaked outside sessions (mL)", "Maximum true p_D (cmH2O)"]):
        for offset, s, colour in [(-0.2, 1.0, "tab:blue"), (0.2, 0.9, "tab:orange")]:
            ax.barh(y + offset, t[t.sphincter_scaling == s][col], height=0.38, color=colour, label=f"sphincter x{s}")
        ax.set_title(title, fontsize=9)
        ax.invert_yaxis() if ax is axs[0] else None
    axs[0].set_yticks(y, labels, fontsize=7)
    axs[2].legend(fontsize=7)
    fig.suptitle("Experiments 1-4, first 12 h, inflow seed 42 (model predictions; synthetic sensor; hypothetical stimulator)",
                 fontsize=9)
    fig.tight_layout()
    fig.savefig(ROOT / "stage6" / "comparison_exp1_to_exp4_bars.png", dpi=150)


if __name__ == "__main__":
    main()
