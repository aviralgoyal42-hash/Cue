"""
TASK 8: Experiment 10, a second independent bladder-volume signal ("sensor B") and three fusion rules.
Plan and criteria frozen in docs/TASK8_PLAN.md before any code was written. Sensor B is ABSTRACT: it is
not a model of any technology or product. Results are model predictions, not evidence for a device.

Usage (PowerShell, from the project folder), in this order:
  python -W ignore experiments\\task8_experiment10.py --check        reproduction with sensor B off
  python -W ignore experiments\\task8_experiment10.py --timing       timing test on a made-up trace
  python -W ignore experiments\\task8_experiment10.py --physiology   20 fresh held-out physiology traces
  python -W ignore experiments\\task8_experiment10.py --sweep main      (resumes; refuses unless --check passed)
  python -W ignore experiments\\task8_experiment10.py --sweep heldout
  python -W ignore experiments\\task8_experiment10.py --score        refuses unless every job file is present
  python -W ignore experiments\\task8_experiment10.py --probe        24 closed-loop runs (descriptive)
Outputs go to results/task8/ only.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config  # noqa: E402
from sensors import Reading, SensorScenario, SyntheticUltrasoundSensor, sensor_b_values  # noqa: E402
from devices import CustomTechDevice, SensorFusion  # noqa: E402
from devices.sensor_fusion import fused_value  # noqa: E402
from evaluation import experiment2_metrics as ev  # noqa: E402
import stage4_experiment2 as s4  # noqa: E402       (physiology simulation, used unchanged)
import task5_sphincter_levels as t5  # noqa: E402    (same_values, save)
import task6_block_check as t6  # noqa: E402         (closed-loop run_one, used unchanged)
import task6_experiment8 as e8  # noqa: E402         (device defaults, thresholds, traces)

OUT = ROOT / "results" / "task8"
RUNS = OUT / "runs"
HELD_PHYS = OUT / "heldout" / "physiology"
TASK5, TASK7 = ROOT / "results" / "task5", ROOT / "results" / "task7"      # read only

# ---- Fixed before running (docs/TASK8_PLAN.md). ASSUMED. Never tuned after results are seen.
B_ERRORS = (0.05, 0.1117, 0.20, 0.30, 0.40)
INDEPENDENCE = (0.0, 0.25, 0.5, 0.75, 1.0)          # 0 = a patch shift does not touch B; 1 = common-mode
B_MISSING, B_GAIN, B_DRIFT = 0.10, 1.0, 0.0
REFERENCE_ERROR = 0.1117
SIDE_CASES = {"gain_b_0.8": {"gain_b": 0.8}, "gain_b_1.2": {"gain_b": 1.2},
              "drift_b_minus2ph": {"drift_per_hour": -0.02}, "drift_b_plus2ph": {"drift_per_hour": 0.02},
              "missing_b_50pct": {"missing": 0.50}}
B_MOVES = {"own_shift": (4.0, 0.7)}                 # B is the sensor that shifts; A is fine
FUSION = {"now_s": 1200.0, "before_s": 5400.0, "min_now": 10, "min_before": 30, "k_noise": 4.0,
          "min_change": 0.10, "min_ml": 100.0, "noise_n": 120, "noise_floor": 0.02}
SENSOR_REPS = 15                                    # may drop to 10 only through the timing test (plan section 6)
FALLBACK_REPS, TIME_LIMIT_MIN = 10, 60.0
THRESHOLDS = e8.THRESHOLDS
SEEDS, SCALINGS = e8.SEEDS, e8.SCALINGS
HELD_SEEDS = list(range(101, 111))                  # fresh inflow seeds, never used before
SEED_PREFIX = {"main": 3000, "heldout": 3100}
FLAG_WINDOW_H = 0.5
A_ALONE, RULE_A, RULE_B, RULE_C = "A_alone", "a_flag", "b_trust_b", "c_average"
NONE = -1.0                                         # grid value for "no sensor B" rows
TARGET = "misaligned_at_4h"
_A = config.value(config.SENSOR, "best_case_mean_relative_error")
PROBE_SEEDS = [42, 1, 2]
EXACT = t5.EXACT


def _mis(gain, start_h, extra_missing=0.30):
    return {"mean_relative_error": _A, "misalignment_start_h": start_h, "misalignment_gain": gain,
            "misalignment_missing_probability": extra_missing}


def grid(kind, name):
    """The sensor B points run for one sensor A scenario: (b_case, error, independence, extra settings)."""
    if kind == "mis":
        points = [("main", e, c, {}) for e in B_ERRORS for c in INDEPENDENCE]
    else:
        points = [("main", e, 0.0, {}) for e in B_ERRORS]       # no patch shift: independence has no effect
    if name in (TARGET, "anchor_11pct"):
        points += [(case, REFERENCE_ERROR, 0.0, extra) for case, extra in SIDE_CASES.items()]
    if name == "anchor_11pct":
        points.append(("b_moves", REFERENCE_ERROR, 0.0, B_MOVES))
    return points


def scenarios(which):
    """Ordered list of (name, kind, sensor A values). The position is the scenario number in the seed."""
    cfg = config.SENSOR_SCENARIOS.value
    if which == "main":
        out = [(TARGET, "mis", cfg[TARGET]), ("mis_x0.7_at_2h", "mis", _mis(0.7, 2.0)),
               ("mis_x0.7_at_4h_gain_only", "mis", _mis(0.7, 4.0, 0.0)), ("mis_x0.85_at_4h", "mis", _mis(0.85, 4.0))]
        return out + [(n, "none", v) for n, v in cfg.items() if n != TARGET]
    return [("held_x0.7_at_4h", "mis", _mis(0.7, 4.0)), ("held_x0.6_at_4h", "mis", _mis(0.6, 4.0)),
            ("held_x0.8_at_4h", "mis", _mis(0.8, 4.0)), ("anchor_11pct", "none", cfg["anchor_11pct"])]


def traces(which):
    seeds, folder = (SEEDS, e8.PHYS) if which == "main" else (HELD_SEEDS, HELD_PHYS)
    return [(folder / f"somatic_x{s}_seed{seed}.csv", s, seed) for s in SCALINGS for seed in seeds]


def jobs(which, reps):
    return [(which, str(path), scaling, seed, si, reps) for path, scaling, seed in traces(which)
            for si in range(len(scenarios(which)))]


def job_files(job):
    which, _, scaling, seed, si, _ = job
    stem = f"{which}_{si:02d}_x{scaling}_s{seed}"
    return RUNS / f"{stem}_flags.csv", RUNS / f"{stem}_alerts.csv"


# ------------------------------------------------------------------ one run
KEEP = ["n_alerts", "any_false_alert", "useful", "late", "missed", "lead_time_min", "true_volume_at_genuine_alert_ml"]


def alerts_for(stream, true_at, t_adv, key):
    """Feed one stream of readings to the unchanged device at each threshold; classify its alerts."""
    rows = []
    for thr in THRESHOLDS:
        dev = CustomTechDevice(thr, **e8.DEFAULT)
        for r in stream:
            dev.receive(r)
        cls = ev.classify_alerts(ev.alert_events(dev.events), true_at, t_adv, e8.FALSE_BELOW)
        rows.append({**key, "threshold_ml": thr, **{k: cls[k] for k in KEEP}})
    return rows


def run_pair(readings_a, readings_b):
    """Run the disagreement test once over the paired readings. Returns the flag dict or None."""
    fusion = SensorFusion(rule="flag", **FUSION)
    for ra, rb in zip(readings_a, readings_b):
        fusion.receive(ra, rb)
    return fusion.flag


def stream_for(rule, readings_a, readings_b, flag):
    """The readings the device gets under one rule. The same as SensorFusion would pass on (a test checks this)."""
    t_flag = flag["t_s"] if flag else np.inf
    return [Reading(ra.t_s, fused_value(rule, ra.volume_ml, rb.volume_ml, ra.t_s >= t_flag))
            for ra, rb in zip(readings_a, readings_b)]


def one_run(readings_a, sensor_b_for, points, true_at, t_adv, key, check_rule_a):
    """All sensor B points for one run of sensor A. Returns (flag rows, alert rows)."""
    none = {"b_case": "none", "b_error": NONE, "independence": NONE}
    flags, alerts = [], alerts_for(readings_a, true_at, t_adv, {**key, **none, "rule": A_ALONE})
    for b_case, error, indep, extra in points:
        point = {"b_case": b_case, "b_error": error, "independence": indep}
        readings_b = sensor_b_for(error, indep, extra)
        flag = run_pair(readings_a, readings_b)
        flags.append({**key, **point, "flagged": flag is not None,
                      "flag_h": flag["t_s"] / 3600 if flag else np.nan,
                      "change": flag["change"] if flag else np.nan})
        for rule, name in (("trust_b", RULE_B), ("average", RULE_C)):
            alerts += alerts_for(stream_for(rule, readings_a, readings_b, flag), true_at, t_adv,
                                 {**key, **point, "rule": name})
        if check_rule_a and b_case == "main" and error == REFERENCE_ERROR and indep == 0.0:
            fusion, stream = SensorFusion(rule="flag", **FUSION), []      # rule (a) run for real, not assumed
            for ra, rb in zip(readings_a, readings_b):
                stream.append(fusion.receive(ra, rb)[0])
            alerts += alerts_for(stream, true_at, t_adv, {**key, **point, "rule": RULE_A})
    return flags, alerts


def run_job(job):
    which, path, scaling, phys_seed, si, reps = job
    flag_file, alert_file = job_files(job)
    if flag_file.exists() and alert_file.exists():
        return "skipped"
    name, kind, a_values = scenarios(which)[si]
    truth = pd.read_csv(path)
    true_at = ev.truth_lookup(truth)
    t_adv, _ = ev.adverse_event(truth, e8.V_REF)
    dt = config.value(config.SENSOR, "sample_interval_s")
    times = [float(t) for t in np.arange(dt, truth["t"].iloc[-1], dt)]
    flags, alerts = [], []
    for rep in range(reps):
        tail = [si, int(round(scaling * 100)), phys_seed, rep]
        seed_a = int(np.random.SeedSequence([SEED_PREFIX[which]] + tail).generate_state(1)[0])
        seed_b = int(np.random.SeedSequence([SEED_PREFIX[which] + 1] + tail).generate_state(1)[0])
        sensor_a = SyntheticUltrasoundSensor(SensorScenario.from_dict(name, a_values), seed_a)
        readings_a = [sensor_a.read(t, true_at) for t in times]

        def sensor_b_for(error, indep, extra):
            values = sensor_b_values(error, indep, a_values, **{"gain_b": B_GAIN, "missing": B_MISSING,
                                                                "drift_per_hour": B_DRIFT, **extra})
            sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict("sensor_b", values), seed_b)
            return [sensor.read(t, true_at) for t in times]
        key = {"set": which, "scenario": name, "kind": kind, "sphincter_scaling": scaling,
               "physiology_seed": phys_seed, "rep": rep}
        f, a = one_run(readings_a, sensor_b_for, grid(kind, name), true_at, t_adv, key, check_rule_a=True)
        flags += f
        alerts += a
    for table, path_out in ((flags, flag_file), (alerts, alert_file)):     # write, then rename
        temp = path_out.with_suffix(".tmp")
        pd.DataFrame(table).to_csv(temp, index=False)
        temp.replace(path_out)
    return "done"


def sweep(which):
    check = OUT / "check.json"
    if not check.exists() or not json.loads(check.read_text())["passed"]:
        sys.exit("Refusing to start: the reproduction check has not passed (results/task8/check.json).")
    reps = json.loads((OUT / "timing.json").read_text())["sensor_reps_to_use"]
    todo = jobs(which, reps)
    missing = [p for p, _, _ in traces(which) if not p.exists()]
    if missing:
        sys.exit(f"Refusing to start: {len(missing)} physiology traces are missing, e.g. {missing[0]}")
    RUNS.mkdir(parents=True, exist_ok=True)
    start, done = time.time(), 0
    print(f"sweep {which}: {len(todo)} jobs, {reps} sensor seeds per trace ...", flush=True)
    with ProcessPoolExecutor() as pool:
        for i, status in enumerate(pool.map(run_job, todo, chunksize=1), 1):
            done += status == "done"
            if i % 20 == 0 or i == len(todo):
                print(f"  {i}/{len(todo)} jobs  ({done} run now)  {time.strftime('%H:%M:%S')}  "
                      f"{(time.time() - start) / 60:.1f} min", flush=True)
    print(f"sweep {which}: finished", flush=True)


# ------------------------------------------------------------------ checks before the sweep
def check():
    """With sensor B off, old results must come back exactly: open loop (Experiment 9) and closed loop (Task 5)."""
    out = {}
    rows = []                                             # (1) Experiment 9 target, "monitor off", its own seeds
    dt = config.value(config.SENSOR, "sample_interval_s")
    for path, scaling, phys_seed in traces("main"):
        truth = pd.read_csv(path)
        true_at = ev.truth_lookup(truth)
        t_adv, _ = ev.adverse_event(truth, e8.V_REF)
        times = [float(t) for t in np.arange(dt, truth["t"].iloc[-1], dt)]
        for rep in range(10):
            seed = int(np.random.SeedSequence([2000, 0, int(round(scaling * 100)), phys_seed, rep]).generate_state(1)[0])
            sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict(TARGET, config.SENSOR_SCENARIOS.value[TARGET]), seed)
            key = {"sphincter_scaling": scaling, "physiology_seed": phys_seed, "rep": rep}
            rows += alerts_for([sensor.read(t, true_at) for t in times], true_at, t_adv, key)
    pd.DataFrame(rows).to_csv(OUT / "check_open_loop_alerts.csv", index=False)
    mine = pd.read_csv(OUT / "check_open_loop_alerts.csv", **EXACT)        # file to file, by value (E58)
    old = pd.read_csv(TASK7 / "exp9_alert_runs.csv", **EXACT)
    old = old[(old.scenario == TARGET) & (old.variant == "monitor_off")]
    keys = ["sphincter_scaling", "physiology_seed", "rep", "threshold_ml"]
    cols = keys + KEEP
    a, b = mine.sort_values(keys).reset_index(drop=True)[cols], old.sort_values(keys).reset_index(drop=True)[cols]
    diff = t5.same_values(a, b) if len(a) == len(b) else {"rows differ": 1}
    out["open_loop"] = {"rows_task8": len(a), "rows_task7": len(b), "columns_compared": len(cols),
                        "differences": diff, "identical": bool(len(a) == len(b) == 900 and not diff)}

    todo = [c for c in t6.cases() if c["group"] == "A-check" and c["stim_name"] == "e0.6_s0.5_5on5off_block1.0_burst"]
    runs, sessions = [], []                               # (2) closed loop, fusion None, against Task 5
    with ProcessPoolExecutor() as pool:
        for row, sess, _ in pool.map(t6.run_one, todo, chunksize=1):
            runs.append(row)
            sessions += sess
    t5.save(runs, OUT / "check_closed_loop_runs.csv")
    t5.save(sessions, OUT / "check_closed_loop_sessions.csv")
    cmp = t6.compare_with_task5(pd.read_csv(OUT / "check_closed_loop_runs.csv", **EXACT),
                                pd.read_csv(OUT / "check_closed_loop_sessions.csv", **EXACT))
    out["closed_loop"] = {k: cmp[k] for k in ("runs", "sessions")}
    out["passed"] = bool(out["open_loop"]["identical"] and cmp["runs"]["identical"] and cmp["sessions"]["identical"]
                         and cmp["runs"]["rows_task6"] == 6)
    (OUT / "check.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("REPRODUCTION CHECK PASSED" if out["passed"] else "REPRODUCTION CHECK FAILED: do not start the sweep")


def timing():
    """Time one run of each kind on a made-up trace (results discarded) and project the main sweep."""
    t = np.arange(0.0, 12 * 3600.0, 1.0)
    true_at = lambda x: float(np.interp(x, t, t / 43200.0 * 950.0))      # noqa: E731  steady filling to 950 mL
    times = [float(x) for x in np.arange(60.0, t[-1], 60.0)]
    spent = {}
    for name, kind, a_values in (scenarios("main")[0], scenarios("main")[-1]):
        start = time.perf_counter()
        sensor_a = SyntheticUltrasoundSensor(SensorScenario.from_dict(name, a_values), 1)
        readings_a = [sensor_a.read(x, true_at) for x in times]

        def sensor_b_for(error, indep, extra):
            values = sensor_b_values(error, indep, a_values, **{"gain_b": B_GAIN, "missing": B_MISSING,
                                                                "drift_per_hour": B_DRIFT, **extra})
            sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict("sensor_b", values), 2)
            return [sensor.read(x, true_at) for x in times]
        one_run(readings_a, sensor_b_for, grid(kind, "x"), true_at, 30000.0, {}, check_rule_a=True)
        spent[kind] = time.perf_counter() - start
    workers = os.cpu_count() or 1
    n_mis = sum(k == "mis" for _, k, _ in scenarios("main"))
    n_none = len(scenarios("main")) - n_mis
    per_rep = 30 * (n_mis * spent["mis"] + n_none * spent["none"])        # core-seconds per sensor seed, 30 traces
    project = lambda reps: per_rep * reps / workers / 60.0 * 1.3          # noqa: E731  30% allowance for uneven load
    reps = SENSOR_REPS if project(SENSOR_REPS) <= TIME_LIMIT_MIN else FALLBACK_REPS
    out = {"seconds_per_run": spent, "workers": workers, "projected_main_sweep_min_at_15": project(SENSOR_REPS),
           "projected_main_sweep_min_at_10": project(FALLBACK_REPS), "limit_min": TIME_LIMIT_MIN,
           "sensor_reps_to_use": reps}
    (OUT / "timing.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


def held_out_physiology(args):
    """The unchanged Experiment 2 simulation, writing into the Task 8 held-out folder."""
    s4.PHYS_DIR = HELD_PHYS
    return s4.run_physiology(args)


def physiology():
    """Simulate the 20 fresh held-out traces with the unchanged Experiment 2 code."""
    HELD_PHYS.mkdir(parents=True, exist_ok=True)
    todo = [(s, seed) for s in SCALINGS for seed in HELD_SEEDS if not (HELD_PHYS / f"somatic_x{s}_seed{seed}.csv").exists()]
    print(f"held-out physiology: {len(todo)} runs ...", flush=True)
    with ProcessPoolExecutor() as pool:
        for name, seconds in pool.map(held_out_physiology, todo):
            print(f"  {name}  {seconds:.0f} s  {time.strftime('%H:%M:%S')}", flush=True)


# ------------------------------------------------------------------ scoring
GRID = ["b_case", "b_error", "independence"]


def load(which):
    """Every job file of one sweep. Refuses if any is missing: partial files are never the full grid."""
    reps = json.loads((OUT / "timing.json").read_text())["sensor_reps_to_use"]
    files = [job_files(j) for j in jobs(which, reps)]
    missing = [f for pair in files for f in pair if not f.exists()]
    if missing:
        sys.exit(f"Refusing to score '{which}': {len(missing)} of {2 * len(files)} job files are missing.")
    flags = pd.concat([pd.read_csv(f) for f, _ in files], ignore_index=True)
    alerts = pd.concat([pd.read_csv(a) for _, a in files], ignore_index=True)
    return flags, alerts


def summarise_flags(flags, which):
    start = {n: v.get("misalignment_start_h") for n, _, v in scenarios(which)}
    rows = []
    for key, g in flags.groupby(["set", "scenario", "kind", "sphincter_scaling"] + GRID, sort=False):
        s = 4.0 if key[4] == "b_moves" else start[key[1]]
        row = dict(zip(["set", "scenario", "kind", "sphincter_scaling"] + GRID, key))
        row.update({"n_runs": len(g), "flag_rate": g["flagged"].mean(),
                    "a_low_share_of_flags": (g["change"] < 0).sum() / max(int(g["flagged"].sum()), 1)})
        if s is not None:
            hit = (g["flag_h"] >= s) & (g["flag_h"] <= s + FLAG_WINDOW_H)
            row.update({"start_h": s, "on_time_rate": hit.mean(), "flag_before_start_rate": (g["flag_h"] < s).mean(),
                        "flag_ever_after_start_rate": (g["flag_h"] >= s).mean(),
                        "median_min_to_flag": ((g["flag_h"][hit] - s) * 60).median()})
        rows.append(row)
    return pd.DataFrame(rows)


def summarise_alerts(alerts):
    rows = []
    for key, g in alerts.groupby(["set", "scenario", "kind", "sphincter_scaling", "threshold_ml"] + GRID + ["rule"],
                                 sort=False):
        lead, v = g["lead_time_min"].dropna(), g["true_volume_at_genuine_alert_ml"].dropna()
        row = dict(zip(["set", "scenario", "kind", "sphincter_scaling", "threshold_ml"] + GRID + ["rule"], key))
        row.update({"n_runs": len(g), "useful_rate": g["useful"].mean(),
                    "false_alert_run_rate": g["any_false_alert"].mean(), "late_rate": g["late"].mean(),
                    "missed_rate": g["missed"].mean(), "median_lead_min": lead.median() if len(lead) else np.nan,
                    "true_volume_at_alert_median_ml": v.median() if len(v) else np.nan,
                    "true_volume_at_alert_p05_ml": v.quantile(0.05) if len(v) else np.nan,
                    "mean_alerts_per_run": g["n_alerts"].mean()})
        row["C1_pass"] = bool(row["useful_rate"] >= 0.95)
        row["C2_pass"] = bool(row["false_alert_run_rate"] <= 0.05)
        row["C3_pass"] = bool(row["median_lead_min"] >= 30)
        row["cue_works"] = row["C1_pass"] and row["C2_pass"] and row["C3_pass"]
        rows.append(row)
    return pd.DataFrame(rows)


def requirement(fs, als, which):
    """One row per misalignment scenario, rule, B error and independence, with every criterion."""
    main_f, main_a = fs[fs.b_case == "main"], als[als.b_case == "main"]
    none_f = main_f[main_f.kind == "none"]
    m2 = none_f.groupby("b_error")["flag_rate"].max()                          # worst cell, per B error
    m2_cells = none_f.groupby("b_error").size()
    alone = als[als.rule == A_ALONE].set_index(["scenario", "sphincter_scaling", "threshold_ml"])["cue_works"]
    harm, gain = {}, {}
    for (error, rule), g in main_a[main_a.kind == "none"].groupby(["b_error", "rule"]):
        if rule == RULE_A:
            continue
        g = g.set_index(["scenario", "sphincter_scaling", "threshold_ml"])["cue_works"]
        before = alone.reindex(g.index)
        harm[(error, rule)], gain[(error, rule)] = int((before & ~g).sum()), int((~before & g).sum())
    rows = []
    for name, kind, _ in scenarios(which):
        if kind != "mis":
            continue
        f = main_f[main_f.scenario == name].groupby(["b_error", "independence"])["on_time_rate"].min()
        a = main_a[main_a.scenario == name]
        base_cells = int(alone.xs(name, level="scenario").sum())
        for (error, indep, rule), g in a.groupby(["b_error", "independence", "rule"]):
            if rule == RULE_A:
                continue
            row = {"set": which, "scenario": name, "rule": rule, "b_error": error, "independence": indep,
                   "cells_working": int(g["cue_works"].sum()), "cells": len(g), "cells_working_A_alone": base_cells,
                   "on_time_rate_min": float(f[(error, indep)]), "M1_pass": bool(f[(error, indep)] >= 0.90),
                   "M2_highest_flag_rate": float(m2[error]), "M2_cells": int(m2_cells[error]),
                   "M2_pass": bool(m2[error] <= 0.05), "M4_cells_harmed": harm[(error, rule)],
                   "cells_gained_without_misalignment": gain[(error, rule)], "M4_pass": harm[(error, rule)] == 0,
                   "worst_false_alert_rate": float(g["false_alert_run_rate"].max()),
                   "lowest_useful_rate": float(g["useful_rate"].min())}
            row["flag_works"] = row["M1_pass"] and row["M2_pass"]
            row["fixed"] = bool(row["cells_working"] == row["cells"] and row["M4_pass"]
                                and (row["flag_works"] or rule == RULE_C))
            rows.append(row)
    return pd.DataFrame(rows)


def curve(req):
    """The requirement curve: for each scenario, rule and independence, the B errors at which it is fixed."""
    rows = []
    for (which, name, rule, indep), g in req.groupby(["set", "scenario", "rule", "independence"]):
        g = g.sort_values("b_error")
        ok = [float(e) for e, fixed in zip(g["b_error"], g["fixed"]) if fixed]
        block = []
        for e, fixed in zip(g["b_error"], g["fixed"]):                         # the block from the best B upward
            if not fixed:
                break
            block.append(float(e))
        rows.append({"set": which, "scenario": name, "rule": rule, "independence": indep,
                     "b_errors_fixed": ";".join(f"{e:g}" for e in ok), "n_fixed": len(ok),
                     "weakest_b_error_fixed": max(ok) if ok else np.nan,
                     "one_block_from_best": ok == block,
                     "cells_working_by_error": ";".join(str(int(c)) for c in g["cells_working"])})
    return pd.DataFrame(rows)


def score():
    out = {}
    all_req, all_curve = [], []
    for which in ("main", "heldout"):
        flags, alerts = load(which)
        fs, als = summarise_flags(flags, which), summarise_alerts(alerts)
        fs.to_csv(OUT / f"exp10_{which}_flag_summary.csv", index=False)
        als.to_csv(OUT / f"exp10_{which}_alert_summary.csv", index=False)
        req = requirement(fs, als, which)
        all_req.append(req)
        all_curve.append(curve(req))
        ref = als[(als.b_case == "main") & (als.b_error == REFERENCE_ERROR) & (als.independence == 0.0)]
        keys = ["scenario", "sphincter_scaling", "threshold_ml"]
        cols = ["useful_rate", "false_alert_run_rate", "late_rate", "missed_rate", "mean_alerts_per_run"]
        ra = ref[ref.rule == RULE_A].set_index(keys)[cols]
        al = als[als.rule == A_ALONE].set_index(keys)[cols].reindex(ra.index)
        out[which] = {"runs": int(len(flags.drop_duplicates(["scenario", "sphincter_scaling", "physiology_seed", "rep"]))),
                      "flag_rows": int(len(flags)), "alert_rows": int(len(alerts)),
                      "rule_a_cells_checked": int(len(ra)),
                      "rule_a_alerts_equal_A_alone": bool((ra.fillna(-1) == al.fillna(-1)).all().all())}
    req, cur = pd.concat(all_req, ignore_index=True), pd.concat(all_curve, ignore_index=True)
    req.to_csv(OUT / "exp10_requirement.csv", index=False)
    cur.to_csv(OUT / "exp10_curve.csv", index=False)
    (OUT / "exp10_key_numbers.json").write_text(json.dumps(out, indent=2))
    pd.set_option("display.width", 250)
    print(cur.to_string(index=False))
    print(json.dumps(out, indent=2))


# ------------------------------------------------------------------ closed-loop probe (descriptive)
def probe_cases():
    out, sensors = [], config.SENSOR_SCENARIOS.value
    stim = config.STIM_PATTERNS.value[t6.PROBE_PATTERN]
    for scaling in t5.SCALINGS:
        for label, sensor, rule, indep in [("anchor_trust_b", "anchor_11pct", "trust_b", 0.0),
                                           ("misaligned_trust_b", TARGET, "trust_b", 0.0),
                                           ("misaligned_average", TARGET, "average", 0.0),
                                           ("misaligned_trust_b_common_mode", TARGET, "trust_b", 1.0)]:
            for seed in PROBE_SEEDS:
                b = sensor_b_values(REFERENCE_ERROR, indep, sensors[sensor], gain_b=B_GAIN, missing=B_MISSING,
                                    drift_per_hour=B_DRIFT)
                out.append({"group": "T8-probe", "stim_name": t6.PROBE_PATTERN, "stim": stim, "task5_twin": "",
                            "controller": {"pressure_ceiling_cmH2O": t5.CEILING_CMH2O},
                            "ultrasound_interval_during_stim_s": t5.US_INTERVAL_S, "sphincter_scaling": scaling,
                            "phys_seed": seed, "sensor_seed": seed, "user_seed": seed, "pressure_seed": seed,
                            "probe": label, "sensor_name": sensor, "sensor": sensors[sensor],
                            "fusion": {"rule": rule, "settings": FUSION, "sensor_b": b, "sensor_b_seed": 1000 + seed}})
    return out


def probe_one(spec):
    """t6.run_one, plus the times at which the two sensors were flagged as disagreeing."""
    import sci_test_rig as rig_mod
    flags = []
    original = rig_mod.CueRig

    class Recording(original):
        def __init__(self, case):
            super().__init__(case)
            flags.append(self.fusion_flags)
    rig_mod.CueRig = Recording
    try:
        row, sessions, _ = t6.run_one(spec)
    finally:
        rig_mod.CueRig = original
    times = flags[0] if flags else []
    row["n_fusion_flags"], row["fusion_flag_h"] = len(times), times[0] / 3600 if times else np.nan
    return row, sessions


def probe():
    todo = probe_cases()
    print(f"task8 closed-loop probe: {len(todo)} runs ...", flush=True)
    rows, sessions = [], []
    with ProcessPoolExecutor() as pool:
        for i, (row, sess) in enumerate(pool.map(probe_one, todo, chunksize=1), 1):
            rows.append(row)
            sessions += sess
            print(f"  {i}/{len(todo)} done  {time.strftime('%H:%M:%S')}", flush=True)
    t5.save(rows, OUT / "probe_runs.csv")
    t5.save(sessions, OUT / "probe_sessions.csv")
    runs = pd.read_csv(OUT / "probe_runs.csv")
    inv = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
    errors = int(runs["error"].fillna("").astype(str).ne("").sum())
    result = {"runs": len(runs), "errors": errors,
              "invariants_hold_in_all_runs": bool(errors == 0 and runs[inv].all().all())}
    (OUT / "probe_check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ("--check", "--timing", "--physiology", "--score", "--probe"):
        group.add_argument(flag, action="store_true")
    group.add_argument("--sweep", choices=["main", "heldout"])
    args = parser.parse_args()
    config.validate()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.check:
        check()
    elif args.timing:
        timing()
    elif args.physiology:
        physiology()
    elif args.sweep:
        sweep(args.sweep)
    elif args.score:
        score()
    else:
        probe()


if __name__ == "__main__":
    main()
