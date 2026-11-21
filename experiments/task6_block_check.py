"""
TASK 6, Part A and B.4: the sphincter block in the closed loop, and a closed-loop probe of the
misalignment monitor. Plan frozen in docs/TASK6_PLAN.md before anything was run.
MODEL ONLY: the block is a normalised model drive, not a nerve-block setting. Results are model
predictions, not evidence for a device. The settings come from Experiment 3b, so every result
is POST-HOC and OPTIMISTIC.

Groups (90 runs, seeds 42, 1, 2)
  A-check    block 0.8 and 1.0 (scope burst), and block 1.0 that fails at 0 s, on the s0.5
             co-activation pattern. Must equal the Task 5 rows at levels 0.1, 0.0 and 0.5.
  A-fault    block 1.0 that fails 20 s into the session.            Descriptive.
  A-session  block 0.8 and 1.0 acting for the whole session.        Descriptive.
  B-probe    misalignment monitor in the closed loop.               Descriptive.

Usage (PowerShell, from the project folder):
  python -W ignore experiments\\task6_block_check.py
Outputs go to results/task6/ only.
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config                                   # noqa: E402
import sci_test_rig as rig_mod                  # noqa: E402
from evaluation import closed_loop_metrics as cm  # noqa: E402
import stage6_experiments3_4 as s6              # noqa: E402  (old scoring, used unchanged)
import task5_sphincter_levels as t5             # noqa: E402  (Task 5 subset and helpers, used unchanged)

RESULTS = ROOT / "results" / "task6"
TASK5 = ROOT / "results" / "task5"              # read only

# ---- Fixed before running (docs/TASK6_PLAN.md). ASSUMED. Never tuned after results are seen.
SEEDS = [42, 1, 2]
BLOCKS = (0.8, 1.0)
FAULT_AT_S = 20.0
COACTIVATION = 0.5                              # the base pattern is always e{d}_s0.5_5on5off
PROBE_PATTERN = "e0.6_s0.0_5on5off"
MONITOR = {"window_n": 15, "k_noise": 3.5, "k_noise_after_dropout": 2.0, "min_drop_fraction": 0.10,
           "min_ml": 100.0, "noise_n": 120, "noise_floor": 0.02, "dropout_slots": 20,
           "dropout_baseline_slots": 120, "dropout_chance": 1e-4, "dropout_floor": 0.02, "compensate": True}
DT, POST = s6.DT, s6.POST
EXACT = t5.EXACT


def block_pattern(detrusor, block, scope="burst", fails_at_s=None):
    """The s0.5 co-activation pattern plus a sphincter block. Returns (name, values, Task 5 twin).
    The twin is the Task 5 pattern that a burst-scope block must reproduce exactly (else None)."""
    base = config.STIM_PATTERNS.value[f"e{detrusor}_s{COACTIVATION}_5on5off"]
    stim = {**base, "sphincter_block": float(block), "block_scope": scope}
    name = f"e{detrusor}_s{COACTIVATION}_5on5off_block{block:.1f}_{scope}"
    twin = None
    if fails_at_s is not None:
        stim["block_fails_at_s"] = float(fails_at_s)
        name += f"_fail{fails_at_s:.0f}s"
    if scope == "burst" and fails_at_s is None:
        twin = t5.pattern(detrusor, round(COACTIVATION * (1 - block), 12))[0]
    if scope == "burst" and fails_at_s == 0:
        twin = t5.pattern(detrusor, COACTIVATION)[0]
    return name, stim, twin


def cases():
    out = []

    def add(group, name, stim, twin, scaling, **extra):
        for seed in SEEDS:
            out.append({"group": group, "stim_name": name, "stim": stim, "task5_twin": twin or "",
                        "controller": {"pressure_ceiling_cmH2O": t5.CEILING_CMH2O},
                        "ultrasound_interval_during_stim_s": t5.US_INTERVAL_S, "sphincter_scaling": scaling,
                        "phys_seed": seed, "sensor_seed": seed, "user_seed": seed, "pressure_seed": seed, **extra})
    for d in t5.DETRUSOR:
        for scaling in t5.SCALINGS:
            for b in BLOCKS:
                add("A-check", *block_pattern(d, b), scaling)
            add("A-check", *block_pattern(d, 1.0, fails_at_s=0.0), scaling)
            add("A-fault", *block_pattern(d, 1.0, fails_at_s=FAULT_AT_S), scaling)
            for b in BLOCKS:
                add("A-session", *block_pattern(d, b, scope="session"), scaling)
    sensors = config.SENSOR_SCENARIOS.value
    for scaling in t5.SCALINGS:
        stim = config.STIM_PATTERNS.value[PROBE_PATTERN]
        for label, sensor, device in [("anchor_monitor_on", "anchor_11pct", {"misalignment_monitor": MONITOR}),
                                      ("misaligned_monitor_off", "misaligned_at_4h", {}),
                                      ("misaligned_monitor_on", "misaligned_at_4h", {"misalignment_monitor": MONITOR})]:
            add("B-probe", PROBE_PATTERN, stim, None, scaling, probe=label, sensor_name=sensor,
                sensor=sensors[sensor], device=device)
    return out


def run_one(spec):
    """Rows built as in Task 5 (so they can be compared with it exactly), plus the patch checks."""
    meta = {k: spec[k] for k in ("group", "stim_name", "task5_twin", "sphincter_scaling", "phys_seed")}
    meta["probe"] = spec.get("probe", "")
    case = rig_mod.default_case(**{k: v for k, v in spec.items() if k not in ("group", "task5_twin", "probe")})
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
        timing = t5.emptying_times(data, rig)
    except Exception as exc:          # logged as a result, not hidden
        return {**meta, "error": repr(exc)}, [], []
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
    checks = [{**meta, "flag_h": c["t_s"] / 3600, "rule": c["rule"], "ratio": c["ratio"]}
              for c in rig.device.patch_checks]
    row["n_patch_checks"] = len(checks)
    return row, [{**meta, **x, **tm} for x, tm in zip(sessions, timing)], checks


def compare_with_task5(runs, sessions):
    """File-to-file comparison (E58) of the A-check rows with their Task 5 twins, by value."""
    old_r, old_s = pd.read_csv(TASK5 / "task5_runs.csv", **EXACT), pd.read_csv(TASK5 / "task5_sessions.csv", **EXACT)
    mine_r, mine_s = runs[runs.group == "A-check"], sessions[sessions.group == "A-check"]
    skip = ("runtime_s", "group", "stim_name", "reference")
    run_keys = ["stim_name", "sphincter_scaling", "phys_seed"]
    wanted = mine_r.assign(stim_name=mine_r["task5_twin"])[run_keys].drop_duplicates()   # the Task 5 twins
    out = {}
    for label, a, b, extra in [("runs", mine_r, old_r, []), ("sessions", mine_s, old_s, ["start_h"])]:
        a = a.assign(stim_name=a["task5_twin"])                       # compare each row with its twin
        b = b.merge(wanted, on=run_keys)
        keys = run_keys + extra
        cols = [c for c in b.columns if c in a.columns and c not in skip]
        a2, b2 = a.sort_values(keys).reset_index(drop=True), b.sort_values(keys).reset_index(drop=True)
        same_keys = len(a2) == len(b2) and t5.same_values(a2[keys], b2[keys]) == {}
        diff = t5.same_values(a2[cols], b2[cols]) if same_keys else {"row keys differ": 1}
        out[label] = {"rows_task6": len(a2), "rows_task5": len(b2), "columns_compared": len(cols),
                      "differences": diff, "identical": bool(same_keys and not diff)}
    out["passed"] = bool(out["runs"]["identical"] and out["sessions"]["identical"] and out["runs"]["rows_task6"] == 36)
    return out


def main():
    config.validate()
    RESULTS.mkdir(parents=True, exist_ok=True)
    todo = cases()
    print(f"task6 closed loop: {len(todo)} runs ...", flush=True)
    rows, sessions, checks = [], [], []
    with ProcessPoolExecutor() as pool:
        for i, (row, sess, chk) in enumerate(pool.map(run_one, todo, chunksize=1), 1):
            rows.append(row)
            sessions += sess
            checks += chk
            if i % 10 == 0:
                print(f"  {i}/{len(todo)} done  {time.strftime('%H:%M:%S')}", flush=True)
    runs = pd.DataFrame(rows)
    runs["error"] = runs["error"].fillna("")
    t5.save(runs, RESULTS / "block_runs.csv")
    t5.save(sessions, RESULTS / "block_sessions.csv")
    t5.save(checks if checks else [{"group": "", "note": "no patch checks"}], RESULTS / "probe_patch_checks.csv")
    pd.DataFrame(config.as_table()).to_csv(RESULTS / "parameters_used.csv", index=False)
    pd.DataFrame([{"name": c["stim_name"], "group": c["group"], **c["stim"]} for c in todo]).drop_duplicates() \
        .to_csv(RESULTS / "block_patterns_used.csv", index=False)

    runs = pd.read_csv(RESULTS / "block_runs.csv", **EXACT)            # file to file (E58)
    sess = pd.read_csv(RESULTS / "block_sessions.csv", **EXACT)
    result = compare_with_task5(runs, sess)
    result["errors"] = int(runs["error"].fillna("").astype(str).ne("").sum())
    inv = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
    result["invariants_hold_in_all_runs"] = bool(result["errors"] == 0 and runs[inv].all().all())
    (RESULTS / "block_check.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))

    # Descriptive tables: the Experiment 3 measures, with NO pass or "works" verdict (3 seeds).
    runs["group"] = runs["group"] + runs["probe"].fillna("").map(lambda p: f":{p}" if p else "")
    sess["group"] = sess["group"] + sess["probe"].fillna("").map(lambda p: f":{p}" if p else "")
    table = s6.summarise_exp3(runs, sess)
    table = table.drop(columns=[c for c in table.columns if c.endswith("_pass") or c == "full_loop_works"])
    table.to_csv(RESULTS / "block_descriptive_summary.csv", index=False)
    print(table.round(3).to_string(index=False))
    print("A-CHECK PASSED" if result["passed"] else "A-CHECK FAILED: Task 5 does not carry over; log it")


if __name__ == "__main__":
    main()
