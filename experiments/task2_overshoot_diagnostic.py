"""
Experiment 3b diagnostic, NOT part of the frozen grid. Why does true pressure pass a 40 cmH2O
ceiling by more than 5 cmH2O in sessions the ceiling never stopped?

Reruns the worst seed of one failing setting at three time steps and records, per session, the
pressure at the start, the peak, how long pressure stayed at or above the ceiling, and the flow
just before the peak. The peak comes in the step where the outlet shuts. A height or width that
changes with the time step points to a numerical effect. The time step is changed in memory only;
config.py and every saved result stay as they are.

Writes results/task2/exp3b_overshoot_diagnostic.csv.
Usage: python experiments/task2_overshoot_diagnostic.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task2_experiment3b as t2  # noqa: E402

SETTING = {"stim_name": "e0.6_s0.0_5on5off", "sphincter_scaling": 1.0, "max_duration_s": 60.0, "threshold_ml": 400.0,
           "pressure_ceiling_cmH2O": 40.0}
STEPS_S = [0.1, 0.05, 0.025]


def one(args):
    dt, seed = args
    config = t2.s6.config
    config.SIMULATION["dt_s"] = replace(config.SIMULATION["dt_s"], value=dt)
    case = next(c for c in t2.cases() if c["phys_seed"] == seed and c["threshold_ml"] == SETTING["threshold_ml"]
                and c["controller"]["max_duration_s"] == SETTING["max_duration_s"]
                and c["controller"]["pressure_ceiling_cmH2O"] == SETTING["pressure_ceiling_cmH2O"]
                and c["sphincter_scaling"] == SETTING["sphincter_scaling"] and c["stim_name"] == SETTING["stim_name"])
    rig_mod = t2.s6.rig_mod
    data, rig = rig_mod.run_closed_loop(rig_mod.default_case(**{k: v for k, v in case.items() if k != "group"}))
    t, p, q = data["t"].to_numpy(), data["p_D_cmH2O"].to_numpy(), data["Q_ml_s"].to_numpy()
    rows = []
    for s in rig.controller.sessions:
        idx = ((t >= s["start_s"]) & (t <= s["stop_s"])).nonzero()[0]
        peak = idx[p[idx].argmax()]
        rows.append({"dt_s": dt, "seed": seed, "start_h": s["start_s"] / 3600, "duration_s": s["stop_s"] - s["start_s"],
                     "cutoff": s["cutoff"], "true_p_D_at_start_cmH2O": p[idx[0]], "true_p_D_peak_cmH2O": p[peak],
                     "seconds_at_or_above_ceiling": (p[idx] >= SETTING["pressure_ceiling_cmH2O"]).sum() * dt,
                     "p_D_one_step_before_peak_cmH2O": p[peak - 1], "Q_one_step_before_peak_ml_s": q[peak - 1],
                     "Q_at_peak_ml_s": q[peak], "Q_100ms_before_peak_ml_s": q[peak - round(0.1 / dt) - 1]})
    return rows


def main():
    z = pd.read_csv(t2.RESULTS / "exp3b_sessions.csv")
    for k, v in SETTING.items():
        z = z[z[k] == v]
    seed = int(z.groupby("phys_seed").ceiling_exceeded_gt5.sum().idxmax())
    with ProcessPoolExecutor(3) as pool:
        rows = [r for part in pool.map(one, [(dt, seed) for dt in STEPS_S]) for r in part]
    table = pd.DataFrame(rows)
    table.to_csv(t2.RESULTS / "exp3b_overshoot_diagnostic.csv", index=False)
    pd.set_option("display.width", 220, "display.max_columns", 20)
    print(table.round(2).to_string())


if __name__ == "__main__":
    main()
