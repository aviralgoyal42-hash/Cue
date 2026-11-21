"""
Figure audit (7 Nov): recompute quoted figures straight from the saved result files.
READ-ONLY: no simulation, no parameter changes. Writes results/figure_audit/.

  (2) leftover (residual) volume after sessions in settings that empty
  (3) 636 closed-loop runs; best alert threshold vs the 14 non-ideal sensor scenarios;
      75 of 108 settings in Experiment 3b; stuck-high sessions 12 -> 1 in Experiment 7
  (4) bladder pressure against volume with no stimulation, and whether storage pressure
      reaches the 55 cmH2O ceiling

Residual volume is the TRUE volume 120 s after a session ends (docs/STAGE5_EXPERIMENT3_4_CRITERIA.md),
so it includes about 2 mL of new urine made during those 120 s.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
OUT = R / "figure_audit"


def spread(x):
    x = pd.Series(x).dropna()
    return {"n": int(len(x)), "median": float(x.median()), "min": float(x.min()), "max": float(x.max()),
            "share_le_3ml": float((x <= 3.0).mean())}


def part2_residuals():
    out = {}
    # Stage 5 map: one fixed 60 or 120 s session from 450 mL, no closed loop
    m = pd.read_csv(R / "stage5" / "stimulation_map.csv")
    out["stage5_map_complete"] = spread(m[m.emptying == "complete"].residual_ml)
    out["stage5_map_partial"] = spread(m[m.emptying == "partial"].residual_ml)
    # Closed-loop experiments: sessions inside settings that pass all frozen criteria ("work")
    for name, summ, sess in [("exp3", "stage6/exp3_settings_summary.csv", "stage6/exp3_sessions.csv"),
                             ("exp3b", "task2/exp3b_settings_summary.csv", "task2/exp3b_sessions.csv")]:
        s = pd.read_csv(R / summ)
        x = pd.read_csv(R / sess)
        keys = ["group", "stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s",
                "threshold_ml", "max_duration_s", "sphincter_scaling"]
        works = s[s.full_loop_works][keys]
        xs = x.merge(works, on=keys)
        out[f"{name}_working_settings"] = int(len(works))
        out[f"{name}_sessions_in_working_settings"] = spread(xs.residual_ml)
        out[f"{name}_setting_median_residual"] = spread(s[s.full_loop_works].median_residual_ml)
        out[f"{name}_sessions_that_emptied_any_setting"] = spread(x[x.emptying != "none"].residual_ml)
        out[f"{name}_complete_sessions"] = spread(x[x.emptying == "complete"].residual_ml)
        out[f"{name}_partial_sessions"] = spread(x[x.emptying == "partial"].residual_ml)
    # Experiment 7, T3 (normal use, no fault), the one passing rule
    s7 = pd.read_csv(R / "task3" / "exp7_sessions.csv")
    t3 = s7[(s7.test == "T3") & (s7.rule == "cap4_drop0.40")]
    out["exp7_T3_cap4_drop0.40_emptied_sessions"] = spread(t3[t3.emptying != "none"].residual_ml)
    return out


def part3_figures():
    out = {}
    # 636 closed-loop runs = Experiment 3 + Experiment 4 (3 seeds each)
    e3 = pd.read_csv(R / "stage6" / "exp3_runs.csv")
    e4 = pd.read_csv(R / "stage6" / "exp4_runs.csv")
    inv = ["A2_start_only_after_press_and_alert", "A3_no_start_in_lockout", "A4_sessions_within_max_duration"]
    both = pd.concat([e3, e4])
    out["exp3_runs"], out["exp4_runs"], out["exp3_exp4_runs"] = len(e3), len(e4), len(both)
    out["exp3_exp4_runs_with_error"] = int(both.error.fillna("").astype(str).ne("").sum())
    out["exp3_exp4_runs_all_invariants_hold"] = int(both[inv].all(axis=1).sum())
    others = {"exp3b": "task2/exp3b_runs.csv", "exp7": "task3/exp7_runs.csv"}
    out["other_closed_loop_runs"] = {k: len(pd.read_csv(R / v, usecols=["phys_seed"])) for k, v in others.items()}

    # Experiment 2 (3 seeds) and 2b (15 seeds): best threshold against the 14 non-ideal scenarios
    for tag, folder in [("exp2", "stage4"), ("exp2b", "stage4b")]:
        s = pd.read_csv(R / folder / "exp2_summary.csv")
        s = s[s.scenario != "ideal"]
        counts = s.groupby(["sphincter_scaling", "threshold_ml"]).agg(
            scenarios=("scenario", "nunique"), passing=("cue_works_C1_C2_C3", "sum"),
            runs_per_cell=("n_runs", "first")).reset_index()
        counts.to_csv(OUT / f"{tag}_passes_by_threshold.csv", index=False)
        best = {}
        for scaling, g in counts.groupby("sphincter_scaling"):
            top = g.passing.max()
            best[f"x{scaling}"] = {"best_passing": int(top), "of": int(g.scenarios.iloc[0]),
                                   "at_thresholds_ml": g[g.passing == top].threshold_ml.tolist(),
                                   "runs_per_cell": int(g.runs_per_cell.iloc[0])}
            at = s[(s.sphincter_scaling == scaling) & (s.threshold_ml.isin(best[f"x{scaling}"]["at_thresholds_ml"]))]
            best[f"x{scaling}"]["failing_at_best"] = {
                f"{t:.0f}": sorted(at[(at.threshold_ml == t) & ~at.cue_works_C1_C2_C3].scenario)
                for t in best[f"x{scaling}"]["at_thresholds_ml"]}
        out[tag] = best
        out[f"{tag}_scenarios"] = sorted(s.scenario.unique())

    # Experiment 3b: 75 of 108
    s = pd.read_csv(R / "task2" / "exp3b_settings_summary.csv")
    recomputed = s.A2_A3_A4_all_hold & s.P1_pass & s.P2_pass & s.P3_pass
    out["exp3b_settings"], out["exp3b_working"] = len(s), int(s.full_loop_works.sum())
    out["exp3b_working_recomputed_from_flags"] = int(recomputed.sum())
    out["exp3b_flag_disagreements"] = int((recomputed != s.full_loop_works).sum())

    # Experiment 7: stuck-high estimate is test T1; sessions per run with the rule off and on
    r7 = pd.read_csv(R / "task3" / "exp7_runs.csv")
    t1 = r7[r7.test == "T1"]
    off, on = t1[t1.rule == "off"], t1[t1.rule != "off"]
    out["exp7_T1_sensor"] = sorted(t1.sensor_name.unique())
    out["exp7_T1_rule_off"] = {"runs": len(off), "sessions_min": int(off.n_sessions.min()),
                               "sessions_max": int(off.n_sessions.max()), "sessions_mean": float(off.n_sessions.mean())}
    out["exp7_T1_rule_on"] = {"runs": len(on), "sessions_min": int(on.n_sessions.min()),
                              "sessions_max": int(on.n_sessions.max()), "sessions_mean": float(on.n_sessions.mean())}
    return out


def part4_pressure():
    out = {}
    curves = {}
    for tag, f in [("sci_x1.0", "trace_ceiling_1000_1Hz.csv"), ("sci_x0.9", "trace_somatic_a_x0.9_1Hz.csv"),
                   ("healthy_control", "trace_control_1Hz.csv")]:
        d = pd.read_csv(R / "stage3" / f, usecols=["t", "V_B_ml", "p_D_cmH2O", "Q_ml_s"])
        d = d[d.t <= 12 * 3600]                       # the 12 h day used in every closed-loop run
        if tag != "healthy_control":
            filling = d
        else:                                         # healthy: stop at the first void
            first_void = d.index[d.Q_ml_s > 0.5]
            filling = d.loc[: first_void[0] - 1] if len(first_void) else d
        bins = np.arange(0, 1050, 50)
        b = filling.groupby(pd.cut(filling.V_B_ml, bins, right=False), observed=True).p_D_cmH2O.agg(["median", "max"])
        b.index = [f"{int(i.left)}-{int(i.right)}" for i in b.index]
        curves[tag] = b
        peak = filling.loc[filling.p_D_cmH2O.idxmax()]
        first = lambda lim: filling[filling.p_D_cmH2O >= lim]
        out[tag] = {
            "max_volume_ml": float(filling.V_B_ml.max()), "peak_p_D": float(peak.p_D_cmH2O),
            "volume_at_peak_ml": float(peak.V_B_ml), "time_at_peak_h": float(peak.t / 3600),
            "p_D_at_max_volume": float(filling.loc[filling.V_B_ml.idxmax()].p_D_cmH2O),
            **{f"first_volume_p_ge_{lim}_ml": (float(first(lim).V_B_ml.iloc[0]) if len(first(lim)) else None)
               for lim in (20, 40, 55)},
            "seconds_p_ge_55": int((filling.p_D_cmH2O >= 55).sum()),
            "p_D_at_400ml": float(filling.iloc[(filling.V_B_ml - 400).abs().argmin()].p_D_cmH2O),
            "p_D_at_450ml": float(filling.iloc[(filling.V_B_ml - 450).abs().argmin()].p_D_cmH2O),
            "outflow_ml": float(filling.Q_ml_s.sum()),          # 1 Hz samples, so sum = mL
        }
    pd.concat(curves, axis=1).to_csv(OUT / "pressure_vs_volume_no_stimulation.csv")
    st3 = pd.read_csv(R / "stage3" / "summary_all_cases.csv")
    sci = st3[st3.sci.astype(str) == "True"]
    out["stage3_sci_cases"] = len(sci)
    out["stage3_sci_cases_max_p_ge_55"] = int((sci.max_p_D_cmH2O >= 55).sum())
    out["stage3_sci_max_p_range"] = [float(sci.max_p_D_cmH2O.min()), float(sci.max_p_D_cmH2O.max())]
    # Closed-loop runs: storage pressure outside sessions (and outside the 120 s after each)
    col = "max_true_p_D_outside_sessions_cmH2O"
    for tag, f in [("exp3", "stage6/exp3_runs.csv"), ("exp4", "stage6/exp4_runs.csv"),
                   ("exp3b", "task2/exp3b_runs.csv"), ("exp7", "task3/exp7_runs.csv")]:
        r = pd.read_csv(R / f)
        hi = r[r[col] >= 55]
        out[f"{tag}_storage_p"] = {"runs": len(r), "max": float(r[col].max()), "median": float(r[col].median()),
                                   "runs_ge_55": int(len(hi)), "runs_ge_40": int((r[col] >= 40).sum()),
                                   "runs_ge_55_without_coactivation": int(hi.stim_name.str.contains("_s0.0_").sum()),
                                   "runs_ge_55_min_max_volume_ml": float(hi.max_volume_ml.min()) if len(hi) else None,
                                   "runs_ge_55_by_ceiling": {f"{k:.0f}": int(v) for k, v in
                                                             hi.pressure_ceiling_cmH2O.value_counts().sort_index().items()}}
    return out, curves


def main():
    OUT.mkdir(exist_ok=True)
    key = {"part2_residual_ml": part2_residuals(), "part3": part3_figures()}
    p4, curves = part4_pressure()
    key["part4_pressure"] = p4
    (OUT / "key_numbers.json").write_text(json.dumps(key, indent=2, default=float))
    print(json.dumps(key, indent=2, default=float))
    print("\nPressure (cmH2O) against volume, no stimulation, first 12 h:")
    print(pd.concat(curves, axis=1).round(1).to_string())


if __name__ == "__main__":
    main()
