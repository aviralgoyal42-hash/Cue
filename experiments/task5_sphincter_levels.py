"""
TASK 5: how much sphincter suppression during bursts the model needs before emptying works.
Plan frozen in docs/TASK5_PLAN.md before anything was run. MODEL ONLY: the levels are normalised
model drives, not clinical stimulation parameters. Results are model predictions, not evidence
for a device. All settings come from Experiment 3b, so every result is POST-HOC and OPTIMISTIC.

What is varied: the sphincter drive during burst-ON time (0, 0.1, 0.2, 0.3, 0.4, 0.5), on four fixed
Experiment 3b working settings, with 15 seeds. Everything else is the unchanged Experiment 3 rig,
device, controller, metrics and scoring. config.py is NOT edited: the new patterns are built here.

Usage (PowerShell, from the project folder):
  python -W ignore experiments\\task5_sphincter_levels.py --check    Step 2: 24 runs, compared with Task 4
  python -W ignore experiments\\task5_sphincter_levels.py --sweep    Step 3: 360 runs (refuses unless --check passed)
Outputs go to results/task5/ only.
"""
import argparse
import ctypes
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
import config                                   # noqa: E402
import sci_test_rig as rig_mod                  # noqa: E402
from evaluation import closed_loop_metrics as cm  # noqa: E402
import stage6_experiments3_4 as s6              # noqa: E402  (old grid and scoring, used unchanged)
import emptying_duration_check as edc           # noqa: E402  (frozen emptying-time definition)

RESULTS = ROOT / "results" / "task5"
CHECK = RESULTS / "check"
TASK4 = ROOT / "results" / "task4"              # read only

# ---- Fixed before running (docs/TASK5_PLAN.md). ASSUMED. Never tuned after results are seen.
LEVELS = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)         # sphincter drive during burst-ON time
DETRUSOR = (0.6, 1.0)                           # the two Experiment 3b burst patterns
SCALINGS = (1.0, 0.9)                           # sphincter strength (x somatic_a)
CEILING_CMH2O, THRESHOLD_ML, MAX_DURATION_S, US_INTERVAL_S = 55.0, 400.0, 60.0, 60.0
SEEDS = [42] + list(range(1, 15))
CHECK_SEEDS = [42, 1, 2]
REFERENCE_LEVELS = (0.0, 0.5)                   # levels that already exist in Experiment 3 / Task 4

DT, POST = s6.DT, s6.POST
EXACT = {"float_precision": "round_trip"}
SETTING_KEYS = ["stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s", "threshold_ml",
                "max_duration_s", "sphincter_scaling"]
RUN_KEYS = SETTING_KEYS + ["phys_seed"]


def pattern(detrusor, level):
    """Copy the existing s0.0 5 s on / 5 s off pattern and change only the sphincter level."""
    base = config.STIM_PATTERNS.value[f"e{detrusor}_s0.0_5on5off"]
    return f"e{detrusor}_s{level:.1f}_5on5off", {**base, "sphincter_drive": float(level)}


def cases(levels=LEVELS, seeds=SEEDS):
    out = []
    for detrusor in DETRUSOR:
        for scaling in SCALINGS:
            for level in levels:
                name, stim = pattern(detrusor, level)
                for seed in seeds:
                    out.append({"group": "task5", "stim_name": name, "stim": stim,
                                "controller": {"pressure_ceiling_cmH2O": CEILING_CMH2O},
                                "ultrasound_interval_during_stim_s": US_INTERVAL_S, "sphincter_scaling": scaling,
                                "phys_seed": seed, "sensor_seed": seed, "user_seed": seed, "pressure_seed": seed})
    return out


def emptying_times(data, rig):
    """Evaluation side (uses true volume). Frozen definition of docs/EMPTYING_DURATION_CHECK.md at 1 Hz."""
    d1 = data.iloc[::10]                                   # 1 Hz, as in the saved traces
    t, v = d1["t"].to_numpy(), d1["V_B_ml"].to_numpy()
    flowing = np.zeros(len(t), dtype=bool)
    flowing[:-1] = (v[:-1] - v[1:]) > edc.FLOW_DROP_ML     # true volume fell by > 0.1 mL in that second
    sessions = rig.controller.sessions
    starts = [int(np.searchsorted(t, s["start_s"] - 1e-6)) for s in sessions]   # first sample at/after start
    rows = []
    for k, (s, i0) in enumerate(zip(sessions, starts)):
        i_limit = starts[k + 1] if k + 1 < len(starts) else len(t) - 1
        if i0 >= len(t) - 1:
            rows.append({"emptying_duration_s": np.nan, "within_1ml_of_lowest_s": np.nan,
                         "flow_s_after_stim_stop": np.nan})
            continue
        end, used = edc.episode(t, flowing, i0, i_limit)
        w_end = min(i_limit, int(np.searchsorted(t, t[i0] + 600.0)))
        v_low = v[i0:w_end + 1].min()
        i_reach = i0 + int(np.flatnonzero(v[i0:w_end + 1] <= v_low + 1.0)[0])
        stop = s.get("stop_s", t[-1])
        rows.append({"emptying_duration_s": float(end - t[i0]), "within_1ml_of_lowest_s": float(t[i_reach] - t[i0]),
                     "flow_s_after_stim_stop": int(sum(t[i] + 0.5 >= stop for i in used))})
    return rows


def run_one(spec):
    """Same as stage6 run_one (rows built identically, so they can be compared with Task 4 exactly),
    plus emptying times on each session row, and no trace files."""
    meta = {k: spec[k] for k in ("group", "stim_name", "sphincter_scaling", "phys_seed") if k in spec}
    meta["reference"] = spec.get("reference", "")
    changes = {k: v for k, v in spec.items() if k not in ("group", "reference")}
    case = rig_mod.default_case(**changes)
    meta.update({"sensor_name": case["sensor_name"], "user_name": case["user_name"],
                 "pressure_name": case["pressure_name"], "threshold_ml": case["threshold_ml"],
                 "pressure_ceiling_cmH2O": case["controller"]["pressure_ceiling_cmH2O"],
                 "max_duration_s": case["controller"]["max_duration_s"],
                 "ultrasound_interval_during_stim_s": case["ultrasound_interval_during_stim_s"]})
    start = time.perf_counter()
    try:
        data, rig = rig_mod.run_closed_loop(case)
        ceiling = case["controller"]["pressure_ceiling_cmH2O"]
        sessions = cm.session_table(data, rig, DT, ceiling, POST)
        timing = emptying_times(data, rig)
    except Exception as exc:          # logged as a result, not hidden
        return {**meta, "error": repr(exc)}, []
    row = {**meta, "error": "", "runtime_s": round(time.perf_counter() - start, 1),
           **cm.run_summary(data, rig, DT, ceiling, POST),
           **cm.invariants(rig, DT, case["controller"]["max_duration_s"])}
    if sessions:
        s = pd.DataFrame(sessions)
        row.update({"sessions_voided_ge_50pct": float(s["voided_ge_50pct"].mean()),
                    "sessions_ceiling_exceeded_gt5": float(s["ceiling_exceeded_gt5"].mean()),
                    "max_true_p_D_during_stim_cmH2O": float(s["max_true_p_D_during_cmH2O"].max()),
                    "median_residual_ml": float(s["residual_ml"].median()),
                    "cutoffs": ";".join(sorted(set(s["cutoff"]))),
                    "n_complete": int((s["emptying"] == "complete").sum()),
                    "n_partial": int((s["emptying"] == "partial").sum()),
                    "n_none": int((s["emptying"] == "none").sum())})
    sessions = [{**meta, **x, **tm} for x, tm in zip(sessions, timing)]
    return row, sessions


def save(table, path):
    """Write then rename, so a crash during a save cannot leave a half-written file."""
    temp = path.with_suffix(".tmp")
    pd.DataFrame(table).to_csv(temp, index=False)
    temp.replace(path)


def run_cases(todo, folder, label):
    """Run in order with 12 workers, saving partial files every 25 runs; resume from them if present."""
    folder.mkdir(parents=True, exist_ok=True)
    run_file, session_file = folder / f"{label}_runs_partial.csv", folder / f"{label}_sessions_partial.csv"
    rows, sessions = [], []
    if run_file.exists():
        rows = pd.read_csv(run_file, **EXACT).to_dict("records")
        sessions = pd.read_csv(session_file, **EXACT).to_dict("records") if session_file.stat().st_size > 2 else []
    print(f"{label}: {len(todo)} runs, {len(rows)} already saved ...", flush=True)
    with ProcessPoolExecutor() as pool:
        for i, (row, sess) in enumerate(pool.map(run_one, todo[len(rows):], chunksize=1), len(rows) + 1):
            rows.append(row)
            sessions += sess
            if i % 25 == 0:
                print(f"  {i}/{len(todo)} done  {time.strftime('%H:%M:%S')}", flush=True)
                save(rows, run_file)
                save(sessions, session_file)
    runs = pd.DataFrame(rows)
    runs["error"] = runs["error"].fillna("")
    save(runs, folder / f"{label}_runs.csv")
    save(sessions, folder / f"{label}_sessions.csv")
    run_file.unlink(missing_ok=True)          # only after the full files are safely written
    session_file.unlink(missing_ok=True)
    print(f"{label}: {len(runs)} runs; errors {int((runs['error'] != '').sum())}", flush=True)


def same_values(a, b):
    """Columns that differ, compared by value (2 == 2.0), with NaN equal to NaN and floats exact."""
    bad = {}
    for c in a.columns:
        x, y = a[c].reset_index(drop=True), b[c].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            ok = (x.astype(float).to_numpy() == y.astype(float).to_numpy()) | (x.isna() & y.isna()).to_numpy()
        else:
            ok = (x.fillna("").astype(str) == y.fillna("").astype(str)).to_numpy()
        if not ok.all():
            bad[c] = int((~ok).sum())
    return bad


def compare_with_task4(runs_path, sessions_path, seeds):
    """File-to-file comparison (E58) of levels 0 and 0.5 with the Task 4 Experiment 3 rows."""
    mine_r, mine_s = pd.read_csv(runs_path, **EXACT), pd.read_csv(sessions_path, **EXACT)
    old_r, old_s = pd.read_csv(TASK4 / "exp3_runs.csv", **EXACT), pd.read_csv(TASK4 / "exp3_sessions.csv", **EXACT)
    names = [pattern(d, lv)[0] for d in DETRUSOR for lv in REFERENCE_LEVELS]
    pick = lambda df: df[df.stim_name.isin(names) & df.phys_seed.isin(seeds)]
    mine_r, mine_s = pick(mine_r), pick(mine_s)
    sel = (old_r.group == "main") & (old_r.pressure_ceiling_cmH2O == CEILING_CMH2O) & \
          (old_r.ultrasound_interval_during_stim_s == US_INTERVAL_S)
    old_r = pick(old_r[sel])
    old_s = pick(old_s[(old_s.group == "main") & (old_s.pressure_ceiling_cmH2O == CEILING_CMH2O)
                       & (old_s.ultrasound_interval_during_stim_s == US_INTERVAL_S)])
    out = {}
    for label, a, b, keys in [("runs", mine_r, old_r, RUN_KEYS), ("sessions", mine_s, old_s, RUN_KEYS + ["start_h"])]:
        cols = [c for c in b.columns if c in a.columns and c not in ("runtime_s", "group")]
        a2, b2 = a.sort_values(keys).reset_index(drop=True), b.sort_values(keys).reset_index(drop=True)
        same_keys = len(a2) == len(b2) and same_values(a2[keys], b2[keys]) == {}
        diff = same_values(a2[cols], b2[cols]) if same_keys else {"row keys differ": 1}
        out[label] = {"rows_task5": len(a2), "rows_task4": len(b2), "columns_compared": len(cols),
                      "columns_only_in_task4": [c for c in b.columns if c not in a.columns],
                      "differences": diff, "identical": same_keys and not diff}
    s05 = mine_s[mine_s.stim_name.str.contains("_s0.5_")]
    out["level_0.5_sessions"] = len(s05)
    out["level_0.5_sessions_voiding_10pct_or_more"] = int((s05.emptying != "none").sum())
    out["errors"] = int(pd.read_csv(runs_path).error.fillna("").astype(str).ne("").sum())
    out["passed"] = bool(out["runs"]["identical"] and out["sessions"]["identical"]
                         and out["level_0.5_sessions_voiding_10pct_or_more"] == 0 and out["errors"] == 0)
    return out


def stay_awake(on):
    """Backup keep-awake approved by the user: system-required only (the screen may still turn off).
    Released when called with on=False, and automatically when this process exits. Changes no setting."""
    if sys.platform != "win32":
        return
    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Step 2: levels 0 and 0.5, seeds 42, 1, 2")
    group.add_argument("--sweep", action="store_true", help="Step 3: all 360 runs")
    args = parser.parse_args()
    config.validate()
    stay_awake(True)
    try:
        if args.check:
            todo = cases(REFERENCE_LEVELS, CHECK_SEEDS)
            run_cases(todo, CHECK, "check")
            result = compare_with_task4(CHECK / "check_runs.csv", CHECK / "check_sessions.csv", CHECK_SEEDS)
            (CHECK / "check.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result, indent=2))
            print("STEP 2 CHECK PASSED" if result["passed"] else "STEP 2 CHECK FAILED: do not start the sweep")
        else:
            check_file = CHECK / "check.json"
            if not check_file.exists() or not json.loads(check_file.read_text())["passed"]:
                sys.exit("Refusing to start: the Step 2 check has not passed (results/task5/check/check.json).")
            pd.DataFrame(config.as_table()).to_csv(RESULTS / "parameters_used.csv", index=False)
            pd.DataFrame([{"level": lv, "stim_name": pattern(d, lv)[0], **pattern(d, lv)[1]}
                          for d in DETRUSOR for lv in LEVELS]).to_csv(RESULTS / "levels_used.csv", index=False)
            run_cases(cases(), RESULTS, "task5")
            runs = pd.read_csv(RESULTS / "task5_runs.csv", **EXACT)
            sessions = pd.read_csv(RESULTS / "task5_sessions.csv", **EXACT)
            s6.summarise_exp3(runs, sessions).to_csv(RESULTS / "task5_settings_summary.csv", index=False)
            rep = compare_with_task4(RESULTS / "task5_runs.csv", RESULTS / "task5_sessions.csv", SEEDS)
            (RESULTS / "reproduction_15_seeds.json").write_text(json.dumps(rep, indent=2))
            print(json.dumps(rep, indent=2))
    finally:
        stay_awake(False)


if __name__ == "__main__":
    main()
