"""
TASK 6, Part B: Experiment 8, the misalignment monitor (flag + correction).
Plan and criteria frozen in docs/TASK6_PLAN.md before anything was run. Open loop: replays the
Experiment 2b ground-truth traces (results/stage4b/physiology), so nothing changes the physiology.
The sensor is a synthetic experimental proxy. Results are model predictions, not evidence for a device.

Usage: python -W ignore experiments/task6_experiment8.py
Outputs go to results/task6/ only.
"""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import config  # noqa: E402
from sensors import SensorScenario, SyntheticUltrasoundSensor  # noqa: E402
from devices import CustomTechDevice, MisalignmentMonitor  # noqa: E402
from devices.misalignment_monitor import LEVEL_DROP, DROPOUT_RISE  # noqa: E402
from evaluation import experiment2_metrics as ev  # noqa: E402

PHYS = ROOT / "results" / "stage4b" / "physiology"      # read only
OUT = ROOT / "results" / "task6"

# ---- Fixed before running (docs/TASK6_PLAN.md). ASSUMED. Never tuned after results are seen.
SEEDS = [42] + list(range(1, 15))
SCALINGS = (1.0, 0.9)
SENSOR_REPS = 10
THRESHOLDS = [350.0, 400.0, 450.0]
MONITOR = {"window_n": 15, "k_noise": 3.5, "k_noise_after_dropout": 2.0, "min_drop_fraction": 0.10,
           "min_ml": 100.0, "noise_n": 120, "noise_floor": 0.02, "dropout_slots": 20,
           "dropout_baseline_slots": 120, "dropout_chance": 1e-4, "dropout_floor": 0.02, "compensate": True}
FLAG_WINDOW_H = 0.5                                     # "within 30 min" (the Experiment 6 definition)
DEFAULT = {k: config.value(config.DEVICE, k) for k in config.DEVICE}
V_REF = config.value(config.EXPERIMENT2, "reference_volume_ml")
FALSE_BELOW = config.value(config.EXPERIMENT2, "false_alert_fraction") * V_REF
_A = config.value(config.SENSOR, "best_case_mean_relative_error")
TARGET = "misaligned_at_4h"


def _mis(gain, start_h, extra_missing=0.30):
    return {"mean_relative_error": _A, "misalignment_start_h": start_h, "misalignment_gain": gain,
            "misalignment_missing_probability": extra_missing}


VARIANTS = {   # target variants, built here so config.py stays as it was
    "mis_x0.5_at_4h": _mis(0.5, 4.0), "mis_x0.85_at_4h": _mis(0.85, 4.0),
    "mis_x0.7_at_2h": _mis(0.7, 2.0), "mis_x0.7_at_6h": _mis(0.7, 6.0),
    "mis_x0.7_at_4h_gain_only": _mis(0.7, 4.0, 0.0), "mis_dropout_only_at_4h": _mis(1.0, 4.0),
}


def scenarios():
    """Ordered list of (name, kind, sensor values). The position is the scenario number in the seed."""
    cfg = config.SENSOR_SCENARIOS.value
    out = [(TARGET, "target", cfg[TARGET])]
    out += [(name, "variant", values) for name, values in VARIANTS.items()]
    out += [(name, "none", values) for name, values in cfg.items() if name != TARGET]
    return out


def monitor_only(readings, **change):
    """First flag time (s) of a monitor with one rule switched off; None if it never flags."""
    monitor = MisalignmentMonitor(**{**MONITOR, **change})
    for r in readings:
        if monitor.receive(r):
            return r.t_s
    return None


def job(args):
    scaling, phys_seed = args
    truth = pd.read_csv(PHYS / f"somatic_x{scaling}_seed{phys_seed}.csv")
    true_at = ev.truth_lookup(truth)
    t_adv, _ = ev.adverse_event(truth, V_REF)
    dt = config.value(config.SENSOR, "sample_interval_s")
    times = np.arange(dt, truth["t"].iloc[-1], dt)
    flag_rows, alert_rows = [], []
    for si, (name, kind, values) in enumerate(scenarios()):
        for rep in range(SENSOR_REPS):
            seed = int(np.random.SeedSequence([1000, si, int(round(scaling * 100)), phys_seed, rep])
                       .generate_state(1)[0])
            sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict(name, values), seed)
            readings = [sensor.read(float(t), true_at) for t in times]
            key = {"scenario": name, "kind": kind, "sphincter_scaling": scaling, "physiology_seed": phys_seed,
                   "rep": rep}
            for variant, monitor in [("monitor_off", None), ("flag_only", {**MONITOR, "compensate": False}),
                                     ("flag_and_correct", MONITOR)]:
                for thr in THRESHOLDS:
                    dev = CustomTechDevice(thr, **DEFAULT, misalignment_monitor=monitor)
                    for r in readings:
                        dev.receive(r)
                    cls = ev.classify_alerts(ev.alert_events(dev.events), true_at, t_adv, FALSE_BELOW)
                    alert_rows.append({**key, "variant": variant, "threshold_ml": thr, **cls})
                    if variant == "flag_and_correct" and thr == THRESHOLDS[0]:   # flags do not depend on threshold
                        by_rule = {c["rule"]: c for c in dev.patch_checks}
                        first = dev.patch_checks[0] if dev.patch_checks else None
                        level = by_rule.get(LEVEL_DROP)
                        flag_rows.append({
                            **key, "flagged": first is not None,
                            "first_flag_h": first["t_s"] / 3600 if first else np.nan,
                            "first_rule": first["rule"] if first else "",
                            "level_drop_h": level["t_s"] / 3600 if level else np.nan,
                            "dropout_rise_h": by_rule[DROPOUT_RISE]["t_s"] / 3600 if DROPOUT_RISE in by_rule else np.nan,
                            "ratio_at_flag": level["ratio"] if level else np.nan,
                            "measured_ratio": dev.correction_ratio if level else np.nan,   # after settling
                            "rule1_alone_h": _hours(monitor_only(readings, dropout_chance=0.0)),
                            "rule2_alone_h": _hours(monitor_only(readings, k_noise=np.inf,
                                                                 k_noise_after_dropout=np.inf))})
    return flag_rows, alert_rows


def _hours(t_s):
    return np.nan if t_s is None else t_s / 3600


def on_time(first_h, start_h):
    """No flag before the start, and the first flag within 30 min after it."""
    return (first_h >= start_h) & (first_h <= start_h + FLAG_WINDOW_H)


def summarise_flags(flags):
    start = {name: values.get("misalignment_start_h") for name, _, values in scenarios()}
    gain = {name: values.get("misalignment_gain", 1.0) for name, _, values in scenarios()}

    rows = []
    for (name, scaling), g in flags.groupby(["scenario", "sphincter_scaling"], sort=False):
        s = start[name]
        out = {"scenario": name, "sphincter_scaling": scaling,
               "kind": g["kind"].iloc[0], "n_runs": len(g), "flag_rate": g["flagged"].mean(),
               "level_drop_rate": g["level_drop_h"].notna().mean(), "dropout_rise_rate": g["dropout_rise_h"].notna().mean(),
               "rule1_alone_flag_rate": g["rule1_alone_h"].notna().mean(),
               "rule2_alone_flag_rate": g["rule2_alone_h"].notna().mean()}
        if s is not None:
            hit = on_time(g["first_flag_h"], s)
            out.update({"start_h": s, "true_ratio": gain[name],
                        "on_time_rate": hit.mean(),
                        "flag_before_start_rate": (g["first_flag_h"] < s).mean(),
                        "rule1_alone_on_time_rate": on_time(g["rule1_alone_h"], s).mean(),
                        "rule2_alone_on_time_rate": on_time(g["rule2_alone_h"], s).mean(),
                        "median_min_to_flag": ((g["first_flag_h"][hit] - s) * 60).median(),
                        "corrected_within_30min_rate": on_time(g["level_drop_h"], s).mean(),
                        "corrected_ever_after_start_rate": (g["level_drop_h"] >= s).mean(),
                        "first_rule_level_drop_share": (g["first_rule"][hit] == LEVEL_DROP).mean(),
                        "measured_ratio_median": g["measured_ratio"][g["level_drop_h"] >= s].median(),
                        "measured_ratio_p05": g["measured_ratio"][g["level_drop_h"] >= s].quantile(0.05),
                        "measured_ratio_p95": g["measured_ratio"][g["level_drop_h"] >= s].quantile(0.95)})
        rows.append(out)
    return pd.DataFrame(rows)       # scenarios without misalignment leave the timing columns empty


def summarise_alerts(alerts):
    def agg(g):
        lead = g["lead_time_min"].dropna()
        v = g["true_volume_at_genuine_alert_ml"].dropna()
        out = {"kind": g["kind"].iloc[0], "n_runs": len(g), "useful_rate": g["useful"].mean(),
               "false_alert_run_rate": g["any_false_alert"].mean(), "late_rate": g["late"].mean(),
               "missed_rate": g["missed"].mean(), "median_lead_min": lead.median() if len(lead) else np.nan,
               "true_volume_at_alert_median_ml": v.median() if len(v) else np.nan,
               "true_volume_at_alert_p95_ml": v.quantile(0.95) if len(v) else np.nan,
               "mean_alerts_per_run": g["n_alerts"].mean()}
        out["C1_pass"] = bool(out["useful_rate"] >= 0.95)
        out["C2_pass"] = bool(out["false_alert_run_rate"] <= 0.05)
        out["C3_pass"] = bool(out["median_lead_min"] >= 30)
        out["cue_works_C1_C2_C3"] = out["C1_pass"] and out["C2_pass"] and out["C3_pass"]
        return pd.Series(out)
    keys = ["scenario", "sphincter_scaling", "threshold_ml", "variant"]
    return alerts.groupby(keys, sort=False).apply(agg).reset_index()


def criteria(flag_summary, alert_summary):
    f, a = flag_summary, alert_summary
    target = f[f.scenario == TARGET]
    none = f[f.kind == "none"]
    wide = a.pivot_table(index=["scenario", "kind", "sphincter_scaling", "threshold_ml"], columns="variant",
                         values="cue_works_C1_C2_C3", aggfunc="first").reset_index()
    harmed = wide[(wide.kind == "none") & wide["monitor_off"].astype(bool) & ~wide["flag_and_correct"].astype(bool)]
    m3 = wide[wide.scenario == TARGET]
    out = {
        "M1_on_time_rate_by_scaling": {str(r.sphincter_scaling): float(r.on_time_rate) for r in target.itertuples()},
        "M1_pass": bool((target["on_time_rate"] >= 0.90).all()),
        "M2_cells": int(len(none)), "M2_highest_flag_rate": float(none["flag_rate"].max()),
        "M2_cells_over_5pct": [f"{r.scenario} x{r.sphincter_scaling}: {r.flag_rate:.3f}"
                               for r in none[none.flag_rate > 0.05].itertuples()],
        "M2_pass": bool((none["flag_rate"] <= 0.05).all()),
        "M4_cells_checked": int((wide.kind == "none").sum()),
        "M4_cells_pass_to_fail": [f"{r.scenario} x{r.sphincter_scaling} {r.threshold_ml:.0f} mL"
                                  for r in harmed.itertuples()],
        "M4_pass": bool(len(harmed) == 0),
        "M3_target_cells_working": {v: int(m3[v].astype(bool).sum())
                                    for v in ("monitor_off", "flag_only", "flag_and_correct")},
        "M3_cells_rescued": [f"x{r.sphincter_scaling} {r.threshold_ml:.0f} mL" for r in m3.itertuples()
                             if bool(r.flag_and_correct)],
        "M3_cells_still_failing": [f"x{r.sphincter_scaling} {r.threshold_ml:.0f} mL" for r in m3.itertuples()
                                   if not bool(r.flag_and_correct)],
    }
    out["flag_works_M1_and_M2"] = out["M1_pass"] and out["M2_pass"]
    return out


def main():
    config.validate()
    OUT.mkdir(parents=True, exist_ok=True)
    if "--rescore" not in sys.argv:              # --rescore: score the saved run files again, run nothing
        jobs = [(s, seed) for s in SCALINGS for seed in SEEDS]
        flags, alerts = [], []
        with ProcessPoolExecutor() as pool:
            for i, (a, b) in enumerate(pool.map(job, jobs), 1):
                flags += a
                alerts += b
                print(f"  trace {i}/{len(jobs)} done", flush=True)
        pd.DataFrame(flags).to_csv(OUT / "exp8_flag_runs.csv", index=False)
        pd.DataFrame(alerts).to_csv(OUT / "exp8_alert_runs.csv", index=False)
    flags = pd.read_csv(OUT / "exp8_flag_runs.csv")         # always scored from the files
    alerts = pd.read_csv(OUT / "exp8_alert_runs.csv")
    pd.DataFrame([{"scenario": n, "kind": k, **v} for n, k, v in scenarios()]).to_csv(OUT / "exp8_scenarios_used.csv",
                                                                                     index=False)
    pd.DataFrame([MONITOR]).to_csv(OUT / "exp8_monitor_settings_used.csv", index=False)
    fs, als = summarise_flags(flags), summarise_alerts(alerts)
    fs.to_csv(OUT / "exp8_flag_summary.csv", index=False)
    als.to_csv(OUT / "exp8_alert_summary.csv", index=False)
    result = criteria(fs, als)
    (OUT / "exp8_criteria.json").write_text(json.dumps(result, indent=2))
    print(fs.round(3).to_string(index=False))
    print(als[als.kind != "none"].round(3).to_string(index=False))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
