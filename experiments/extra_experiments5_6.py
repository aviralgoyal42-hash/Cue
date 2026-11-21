"""
EXTRA: Experiment 5 (device parameter variation) and Experiment 6 (misalignment detector).
Criteria frozen in docs/EXPERIMENT5_6_CRITERIA.md. Open loop: replays the Experiment 2b
ground-truth traces (results/stage4b/physiology), so nothing here changes the physiology.
Usage: python experiments/extra_experiments5_6.py
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from sensors import SensorScenario, SyntheticUltrasoundSensor  # noqa: E402
from devices import CustomTechDevice  # noqa: E402
from devices.custom_tech_device import POSSIBLE_MISALIGNMENT  # noqa: E402
from evaluation import experiment2_metrics as ev  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PHYS = ROOT / "results" / "stage4b" / "physiology"
OUT = ROOT / "results" / "extra"
SEEDS = [42] + list(range(1, 15))
SENSOR_REPS = 10
DEFAULT = {k: config.value(config.DEVICE, k) for k in config.DEVICE}
VARIANTS = [("default", {})] + [(f"median_window={v}", {"median_window": v}) for v in (1, 3, 9)] + \
           [(f"confirm_n={v}", {"confirm_n": v}) for v in (1, 5)] + \
           [(f"rearm_hysteresis_ml={v}", {"rearm_hysteresis_ml": v}) for v in (25.0, 100.0)] + \
           [(f"stale_timeout_s={v}", {"stale_timeout_s": v}) for v in (300.0, 1200.0)]
E5_SCENARIOS = ["anchor_11pct", "mre_30pct", "missing_50pct", "misaligned_at_4h"]
E6_SCENARIOS = ["misaligned_at_4h", "ideal", "anchor_11pct", "mre_20pct", "mre_30pct", "drift_minus2ph",
                "gain_minus20", "missing_50pct"]
THRESHOLDS = [350.0, 400.0, 450.0]
V_REF = config.value(config.EXPERIMENT2, "reference_volume_ml")
FALSE_BELOW = config.value(config.EXPERIMENT2, "false_alert_fraction") * V_REF


def readings_for(truth, scen_name, seed):
    sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict(scen_name, config.SENSOR_SCENARIOS.value[scen_name]), seed)
    dt = config.value(config.SENSOR, "sample_interval_s")
    true_at = ev.truth_lookup(truth)
    return [sensor.read(float(t), true_at) for t in np.arange(dt, truth["t"].iloc[-1], dt)], true_at


def job(args):
    scaling, phys_seed = args
    truth = pd.read_csv(PHYS / f"somatic_x{scaling}_seed{phys_seed}.csv")
    t_adv, _ = ev.adverse_event(truth, V_REF)
    e5, e6 = [], []
    for si, scen in enumerate(sorted(set(E5_SCENARIOS + E6_SCENARIOS))):
        for rep in range(SENSOR_REPS):
            seed = int(np.random.SeedSequence([900 + si, int(scaling * 100), phys_seed, rep]).generate_state(1)[0])
            readings, true_at = readings_for(truth, scen, seed)
            if scen in E5_SCENARIOS:
                for vname, change in VARIANTS:
                    for thr in THRESHOLDS:
                        dev = CustomTechDevice(thr, **{**DEFAULT, **change})
                        for r in readings:
                            dev.receive(r)
                        cls = ev.classify_alerts(ev.alert_events(dev.events), true_at, t_adv, FALSE_BELOW)
                        gaps, flagged = ev.stale_detection(readings, dev.events, dev.stale_timeout_s)
                        e5.append({"variant": vname, "scenario": scen, "threshold_ml": thr, "sphincter_scaling": scaling,
                                   "physiology_seed": phys_seed, "rep": rep, **cls, "stale_gaps": gaps,
                                   "stale_flagged": flagged})
            if scen in E6_SCENARIOS:
                for d in (0.15, 0.25, 0.35):
                    dev = CustomTechDevice(400.0, **DEFAULT, misalignment_drop_fraction=d)
                    for r in readings:
                        dev.receive(r)
                    flags = [e.t_s for e in dev.events if e.kind == POSSIBLE_MISALIGNMENT]
                    e6.append({"drop_fraction": d, "scenario": scen, "sphincter_scaling": scaling,
                               "physiology_seed": phys_seed, "rep": rep, "flagged": bool(flags),
                               "flag_time_h": flags[0] / 3600 if flags else np.nan})
    return e5, e6


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [(s, seed) for s in (1.0, 0.9) for seed in SEEDS]
    e5, e6 = [], []
    with ProcessPoolExecutor() as pool:
        for a, b in pool.map(job, jobs):
            e5 += a
            e6 += b
    r5, r6 = pd.DataFrame(e5), pd.DataFrame(e6)
    r5.to_csv(OUT / "exp5_device_params_runs.csv", index=False)
    r6.to_csv(OUT / "exp6_misalignment_runs.csv", index=False)

    def agg5(g):
        lead = g["lead_time_min"].dropna()
        v = g["true_volume_at_genuine_alert_ml"]
        out = {"useful_rate": g["useful"].mean(), "false_alert_run_rate": g["any_false_alert"].mean(),
               "median_lead_min": lead.median() if len(lead) else np.nan, "mean_alerts_per_run": g["n_alerts"].mean(),
               "POSTHOC_band_350_450_rate": (g["useful"] & (v >= 350) & (v <= 450)).mean(),
               "stale_gaps": g["stale_gaps"].sum(), "stale_flagged": g["stale_flagged"].sum()}
        out["cue_works_C1_C2_C3"] = bool(out["useful_rate"] >= 0.95 and out["false_alert_run_rate"] <= 0.05
                                         and out["median_lead_min"] >= 30)
        return pd.Series(out)
    s5 = r5.groupby(["variant", "sphincter_scaling", "scenario", "threshold_ml"]).apply(agg5).reset_index()
    s5.to_csv(OUT / "exp5_device_params_summary.csv", index=False)

    def agg6(g):
        mis = g["scenario"].iloc[0] == "misaligned_at_4h"
        on_time = g["flagged"] & (g["flag_time_h"] >= 4.0) & (g["flag_time_h"] <= 4.5)
        return pd.Series({"flag_rate": g["flagged"].mean(),
                          "flag_within_30min_after_4h_rate": on_time.mean() if mis else np.nan,
                          "median_flag_time_h": g["flag_time_h"].median()})
    s6 = r6.groupby(["drop_fraction", "sphincter_scaling", "scenario"]).apply(agg6).reset_index()
    s6["M1_pass"] = np.where(s6["scenario"] == "misaligned_at_4h", s6["flag_within_30min_after_4h_rate"] >= 0.90, np.nan)
    s6["M2_pass"] = np.where(s6["scenario"] != "misaligned_at_4h", s6["flag_rate"] <= 0.05, np.nan)
    s6.to_csv(OUT / "exp6_misalignment_summary.csv", index=False)
    print(s5.pivot_table(index=["variant"], columns=["sphincter_scaling"], values="cue_works_C1_C2_C3", aggfunc="sum").to_string())
    print(s6.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
