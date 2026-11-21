"""
Experiment 7: score the saved runs against docs/EXPERIMENT7_CRITERIA.md. Runs no simulation.

Each criterion is judged in every cell it applies to. A rule setting passes only if every
criterion holds in every cell. With 15 runs per cell, "at least 95%" means all 15.

Writes results/task3/: exp7_cells.csv (every criterion in every cell), exp7_rule_verdicts.csv,
exp7_before_after.csv, exp7_key_numbers.json, exp7_verdict_map.png, and prints a summary.
Usage: python experiments/task3_analysis.py
"""
import ast
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task3_experiment7 as t3  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = t3.RESULTS
LIMIT_S = 600.0
AT_LEAST, AT_MOST = 0.95, 0.05
ORDER = ["I1", "I2", "I3", "I4", "T1a", "T1b", "T1c", "T1d", "T2a", "T2b", "T2c", "T3a", "T3b", "T3c", "T3d"]
T1, T2, T3 = ["stim_name", "sphincter_scaling"], ["sphincter_scaling"], ["stim_name", "threshold_ml", "sphincter_scaling"]


def code_uses_no_truth():
    """I4: the same test as tests/test_task3_session_guard.py, recorded with the verdict."""
    tree = ast.parse((ROOT / "devices" / "session_guard.py").read_text(encoding="utf8"))
    names = {getattr(n, "id", getattr(n, "attr", getattr(n, "arg", ""))) for n in ast.walk(tree)
             if isinstance(n, (ast.Name, ast.Attribute, ast.arg))}
    bad = ["v_b", "p_d", "true", "truth", "ground", "pressure"]
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    return not imports and not any(b in name.lower() for name in names for b in bad)


def label(keys, level):
    level = level if isinstance(level, tuple) else (level,)
    return ", ".join(f"{k}={v}" for k, v in zip(keys, level))


def judge(rows, rule, test, criterion, keys, score):
    """`score(g)` gives (rate, needed, sense) for one cell, or None if the cell has no such case."""
    out = []
    for level, g in rows.groupby(keys):
        rate, runs = score(g)
        need = AT_MOST if criterion in ("T3a", "T3b") else AT_LEAST
        ok = bool(rate <= need) if criterion in ("T3a", "T3b") else bool(rate >= need)
        out.append({"rule": rule, "test": test, "criterion": criterion, "cell": label(keys, level), "rate": rate,
                    "runs_counted": runs, "required": need, "passed": ok})
    return out


def rate(condition):
    return lambda g: (float(condition(g).mean()), len(g))


def rate_among(applies, condition):
    """The rate among the runs a criterion applies to. No such run counts as a failure to show it."""
    def score(g):
        a = g[applies(g)]
        return (float(condition(a).mean()), len(a)) if len(a) else (0.0, 0)
    return score


def p_values(runs, sessions, keys):
    """P1, P2 and P3 for each cell, from the raw rows."""
    r = runs.groupby(keys).agg(P2=("overflow_despite_alert", lambda x: 1 - x.mean()))
    s = sessions.groupby(keys).agg(P1=("voided_ge_50pct", "mean"), P3=("ceiling_exceeded_gt5", lambda x: 1 - x.mean()))
    t = r.join(s)
    return pd.DataFrame({"P1": t.P1 >= 0.80, "P2": t.P2 >= 0.95, "P3": t.P3 >= 0.95})


def old_t3():
    """Experiment 3b, cut down to the settings T3 is judged against."""
    exact = {"float_precision": "round_trip"}
    def cut(t):
        return t[t.stim_name.isin(t3.EMPTIES) & t.threshold_ml.isin(t3.THRESHOLDS_T3) & (t.max_duration_s == 60)
                 & (t.pressure_ceiling_cmH2O == 55)]
    return (cut(pd.read_csv(ROOT / "results" / "task2" / "exp3b_runs.csv", **exact)),
            cut(pd.read_csv(ROOT / "results" / "task2" / "exp3b_sessions.csv", **exact)))


def untouched_runs_match(new_runs, old_runs, new_sessions, old_sessions, keys):
    """T3d: every run with no catheter alert must equal its Experiment 3b twin, sessions included."""
    skip = set(keys) | {"group", "runtime_s", "error", "reference", "phys_seed", "test", "rule"}
    rows = new_runs[new_runs.catheter_reason.fillna("") == ""]
    if rows.empty:
        return 1.0, 0
    key = keys + ["phys_seed"]
    a = rows.merge(old_runs[key], on=key).sort_values(key).reset_index(drop=True)
    b = old_runs.merge(rows[key], on=key).sort_values(key).reset_index(drop=True)
    cols = [c for c in old_runs.columns if c in a.columns and c not in skip]
    if len(a) != len(rows) or not t3.same_values(a, b, cols):
        return 0.0, len(rows)
    order = key + ["start_h"]
    s_new = new_sessions.merge(rows[key], on=key).sort_values(order).reset_index(drop=True)
    s_old = old_sessions.merge(rows[key], on=key).sort_values(order).reset_index(drop=True)
    cols = [c for c in old_sessions.columns if c in s_new.columns and c not in skip]
    return (1.0 if len(s_new) == len(s_old) and t3.same_values(s_new, s_old, cols) else 0.0), len(rows)


def score_rule(rule, runs, sessions, old_runs, old_sessions, old_p):
    r = runs[runs.rule == rule]
    z = sessions[sessions.rule == rule]
    a, b, c = r[r.test == "T1"], r[r.test == "T2"], r[r.test == "T3"]
    cap = int(r.session_cap.iloc[0])
    all_keys = ["test"] + ["stim_name", "threshold_ml", "sphincter_scaling"]
    out = []
    inv = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
    out += judge(r, rule, "all", "I1", all_keys, rate(lambda g: g[inv].all(axis=1)))
    out += judge(r, rule, "all", "I2", all_keys, rate(lambda g: g["I2_nothing_offered_after_latch"]))
    out += judge(r, rule, "all", "I3", all_keys, rate(lambda g: g["I3_never_silent"]))
    out.append({"rule": rule, "test": "all", "criterion": "I4", "cell": "code", "rate": float(code_uses_no_truth()),
                "runs_counted": 0, "required": 1.0, "passed": code_uses_no_truth()})

    out += judge(a, rule, "T1", "T1a", T1, rate(lambda g: g.fault_alert))
    out += judge(a, rule, "T1", "T1b", T1, rate_among(lambda g: g.sessions_after_fault_onset >= 1,
                                                      lambda g: g.alert_s_after_first_session_after_onset <= LIMIT_S))
    out += judge(a, rule, "T1", "T1c", T1, rate(lambda g: g.sessions_after_fault_onset <= 1))
    for row in judge(a, rule, "T1", "T1d", T1, rate(lambda g: g.n_sessions <= cap)):
        out.append({**row, "required": 1.0, "passed": row["rate"] == 1.0})     # "in all runs"

    out += judge(b, rule, "T2", "T2a", T2, rate_among(lambda g: g.first_failed_session >= 0,
                                                      lambda g: g.alert_s_after_first_failed <= LIMIT_S))
    out += judge(b, rule, "T2", "T2b", T2, rate(lambda g: g.fault_alert_before_first_leak))
    out += judge(b, rule, "T2", "T2c", T2, rate(lambda g: g.sessions_after_first_failed <= 1))

    out += judge(c, rule, "T3", "T3a", T3, rate(lambda g: g.false_alarm))
    out += judge(c, rule, "T3", "T3b", T3, rate(lambda g: g.session_limit_alert))
    new_p = p_values(c, z[z.test == "T3"], T3)
    for level, row in new_p.iterrows():
        same = bool((row == old_p.loc[level]).all())
        out.append({"rule": rule, "test": "T3", "criterion": "T3c", "cell": label(T3, level), "rate": float(same),
                    "runs_counted": int(len(c.groupby(T3).get_group(level))), "required": 1.0, "passed": same})
    for level, g in c.groupby(T3):
        where = dict(zip(T3, level))
        def pick(t):
            return t[(t.stim_name == where["stim_name"]) & (t.threshold_ml == where["threshold_ml"])
                     & (t.sphincter_scaling == where["sphincter_scaling"])]
        match, n = untouched_runs_match(g, pick(old_runs), pick(z[z.test == "T3"]), pick(old_sessions), T3)
        out.append({"rule": rule, "test": "T3", "criterion": "T3d", "cell": label(T3, level), "rate": match,
                    "runs_counted": n, "required": 1.0, "passed": match == 1.0})
    return out


def before_after(runs, old_runs):
    def block(g):
        latency = g.alert_s_after_first_session_after_onset.where(g.test == "T1", g.alert_s_after_first_failed)
        return pd.Series({
            "runs": len(g), "sessions_per_run": g.n_sessions.mean(), "sessions_per_run_max": g.n_sessions.max(),
            "sessions_after_fault_per_run": g.sessions_after_fault_onset.mean() if "sessions_after_fault_onset" in g else np.nan,
            "sessions_on_bladder_below_100ml_per_run": g.sessions_below_100ml.mean() if "sessions_below_100ml" in g else np.nan,
            "runs_with_fault_alert": int(g.fault_alert.sum()) if "fault_alert" in g else 0,
            "runs_with_session_limit_alert": int(g.session_limit_alert.sum()) if "session_limit_alert" in g else 0,
            "alert_s_after_session_median": latency.median(),
            "true_volume_at_alert_ml_median": g.true_volume_at_catheter_alert_ml.median() if "true_volume_at_catheter_alert_ml" in g else np.nan,
            "leaked_ml_mean": g.leaked_outside_sessions_ml.mean(), "leaked_ml_max": g.leaked_outside_sessions_ml.max(),
            "max_volume_ml_mean": g.max_volume_ml.mean(), "max_volume_ml_max": g.max_volume_ml.max(),
            "peak_true_p_D_cmH2O": g.max_true_p_D_during_stim_cmH2O.max(), "median_residual_ml": g.median_residual_ml.median()})
    keys = ["test", "stim_name", "threshold_ml", "sphincter_scaling", "rule"]
    table = runs.groupby(keys, dropna=False).apply(block).reset_index()
    old = old_runs.assign(test="T3", rule="off (Experiment 3b)", alert_s_after_first_session_after_onset=np.nan,
                          alert_s_after_first_failed=np.nan)
    return pd.concat([table, old.groupby(keys).apply(block).reset_index()]).sort_values(keys).reset_index(drop=True)


def key_numbers(runs, sessions, cells, verdicts):
    on = runs[runs.rule != "off"]
    off = runs[runs.rule == "off"]
    t3rows = on[on.test == "T3"]
    return {"runs": len(runs), "error_rows": int(runs.error.notna().sum()), "sessions": len(sessions),
            "rule_settings": len(verdicts), "rule_settings_passing": int(verdicts.verdict_pass.sum()),
            "T1_off_sessions_per_run": float(off[off.test == "T1"].n_sessions.mean()),
            "T2_off_sessions_per_run": float(off[off.test == "T2"].n_sessions.mean()),
            "T1_on_sessions_per_run_max": int(on[on.test == "T1"].n_sessions.max()),
            "T2_on_sessions_per_run_max": int(on[on.test == "T2"].n_sessions.max()),
            "T3_false_alarm_runs": int(t3rows.false_alarm.sum()), "T3_session_limit_runs": int(t3rows.session_limit_alert.sum()),
            "T3_runs_with_any_catheter_alert": int((t3rows.catheter_reason.fillna("") != "").sum()),
            "T3_fault_alerts_after_partial_or_failed": int((t3rows.fault_alert & ~t3rows.false_alarm).sum()),
            "timeouts_all_runs": int((runs.catheter_reason == "check_timed_out").sum()),
            "I3_failures": int((~on["I3_never_silent"].astype(bool)).sum()),
            "I2_failures": int((~on["I2_nothing_offered_after_latch"].astype(bool)).sum()),
            "peak_true_p_D_on": float(on.max_true_p_D_during_stim_cmH2O.max()),
            "peak_true_p_D_off": float(off.max_true_p_D_during_stim_cmH2O.max())}


def plot_map(verdicts, path):
    grid = verdicts.set_index("rule")[ORDER]
    fig, ax = plt.subplots(figsize=(12, 4.2))
    fails = (grid.to_numpy() > 0).astype(float)
    ax.imshow(fails, cmap=matplotlib.colors.ListedColormap(["#eef1f5", "#1f4e8c"]), vmin=0, vmax=1, aspect="auto")
    for i in range(grid.shape[0]):
        for j in range(grid.shape[1]):
            n = int(grid.iat[i, j])
            ax.text(j, i, "pass" if n == 0 else f"{n} fail", ha="center", va="center", fontsize=8,
                    color="white" if n else "#333333")
    ax.set_xticks(range(len(ORDER)), ORDER, fontsize=9)
    ax.set_yticks(range(grid.shape[0]), [r.replace("cap", "cap ").replace("_drop", ", drop ") for r in grid.index], fontsize=9)
    ax.set_xticks(np.arange(-.5, len(ORDER)), minor=True)
    ax.set_yticks(np.arange(-.5, grid.shape[0]), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="both", length=0)
    for side in ax.spines.values():
        side.set_visible(False)
    ax.set_title("Experiment 7: cells failing each frozen criterion, by rule setting (model predictions; T3 is POST-HOC, OPTIMISTIC)",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    runs = pd.read_csv(RESULTS / "exp7_runs.csv", float_precision="round_trip")
    sessions = pd.read_csv(RESULTS / "exp7_sessions.csv", float_precision="round_trip")
    old_runs, old_sessions = old_t3()
    old_p = p_values(old_runs, old_sessions, T3)
    rules = [r for r in runs.rule.unique() if r != "off"]
    cells = pd.DataFrame([x for rule in rules for x in score_rule(rule, runs, sessions, old_runs, old_sessions, old_p)])
    cells.to_csv(RESULTS / "exp7_cells.csv", index=False)
    fails = cells[~cells.passed].groupby(["rule", "criterion"]).size().unstack(fill_value=0).reindex(index=rules, columns=ORDER, fill_value=0)
    verdicts = fails.reset_index()
    verdicts["verdict_pass"] = (fails.sum(axis=1) == 0).to_numpy()
    verdicts.to_csv(RESULTS / "exp7_rule_verdicts.csv", index=False)
    table = before_after(runs, old_runs)
    table.to_csv(RESULTS / "exp7_before_after.csv", index=False)
    keys = key_numbers(runs, sessions, cells, verdicts)
    with open(RESULTS / "exp7_key_numbers.json", "w") as f:
        json.dump(keys, f, indent=2)
    plot_map(verdicts, RESULTS / "exp7_verdict_map.png")

    pd.set_option("display.width", 230, "display.max_columns", 40, "display.max_rows", 300, "display.max_colwidth", 70)
    print(json.dumps(keys, indent=1))
    print(verdicts.to_string(index=False))
    print(cells[~cells.passed].drop(columns=["required", "passed"]).round(3).to_string(index=False))
    show = ["test", "stim_name", "threshold_ml", "sphincter_scaling", "rule", "sessions_per_run", "sessions_per_run_max",
            "sessions_after_fault_per_run", "runs_with_fault_alert", "runs_with_session_limit_alert",
            "alert_s_after_session_median", "true_volume_at_alert_ml_median", "leaked_ml_max", "max_volume_ml_max",
            "peak_true_p_D_cmH2O", "median_residual_ml"]
    print(table[show].round(1).to_string(index=False))


if __name__ == "__main__":
    main()
