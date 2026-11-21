"""
TASK 7: Experiment 9, a misalignment correction that allows for bladder filling.
Plan and criteria frozen in docs/TASK7_PLAN.md before any code was written. POST-HOC: the design
answers a weakness seen in Experiment 8 and is tested on the same physiology traces (new sensor seeds).
The sensor is a synthetic experimental proxy. Results are model predictions, not evidence for a device.

Usage (PowerShell, from the project folder):
  python -W ignore experiments\\task7_experiment9.py --check     reproduce Experiment 8 with the option off
  python -W ignore experiments\\task7_experiment9.py --run       Experiment 9 (refuses unless --check passed)
  python -W ignore experiments\\task7_experiment9.py --rescore   score the saved run files again, run nothing
  python -W ignore experiments\\task7_experiment9.py --probe     12 closed-loop runs (descriptive)
Outputs go to results/task7/ only.
"""
import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config  # noqa: E402
from sensors import SensorScenario, SyntheticUltrasoundSensor  # noqa: E402
from devices import CustomTechDevice  # noqa: E402
from devices.misalignment_monitor import LEVEL_DROP, DROPOUT_RISE  # noqa: E402
from evaluation import experiment2_metrics as ev  # noqa: E402
import task5_sphincter_levels as t5  # noqa: E402  (same_values, save)
import task6_block_check as t6  # noqa: E402       (closed-loop run_one, used unchanged)
import task6_experiment8 as e8  # noqa: E402       (scenarios, scoring, used unchanged)

OUT = ROOT / "results" / "task7"
TASK6 = ROOT / "results" / "task6"                      # read only

# ---- Fixed before running (docs/TASK7_PLAN.md). ASSUMED. Never tuned after results are seen.
SEED_PREFIX = 2000                                      # Experiment 8 used 1000
OLD = dict(e8.MONITOR)                                  # the Task 6 correction, unchanged
NEW = {**e8.MONITOR, "fill_adjust": True, "fill_history_n": 90, "fill_min_n": 30, "ratio_floor": 0.40}
VARIANTS = [("monitor_off", None), ("old_correction", OLD), ("new_correction", NEW)]
E8_VARIANTS = [("monitor_off", None), ("flag_only", {**OLD, "compensate": False}), ("flag_and_correct", OLD)]
TARGET, R1_BAND = e8.TARGET, (0.65, 0.75)
HELD_OUT = {"mis_x0.5_at_4h": (0.45, 0.55), "mis_x0.85_at_4h": (0.80, 0.90)}   # plan section 7
OVER_CORRECTED_BY = 0.05
PROBE_SEEDS = [42, 1, 2]
EXACT = t5.EXACT


def rows_for(readings, true_at, t_adv, key, variants, flag_variants):
    """Run every device variant on the same readings. Returns (flag rows, alert rows)."""
    flag_rows, alert_rows = [], []
    alone1 = e8._hours(e8.monitor_only(readings, dropout_chance=0.0))
    alone2 = e8._hours(e8.monitor_only(readings, k_noise=np.inf, k_noise_after_dropout=np.inf))
    for variant, monitor in variants:
        for thr in e8.THRESHOLDS:
            dev = CustomTechDevice(thr, **e8.DEFAULT, misalignment_monitor=monitor)
            for r in readings:
                dev.receive(r)
            cls = ev.classify_alerts(ev.alert_events(dev.events), true_at, t_adv, e8.FALSE_BELOW)
            alert_rows.append({**key, "variant": variant, "threshold_ml": thr, **cls})
            if variant in flag_variants and thr == e8.THRESHOLDS[0]:      # flags do not depend on threshold
                by_rule = {c["rule"]: c for c in dev.patch_checks}
                first = dev.patch_checks[0] if dev.patch_checks else None
                level = by_rule.get(LEVEL_DROP)
                flag_rows.append({
                    **key, "variant": variant, "flagged": first is not None,
                    "first_flag_h": first["t_s"] / 3600 if first else np.nan,
                    "first_rule": first["rule"] if first else "",
                    "level_drop_h": level["t_s"] / 3600 if level else np.nan,
                    "dropout_rise_h": by_rule[DROPOUT_RISE]["t_s"] / 3600 if DROPOUT_RISE in by_rule else np.nan,
                    "ratio_at_flag": level["ratio"] if level else np.nan,
                    "measured_ratio": dev.correction_ratio if level else np.nan,   # after settling
                    "rule1_alone_h": alone1, "rule2_alone_h": alone2,
                    "line_kind": dev.monitor.line_kind})
    return flag_rows, alert_rows


def job(args):
    """One physiology trace. mode 'e9' = all scenarios, new seeds; 'check' = the Experiment 8 target."""
    scaling, phys_seed, mode = args
    truth = pd.read_csv(e8.PHYS / f"somatic_x{scaling}_seed{phys_seed}.csv")
    true_at = ev.truth_lookup(truth)
    t_adv, _ = ev.adverse_event(truth, e8.V_REF)
    dt = config.value(config.SENSOR, "sample_interval_s")
    times = np.arange(dt, truth["t"].iloc[-1], dt)
    prefix = SEED_PREFIX if mode == "e9" else 1000
    flags, alerts = [], []
    for si, (name, kind, values) in enumerate(e8.scenarios()):
        if mode == "check" and name != TARGET:
            continue
        for rep in range(e8.SENSOR_REPS):
            seed = int(np.random.SeedSequence([prefix, si, int(round(scaling * 100)), phys_seed, rep])
                       .generate_state(1)[0])
            sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict(name, values), seed)
            readings = [sensor.read(float(t), true_at) for t in times]
            key = {"scenario": name, "kind": kind, "sphincter_scaling": scaling, "physiology_seed": phys_seed,
                   "rep": rep}
            if mode == "e9":
                f, a = rows_for(readings, true_at, t_adv, key, VARIANTS, ("old_correction", "new_correction"))
            else:
                f, a = rows_for(readings, true_at, t_adv, key, E8_VARIANTS, ("flag_and_correct",))
            flags += f
            alerts += a
    return flags, alerts


def run_jobs(mode):
    jobs = [(s, seed, mode) for s in e8.SCALINGS for seed in e8.SEEDS]
    flags, alerts = [], []
    with ProcessPoolExecutor() as pool:
        for i, (a, b) in enumerate(pool.map(job, jobs), 1):
            flags += a
            alerts += b
            print(f"  trace {i}/{len(jobs)} done  {time.strftime('%H:%M:%S')}", flush=True)
    return pd.DataFrame(flags), pd.DataFrame(alerts)


# ------------------------------------------------------------------ reproduction check
def check():
    """With fill_adjust off and the Experiment 8 seeds, the Experiment 8 target rows must come back exactly."""
    flags, alerts = run_jobs("check")
    flags.drop(columns=["variant", "line_kind"]).to_csv(OUT / "check_flag_runs.csv", index=False)
    alerts.to_csv(OUT / "check_alert_runs.csv", index=False)
    out = {}
    for label, mine, old, keys in [
            ("flags", "check_flag_runs.csv", "exp8_flag_runs.csv", ["sphincter_scaling", "physiology_seed", "rep"]),
            ("alerts", "check_alert_runs.csv", "exp8_alert_runs.csv",
             ["sphincter_scaling", "physiology_seed", "rep", "variant", "threshold_ml"])]:
        a = pd.read_csv(OUT / mine, **EXACT)                           # file to file, by value (E58)
        b = pd.read_csv(TASK6 / old, **EXACT)
        b = b[b.scenario == TARGET]
        a, b = a.sort_values(keys).reset_index(drop=True), b.sort_values(keys).reset_index(drop=True)
        same_shape = len(a) == len(b) and list(a.columns) == list(b.columns)
        diff = t5.same_values(a, b) if same_shape else {"rows or columns differ": 1}
        out[label] = {"rows_task7": len(a), "rows_task6": len(b), "columns_compared": len(b.columns),
                      "differences": diff, "identical": bool(same_shape and not diff)}
    out["passed"] = bool(out["flags"]["identical"] and out["alerts"]["identical"] and out["flags"]["rows_task7"] == 300)
    (OUT / "check.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("REPRODUCTION CHECK PASSED" if out["passed"] else "REPRODUCTION CHECK FAILED: do not run Experiment 9")


# ------------------------------------------------------------------ scoring
def ratio_table(flags):
    """Measured ratio against the true one, per scenario, strength and correction (corrected runs only)."""
    start = {n: v.get("misalignment_start_h") for n, _, v in e8.scenarios()}
    gain = {n: v.get("misalignment_gain", 1.0) for n, _, v in e8.scenarios()}
    rows = []
    for (name, scaling, variant), g in flags[flags.kind != "none"].groupby(
            ["scenario", "sphincter_scaling", "variant"], sort=False):
        c = g[g["level_drop_h"] >= start[name]]                        # a correction applied after the fall
        r = c["measured_ratio"]
        rows.append({"scenario": name, "sphincter_scaling": scaling, "variant": variant, "true_ratio": gain[name],
                     "n_runs": len(g), "corrected_runs": len(c), "corrected_rate": len(c) / len(g),
                     "ratio_median": r.median(), "ratio_p05": r.quantile(0.05), "ratio_p95": r.quantile(0.95),
                     "over_corrected_rate": float((r < gain[name] - OVER_CORRECTED_BY).mean()) if len(c) else np.nan,
                     "under_corrected_rate": float((r > gain[name] + OVER_CORRECTED_BY).mean()) if len(c) else np.nan,
                     "line_rate": float((c["line_kind"] == "line").mean()) if len(c) else np.nan,
                     "flat_few_readings": int((c["line_kind"] == "flat_few_readings").sum()),
                     "flat_negative_slope": int((c["line_kind"] == "flat_negative_slope").sum())})
    return pd.DataFrame(rows)


def criteria(flags, flag_summary, ratios, alert_summary):
    old, new = flags[flags.variant == "old_correction"], flags[flags.variant == "new_correction"]
    keys = ["scenario", "sphincter_scaling", "physiology_seed", "rep"]
    # F1 is "the same flags at the same times" (plan section 4). `ratio_at_flag` is NOT a flag: the device
    # records the correction it starts using there, which is meant to differ between old and new (E111).
    same = ["flagged", "first_flag_h", "first_rule", "level_drop_h", "dropout_rise_h"]
    a, b = old.sort_values(keys).reset_index(drop=True), new.sort_values(keys).reset_index(drop=True)
    f1_diff = t5.same_values(a[keys + same], b[keys + same])
    fs = flag_summary
    target, none = fs[fs.scenario == TARGET], fs[fs.kind == "none"]
    wide = alert_summary.pivot_table(index=["scenario", "kind", "sphincter_scaling", "threshold_ml"],
                                     columns="variant", values="cue_works_C1_C2_C3", aggfunc="first").reset_index()
    for v in ("monitor_off", "old_correction", "new_correction"):
        wide[v] = wide[v].astype(bool)
    harmed = wide[(wide.kind == "none") & wide["monitor_off"] & ~wide["new_correction"]]
    m3 = wide[wide.scenario == TARGET]
    cell = lambda r: f"x{r.sphincter_scaling} {r.threshold_ml:.0f} mL"   # noqa: E731
    med = lambda name, variant: {str(r.sphincter_scaling): float(r.ratio_median) for r in ratios[   # noqa: E731
        (ratios.scenario == name) & (ratios.variant == variant)].itertuples()}
    inside = lambda values, band: bool(values and all(band[0] <= v <= band[1] for v in values.values()))  # noqa: E731
    out = {
        "F1_runs_compared": int(len(a)), "F1_differences": f1_diff, "F1_pass": bool(len(a) == len(b) and not f1_diff),
        "M1_on_time_rate_by_scaling": {str(r.sphincter_scaling): float(r.on_time_rate) for r in target.itertuples()},
        "M1_pass": bool((target["on_time_rate"] >= 0.90).all()),
        "M2_cells": int(len(none)), "M2_highest_flag_rate": float(none["flag_rate"].max()),
        "M2_pass": bool((none["flag_rate"] <= 0.05).all()),
        "R1_ratio_median_new": med(TARGET, "new_correction"), "R1_ratio_median_old": med(TARGET, "old_correction"),
        "R1_band": list(R1_BAND),
        "M4_cells_checked": int((wide.kind == "none").sum()),
        "M4_cells_pass_to_fail": [f"{r.scenario} {cell(r)}" for r in harmed.itertuples()],
        "M3_target_cells_working": {v: int(m3[v].sum()) for v in ("monitor_off", "old_correction", "new_correction")},
        "M3_cells_rescued_new": [cell(r) for r in m3.itertuples() if r.new_correction],
        "M3_cells_still_failing_new": [cell(r) for r in m3.itertuples() if not r.new_correction],
        "M3_cells_old_rescued_but_new_lost": [cell(r) for r in m3.itertuples() if r.old_correction and not r.new_correction],
    }
    out["R1_pass"] = inside(out["R1_ratio_median_new"], R1_BAND)
    out["M4_pass"] = len(out["M4_cells_pass_to_fail"]) == 0
    more = out["M3_target_cells_working"]["new_correction"] > out["M3_target_cells_working"]["old_correction"]
    out["improvement"] = bool(out["F1_pass"] and out["M1_pass"] and out["M2_pass"] and out["R1_pass"] and out["M4_pass"]
                              and more and not out["M3_cells_old_rescued_but_new_lost"])
    held = {}
    for name, band in HELD_OUT.items():                                 # plan section 7: judged on their own
        w = wide[wide.scenario == name]
        r = ratios[(ratios.scenario == name)]
        held[name] = {"band": list(band), "ratio_median_new": med(name, "new_correction"),
                      "ratio_median_old": med(name, "old_correction"),
                      "pass": inside(med(name, "new_correction"), band),
                      "corrected_rate_new": {str(x.sphincter_scaling): float(x.corrected_rate)
                                             for x in r[r.variant == "new_correction"].itertuples()},
                      "over_corrected_rate_new": {str(x.sphincter_scaling): float(x.over_corrected_rate)
                                                  for x in r[r.variant == "new_correction"].itertuples()},
                      "cells_working": {v: int(w[v].sum()) for v in ("monitor_off", "old_correction", "new_correction")}}
    out["HELD_OUT"] = held
    out["H1_pass"], out["H2_pass"] = held["mis_x0.5_at_4h"]["pass"], held["mis_x0.85_at_4h"]["pass"]
    return out


def score():
    flags = pd.read_csv(OUT / "exp9_flag_runs.csv")                     # always scored from the files
    alerts = pd.read_csv(OUT / "exp9_alert_runs.csv")
    fs = e8.summarise_flags(flags[flags.variant == "new_correction"])
    als = e8.summarise_alerts(alerts)
    ratios = ratio_table(flags)
    fs.to_csv(OUT / "exp9_flag_summary.csv", index=False)
    als.to_csv(OUT / "exp9_alert_summary.csv", index=False)
    ratios.to_csv(OUT / "exp9_ratio_summary.csv", index=False)
    result = criteria(flags, fs, ratios, als)
    (OUT / "exp9_criteria.json").write_text(json.dumps(result, indent=2))
    print(ratios.round(3).to_string(index=False))
    print(json.dumps(result, indent=2))


# ------------------------------------------------------------------ closed-loop probe (descriptive)
def probe_cases():
    out, sensors = [], config.SENSOR_SCENARIOS.value
    stim = config.STIM_PATTERNS.value[t6.PROBE_PATTERN]
    for scaling in t5.SCALINGS:
        for label, sensor in [("anchor_new_correction", "anchor_11pct"), ("misaligned_new_correction", TARGET)]:
            for seed in PROBE_SEEDS:
                out.append({"group": "T7-probe", "stim_name": t6.PROBE_PATTERN, "stim": stim, "task5_twin": "",
                            "controller": {"pressure_ceiling_cmH2O": t5.CEILING_CMH2O},
                            "ultrasound_interval_during_stim_s": t5.US_INTERVAL_S, "sphincter_scaling": scaling,
                            "phys_seed": seed, "sensor_seed": seed, "user_seed": seed, "pressure_seed": seed,
                            "probe": label, "sensor_name": sensor, "sensor": sensors[sensor],
                            "device": {"misalignment_monitor": NEW}})
    return out


def probe():
    todo = probe_cases()
    print(f"task7 closed-loop probe: {len(todo)} runs ...", flush=True)
    rows, sessions, checks = [], [], []
    with ProcessPoolExecutor() as pool:
        for i, (row, sess, chk) in enumerate(pool.map(t6.run_one, todo, chunksize=1), 1):
            rows.append(row)
            sessions += sess
            checks += chk
            print(f"  {i}/{len(todo)} done  {time.strftime('%H:%M:%S')}", flush=True)
    t5.save(rows, OUT / "probe_runs.csv")
    t5.save(sessions, OUT / "probe_sessions.csv")
    t5.save(checks if checks else [{"group": "", "note": "no patch checks"}], OUT / "probe_patch_checks.csv")
    runs = pd.read_csv(OUT / "probe_runs.csv")
    inv = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
    result = {"runs": len(runs), "errors": int(runs["error"].fillna("").astype(str).ne("").sum()),
              "invariants_hold_in_all_runs": bool(runs[inv].all().all())}
    (OUT / "probe_check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--check", "--run", "--rescore", "--probe"):
        group.add_argument(flag, action="store_true")
    args = parser.parse_args()
    config.validate()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.check:
        check()
    elif args.probe:
        probe()
    else:
        if args.run:
            passed = (OUT / "check.json").exists() and json.loads((OUT / "check.json").read_text())["passed"]
            if not passed:
                sys.exit("Refusing to start: the reproduction check has not passed (results/task7/check.json).")
            flags, alerts = run_jobs("e9")
            flags.to_csv(OUT / "exp9_flag_runs.csv", index=False)
            alerts.to_csv(OUT / "exp9_alert_runs.csv", index=False)
            pd.DataFrame([{"correction": "old", **OLD}, {"correction": "new", **NEW}]) \
                .to_csv(OUT / "exp9_monitor_settings_used.csv", index=False)
            pd.DataFrame([{"scenario": n, "kind": k, **v} for n, k, v in e8.scenarios()]) \
                .to_csv(OUT / "exp9_scenarios_used.csv", index=False)
        score()


if __name__ == "__main__":
    main()
