"""
Final experiment: Experiments 3 and 4 rerun on the same grid and criteria with 15 inflow seeds per
cell. Plan frozen in docs/EXPERIMENT3_4_15SEED_PLAN.md. The grids and the run itself come from
experiments/stage6_experiments3_4.py, so only the seed list differs. config.py is not changed.

Writes results/task4/: exp3_*.csv, exp4_*.csv, traces/, parameters_used.csv, reproduction.json and
old_results_manifest.csv. Old result folders are read, never written.
Scoring and the comparison with the old verdicts are in experiments/task4_analysis.py.
Usage: python experiments/task4_rerun_exp3_4.py [--recheck]
A stopped sweep continues from its saved partial files when started again.
"""
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage6_experiments3_4 as s6  # noqa: E402
from task3_experiment7 import same_values  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "task4"
OLD = ROOT / "results" / "stage6"
SEEDS = [42] + list(range(1, 15))
OLD_SEEDS = [42, 1, 2]
KEYS = {"exp3": ["group", "stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s", "threshold_ml",
                 "max_duration_s", "sphincter_scaling", "phys_seed"],
        "exp4": ["reference", "group", "sphincter_scaling", "phys_seed"]}
SUMMARY = {"exp3": (s6.summarise_exp3, "exp3_settings_summary.csv"), "exp4": (s6.summarise_exp4, "exp4_fault_summary.csv")}
EXACT = {"float_precision": "round_trip"}


def cases():
    """The old grids with the new seed list, built by the old functions."""
    saved = s6.SEEDS
    s6.SEEDS = SEEDS
    try:
        return {"exp3": s6.exp3_cases(), "exp4": s6.exp4_cases()}
    finally:
        s6.SEEDS = saved


def run_one(spec):
    """One old-style run, with its optional trace sent to the new folder."""
    s6.RESULTS = RESULTS
    return s6.run_one(spec)


def save(table, path):
    """Write then rename, so a crash during a save cannot leave a half-written file."""
    temp = path.with_suffix(".tmp")
    pd.DataFrame(table).to_csv(temp, index=False)
    temp.replace(path)


def sweep(label, todo):
    run_file, session_file = RESULTS / f"{label}_runs_partial.csv", RESULTS / f"{label}_sessions_partial.csv"
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
                print(f"  {i}/{len(todo)} done", flush=True)
                save(rows, run_file)
                save(sessions, session_file)
    runs, session_table = pd.DataFrame(rows), pd.DataFrame(sessions)
    runs["error"] = runs["error"].fillna("")
    save(runs, RESULTS / f"{label}_runs.csv")
    save(session_table, RESULTS / f"{label}_sessions.csv")
    summarise, name = SUMMARY[label]
    summarise(runs, session_table).to_csv(RESULTS / name, index=False)
    run_file.unlink(missing_ok=True)
    session_file.unlink(missing_ok=True)
    print(f"{label}: {len(runs)} runs; errors {int((runs['error'] != '').sum())}", flush=True)


def reproduction():
    """Seeds 42, 1 and 2 must match the old files exactly, file to file (errors E58 and E73)."""
    out = {}
    for label, keys in KEYS.items():
        for kind in ["runs", "sessions"]:
            new = pd.read_csv(RESULTS / f"{label}_{kind}.csv", **EXACT)
            new = new[new.phys_seed.isin(OLD_SEEDS)]
            old = pd.read_csv(OLD / f"{label}_{kind}.csv", **EXACT)
            order = keys + (["start_h"] if kind == "sessions" else [])
            a = old.sort_values(order).reset_index(drop=True)
            b = new.sort_values(order).reset_index(drop=True)
            cols = [c for c in a.columns if c in b.columns and c != "runtime_s"]
            out[f"{label}_{kind}"] = {"rows_old": len(a), "rows_new": len(b), "columns_compared": len(cols),
                                      "columns_only_in_old": [c for c in a.columns if c not in b.columns],
                                      "identical": len(a) == len(b) and same_values(a, b, cols)}
    out["reproduces"] = all(v["identical"] and v["rows_old"] > 0 and not v["columns_only_in_old"] for v in out.values())
    with open(RESULTS / "reproduction.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out), flush=True)
    return out


def old_result_files():
    """Every result file from earlier work. results/doc_number_check.csv is refreshed by design."""
    top = ROOT / "results"
    return sorted(p for p in top.rglob("*") if p.is_file() and RESULTS not in p.parents
                  and p.name != "doc_number_check.csv")


def manifest():
    return pd.DataFrame([{"file": str(p.relative_to(ROOT / "results")).replace("\\", "/"),
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in old_result_files()])


def main():
    s6.config.validate()
    (RESULTS / "traces").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(s6.config.as_table()).to_csv(RESULTS / "parameters_used.csv", index=False)
    before = RESULTS / "old_results_manifest.csv"
    if not before.exists():
        manifest().to_csv(before, index=False)
    for label, todo in cases().items():
        if not (RESULTS / SUMMARY[label][1]).exists():
            sweep(label, todo)
    same = pd.read_csv(before).sort_values("file").reset_index(drop=True).equals(
        manifest().sort_values("file").reset_index(drop=True))
    print(f"old results unchanged: {same}", flush=True)
    with open(RESULTS / "old_results_check.json", "w") as f:
        json.dump({"old_results_unchanged": same, "files": len(pd.read_csv(before))}, f, indent=2)
    reproduction()


if __name__ == "__main__":
    reproduction() if "--recheck" in sys.argv else main()
