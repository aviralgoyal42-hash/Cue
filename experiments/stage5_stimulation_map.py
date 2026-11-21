"""
STAGE 5: (1) check A1 - with stimulation off, the closed-loop model reproduces Stage 3 exactly;
         (2) the stimulation map - what the MODEL does when the hypothetical stimulator replaces
             the neural inputs, from a full bladder, over burst strength and timing.

No controller, sensor or user is involved in (2): the stimulator is switched on at a fixed time
and off after a fixed session length, so only the physiology's response is measured.
Criteria: docs/STAGE5_EXPERIMENT3_4_CRITERIA.md (A1 and section B).
Usage: python experiments/stage5_stimulation_map.py
"""
import itertools
import json
import sys
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
from devices import BurstPattern, HypotheticalStimulator  # noqa: E402
import sci_test_rig as rig_mod  # noqa: E402
from evaluation.closed_loop_metrics import emptying_class  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results" / "stage5"
SI = ["t", "V_B", "f_aD_s", "f_aS_s", "r_U", "Q", "p_D", "p_S", "Q_in", "w_e_s", "w_i_s", "w_s_s", "voiding"]
T_START_S, AFTER_S = 120.0, 120.0     # stimulation starts after 2 min; residual measured 2 min after it ends


class FixedSessionRig:
    """Duck-typed rig: switches the stimulator on at T_START_S for `session_s` seconds."""
    def __init__(self, pattern, session_s):
        self.stimulator = HypotheticalStimulator(pattern)
        self.session_s = session_s

    def on_step(self, model):
        if not self.stimulator.active and not self.stimulator.sessions and model.t >= T_START_S - 1e-9:
            self.stimulator.start(model.t)
        if self.stimulator.active and model.t >= T_START_S + self.session_s - 1e-9:
            self.stimulator.stop(model.t)


def check_a1():
    """24 h, seed 42, 1000 mL ceiling: closed loop with a user who never presses vs plain Stage 3 model."""
    case = rig_mod.default_case(duration_s=24 * 3600, user_name="no_press", user=config.USER_SCENARIOS.value["no_press"])
    data, rig = rig_mod.run_closed_loop(case)
    plain = CueLUT(sci_enabled=True, volume_ceiling_ml=case["volume_ceiling_ml"])
    expected = simulate(plain, case["duration_s"], config.value(config.SIMULATION, "dt_s"), 42,
                        config.value(config.SIMULATION, "inflow_noise"))
    exact = data[SI].equals(expected[SI])
    saved = pd.read_csv(Path(__file__).resolve().parents[1] / "results" / "stage3" / "trace_ceiling_1000_1Hz.csv")
    vs_saved = float(np.abs(data["V_B_ml"].iloc[::10].to_numpy() - saved["V_B_ml"].to_numpy()).max())
    return {"A1_bit_identical_to_fresh_stage3_model": bool(exact),
            "A1_max_abs_diff_vs_saved_stage3_trace_ml": vs_saved, "alerts_during_check": len(rig.alert_times),
            "stimulation_ever_on": bool(data["stim_active"].any())}


def run_point(args):
    e, s, (on, off), session, scaling = args
    pattern = BurstPattern(f"e{e}_s{s}_{on}on{off}off", detrusor_drive=e, sphincter_drive=s, on_s=on, off_s=off)
    rig = FixedSessionRig(pattern, session)
    model = rig_mod.ClosedLoopLUT(rig, sci_enabled=True, volume_ceiling_ml=config.value(config.SCI, "volume_ceiling_ml"),
                                  initial_volume_ml=config.STIM_MAP_GRID.value["start_volume_ml"],
                                  overrides={"neural_args.somatic_a": CueLUT().neural_args["somatic_a"] * scaling})
    with np.errstate(invalid="ignore", over="ignore"):
        d = simulate(model, T_START_S + session + AFTER_S, config.value(config.SIMULATION, "dt_s"), 42,
                     config.value(config.SIMULATION, "inflow_noise"))
    t = d["t"].to_numpy()
    during = (t >= T_START_S) & (t < T_START_S + session)
    burst = np.array([rig.stimulator.pattern.off_s <= 0 or (x - T_START_S) % (on + off) < on for x in t]) & during
    flow = d["Q_ml_s"].to_numpy() > 0
    before = float(d["V_B_ml"].to_numpy()[t < T_START_S][-1])
    residual = float(d["V_B_ml"].iloc[-1])
    frac = (before - residual) / before
    off_mask = during & ~burst
    return {"detrusor_drive": e, "sphincter_drive": s, "on_s": on, "off_s": off, "session_s": session,
            "sphincter_scaling": scaling, "volume_before_ml": before, "residual_ml": residual,
            "voided_fraction": frac, "emptying": emptying_class(frac),
            "peak_p_D_during_cmH2O": float(d["p_D_cmH2O"].to_numpy()[during].max()),
            "peak_flow_ml_s": float(d["Q_ml_s"].max()),
            "flow_fraction_burst_on": float(flow[burst].mean()) if burst.any() else np.nan,
            "flow_fraction_burst_off": float(flow[off_mask].mean()) if off_mask.any() else np.nan,
            "urethra_closed_fraction_burst_on": float(1 - flow[burst].mean()) if burst.any() else np.nan,
            "flow_after_session_ml": float(d["Q_ml_s"].to_numpy()[t >= T_START_S + session].sum()
                                           * config.value(config.SIMULATION, "dt_s"))}


def heatmaps(df, path):
    timings = config.STIM_MAP_GRID.value["timing_on_off_s"]
    fig, axs = plt.subplots(2, len(timings), figsize=(3.1 * len(timings), 6), sharey=True)
    for r, scaling in enumerate([1.0, 0.9]):
        for c, (on, off) in enumerate(timings):
            sub = df[(df.session_s == 60.0) & (df.sphincter_scaling == scaling) & (df.on_s == on) & (df.off_s == off)]
            grid = sub.pivot(index="sphincter_drive", columns="detrusor_drive", values="voided_fraction")
            ax = axs[r, c]
            ax.imshow(grid.to_numpy(), cmap="Blues", vmin=0, vmax=1, origin="lower", aspect="auto")
            for i in range(grid.shape[0]):
                for j in range(grid.shape[1]):
                    ax.text(j, i, f"{grid.iat[i, j]:.2f}", ha="center", va="center", fontsize=7,
                            color="white" if grid.iat[i, j] > 0.6 else "black")
            ax.set_xticks(range(grid.shape[1]), grid.columns)
            ax.set_yticks(range(grid.shape[0]), grid.index)
            ax.set_title(("continuous" if off == 0 else f"{on:.0f} s on / {off:.0f} s off") + f", sph x{scaling}",
                         fontsize=8)
            if r == 1:
                ax.set_xlabel("detrusor drive")
            if c == 0:
                ax.set_ylabel("sphincter co-activation")
    fig.suptitle("Stage 5 stimulation map: voided fraction after a 60 s session from 450 mL "
                 "(model prediction; hypothetical stimulator; normalised drive, not clinical settings)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def example_trace(path):
    pattern = BurstPattern.from_dict(config.REFERENCE_STIM.value, config.STIM_PATTERNS.value[config.REFERENCE_STIM.value])
    rig = FixedSessionRig(pattern, 60.0)
    model = rig_mod.ClosedLoopLUT(rig, sci_enabled=True, volume_ceiling_ml=1000.0, initial_volume_ml=450.0)
    d = simulate(model, T_START_S + 60.0 + AFTER_S, 0.1, 42, 1.0)
    fig, axs = plt.subplots(4, 1, sharex=True, figsize=(9, 8))
    t = d["t"]
    axs[0].plot(t, d["V_B_ml"], color="black")
    axs[0].set_ylabel("Volume (mL)")
    axs[1].plot(t, d["p_D_cmH2O"], label="p_D detrusor", color="black")
    axs[1].plot(t, d["p_S_cmH2O"], label="p_S sphincter", color="tab:red", ls="--")
    axs[1].set_ylabel("cmH2O")
    axs[1].legend(fontsize=7)
    axs[2].plot(t, d["Q_ml_s"], color="tab:blue")
    axs[2].set_ylabel("Flow (mL/s)")
    axs[3].plot(t, d["w_e_s"], label="omega_e* (detrusor drive)")
    axs[3].plot(t, d["w_s_s"], label="omega_s* (sphincter drive)")
    axs[3].plot(t, d["f_aD_s"], label="f_aD* activation", ls=":")
    axs[3].plot(t, d["f_aS_s"], label="f_aS* activation", ls=":")
    axs[3].legend(fontsize=7)
    axs[3].set_xlabel("Time (s)")
    for ax in axs:
        ax.axvspan(T_START_S, T_START_S + 60.0, color="orange", alpha=0.1)
    fig.suptitle(f"Reference pattern {config.REFERENCE_STIM.value}, 60 s session from 450 mL (model prediction)", fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    RESULTS.mkdir(parents=True, exist_ok=True)
    g = config.STIM_MAP_GRID.value
    points = list(itertools.product(g["detrusor_drive"], g["sphincter_drive"], [tuple(x) for x in g["timing_on_off_s"]],
                                    g["session_s"], [1.0, 0.9]))
    with ProcessPoolExecutor() as pool:
        a1_future = pool.submit(check_a1)
        rows = list(pool.map(run_point, points))
        a1 = a1_future.result()
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS / "stimulation_map.csv", index=False)
    heatmaps(df, RESULTS / "stimulation_map_voided_fraction.png")
    example_trace(RESULTS / "stimulation_reference_trace.png")
    counts = df.groupby(["sphincter_scaling", "session_s"])["emptying"].value_counts().unstack(fill_value=0)
    counts.to_csv(RESULTS / "stimulation_map_class_counts.csv")
    with open(RESULTS / "stage5_A1_check.json", "w") as f:
        json.dump(a1, f, indent=2)
    print(json.dumps(a1, indent=2))
    print(counts.to_string())


if __name__ == "__main__":
    main()
