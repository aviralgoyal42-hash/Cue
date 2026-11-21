"""
Experiment 7: session cap and post-session check, against the stuck-high fault, a genuine failed
emptying, and the no-fault patterns that empty. Grid and criteria frozen in
docs/EXPERIMENT7_CRITERIA.md. Old result folders are read, never written.

Writes results/task3/: exp7_runs.csv, exp7_sessions.csv, parameters_used.csv, exp7_consistency.json.
Scoring against the criteria is in experiments/task3_analysis.py.
Usage: python experiments/task3_experiment7.py [--recheck]
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage6_experiments3_4 as s6  # noqa: E402
from evaluation import closed_loop_metrics as cm, guard_metrics as gm  # noqa: E402

config, rig_mod = s6.config, s6.rig_mod
RESULTS = Path(__file__).resolve().parents[1] / "results" / "task3"
OLD = RESULTS.parent
DECLARED, EMPTIES = config.REFERENCE_STIM.value, ["e0.6_s0.0_5on5off", "e1.0_s0.0_5on5off"]
SECOND = s6.SECOND_REFERENCE
THRESHOLDS_T3 = [350.0, 400.0, 450.0]
SCALINGS = [1.0, 0.9]
SEEDS = [42] + list(range(1, 15))
STUCK = "stuck_high_450ml_from_5h"
FAULT_ONSET_S = config.EXTRA_SENSOR_FAULTS.value[STUCK]["stuck_from_h"] * 3600
RULES = [None] + [(cap, fraction) for cap in config.value(config.SESSION_GUARD, "session_caps")
                  for fraction in config.value(config.SESSION_GUARD, "min_drop_fractions")]


def guard_settings(rule):
    if rule is None:
        return None
    g = config.SESSION_GUARD
    return {"session_cap": rule[0], "min_drop_fraction": rule[1], "readings_needed": config.value(g, "readings_before_check"),
            "deadline_s": config.value(g, "check_deadline_s"), "repeat_s": config.value(g, "alert_repeat_s")}


def cases():
    out = []
    def add(test, pattern, threshold, rule, scaling, seed, **change):
        out.append({"test": test, **s6.stim(pattern), "threshold_ml": threshold, "guard": guard_settings(rule),
                    "sphincter_scaling": scaling, "phys_seed": seed, "sensor_seed": seed, "user_seed": seed,
                    "pressure_seed": seed, **change})
    for rule in RULES:
        for scaling in SCALINGS:
            for seed in SEEDS:
                for pattern in [DECLARED, SECOND]:
                    add("T1", pattern, 400.0, rule, scaling, seed, sensor_name=STUCK,
                        sensor=config.EXTRA_SENSOR_FAULTS.value[STUCK])
                add("T2", DECLARED, 400.0, rule, scaling, seed)
                if rule is not None:         # rule off is already in Experiment 3b, which T3 is judged against
                    for pattern in EMPTIES:
                        for threshold in THRESHOLDS_T3:
                            add("T3", pattern, threshold, rule, scaling, seed)
    return out


def run_one(spec):
    """Run one person; return (run row, session rows). Never raises: failures become rows."""
    changes = {k: v for k, v in spec.items() if k != "test"}
    guard = spec["guard"]
    meta = {"test": spec["test"], "rule": f"cap{guard['session_cap']}_drop{guard['min_drop_fraction']:.2f}" if guard else "off",
            "session_cap": guard["session_cap"] if guard else None, "min_drop_fraction": guard["min_drop_fraction"] if guard else None,
            "stim_name": spec["stim_name"], "sphincter_scaling": spec["sphincter_scaling"], "phys_seed": spec["phys_seed"]}
    case = rig_mod.default_case(**changes)
    ceiling = case["controller"]["pressure_ceiling_cmH2O"]
    meta.update({"sensor_name": case["sensor_name"], "user_name": case["user_name"], "pressure_name": case["pressure_name"],
                 "threshold_ml": case["threshold_ml"], "pressure_ceiling_cmH2O": ceiling,
                 "max_duration_s": case["controller"]["max_duration_s"]})
    start = time.perf_counter()
    try:
        data, rig = rig_mod.run_closed_loop(case)
        sessions = cm.session_table(data, rig, s6.DT, ceiling, s6.POST)
        onset = FAULT_ONSET_S if case["sensor_name"] == STUCK else None
        row = {**meta, "error": "", "runtime_s": round(time.perf_counter() - start, 1),
               **cm.run_summary(data, rig, s6.DT, ceiling, s6.POST),
               **cm.invariants(rig, s6.DT, case["controller"]["max_duration_s"]),
               **gm.guard_summary(data, rig, sessions, onset, s6.DT, s6.POST)}
        gm.add_checks_to_sessions(sessions, rig)
    except Exception as exc:              # logged as a result, not hidden
        return {**meta, "error": repr(exc)}, []
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
    return row, [{**meta, **x} for x in sessions]


def same_values(a, b, cols):
    """True if two equally ordered tables hold exactly the same values. Compares values, not
    storage types, so whole numbers saved as 2 in one file and 2.0 in another still match."""
    for c in cols:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            if not ((x == y) | (x.isna() & y.isna())).all():
                return False
        elif not (x.astype(object).where(x.notna(), "") == y.astype(object).where(y.notna(), "")).all():
            return False
    return True


def consistency():
    """Rule off, seeds 42, 1 and 2: must match Experiment 4 (stuck-high) and Experiment 3
    (declared reference) exactly, in every shared column, compared file to file (error E58)."""
    exact = {"float_precision": "round_trip"}
    keys = ["stim_name", "sphincter_scaling", "phys_seed"]
    skip = keys + ["group", "runtime_s", "error", "reference"]
    out = {}
    for label in ["runs", "sessions"]:
        new = pd.read_csv(RESULTS / f"exp7_{label}.csv", **exact)
        new = new[(new.rule == "off") & new.phys_seed.isin([42, 1, 2])]
        e4 = pd.read_csv(OLD / "stage6" / f"exp4_{label}.csv", **exact)
        e4 = e4[e4.group == "estimate:" + STUCK]
        e3 = pd.read_csv(OLD / "stage6" / f"exp3_{label}.csv", **exact)
        e3 = e3[(e3.group == "main") & (e3.ultrasound_interval_during_stim_s == 60) & (e3.stim_name == DECLARED)
                & (e3.pressure_ceiling_cmH2O == 55)]
        for name, old, test in [("T1_vs_exp4", e4, "T1"), ("T2_vs_exp3", e3, "T2")]:
            b = new[new.test == test]
            order = keys + (["start_h"] if label == "sessions" else [])
            a, b = old.sort_values(order).reset_index(drop=True), b.sort_values(order).reset_index(drop=True)
            cols = [c for c in a.columns if c in b.columns and c not in skip]
            out[f"{name}_{label}"] = {"rows_old": len(a), "rows_new": len(b), "columns_compared": len(cols),
                                      "identical": len(a) == len(b) and same_values(a, b, cols)}
    out["reproduces"] = all(v["identical"] and v["rows_old"] > 0 for v in out.values())
    with open(RESULTS / "exp7_consistency.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out))
    return out


def main():
    config.validate()
    RESULTS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(config.as_table()).to_csv(RESULTS / "parameters_used.csv", index=False)
    todo = cases()
    print(f"exp7: {len(todo)} runs ...", flush=True)
    rows, sessions = [], []
    with ProcessPoolExecutor() as pool:
        for i, (row, sess) in enumerate(pool.map(run_one, todo, chunksize=1)):
            rows.append(row)
            sessions += sess
            if (i + 1) % 25 == 0:
                print(f"  {i + 1}/{len(todo)} done", flush=True)
                pd.DataFrame(rows).to_csv(RESULTS / "exp7_runs_partial.csv", index=False)   # save as we go
    runs = pd.DataFrame(rows)
    runs.to_csv(RESULTS / "exp7_runs.csv", index=False)
    pd.DataFrame(sessions).to_csv(RESULTS / "exp7_sessions.csv", index=False)
    (RESULTS / "exp7_runs_partial.csv").unlink(missing_ok=True)
    consistency()
    print(f"{len(runs)} runs; errors {int((runs['error'] != '').sum())}")


if __name__ == "__main__":
    consistency() if "--recheck" in sys.argv else main()
