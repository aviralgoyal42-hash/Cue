"""
Final consistency check: recompute the numbers quoted in the docs from the result files.
Each check is (description, quoted value, recomputed value, allowed difference).
Writes results/doc_number_check.csv and prints every mismatch.
Usage: python experiments/check_doc_numbers.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"


def checks():
    out = []
    add = lambda name, quoted, value, tol: out.append((name, quoted, float(value), tol))  # noqa: E731

    # Stage 2
    s2 = json.load(open(R / "stage2" / "stage2_report.json"))
    f2, b5 = s2["figure2_run"], s2["baseline_5day"]
    add("S2 max diff vs notebook", 4.9e-7, f2["max_abs_difference_vs_notebook"], 5e-9)
    add("S2 5-day intervoid h", 6.04, b5["metrics"]["mean_intervoid_interval_hrs"], 0.005)
    add("S2 5-day capacity mL", 489.56, b5["metrics"]["mean_peak_capacity_ml"], 0.005)
    add("S2 peak flow", 21.11, f2["summary"]["peak_flow_ml_per_s"], 0.01)
    add("S2 closure pressure", 59.08, f2["summary"]["storage_closure_p_S_cmH2O_at_end"], 0.01)

    # Stage 3
    s3 = pd.read_csv(R / "stage3" / "summary_all_cases.csv").set_index("case")
    add("S3 peak p_D default", 56.57, s3.loc["ceiling_1000", "max_p_D_cmH2O"], 0.01)
    add("S3 final p_D default", 12.24, s3.loc["ceiling_1000", "final_p_D_cmH2O"], 0.01)
    add("S3 discarded default", 957.08, s3.loc["ceiling_1000", "discarded_at_ceiling_ml"], 0.01)
    add("S3 discarded ceiling 500", 1457.08, s3.loc["ceiling_500", "discarded_at_ceiling_ml"], 0.01)
    add("S3 discarded ceiling 1500", 457.08, s3.loc["ceiling_1500", "discarded_at_ceiling_ml"], 0.01)
    add("S3 hold final p_D 1000", 32.96, s3.loc["hold_ceiling_1000", "final_p_D_cmH2O"], 0.01)
    add("S3 weak leak x0.9", 1470.61, s3.loc["somatic_a_x0.9", "leaked_ml"], 0.01)
    add("S3 urine produced", 1957.08, s3.loc["control", "urine_produced_ml"], 0.01)

    # Stage 4b
    c = pd.read_csv(R / "stage4b" / "exp2b_vs_exp2_comparison.csv")
    real = c[c.scenario != "ideal"]
    passes = real.groupby(["sphincter_scaling", "threshold_ml"])["cue_works_C1_C2_C3_15seeds"].sum()
    add("4b passes default 400", 10, passes[(1.0, 400.0)], 0)
    add("4b passes x0.9 400", 10, passes[(0.9, 400.0)], 0)
    add("4b combos passing", 69, c["cue_works_C1_C2_C3_15seeds"].sum(), 0)
    add("4b flips", 7, c["pass_changed"].sum(), 0)
    a = c[(c.scenario == "anchor_11pct") & (c.threshold_ml == 400) & (c.sphincter_scaling == 1.0)].iloc[0]
    add("4b anchor lead 400", 83.9, a["median_lead_min_15seeds"], 0.05)
    add("4b anchor band 400", 0.987, a["POSTHOC_band_350_450_rate"], 0.0005)

    # Stage 5 map
    m = pd.read_csv(R / "stage5" / "stimulation_map.csv")
    one = m[(m.sphincter_scaling == 1.0) & (m.session_s == 60)]["emptying"].value_counts()
    add("S5 60 s complete", 15, one["complete"], 0)
    add("S5 60 s none", 59, one["none"], 0)
    add("S5 peak p_D 60 s", 53.8, m[m.session_s == 60]["peak_p_D_during_cmH2O"].max(), 0.05)
    add("S5 peak p_D all", 57.9, m["peak_p_D_during_cmH2O"].max(), 0.05)
    add("S5 voided fraction max at s>=0.5", 0.0, m[m.sphincter_drive >= 0.5]["voided_fraction"].max(), 0.1)
    add("S5 flow in OFF max", 0.14, m["flow_fraction_burst_off"].max(), 0.005)

    # Experiment 3
    s = pd.read_csv(R / "stage6" / "exp3_settings_summary.csv")
    x = pd.read_csv(R / "stage6" / "exp3_sessions.csv")
    add("E3 settings", 104, len(s), 0)
    add("E3 works", 38, s["full_loop_works"].sum(), 0)
    add("E3 works with co-activation", 0, s[s.stim_name.str.contains("s0.5")]["full_loop_works"].sum(), 0)
    rate = x.groupby("ultrasound_interval_during_stim_s")["cutoff"]
    add("E3 sessions at 60 s", 1236, rate.count()[60.0], 0)
    add("E3 sessions at 5 s", 978, rate.count()[5.0], 0)
    add("E3 volume stops at 60 s", 0, x[(x.ultrasound_interval_during_stim_s == 60) & x.cutoff.str.contains("volume_stop")].shape[0], 0)
    add("E3 volume stops at 5 s", 87, x[(x.ultrasound_interval_during_stim_s == 5) & x.cutoff.str.contains("volume_stop")].shape[0], 0)
    add("E3 max p working", 53.8, s[s.full_loop_works]["max_true_p_D_during_stim_cmH2O"].max(), 0.05)
    add("E3 max p all", 58.5, s["max_true_p_D_during_stim_cmH2O"].max(), 0.05)
    add("E3 residual max working", 97.0, s[s.full_loop_works]["median_residual_ml"].max(), 0.6)

    # Experiment 4
    e = pd.read_csv(R / "stage6" / "exp4_fault_summary.csv")
    r2, r1 = e[e.reference == "e1.0_s0.0_5on5off"], e[e.reference == "e1.0_s0.5_5on5off"]
    get = lambda d, g, s_, col: d[(d.group == g) & (d.sphincter_scaling == s_)][col].iloc[0]  # noqa: E731
    combo = "combo:dead_pressure+stuck_high_estimate"
    add("E4 worst pressure", 64.2, e["max_true_p_D_during_stim_cmH2O"].max(), 0.05)
    add("E4 stuck high sessions", 12, get(r2, "estimate:stuck_high_450ml_from_5h", 1.0, "sessions_per_run"), 0.01)
    add("E4 combo all max duration", 1.0, get(r2, combo, 1.0, "cutoff_max_duration"), 0)
    add("E4 noisy P1", 0.15, get(r2, "pressure:noisy", 1.0, "P1_sessions_voided_ge_50pct"), 0.005)
    add("E4 noisy sessions", 4.33, get(r2, "pressure:noisy", 1.0, "sessions_per_run"), 0.01)
    add("E4 no-press leak x0.9", 412.48, get(r2, "user:no_press", 0.9, "leaked_outside_sessions_ml_mean"), 0.01)
    add("E4 misaligned maxV default", 565.0, get(r2, "sensor:misaligned_at_4h", 1.0, "max_volume_ml_mean"), 0.5)
    add("E4 misaligned leak x0.9", 274.0, get(r2, "sensor:misaligned_at_4h", 0.9, "leaked_outside_sessions_ml_mean"), 0.5)
    add("E4 delayed peak", 56.7, get(r2, "user:delayed", 1.0, "max_true_p_D_during_stim_cmH2O"), 0.05)
    add("E4 invariants hold", 1, e["A2_A3_A4_all_hold"].all(), 0)

    # Extras
    s5 = pd.read_csv(R / "extra" / "exp5_device_params_summary.csv")
    add("E5 misaligned passes", 0, s5[s5.scenario == "misaligned_at_4h"]["cue_works_C1_C2_C3"].sum(), 0)
    add("E5 churn window 1, 30% error", 30.64, s5[(s5.variant == "median_window=1") & (s5.scenario == "mre_30pct")]["mean_alerts_per_run"].mean(), 0.005)
    s6 = pd.read_csv(R / "extra" / "exp6_misalignment_summary.csv")
    d = s6[(s6.drop_fraction == 0.25) & (s6.scenario == "misaligned_at_4h") & (s6.sphincter_scaling == 1.0)].iloc[0]
    add("E6 M1 d=0.25", 0.687, d["flag_within_30min_after_4h_rate"], 0.0005)

    # Task 2, Experiment 3b
    k = json.load(open(R / "task2" / "exp3b_key_numbers.json"))
    r3 = json.load(open(R / "task2" / "exp3b_reproduces_exp3.json"))
    m = pd.read_csv(R / "task2" / "exp3b_main_effects.csv")
    effect = lambda factor, level: m[(m.factor == factor) & (m.level.astype(str) == str(level))].iloc[0]  # noqa: E731
    p = pd.read_csv(R / "task2" / "exp3b_pairs.csv")
    pair = lambda a, x, b, y: p[(p.factor_a == a) & (p.level_a.astype(str) == x) & (p.factor_b == b) & (p.level_b.astype(str) == y)].works.iloc[0]  # noqa: E731
    v = pd.read_csv(R / "task2" / "exp3b_3_vs_15_seeds.csv")
    ceil, dur, thr = "pressure_ceiling_cmH2O", "max_duration_s", "threshold_ml"
    add("E3b reproduces Exp 3", 1, r3["reproduces"], 0)
    add("E3b shared runs", 36, r3["runs"]["rows_exp3b"], 0)
    add("E3b shared sessions", 104, r3["sessions"]["rows_exp3b"], 0)
    add("E3b run columns compared", 31, r3["runs"]["columns_compared"], 0)
    add("E3b session columns compared", 22, r3["sessions"]["columns_compared"], 0)
    add("E3b verdict changes 3 to 15 seeds", 0, (v.full_loop_works_3seeds != v.full_loop_works_15seeds).sum(), 0)
    for quoted, name in [(75, "settings_work"), (5123, "sessions"), (0, "error_rows"), (0, "volume_stops"),
                         (376, "stops_at_55"), (376, "stops_at_55_true_p_below_ceiling"), (1109, "sessions_at_70"),
                         (0, "stops_at_70"), (255, "sessions_over_ceiling_plus5"), (202, "over_and_under_1s"),
                         (53, "over_and_1s_or_longer"), (22, "over_and_ended_by_max_duration"),
                         (42, "works_residual_le_10ml"), (27, "works_residual_gt_50ml"), (6, "leak_settings"),
                         (30, "leak_runs"), (0, "leak_before_alert_runs"), (29, "trap_x1_runs_over_500ml"),
                         (90, "trap_x1_runs"), (0, "trap_x1_leaked_ml")]:
        add("E3b " + name, quoted, k[name], 0)
    for quoted, name, tol in [(56.6, "peak_p_all", 0.05), (53.7, "peak_p_working", 0.05), (487, "under_1s_median_volume_ml", 0.5),
                              (156, "works_max_residual_ml", 0.5), (429.5, "leak_max_ml", 0.05), (491, "leak_settings_max_volume_ml", 0.5),
                              (661, "trap_x1_max_volume_ml", 0.5), (478, "highest_volume_other_settings_ml", 0.5),
                              (0.82, "p2_lower_bound_15_of_15", 0.005)]:
        add("E3b " + name, quoted, k[name], tol)
    for quoted, factor, level in [(7, ceil, 40.0), (34, ceil, 55.0), (34, ceil, 70.0), (23, dur, 30.0), (26, dur, 60.0),
                                  (26, dur, 120.0), (27, thr, 350.0), (28, thr, 400.0), (20, thr, 450.0),
                                  (40, "sphincter_scaling", 0.9), (35, "sphincter_scaling", 1.0),
                                  (39, "stim_name", "e0.6_s0.0_5on5off"), (36, "stim_name", "e1.0_s0.0_5on5off")]:
        add(f"E3b works {factor} {level}", quoted, effect(factor, level)["works"], 0)
    for quoted, a, x, y in [(7, "stim_name", "e0.6_s0.0_5on5off", "40.0"), (16, "stim_name", "e0.6_s0.0_5on5off", "55.0"),
                            (0, "stim_name", "e1.0_s0.0_5on5off", "40.0"), (18, "stim_name", "e1.0_s0.0_5on5off", "70.0"),
                            (3, thr, "350.0", "40.0"), (4, thr, "400.0", "40.0"), (0, thr, "450.0", "40.0"), (10, thr, "450.0", "55.0")]:
        add(f"E3b pair {a} {x} ceiling {y}", quoted, pair(a, x, ceil, y), 0)
    for quoted, level in [(129.7, 30.0), (3.9, 60.0), (3.5, 120.0)]:
        add(f"E3b median residual {level}", quoted, effect(dur, level)["median_residual_ml"], 0.05)

    # Task 3: Experiment 7
    run7 = pd.read_csv(R / "task3" / "exp7_runs.csv")
    ses7 = pd.read_csv(R / "task3" / "exp7_sessions.csv")
    key7 = json.load(open(R / "task3" / "exp7_key_numbers.json"))
    rules7 = pd.read_csv(R / "task3" / "exp7_rule_verdicts.csv")
    con7 = json.load(open(R / "task3" / "exp7_consistency.json"))
    on7, off7 = run7[run7.rule != "off"], run7[run7.rule == "off"]
    sun7 = ses7[ses7.rule != "off"]
    best = run7[run7.rule == "cap4_drop0.40"]
    add("E7 runs", 1710, len(run7), 0)
    add("E7 sessions", 3767, len(ses7), 0)
    add("E7 rule-on runs", 1620, len(on7), 0)
    add("E7 settings passing", 1, rules7.verdict_pass.sum(), 0)
    add("E7 passing setting is cap 4 drop 0.40", 1, rules7[rules7.rule == "cap4_drop0.40"].verdict_pass.iloc[0], 0)
    for name, quoted in [("I1", 0), ("I2", 0), ("I3", 0), ("I4", 0)]:
        add(f"E7 {name} failing cells", quoted, rules7[name].sum(), 0)
    add("E7 consistency", 1, con7["reproduces"], 0)
    add("E7 consistency exp4 sessions", 144, con7["T1_vs_exp4_sessions"]["rows_new"], 0)
    add("E7 consistency exp3 sessions", 64, con7["T2_vs_exp3_sessions"]["rows_new"], 0)
    add("E7 T3 runs with no alert", 1042, (on7[on7.test == "T3"].catheter_reason.fillna("") == "").sum(), 0)
    add("E7 latched runs", 578, (on7.catheter_reason.fillna("") != "").sum(), 0)
    add("E7 fault alerts", 540, on7.fault_alert.sum(), 0)
    add("E7 fault alerts in fault groups", 540, on7[on7.test != "T3"].fault_alert.sum(), 0)
    add("E7 session-limit alerts", 38, on7.session_limit_alert.sum(), 0)
    add("E7 session-limit alerts in T3", 38, on7[on7.test == "T3"].session_limit_alert.sum(), 0)
    add("E7 timeouts", 0, (run7.catheter_reason == "check_timed_out").sum(), 0)
    add("E7 presses while latched", 0, on7.presses_while_latched.sum(), 0)
    add("E7 T3 false alarms", 0, key7["T3_false_alarm_runs"], 0)
    add("E7 T1 off sessions", 12.0, off7[off7.test == "T1"].n_sessions.mean(), 0)
    add("E7 T1 on sessions max", 1, on7[on7.test == "T1"].n_sessions.max(), 0)
    add("E7 T2 off sessions", 10.7, off7[off7.test == "T2"].n_sessions.mean(), 0.005)
    add("E7 T2 on sessions, drop 0.20", 1.07, on7[(on7.test == "T2") & (on7.min_drop_fraction == 0.2)].n_sessions.mean(), 0.005)
    add("E7 T1 alert latency max", 300, on7[on7.test == "T1"].alert_s_after_first_session_after_onset.max(), 0)
    add("E7 T1 alert latency min", 241, on7[on7.test == "T1"].alert_s_after_first_session_after_onset.min(), 0)
    add("E7 T2 alert latency max, drop 0.40", 293, best[best.test == "T2"].alert_s_after_first_failed.max(), 0)
    add("E7 T2 alert latency max, drop 0.20", 3293, on7[on7.test == "T2"].alert_s_after_first_failed.max(), 0)

    empties = run7[(run7.test == "T1") & (run7.stim_name == "e1.0_s0.0_5on5off")]
    coact = run7[(run7.test == "T1") & (run7.stim_name == "e1.0_s0.5_5on5off")]
    t2r = run7[run7.test == "T2"]
    def part(t, rule, scaling):
        return t[(t.rule == rule) & (t.sphincter_scaling == scaling)]
    add("E7 empties off max volume", 367.1, part(empties, "off", 1.0).max_volume_ml.max(), 0.05)
    add("E7 empties on max volume", 708.6, part(empties, "cap4_drop0.40", 1.0).max_volume_ml.max(), 0.05)
    add("E7 empties on leak mean x0.9", 113.4, part(empties, "cap4_drop0.40", 0.9).leaked_outside_sessions_ml.mean(), 0.05)
    add("E7 empties on leak max x0.9", 217.3, part(empties, "cap4_drop0.40", 0.9).leaked_outside_sessions_ml.max(), 0.05)
    add("E7 empties on leaking runs x0.9", 15, (part(empties, "cap4_drop0.40", 0.9).leaked_outside_sessions_ml > 0).sum(), 0)
    add("E7 empties off sessions below 100", 10.6, part(empties, "off", 1.0).sessions_below_100ml.mean(), 0.05)
    add("E7 empties volume at alert", 7.8, part(empties, "cap4_drop0.40", 1.0).true_volume_at_catheter_alert_ml.median(), 0.05)
    add("E7 coact volume at alert", 343.4, part(coact, "cap4_drop0.40", 1.0).true_volume_at_catheter_alert_ml.median(), 0.05)
    add("E7 T2 volume at alert", 413.8, part(t2r, "cap4_drop0.40", 1.0).true_volume_at_catheter_alert_ml.median(), 0.05)
    add("E7 coact max volume x1.0", 940.4, part(coact, "off", 1.0).max_volume_ml.max(), 0.05)
    add("E7 coact off leak mean x0.9", 392.5, part(coact, "off", 0.9).leaked_outside_sessions_ml.mean(), 0.05)
    add("E7 coact on leak mean x0.9", 416.8, part(coact, "cap4_drop0.40", 0.9).leaked_outside_sessions_ml.mean(), 0.05)
    add("E7 T2 off leak mean x0.9", 393.7, part(t2r, "off", 0.9).leaked_outside_sessions_ml.mean(), 0.05)
    add("E7 T2 off leak max x0.9", 432.5, part(t2r, "off", 0.9).leaked_outside_sessions_ml.max(), 0.05)
    add("E7 peak with rule on", 59.4, on7.max_true_p_D_during_stim_cmH2O.max(), 0.05)
    add("E7 peak with rule off", 59.4, off7.max_true_p_D_during_stim_cmH2O.max(), 0.05)
    add("E7 peak with 3 seeds", 58.6, off7[off7.phys_seed.isin([42, 1, 2])].max_true_p_D_during_stim_cmH2O.max(), 0.05)
    add("E7 sessions over the P3 margin in T1", 0, ses7[ses7.test == "T1"].ceiling_exceeded_gt5.sum(), 0)
    add("E7 T2 peak on", 55.3, part(t2r, "cap4_drop0.40", 1.0).max_true_p_D_during_stim_cmH2O.max(), 0.05)
    add("E7 T2 peak off x1.0", 56.5, part(t2r, "off", 1.0).max_true_p_D_during_stim_cmH2O.max(), 0.05)
    add("E7 T2 peak off x0.9", 56.2, part(t2r, "off", 0.9).max_true_p_D_during_stim_cmH2O.max(), 0.05)

    lead = on7[on7.test != "T3"].dropna(subset=["first_leak_h"])
    lead = lead.assign(gap=lead.first_leak_h - lead.catheter_alert_h)
    best_lead = lead[lead.rule == "cap4_drop0.40"]
    add("E7 earliest leak h", 6.63, best_lead[best_lead.stim_name == "e1.0_s0.5_5on5off"].first_leak_h.min(), 0.005)
    add("E7 lead T2", 0.51, best_lead[best_lead.test == "T2"].gap.min(), 0.005)
    add("E7 lead T1 coact", 1.43, best_lead[(best_lead.test == "T1") & (best_lead.stim_name == "e1.0_s0.5_5on5off")].gap.min(), 0.005)
    add("E7 lead T1 empties", 4.52, best_lead[(best_lead.test == "T1") & (best_lead.stim_name == "e1.0_s0.0_5on5off")].gap.min(), 0.005)

    t3r = on7[on7.test == "T3"]
    for rule, limits, leaks, volume in [("cap2_drop0.40", 18, 1, 523.9), ("cap3_drop0.40", 1, 0, 477.6), ("cap4_drop0.40", 0, 0, 477.6)]:
        g = t3r[t3r.rule == rule]
        add(f"E7 {rule} limit alerts", limits, g.session_limit_alert.sum(), 0)
        add(f"E7 {rule} leaking runs", leaks, (g.leaked_outside_sessions_ml > 0).sum(), 0)
        add(f"E7 {rule} max volume", volume, g.max_volume_ml.max(), 0.05)
    add("E7 cap 2 T3 leak", 136.4, t3r[t3r.rule == "cap2_drop0.40"].leaked_outside_sessions_ml.max(), 0.05)
    best_t3 = t3r[t3r.rule == "cap4_drop0.40"]
    add("E7 cap 4 runs per setting", 180, len(best_t3), 0)
    add("E7 cap 4 runs using all 4 sessions", 1, (best_t3.n_sessions == 4).sum(), 0)

    done = sun7[sun7.check_drop.notna()]
    t3s = done[done.test == "T3"]
    t2s = done[done.test == "T2"]
    add("E7 T3 finished checks", 2166, len(t3s), 0)
    add("E7 T3 finished checks passed", 2166, (t3s.check_passed == True).sum(), 0)      # noqa: E712
    add("E7 T3 unfinished checks", 14, sun7[(sun7.test == "T3") & sun7.check_drop.isna()].shape[0], 0)
    add("E7 unfinished checks latest start margin h", 11.96, sun7[(sun7.test == "T3") & sun7.check_drop.isna()].start_h.min(), 0.005)
    add("E7 T3 sessions below 10 percent", 0, (ses7[ses7.test == "T3"].voided_fraction < 0.1).sum(), 0)
    add("E7 failed drop lowest", -0.227, t2s.check_drop.min(), 0.0005)
    add("E7 failed drop highest", 0.262, t2s.check_drop.max(), 0.0005)
    add("E7 partial drop lowest", 0.417, t3s[t3s.voided_fraction < 0.5].check_drop.min(), 0.0005)
    add("E7 partial drop highest", 0.569, t3s[t3s.voided_fraction < 0.5].check_drop.max(), 0.0005)
    add("E7 emptied drop lowest", 0.493, t3s[t3s.voided_fraction >= 0.5].check_drop.min(), 0.0005)
    add("E7 emptied drop median", 0.989, t3s[t3s.voided_fraction >= 0.5].check_drop.median(), 0.0005)
    seed11 = t2s[(t2s.phys_seed == 11) & (t2s.rule == "cap4_drop0.40")].iloc[0]
    add("E7 seed 11 estimate before", 413, seed11.check_estimate_before_ml, 0.5)
    add("E7 seed 11 estimate after", 305, seed11.check_estimate_after_ml, 0.5)
    add("E7 seed 11 true volume", 341, seed11.true_volume_before_ml, 0.5)
    first = t2s[(t2s.rule == "cap4_drop0.40") & (t2s.sphincter_scaling == 1.0)]
    add("E7 estimate above truth, of 15", 12, (first.check_estimate_before_ml > first.true_volume_before_ml).sum(), 0)
    add("E7 estimate above truth runs", 15, len(first), 0)
    add("E7 run time T1", 129, run7[run7.test == "T1"].runtime_s.mean(), 0.5)
    add("E7 run time T2", 166, run7[run7.test == "T2"].runtime_s.mean(), 0.5)
    add("E7 run time T3", 69, run7[run7.test == "T3"].runtime_s.mean(), 0.5)

    # Emptying-duration and sphincter-timing check (docs/EMPTYING_DURATION_CHECK.md, E84-E87)
    E = R / "emptying_check"
    ke = json.load(open(E / "key_numbers.json"))
    se = pd.read_csv(E / "sessions.csv")
    st = pd.read_csv(E / "settings_that_empty.csv")
    sph = pd.read_csv(E / "sphincter_off_targets.csv")
    det = pd.read_csv(E / "detrusor_off_targets.csv")
    off5 = pd.read_csv(E / "stage5_off_phase_flow.csv")
    s6 = pd.read_csv(R / "stage6" / "exp3_sessions.csv")
    s6 = s6[(s6.group == "main") & (s6.phys_seed == 42) & (s6.sphincter_scaling == 1.0)]
    add("ED traces used", 48, ke["traces_used"], 0)
    add("ED sessions in traces", 313, ke["sessions_in_traces"], 0)
    add("ED sessions unmatched", 0, ke["sessions_unmatched"], 0)
    add("ED table sessions not in traces", 20, len(s6) - ke["sessions_in_traces"], 0)
    add("ED those sessions longest s", 0.5, s6[s6.duration_s <= 0.5].duration_s.max(), 1e-9)
    add("ED those sessions count", 20, (s6.duration_s <= 0.5).sum(), 0)
    add("ED those sessions emptied", 0, (s6[s6.duration_s <= 0.5].emptying != "none").sum(), 0)
    add("ED those sessions with s0.0", 0, s6[s6.duration_s <= 0.5].stim_name.str.contains("_s0.0_").sum(), 0)
    add("ED sessions emptied", 67, ke["sessions_that_emptied"], 0)
    add("ED sessions emptied post-hoc", 67, ke["sessions_that_emptied_post_hoc"], 0)
    add("ED settings that empty", 24, ke["settings_that_empty"], 0)
    add("ED settings that empty post-hoc", 24, st.post_hoc_optimistic.sum(), 0)
    add("ED co-activation sessions emptied", 0, se[~se.post_hoc_optimistic & (se.emptying != "none")].shape[0], 0)
    add("ED median duration", 17, ke["median_emptying_duration_s"], 0)
    add("ED max duration", 51, ke["max_emptying_duration_s"], 0)
    add("ED over 120 s", 0, ke["sessions_over_120s"], 0)
    add("ED over 180 s", 0, ke["sessions_over_180s"], 0)
    add("ED max flow s after stop", 1, ke["max_flow_s_after_stim_stop"], 0)
    add("ED max stimulation s", 60, ke["max_stim_s"], 0)
    add("ED sensitivity median", 17, ke["median_within_1ml_of_lowest_s"], 0)
    add("ED sensitivity max", 44, ke["max_within_1ml_of_lowest_s"], 0)
    add("ED sessions stretched by trickle", 3, (se.emptying_duration_s - se.within_1ml_of_lowest_s > 3).sum(), 0)
    add("ED Q-based max", 61, ke["max_q_based_duration_s"], 0)
    c40 = st[st.pressure_ceiling_cmH2O == 40.0]
    c40e1 = c40[c40.stim_name.str.startswith("e1.0")]
    add("ED ceiling 40 e1.0 shortest max", 5, c40e1.max_duration_s.min(), 0)
    add("ED ceiling 40 e1.0 longest", 12, c40e1.max_duration_s.max(), 0)
    add("ED ceiling 40 e1.0 shortest median", 4, c40e1.median_duration_s.min(), 0)
    add("ED ceiling 40 e1.0 voided low", 67, c40e1.median_voided_ml.min(), 0.5)
    add("ED ceiling 40 e1.0 voided high", 77, c40e1.median_voided_ml.max(), 0.5)
    add("ED burst sessions emptied", 33, ke["burst_sessions_emptied"], 0)
    add("ED burst flow s ON", 446, ke["burst_flow_s_on"], 0)
    add("ED burst flow s OFF", 71, ke["burst_flow_s_off"], 0)
    add("ED OFF flow in first second", 68, ke["burst_off_flow_s_by_seconds_after_burst_end"]["0"], 0)
    add("ED OFF flow in second second", 3, ke["burst_off_flow_s_by_seconds_after_burst_end"]["1"], 0)
    add("ED tau_S", 0.2, ke["tau_S_s"], 0)
    add("ED tau_D", 1.0, ke["tau_D_s"], 0)
    add("ED effective tau_D low", 0.59, det.effective_tau_D_s.min(), 0.005)
    add("ED effective tau_D high", 0.91, det.effective_tau_D_s.max(), 0.005)
    for scaling, quoted in [(1.0, {0.0: 0.5, 0.6: 0.5, 0.7: 0.494, 0.8: 0.432, 0.9: 0.197, 1.0: 0.0}),
                            (0.9, {0.0: 0.45, 0.6: 0.45, 0.7: 0.445, 0.8: 0.389, 0.9: 0.177, 1.0: 0.0})]:
        for openness, q in quoted.items():
            v = sph[(sph.sphincter_scaling == scaling) & (sph.openness == openness)].off_phase_sphincter_target.iloc[0]
            add(f"ED sphincter target x{scaling} at {openness:.0%}", q, v, 0.0005)
    co = off5[off5.sphincter_drive >= 0.5]
    add("ED map burst runs at s0.5 and s1.0", 128, co.n.sum(), 0)
    add("ED map between-burst flow there", 0, co.max_flow_fraction_burst_off.max(), 0)
    add("ED map after-session flow there", 0, co.max_flow_after_session_ml.max(), 0)
    # the per-setting table in the doc: (pattern, ceiling, rate) -> (n, median, max)
    table = {
        ("e0.6_s0.0_5on5off", 40, 60): (2, 35.5, 36), ("e0.6_s0.0_5on5off", 40, 5): (2, 35.5, 36),
        ("e0.6_s0.0_5on5off", 55, 60): (2, 47.5, 51), ("e0.6_s0.0_5on5off", 55, 5): (2, 43, 43),
        ("e0.6_s0.0_5on5off", 70, 60): (2, 47.5, 51), ("e0.6_s0.0_5on5off", 70, 5): (2, 43, 43),
        ("e0.6_s0.0_continuous", 40, 60): (2, 21, 22), ("e0.6_s0.0_continuous", 40, 5): (2, 20.5, 22),
        ("e0.6_s0.0_continuous", 55, 60): (2, 22, 22), ("e0.6_s0.0_continuous", 55, 5): (2, 22, 22),
        ("e0.6_s0.0_continuous", 70, 60): (2, 22, 22), ("e0.6_s0.0_continuous", 70, 5): (2, 22, 22),
        ("e1.0_s0.0_5on5off", 40, 60): (6, 4, 12), ("e1.0_s0.0_5on5off", 40, 5): (7, 5, 5),
        ("e1.0_s0.0_5on5off", 55, 60): (2, 28.5, 32), ("e1.0_s0.0_5on5off", 55, 5): (2, 24.5, 25),
        ("e1.0_s0.0_5on5off", 70, 60): (2, 41.5, 51), ("e1.0_s0.0_5on5off", 70, 5): (2, 32, 32),
        ("e1.0_s0.0_continuous", 40, 60): (7, 4, 7), ("e1.0_s0.0_continuous", 40, 5): (7, 5, 5),
        ("e1.0_s0.0_continuous", 55, 60): (2, 14.5, 15), ("e1.0_s0.0_continuous", 55, 5): (2, 15.5, 16),
        ("e1.0_s0.0_continuous", 70, 60): (2, 17, 17), ("e1.0_s0.0_continuous", 70, 5): (2, 17, 17),
    }
    for (name, ceil, rate), (n, med, mx) in table.items():
        row = st[(st.stim_name == name) & (st.pressure_ceiling_cmH2O == ceil) & (st.us_interval_s == rate)].iloc[0]
        add(f"ED {name} {ceil} {rate} n", n, row.sessions_that_emptied, 0)
        add(f"ED {name} {ceil} {rate} median", med, row.median_duration_s, 0)
        add(f"ED {name} {ceil} {rate} max", mx, row.max_duration_s, 0)
    ex = pd.read_csv(R / "stage6" / "traces" / "exp3_e1.0_s0.0_5on5off_70_60.csv")
    v = ex.set_index("t").V_B_ml
    add("ED example drop after burst end mL", 9.7, v[20704.0] - v[20705.0], 0.05)
    add("ED example inflow mL/s", 0.03, v[20706.0] - v[20705.0], 0.005)
    add("ED trickle pushed out mL", 0.12, v[20739.0] - v[20740.0], 0.005)

    # Figure audit (docs/FIGURE_AUDIT.md, E35 correction, E89-E92)
    fa = json.load(open(R / "figure_audit" / "key_numbers.json"))
    r2, p3, p4 = fa["part2_residual_ml"], fa["part3"], fa["part4_pressure"]
    mp = pd.read_csv(R / "stage5" / "stimulation_map.csv")            # raw, not via the audit
    comp = mp[mp.emptying == "complete"]
    add("FA map complete n", 72, len(comp), 0)
    add("FA map complete median", 0.2, comp.residual_ml.median(), 0.05)
    add("FA map complete min", 0.0, comp.residual_ml.min(), 0.05)
    add("FA map complete max", 11.3, comp.residual_ml.max(), 0.05)
    add("FA map 2on2off x0.9 residual", 2.8, comp[(comp.on_s == 2) & (comp.detrusor_drive == 0.6)
                                                  & (comp.session_s == 60) & (comp.sphincter_scaling == 0.9)].residual_ml.iloc[0], 0.05)
    add("FA map other 70 max", 1.8, comp.residual_ml.nsmallest(70).max(), 0.05)
    add("FA map complete within 3 mL share", 0.99, (comp.residual_ml <= 3).mean(), 0.005)
    part = mp[mp.emptying == "partial"]
    add("FA map partial n", 14, len(part), 0)
    add("FA map partial min", 46, part.residual_ml.min(), 0.5)
    add("FA map partial max", 393, part.residual_ml.max(), 0.5)
    for k, n, med, lo, hi, share in [("exp3_sessions_in_working_settings", 228, 2.5, 0.0, 199.5, 0.58),
                                     ("exp3_complete_sessions", 175, 1.9, 0.0, 17.8, 0.78),
                                     ("exp3b_sessions_in_working_settings", 2380, 5.1, 0.0, 251.1, 0.33),
                                     ("exp3b_complete_sessions", 1470, 2.5, 0.0, 21.2, 0.57),
                                     ("exp7_T3_cap4_drop0.40_emptied_sessions", 370, 3.9, 0.0, 240.9, 0.38)]:
        add(f"FA {k} n", n, r2[k]["n"], 0)
        add(f"FA {k} median", med, r2[k]["median"], 0.05)
        add(f"FA {k} min", lo, r2[k]["min"], 0.05)
        add(f"FA {k} max", hi, r2[k]["max"], 0.05)
        add(f"FA {k} share le 3", share, r2[k]["share_le_3ml"], 0.005)
    add("FA exp3 setting median low", 1.3, r2["exp3_setting_median_residual"]["min"], 0.05)
    add("FA exp3 setting median high", 97.5, r2["exp3_setting_median_residual"]["max"], 0.05)
    add("FA exp3b setting median low", 1.9, r2["exp3b_setting_median_residual"]["min"], 0.05)
    add("FA exp3b setting median high", 156.4, r2["exp3b_setting_median_residual"]["max"], 0.05)
    keys = ["group", "stim_name", "pressure_ceiling_cmH2O", "ultrasound_interval_during_stim_s", "threshold_ml",
            "max_duration_s", "sphincter_scaling"]
    for tag, summ, sess, over3, over50, ceil_med, ceil_max in [
            ("exp3", "stage6/exp3_settings_summary.csv", "stage6/exp3_sessions.csv", 96, 42, 60.8, 199.5),
            ("exp3b", "task2/exp3b_settings_summary.csv", "task2/exp3b_sessions.csv", 1597, 868, 92.6, 207.2)]:
        ss = pd.read_csv(R / summ)
        xs = pd.read_csv(R / sess).merge(ss[ss.full_loop_works][keys], on=keys)
        add(f"FA {tag} working sessions over 3 mL", over3, (xs.residual_ml > 3).sum(), 0)
        add(f"FA {tag} working sessions over 50 mL", over50, (xs.residual_ml > 50).sum(), 0)
        cp = xs[xs.cutoff == "pressure_ceiling"].residual_ml
        add(f"FA {tag} ceiling-stopped median", ceil_med, cp.median(), 0.05)
        add(f"FA {tag} ceiling-stopped max", ceil_max, cp.max(), 0.05)
        if tag == "exp3":
            other = xs[xs.cutoff.isin(["max_duration", "volume_stop"])].residual_ml
            add("FA exp3 other cutoffs min", 0.0, other.min(), 0.05)
            add("FA exp3 other cutoffs max", 6.3, other.max(), 0.05)
    e3r = pd.read_csv(R / "stage6" / "exp3_runs.csv")
    e4r = pd.read_csv(R / "stage6" / "exp4_runs.csv")
    add("FA exp3 runs", 312, len(e3r), 0)
    add("FA exp4 runs", 324, len(e4r), 0)
    add("FA exp3+4 runs", 636, len(e3r) + len(e4r), 0)
    add("FA exp3+4 errors", 0, p3["exp3_exp4_runs_with_error"], 0)
    add("FA exp3+4 invariants hold", 636, p3["exp3_exp4_runs_all_invariants_hold"], 0)
    add("FA exp3b runs", 1620, p3["other_closed_loop_runs"]["exp3b"], 0)
    add("FA exp7 runs", 1710, p3["other_closed_loop_runs"]["exp7"], 0)
    for tag, scaling, best, of, runs in [("exp2b", "x1.0", 10, 14, 300), ("exp2b", "x0.9", 10, 14, 300),
                                         ("exp2", "x1.0", 11, 14, 60), ("exp2", "x0.9", 9, 14, 60)]:
        add(f"FA {tag} {scaling} best", best, p3[tag][scaling]["best_passing"], 0)
        add(f"FA {tag} {scaling} of", of, p3[tag][scaling]["of"], 0)
        add(f"FA {tag} {scaling} runs per cell", runs, p3[tag][scaling]["runs_per_cell"], 0)
        add(f"FA {tag} {scaling} best at 400", 1, 400.0 in p3[tag][scaling]["at_thresholds_ml"], 0)
    add("FA exp2b x1.0 best thresholds", 2, len(p3["exp2b"]["x1.0"]["at_thresholds_ml"]), 0)
    add("FA exp2b x0.9 400 failing", 4, len(p3["exp2b"]["x0.9"]["failing_at_best"]["400"]), 0)
    add("FA exp2b x1.0 450 failing", 4, len(p3["exp2b"]["x1.0"]["failing_at_best"]["450"]), 0)
    add("FA scenarios listed", 14, len(p3["exp2b_scenarios"]), 0)
    add("FA exp3b settings", 108, p3["exp3b_settings"], 0)
    add("FA exp3b working", 75, p3["exp3b_working"], 0)
    add("FA exp3b flag disagreements", 0, p3["exp3b_flag_disagreements"], 0)
    for k, runs, lo, hi in [("exp7_T1_rule_off", 60, 12, 12), ("exp7_T1_rule_on", 360, 1, 1)]:
        add(f"FA {k} runs", runs, p3[k]["runs"], 0)
        add(f"FA {k} sessions min", lo, p3[k]["sessions_min"], 0)
        add(f"FA {k} sessions max", hi, p3[k]["sessions_max"], 0)
    s1 = p4["sci_x1.0"]
    add("FA p at 400", 11.6, s1["p_D_at_400ml"], 0.05)
    add("FA p at 450", 32.5, s1["p_D_at_450ml"], 0.05)
    add("FA first 40 at mL", 461, s1["first_volume_p_ge_40_ml"], 0.5)
    add("FA first 55 at mL", 491, s1["first_volume_p_ge_55_ml"], 0.5)
    add("FA peak p", 56.6, s1["peak_p_D"], 0.05)
    add("FA peak at mL", 502, s1["volume_at_peak_ml"], 0.5)
    add("FA peak at h", 7.2, s1["time_at_peak_h"], 0.05)
    add("FA max volume 12 h", 909, s1["max_volume_ml"], 0.5)
    add("FA seconds at or above 55", 1269, s1["seconds_p_ge_55"], 0)
    pv = pd.read_csv(R / "figure_audit" / "pressure_vs_volume_no_stimulation.csv", header=[0, 1], index_col=0)
    for band, med, mx in [("0-50", 6.9, 7.8), ("200-250", 8.9, 9.2), ("350-400", 9.0, 11.5), ("400-450", 17.2, 32.4),
                          ("450-500", 51.5, 56.5), ("500-550", 50.1, 56.6), ("550-600", 25.0, 39.0),
                          ("650-700", 13.3, 13.4), ("850-900", 14.1, 14.4)]:
        add(f"FA curve {band} median", med, pv.loc[band, ("sci_x1.0", "median")], 0.05)
        add(f"FA curve {band} max", mx, pv.loc[band, ("sci_x1.0", "max")], 0.05)
    add("FA curve up to 400 low", 6.9, pv.loc["0-50":"350-400", ("sci_x1.0", "median")].min(), 0.05)
    add("FA curve up to 400 high", 9.4,pv.loc["0-50":"350-400", ("sci_x1.0", "median")].max(), 0.05)
    add("FA curve above 650 low", 13.3, pv.loc["650-700":, ("sci_x1.0", "median")].min(), 0.05)
    add("FA curve above 650 high", 14.4, pv.loc["650-700":, ("sci_x1.0", "median")].max(), 0.05)
    s9 = p4["sci_x0.9"]
    add("FA x0.9 peak", 55.1, s9["peak_p_D"], 0.05)
    add("FA x0.9 at mL", 491, s9["volume_at_peak_ml"], 0.5)
    add("FA x0.9 leaked", 420, s9["outflow_ml"], 0.5)
    add("FA x0.9 seconds at or above 55", 36, s9["seconds_p_ge_55"], 0)
    add("FA healthy peak", 54.7, p4["healthy_control"]["peak_p_D"], 0.05)
    add("FA healthy seconds at or above 55", 0, p4["healthy_control"]["seconds_p_ge_55"], 0)
    add("FA stage3 sci cases", 34, p4["stage3_sci_cases"], 0)
    add("FA stage3 cases at or above 55", 30, p4["stage3_sci_cases_max_p_ge_55"], 0)
    add("FA stage3 peak low", 45.2, p4["stage3_sci_max_p_range"][0], 0.05)
    add("FA stage3 peak high", 57.3, p4["stage3_sci_max_p_range"][1], 0.05)
    lowest_vol = []
    for tag, runs, hi, s0 in [("exp3", 312, 119, 0), ("exp4", 324, 129, 21), ("exp3b", 1620, 40, 40),
                              ("exp7", 1710, 412, 104)]:
        k = p4[f"{tag}_storage_p"]
        add(f"FA {tag} storage runs", runs, k["runs"], 0)
        add(f"FA {tag} storage runs at or above 55", hi, k["runs_ge_55"], 0)
        add(f"FA {tag} of those without co-activation", s0, k["runs_ge_55_without_coactivation"], 0)
        add(f"FA {tag} storage max", 56.6, k["max"], 0.05)
        lowest_vol.append(k["runs_ge_55_min_max_volume_ml"])
    add("FA exp3b at or above 55 all at ceiling 40", 40, p4["exp3b_storage_p"]["runs_ge_55_by_ceiling"].get("40", 0), 0)
    add("FA lowest max volume in those runs", 490.7, min(lowest_vol), 0.05)

    # Final experiment: Experiments 3 and 4 with 15 seeds (docs/EXPERIMENT3_4_15SEED_RESULTS.md, E93-E99)
    t4 = R / "task4"
    ex = {"float_precision": "round_trip"}
    kn = json.load(open(t4 / "key_numbers.json"))
    old, new = kn["old_3_seeds"], kn["new_15_seeds"]
    rp = json.load(open(t4 / "reproduction.json"))
    add("RR reproduces", 1, rp["reproduces"], 0)
    for key, rows, cols in [("exp3_runs", 312, 37), ("exp3_sessions", 2214, 27), ("exp4_runs", 324, 37),
                            ("exp4_sessions", 1889, 27)]:
        add(f"RR {key} old rows", rows, rp[key]["rows_old"], 0)
        add(f"RR {key} new rows matched", rows, rp[key]["rows_new"], 0)
        add(f"RR {key} columns", cols, rp[key]["columns_compared"], 0)
    for k, v in [("exp3_runs", 1560), ("exp4_runs", 1620), ("exp3_sessions", 11105), ("exp4_sessions", 9379),
                 ("exp3_errors", 0), ("exp4_errors", 0), ("settings", 104), ("settings_work", 38),
                 ("settings_work_with_co_activation", 0), ("P1_pass", 40), ("P2_pass", 76), ("P3_pass", 86),
                 ("exp3_invariants_hold", 1), ("exp4_invariants_hold", 1), ("worst_case_all_max_duration", 1),
                 ("volume_stop_60s", 0), ("sessions_60s", 6193), ("volume_stop_5s", 440), ("sessions_5s", 4912),
                 ("stuck_high_sessions_per_run_max", 12), ("reference_P1_max", 0)]:
        add(f"RR new {k}", v, new[k], 0)
    add("RR total sessions", 20484, new["exp3_sessions"] + new["exp4_sessions"], 0)
    for k, o, n in [("peak_exp3", 58.47, 60.18), ("peak_exp3_working", 53.83, 53.83), ("peak_exp4", 64.21, 67.17),
                    ("max_exceed_of_ceiling_exp4", 9.21, 12.17), ("peak_stuck_high_ok_channel", 58.65, 59.44),
                    ("median_residual_working_min", 1.33, 1.84), ("median_residual_working_max", 97.48, 98.76)]:
        add(f"RR old {k}", o, old[k], 0.005)
        add(f"RR new {k}", n, new[k], 0.005)
    add("RR old volume stop 5 s", 87, old["volume_stop_5s"], 0)
    add("RR old sessions 5 s", 978, old["sessions_5s"], 0)
    add("RR old sessions 60 s", 1236, old["sessions_60s"], 0)
    add("RR verdicts changed", 0, kn["verdicts_changed"], 0)
    add("RR exp4 crossings", 6, kn["exp4_cells_crossing_a_line"], 0)
    v = pd.read_csv(t4 / "exp3_verdict_compare.csv", **ex)
    add("RR settings compared", 104, len(v), 0)
    add("RR P1 lowest pass", 0.933, v[v.P1_pass_new].P1_sessions_voided_ge_50pct_new.min(), 0.0005)
    add("RR P1 highest fail", 0.0, v[~v.P1_pass_new].P1_sessions_voided_ge_50pct_new.max(), 0)
    add("RR P2 lowest pass", 1.0, v[v.P2_pass_new].P2_runs_without_overflow_after_alert_new.min(), 0)
    add("RR P2 highest fail", 0.0, v[~v.P2_pass_new].P2_runs_without_overflow_after_alert_new.max(), 0)
    add("RR P3 lowest pass", 0.967, v[v.P3_pass_new].P3_sessions_within_ceiling_plus5_new.min(), 0.0005)
    add("RR P3 highest fail", 0.881, v[~v.P3_pass_new].P3_sessions_within_ceiling_plus5_new.max(), 0.0005)
    add("RR working P2 all 15 of 15", 1.0, v[v.full_loop_works_new].P2_runs_without_overflow_after_alert_new.min(), 0)
    dp1 = (v.P1_sessions_voided_ge_50pct_new - v.P1_sessions_voided_ge_50pct_old).abs()
    dp3 = v.P3_sessions_within_ceiling_plus5_new - v.P3_sessions_within_ceiling_plus5_old
    add("RR largest P1 move", 0.067, dp1.max(), 0.0005)
    add("RR largest P3 move", 0.267, dp3.abs().max(), 0.0005)
    big = v.loc[dp3.abs().idxmax()]
    add("RR largest P3 move old", 0.500, big.P3_sessions_within_ceiling_plus5_old, 0.0005)
    add("RR largest P3 move new", 0.767, big.P3_sessions_within_ceiling_plus5_new, 0.0005)
    add("RR largest P3 move setting", 1, big.stim_name == "e0.6_s0.0_5on5off" and big.pressure_ceiling_cmH2O == 40
        and big.ultrasound_interval_during_stim_s == 60 and big.sphincter_scaling == 1.0 and not big.P3_pass_new, 0)
    ref350 = v[(v.group == "threshold_350")]
    add("RR threshold 350 P3 old", 1.0, ref350.P3_sessions_within_ceiling_plus5_old.min(), 0)
    add("RR threshold 350 P3 new", 0.994, ref350.P3_sessions_within_ceiling_plus5_new.max(), 0.0005)
    add("RR threshold 350 still passes P3", 1, ref350.P3_pass_new.all(), 0)
    s3n = pd.read_csv(t4 / "exp3_sessions.csv", **ex)
    s3o = pd.read_csv(R / "stage6" / "exp3_sessions.csv", **ex)
    top = s3n.loc[s3n.max_true_p_D_during_cmH2O.idxmax()]
    add("RR exp3 peak seed", 4, top.phys_seed, 0)
    add("RR exp3 peak group threshold 350", 1, top.group == "threshold_350" and top.stim_name == "e1.0_s0.5_5on5off", 0)
    add("RR exp3 peak start volume", 315.9, top.true_volume_before_ml, 0.05)
    add("RR exp3 peak duration", 1.8, top.duration_s, 0.05)
    add("RR exp3 peak over ceiling", 5.18, top.exceeded_ceiling_by_cmH2O, 0.005)
    add("RR exp3 sessions over margin old", 261, s3o.ceiling_exceeded_gt5.sum(), 0)
    add("RR exp3 sessions over margin new", 1306, s3n.ceiling_exceeded_gt5.sum(), 0)
    add("RR exp3 share over margin old pct", 11.8, 100 * s3o.ceiling_exceeded_gt5.mean(), 0.05)
    add("RR exp3 share over margin new pct", 11.8, 100 * s3n.ceiling_exceeded_gt5.mean(), 0.05)
    c4 = pd.read_csv(t4 / "exp4_cell_compare.csv", **ex)
    add("RR exp4 cells", 108, len(c4), 0)
    add("RR exp4 errors", 0, c4.errors_new.sum(), 0)
    combo = c4[c4.group == "combo:dead_pressure+stuck_high_estimate"]
    cref = combo[combo.reference == "e1.0_s0.5_5on5off"]
    add("RR combo P3 old", 0.972, cref.P3_sessions_within_ceiling_plus5_old.min(), 0.0005)
    add("RR combo P3 new", 0.961, cref.P3_sessions_within_ceiling_plus5_new.min(), 0.0005)
    add("RR combo peak x1.0", 67.16, cref[cref.sphincter_scaling == 1.0].max_true_p_D_during_stim_cmH2O_new.iloc[0], 0.005)
    s4n = pd.read_csv(t4 / "exp4_sessions.csv", **ex)
    s4o = pd.read_csv(R / "stage6" / "exp4_sessions.csv", **ex)
    worst = s4n[s4n.group == "combo:dead_pressure+stuck_high_estimate"]
    add("RR combo sessions", 720, len(worst), 0)
    add("RR combo all 60 s", 720, (worst.duration_s == 60.0).sum(), 0)
    t = s4n.loc[s4n.max_true_p_D_during_cmH2O.idxmax()]
    add("RR exp4 peak seed", 14, t.phys_seed, 0)
    add("RR exp4 peak at x0.9", 0.9, t.sphincter_scaling, 0)
    add("RR exp4 over margin old", 2, s4o.ceiling_exceeded_gt5.sum(), 0)
    add("RR exp4 over margin old all combo", 2, s4o[s4o.group.str.startswith("combo")].ceiling_exceeded_gt5.sum(), 0)
    add("RR exp4 over margin new", 24, s4n.ceiling_exceeded_gt5.sum(), 0)
    add("RR exp4 over margin new combo", 14, s4n[s4n.group.str.startswith("combo")].ceiling_exceeded_gt5.sum(), 0)
    okc = s4n[s4n.ceiling_exceeded_gt5 & (s4n.pressure_name == "ok")]
    add("RR exp4 ok-channel over margin", 10, len(okc), 0)
    add("RR ok-channel all ceiling cutoff", 10, okc.cutoff.str.contains("pressure_ceiling").sum(), 0)
    add("RR ok-channel faults", 3, okc.group.nunique(), 0)
    add("RR ok-channel peak low", 60.18, okc.max_true_p_D_during_cmH2O.min(), 0.005)
    add("RR ok-channel peak high", 61.38, okc.max_true_p_D_during_cmH2O.max(), 0.005)
    add("RR ok-channel duration low", 1.5, okc.duration_s.min(), 0.05)
    add("RR ok-channel duration high", 1.8, okc.duration_s.max(), 0.05)
    add("RR ok-channel start volume low", 296.4, okc.true_volume_before_ml.min(), 0.05)
    add("RR ok-channel start volume high", 315.9, okc.true_volume_before_ml.max(), 0.05)
    dov = (c4.overflow_despite_alert_rate_new - c4.overflow_despite_alert_rate_old).abs()
    add("RR largest overflow-rate move", 0.467, dov.max(), 0.0005)
    mv = c4.loc[dov.idxmax()]
    add("RR largest overflow move cell", 1, mv.group == "sensor:drift_minus2ph" and mv.sphincter_scaling == 0.9
        and mv.reference == "e1.0_s0.0_5on5off", 0)
    add("RR drift_minus2ph x0.9 old rate", 0.0, mv.overflow_despite_alert_rate_old, 0)
    dp = (c4.P1_sessions_voided_ge_50pct_new - c4.P1_sessions_voided_ge_50pct_old).abs()
    add("RR largest exp4 P1 move", 0.219, dp.max(), 0.0005)
    add("RR cells with overflow old", 32, (c4.overflow_despite_alert_rate_old > 0).sum(), 0)
    add("RR cells with overflow new", 33, (c4.overflow_despite_alert_rate_new > 0).sum(), 0)
    add("RR cells with overflow new at x1.0", 0, ((c4.overflow_despite_alert_rate_new > 0) & (c4.sphincter_scaling == 1.0)).sum(), 0)
    ud = c4[(c4.group == "user:delayed") & (c4.sphincter_scaling == 0.9) & (c4.reference == "e1.0_s0.0_5on5off")].iloc[0]
    add("RR user delayed x0.9 overflow old", 0.333, ud.overflow_despite_alert_rate_old, 0.0005)
    add("RR user delayed x0.9 overflow new", 0.733, ud.overflow_despite_alert_rate_new, 0.0005)
    x = pd.read_csv(t4 / "exp4_line_crossings.csv", **ex)
    add("RR crossings all second reference", 6, (x.reference == "e1.0_s0.0_5on5off").sum(), 0)
    for g, sc, col, o, n in [("sensor:combined_bad", 0.9, "P1_sessions_voided_ge_50pct", 0.714, 0.933),
                             ("sensor:combined_bad", 1.0, "P1_sessions_voided_ge_50pct", 0.750, 0.879),
                             ("sensor:drift_minus2ph", 0.9, "overflow_despite_alert_rate", 0.000, 0.467),
                             ("sensor:gain_minus20", 0.9, "P1_sessions_voided_ge_50pct", 0.833, 0.633),
                             ("sensor:misaligned_at_4h", 1.0, "P1_sessions_voided_ge_50pct", 0.750, 0.833),
                             ("user:delayed", 0.9, "P1_sessions_voided_ge_50pct", 0.750, 0.957)]:
        r = x[(x.group == g) & (x.sphincter_scaling == sc)].iloc[0]
        add(f"RR crossing {g} x{sc} old", o, r[f"{col}_old"], 0.0005)
        add(f"RR crossing {g} x{sc} new", n, r[f"{col}_new"], 0.0005)
    oc = json.load(open(t4 / "old_results_check.json"))
    add("RR old files hashed", 214, oc["files"], 0)

    # Task 5: sphincter level during bursts (results/task5/SUMMARY.md, E100-E103)
    t5 = R / "task5"
    k5 = json.load(open(t5 / "task5_key_numbers.json"))
    rp5 = json.load(open(t5 / "reproduction_15_seeds.json"))
    bl = pd.read_csv(t5 / "task5_by_level.csv", **ex)
    s5 = pd.read_csv(t5 / "task5_sessions.csv", **ex)
    for k, v in [("runs", 360), ("sessions", 2612), ("errors", 0), ("invariants_hold_all_runs", 1), ("working", 8)]:
        add(f"T5 {k}", v, k5[k], 0)
    for tag in ["e0.6_x1.0", "e0.6_x0.9", "e1.0_x1.0", "e1.0_x0.9"]:
        h = k5["highest_working_level"][tag]
        add(f"T5 {tag} highest working level", 0.1, h["highest_level_that_works"], 0)
        add(f"T5 {tag} one block from 0", 1, h["working_levels_form_one_block_from_0"], 0)
    for part, rows in [("runs", 120), ("sessions", 761)]:
        add(f"T5 reproduction {part} rows", rows, rp5[part]["rows_task5"], 0)
        add(f"T5 reproduction {part} identical", 1, rp5[part]["identical"], 0)
    add("T5 level 0.5 sessions", 641, rp5["level_0.5_sessions"], 0)
    add("T5 level 0.5 sessions voiding 10% or more", 0, rp5["level_0.5_sessions_voiding_10pct_or_more"], 0)
    # summary tables: (detrusor, scaling, level) -> P1, P2, residual median/min/max, sessions per run, emptied, emptying median/max, peak, max volume
    tab = {(0.6, 1.0, 0.0): (1.000, 1, 2.2, 0.0, 6.8, 2.00, 30, 50, 51, 49.6, 426.4),
           (0.6, 1.0, 0.1): (0.968, 1, 91.0, 0.7, 385.2, 2.07, 30, 55, 56, 49.0, 424.6),
           (0.6, 1.0, 0.2): (0.000, 1, 572.6, 322.7, 830.4, 10.60, 0, None, None, 55.8, 851.7),
           (0.6, 1.0, 0.3): (0.000, 1, 633.5, 343.4, 920.9, 10.67, 0, None, None, 54.6, 938.7),
           (0.6, 1.0, 0.4): (0.000, 1, 634.2, 343.4, 920.9, 10.67, 0, None, None, 54.5, 940.4),
           (0.6, 1.0, 0.5): (0.000, 1, 634.2, 343.4, 920.9, 10.67, 0, None, None, 54.5, 940.4),
           (0.6, 0.9, 0.0): (1.000, 1, 2.2, 0.0, 6.8, 2.00, 30, 50, 51, 46.3, 426.4),
           (0.6, 0.9, 0.1): (1.000, 1, 82.1, 0.7, 170.1, 2.00, 30, 55, 56, 47.0, 424.6),
           (0.6, 0.9, 0.2): (0.000, 0, 469.3, 322.7, 489.9, 10.67, 0, None, None, 53.1, 491.6),
           (0.6, 0.9, 0.3): (0.000, 0, 486.3, 343.4, 490.3, 10.67, 0, None, None, 54.4, 491.6),
           (0.6, 0.9, 0.4): (0.000, 0, 486.4, 343.4, 490.4, 10.67, 0, None, None, 54.5, 491.6),
           (0.6, 0.9, 0.5): (0.000, 0, 486.4, 343.4, 490.4, 10.67, 0, None, None, 54.5, 491.6),
           (1.0, 1.0, 0.0): (1.000, 1, 62.3, 0.5, 199.5, 2.00, 30, 25, 50, 53.7, 424.6),
           (1.0, 1.0, 0.1): (0.903, 1, 116.2, 1.1, 209.1, 2.07, 31, 25, 51, 54.6, 424.6),
           (1.0, 1.0, 0.2): (0.000, 1, 260.7, 201.8, 330.5, 4.27, 64, 35, 56, 56.6, 439.4),
           (1.0, 1.0, 0.3): (0.000, 1, 607.0, 341.6, 840.3, 10.67, 0, None, None, 56.6, 858.0),
           (1.0, 1.0, 0.4): (0.000, 1, 629.8, 343.3, 907.4, 10.67, 0, None, None, 56.5, 936.7),
           (1.0, 1.0, 0.5): (0.000, 1, 632.1, 343.4, 911.0, 10.67, 0, None, None, 56.5, 940.4),
           (1.0, 0.9, 0.0): (1.000, 1, 67.7, 1.5, 188.4, 2.00, 30, 25, 50, 53.7, 424.6),
           (1.0, 0.9, 0.1): (0.903, 1, 120.9, 1.1, 204.3, 2.07, 31, 25, 51, 54.6, 424.6),
           (1.0, 0.9, 0.2): (0.032, 1, 257.9, 188.0, 304.6, 4.20, 63, 42, 56, 56.4, 425.8),
           (1.0, 0.9, 0.3): (0.000, 0, 486.1, 341.6, 490.4, 10.73, 0, None, None, 55.4, 491.6),
           (1.0, 0.9, 0.4): (0.000, 0, 486.3, 343.3, 490.6, 10.73, 0, None, None, 56.0, 491.6),
           (1.0, 0.9, 0.5): (0.000, 0, 486.3, 343.4, 490.8, 10.73, 0, None, None, 56.2, 491.6)}
    for (d, sc, lv), (p1, p2, rmed, rmin, rmax, spr, emp, tmed, tmax, peak, vmax) in tab.items():
        r = bl[(bl.detrusor_drive == d) & (bl.sphincter_scaling == sc) & (bl.level == lv)].iloc[0]
        n = f"T5 e{d} x{sc} level {lv}"
        add(f"{n} P1", p1, r.P1, 0.0005)
        add(f"{n} P2", p2, r.P2, 0)
        add(f"{n} P3", 1, r.P3, 0)
        add(f"{n} works", int(lv <= 0.1), r.works, 0)
        for lab, q, v in [("leftover median", rmed, r.residual_median_ml), ("leftover min", rmin, r.residual_min_ml),
                          ("leftover max", rmax, r.residual_max_ml), ("peak p_D", peak, r.peak_true_p_D_cmH2O),
                          ("max volume", vmax, r.max_volume_ml_max)]:
            add(f"{n} {lab}", q, v, 0.05)
        add(f"{n} sessions per run", spr, r.sessions_per_run, 0.005)
        add(f"{n} emptied sessions", emp, r.emptied_sessions, 0)
        if tmed is not None:
            add(f"{n} emptying time median", tmed, r.emptying_time_median_s, 0)
            add(f"{n} emptying time max", tmax, r.emptying_time_max_s, 0)
    add("T5 highest peak p_D", 56.6, bl.peak_true_p_D_cmH2O.max(), 0.05)
    add("T5 cells passing P3", 24, bl.P3_pass.sum(), 0)
    add("T5 max leaked after alert", 432.5, bl.leaked_after_alert_ml_max.max(), 0.05)
    add("T5 flow after stimulation stop max", 2, bl.flow_s_after_stim_stop_max.max(), 0)
    add("T5 emptying time max overall", 56, bl.emptying_time_max_s.max(), 0)
    lv01 = s5[s5.stim_name.str.contains("_s0.1_") & (s5.voided_fraction < 0.5)]
    add("T5 level 0.1 sessions under 50%", 7, len(lv01), 0)
    add("T5 level 0.1 worst session voided", 0.053, lv01.voided_fraction.min(), 0.0005)
    for sc, med, mx in [(1.0, 0.331, 0.483), (0.9, 0.343, 0.529)]:
        x = s5[(s5.stim_name == "e1.0_s0.2_5on5off") & (s5.sphincter_scaling == sc)]
        add(f"T5 e1.0 x{sc} level 0.2 voided median", med, x.voided_fraction.median(), 0.0005)
        add(f"T5 e1.0 x{sc} level 0.2 voided max", mx, x.voided_fraction.max(), 0.0005)
        add(f"T5 e1.0 x{sc} level 0.2 sessions reaching 50%", {1.0: 0, 0.9: 2}[sc], (x.voided_fraction >= 0.5).sum(), 0)

    # Task 6: sphincter block and misalignment monitor (results/task6/SUMMARY.md, E104-E110)
    t6 = R / "task6"
    bc = json.load(open(t6 / "block_check.json"))
    add("T6 check runs", 36, bc["runs"]["rows_task6"], 0)
    add("T6 check sessions", 176, bc["sessions"]["rows_task6"], 0)
    add("T6 check run columns", 34, bc["runs"]["columns_compared"], 0)
    add("T6 check session columns", 27, bc["sessions"]["columns_compared"], 0)
    add("T6 check differences", 0, len(bc["runs"]["differences"]) + len(bc["sessions"]["differences"]), 0)
    add("T6 check passed, invariants hold", 2, int(bc["passed"]) + int(bc["invariants_hold_in_all_runs"]), 0)
    br = pd.read_csv(t6 / "block_runs.csv")
    add("T6 closed-loop runs", 90, len(br), 0)
    add("T6 closed-loop errors", 0, br.error.fillna("").ne("").sum(), 0)
    bs = pd.read_csv(t6 / "block_sessions.csv")
    cell = lambda name, sc: bs[(bs.stim_name == name) & (bs.sphincter_scaling == sc) & (bs.group != "B-probe")]  # noqa: E731
    for d, sc, n, n50, void, left, peak, within in [(0.6, 1.0, 12, 0, 0.37, 247, 50.0, 12), (0.6, 0.9, 12, 0, 0.38, 245, 49.2, 12),
                                                    (1.0, 1.0, 9, 9, 0.58, 166, 72.0, 5), (1.0, 0.9, 9, 9, 0.58, 161, 73.8, 5)]:
        x = cell(f"e{d}_s0.5_5on5off_block1.0_burst_fail20s", sc)
        add(f"T6 fault e{d} x{sc} sessions", n, len(x), 0)
        add(f"T6 fault e{d} x{sc} sessions voiding 50%", n50, x.voided_ge_50pct.sum(), 0)
        add(f"T6 fault e{d} x{sc} voided median", void, x.voided_fraction.median(), 0.005)
        add(f"T6 fault e{d} x{sc} leftover median", left, x.residual_ml.median(), 0.5)
        add(f"T6 fault e{d} x{sc} peak p_D", peak, x.max_true_p_D_during_cmH2O.max(), 0.05)
        add(f"T6 fault e{d} x{sc} sessions within ceiling+5", within, (~x.ceiling_exceeded_gt5.astype(bool)).sum(), 0)
    for d, b, scope, sc, left in [(0.6, 0.8, "burst", 1.0, 85), (0.6, 0.8, "burst", 0.9, 74), (0.6, 0.8, "session", 1.0, 1.5),
                                  (0.6, 0.8, "session", 0.9, 1.5), (0.6, 1.0, "burst", 1.0, 1.5), (0.6, 1.0, "burst", 0.9, 1.5),
                                  (0.6, 1.0, "session", 1.0, 1.3), (0.6, 1.0, "session", 0.9, 1.3),
                                  (1.0, 0.8, "burst", 1.0, 136), (1.0, 0.8, "burst", 0.9, 107), (1.0, 0.8, "session", 1.0, 75),
                                  (1.0, 0.8, "session", 0.9, 78), (1.0, 1.0, "burst", 1.0, 53), (1.0, 1.0, "burst", 0.9, 73),
                                  (1.0, 1.0, "session", 1.0, 8), (1.0, 1.0, "session", 0.9, 3)]:
        x = cell(f"e{d}_s0.5_5on5off_block{b}_{scope}", sc)
        add(f"T6 leftover e{d} block{b} {scope} x{sc}", left, x.residual_ml.median(), 0.5 if left > 10 else 0.05 if left < 2 else 0.5)
    ses = bs[bs.group == "A-session"]
    add("T6 session-block lowest voided", 0.69, ses.voided_fraction.min(), 0.005)
    add("T6 session-block sessions under 50%", 0, (ses.voided_fraction < 0.5).sum(), 0)
    add("T6 session-block gap flow min", 0.31, ses.groupby(["stim_name", "sphincter_scaling"]).flow_fraction_burst_off.median().min(), 0.005)
    add("T6 session-block flow after stop max s", 2, ses.flow_s_after_stim_stop.max(), 0)
    pr = br[br.group == "B-probe"]
    add("T6 probe runs", 18, len(pr), 0)
    add("T6 probe anchor patch checks", 0, pr[pr.probe == "anchor_monitor_on"].n_patch_checks.sum(), 0)
    add("T6 probe anchor sessions", 12, pr[pr.probe == "anchor_monitor_on"].n_sessions.sum(), 0)
    on = pr[pr.probe == "misaligned_monitor_on"]
    add("T6 probe misaligned runs flagged", 6, (on.n_patch_checks > 0).sum(), 0)
    add("T6 probe misaligned runs with alert", 6, (on.n_alerts > 0).sum(), 0)
    off9 = pr[(pr.probe == "misaligned_monitor_off") & (pr.sphincter_scaling == 0.9)]
    add("T6 probe x0.9 monitor off runs without alert", 2, (off9.n_alerts == 0).sum(), 0)
    for probe, sc, lo, hi in [("misaligned_monitor_off", 1.0, 549, 600), ("misaligned_monitor_on", 1.0, 411, 548),
                              ("misaligned_monitor_on", 0.9, 411, 490), ("anchor_monitor_on", 1.0, 391, 411)]:
        x = pr[(pr.probe == probe) & (pr.sphincter_scaling == sc)].max_volume_ml
        add(f"T6 probe {probe} x{sc} max volume low", lo, x.min(), 0.5)
        add(f"T6 probe {probe} x{sc} max volume high", hi, x.max(), 0.5)
    pc = pd.read_csv(t6 / "probe_patch_checks.csv")
    add("T6 probe first flag earliest h", 4.15, pc.groupby(["sphincter_scaling", "phys_seed"]).flag_h.min().min(), 0.005)
    add("T6 probe first flag latest h", 4.30, pc.groupby(["sphincter_scaling", "phys_seed"]).flag_h.min().max(), 0.005)

    cr = json.load(open(t6 / "exp8_criteria.json"))
    fs = pd.read_csv(t6 / "exp8_flag_summary.csv").set_index(["scenario", "sphincter_scaling"])
    al = pd.read_csv(t6 / "exp8_alert_summary.csv")
    fr = pd.read_csv(t6 / "exp8_flag_runs.csv")
    add("E8 runs", 6300, len(fr), 0)
    add("E8 M1 x1.0", 1.0, cr["M1_on_time_rate_by_scaling"]["1.0"], 0)
    add("E8 M1 x0.9", 1.0, cr["M1_on_time_rate_by_scaling"]["0.9"], 0)
    add("E8 M2 highest", 0.020, cr["M2_highest_flag_rate"], 0.0005)
    add("E8 M2 cells", 28, cr["M2_cells"], 0)
    add("E8 false flags", 25, fr[fr.kind == "none"].flagged.sum(), 0)
    add("E8 runs without misalignment", 4200, (fr.kind == "none").sum(), 0)
    add("E8 false flags from rule 1", 22, (fr[fr.kind == "none"].first_rule == "level_drop").sum(), 0)
    add("E8 M4 cells", 84, cr["M4_cells_checked"], 0)
    add("E8 M4 harmed", 0, len(cr["M4_cells_pass_to_fail"]), 0)
    none = al[al.kind == "none"]
    add("E8 cells working, monitor off", 54, none[none.variant == "monitor_off"].cue_works_C1_C2_C3.sum(), 0)
    add("E8 cells working, correction", 54, none[none.variant == "flag_and_correct"].cue_works_C1_C2_C3.sum(), 0)
    add("E8 M3 rescued", 2, cr["M3_target_cells_working"]["flag_and_correct"], 0)
    add("E8 M3 before", 0, cr["M3_target_cells_working"]["monitor_off"] + cr["M3_target_cells_working"]["flag_only"], 0)
    tg = "misaligned_at_4h"
    for sc, both, r1, r2, corr in [(1.0, 1.0, 0.933, 0.927, 1.0), (0.9, 1.0, 0.920, 0.953, 0.993)]:
        add(f"E8 target x{sc} on time", both, fs.loc[(tg, sc), "on_time_rate"], 0.0005)
        add(f"E8 target x{sc} rule 1 alone", r1, fs.loc[(tg, sc), "rule1_alone_on_time_rate"], 0.0005)
        add(f"E8 target x{sc} rule 2 alone", r2, fs.loc[(tg, sc), "rule2_alone_on_time_rate"], 0.0005)
        add(f"E8 target x{sc} corrected", corr, fs.loc[(tg, sc), "level_drop_rate"], 0.0005)
    add("E8 target minutes to flag", 13, fs.loc[(tg, 1.0), "median_min_to_flag"], 0.5)
    add("E8 target ratio median", 0.818, fs.loc[(tg, 1.0), "measured_ratio_median"], 0.0005)
    add("E8 target ratio p05", 0.743, fs.loc[(tg, 1.0), "measured_ratio_p05"], 0.0005)
    add("E8 target ratio p95", 0.895, fs.loc[(tg, 1.0), "measured_ratio_p95"], 0.0005)
    for name, a, b in [("mis_x0.5_at_4h", 1.0, 1.0), ("mis_x0.7_at_6h", 1.0, 1.0), ("mis_x0.7_at_2h", 0.967, 0.967),
                       ("mis_x0.7_at_4h_gain_only", 0.953, 0.960), ("mis_dropout_only_at_4h", 0.947, 0.933),
                       ("mis_x0.85_at_4h", 0.913, 0.940)]:
        add(f"E8 {name} on time x1.0", a, fs.loc[(name, 1.0), "on_time_rate"], 0.0005)
        add(f"E8 {name} on time x0.9", b, fs.loc[(name, 0.9), "on_time_rate"], 0.0005)
    add("E8 x0.85 rule 1 alone x1.0", 0.040, fs.loc[("mis_x0.85_at_4h", 1.0), "rule1_alone_on_time_rate"], 0.0005)
    add("E8 x0.85 rule 1 alone x0.9", 0.027, fs.loc[("mis_x0.85_at_4h", 0.9), "rule1_alone_on_time_rate"], 0.0005)
    add("E8 2 h rule 1 alone x1.0", 0.493, fs.loc[("mis_x0.7_at_2h", 1.0), "rule1_alone_on_time_rate"], 0.0005)
    add("E8 2 h rule 1 alone x0.9", 0.527, fs.loc[("mis_x0.7_at_2h", 0.9), "rule1_alone_on_time_rate"], 0.0005)
    add("E8 2 h ratio median", 0.937, fs.loc[("mis_x0.7_at_2h", 1.0), "measured_ratio_median"], 0.0005)
    add("E8 x0.5 minutes to flag", 9, fs.loc[("mis_x0.5_at_4h", 1.0), "median_min_to_flag"], 0.5)
    tc = al[al.scenario == tg].set_index(["threshold_ml", "sphincter_scaling", "variant"])
    for thr, sc, off, on_, v_off, v_on in [(350, 1.0, 0.693, 1.000, 490, 403), (350, 0.9, 0.393, 0.973, 486, 403),
                                           (400, 1.0, 0.013, 0.887, 552, 456), (400, 0.9, 0.000, 0.753, None, 461),
                                           (450, 1.0, 0.000, 0.427, 619, 515), (450, 0.9, 0.000, 0.260, None, 486)]:
        add(f"E8 target {thr} x{sc} useful, off", off, tc.loc[(thr, sc, "monitor_off"), "useful_rate"], 0.0005)
        add(f"E8 target {thr} x{sc} useful, flag only", off, tc.loc[(thr, sc, "flag_only"), "useful_rate"], 0.0005)
        add(f"E8 target {thr} x{sc} useful, corrected", on_, tc.loc[(thr, sc, "flag_and_correct"), "useful_rate"], 0.0005)
        add(f"E8 target {thr} x{sc} volume, corrected", v_on, tc.loc[(thr, sc, "flag_and_correct"), "true_volume_at_alert_median_ml"], 0.5)
        if v_off is not None:
            add(f"E8 target {thr} x{sc} volume, off", v_off, tc.loc[(thr, sc, "monitor_off"), "true_volume_at_alert_median_ml"], 0.5)
        add(f"E8 target {thr} x{sc} false alerts, corrected", 0.0, tc.loc[(thr, sc, "flag_and_correct"), "false_alert_run_rate"], 0)
    works = al[al.kind != "none"].groupby(["scenario", "variant"]).cue_works_C1_C2_C3.sum()
    for name, before, after in [("mis_x0.5_at_4h", 0, 2), ("mis_x0.7_at_4h_gain_only", 0, 2), ("mis_x0.7_at_6h", 2, 4),
                                ("mis_x0.85_at_4h", 3, 3), ("mis_x0.7_at_2h", 0, 0), ("mis_dropout_only_at_4h", 6, 6)]:
        add(f"E8 {name} cells before", before, works[(name, "monitor_off")], 0)
        add(f"E8 {name} cells after", after, works[(name, "flag_and_correct")], 0)

    # Task 7: Experiment 9, correction that allows for filling (results/task7/SUMMARY.md, E111-E116)
    t7 = R / "task7"
    ck = json.load(open(t7 / "check.json"))
    add("T7 check flag rows", 300, ck["flags"]["rows_task7"], 0)
    add("T7 check alert rows", 2700, ck["alerts"]["rows_task7"], 0)
    add("T7 check flag columns", 14, ck["flags"]["columns_compared"], 0)
    add("T7 check alert columns", 17, ck["alerts"]["columns_compared"], 0)
    add("T7 check differences", 0, len(ck["flags"]["differences"]) + len(ck["alerts"]["differences"]), 0)
    add("T7 check passed", 1, int(ck["passed"]), 0)
    c9 = json.load(open(t7 / "exp9_criteria.json"))
    first = json.load(open(t7 / "exp9_criteria_first_scoring_F1_wrong_column.json"))
    add("E9 first scoring F1 differences", 1785, first["F1_differences"]["ratio_at_flag"], 0)
    add("E9 F1 runs", 6300, c9["F1_runs_compared"], 0)
    add("E9 F1 differences", 0, len(c9["F1_differences"]), 0)
    add("E9 all criteria pass", 8, sum(int(c9[k]) for k in ("F1_pass", "M1_pass", "M2_pass", "R1_pass", "M4_pass",
                                                             "improvement", "H1_pass", "H2_pass")), 0)
    add("E9 M1 x1.0", 0.993, c9["M1_on_time_rate_by_scaling"]["1.0"], 0.0005)
    add("E9 M1 x0.9", 1.0, c9["M1_on_time_rate_by_scaling"]["0.9"], 0)
    add("E9 M2 highest", 0.040, c9["M2_highest_flag_rate"], 0.0005)
    add("E9 M4 cells", 84, c9["M4_cells_checked"], 0)
    add("E9 M4 harmed", 0, len(c9["M4_cells_pass_to_fail"]), 0)
    f9 = pd.read_csv(t7 / "exp9_flag_runs.csv")
    n9 = f9[(f9.variant == "new_correction") & (f9.kind == "none")]
    add("E9 false flags", 29, n9.flagged.sum(), 0)
    add("E9 runs without misalignment", 4200, len(n9), 0)
    o9 = f9[f9.variant == "old_correction"]
    add("E9 runs with a level flag", 1800, o9.level_drop_h.notna().sum(), 0)
    fs9 = pd.read_csv(t7 / "exp9_flag_summary.csv").set_index(["scenario", "sphincter_scaling"])
    add("E9 anchor x0.9 flag rate", 0.040, fs9.loc[("anchor_11pct", 0.9), "flag_rate"], 0.0005)
    r9 = pd.read_csv(t7 / "exp9_ratio_summary.csv").set_index(["scenario", "sphincter_scaling", "variant"])
    a9 = pd.read_csv(t7 / "exp9_alert_summary.csv")
    w9 = a9.groupby(["scenario", "variant"]).cue_works_C1_C2_C3.sum()
    c9a = a9.set_index(["scenario", "threshold_ml", "sphincter_scaling", "variant"])
    NEWC, OLDC, OFF = "new_correction", "old_correction", "monitor_off"
    for name, sc, old, new in [(tg, 1.0, 0.816, 0.700), (tg, 0.9, 0.824, 0.706),
                               ("mis_x0.5_at_4h", 1.0, 0.576, 0.496), ("mis_x0.5_at_4h", 0.9, 0.578, 0.499),
                               ("mis_x0.85_at_4h", 1.0, 0.976, 0.846), ("mis_x0.85_at_4h", 0.9, 0.955, 0.870),
                               ("mis_x0.7_at_4h_gain_only", 1.0, 0.790, 0.698), ("mis_x0.7_at_6h", 1.0, 0.785, 0.708),
                               ("mis_x0.7_at_2h", 1.0, 0.944, 0.703), ("mis_dropout_only_at_4h", 1.0, 1.000, 0.953),
                               ("mis_dropout_only_at_4h", 0.9, 0.936, 0.914)]:
        add(f"E9 {name} x{sc} ratio old", old, r9.loc[(name, sc, OLDC), "ratio_median"], 0.0005)
        add(f"E9 {name} x{sc} ratio new", new, r9.loc[(name, sc, NEWC), "ratio_median"], 0.0005)
    for name, sc, p05, p95, over, corr in [(tg, 1.0, 0.623, 0.783, 0.181, 0.993), (tg, 0.9, None, None, 0.167, 1.0),
                                           ("mis_x0.5_at_4h", 1.0, 0.457, 0.544, 0.020, 1.0),
                                           ("mis_x0.5_at_4h", 0.9, None, None, 0.133, 1.0),
                                           ("mis_x0.85_at_4h", 1.0, 0.745, 0.966, 0.242, 0.413),
                                           ("mis_x0.85_at_4h", 0.9, None, None, 0.116, 0.807),
                                           ("mis_dropout_only_at_4h", 1.0, None, None, None, 0.140),
                                           ("mis_dropout_only_at_4h", 0.9, None, None, None, 0.687)]:
        row = r9.loc[(name, sc, NEWC)]
        add(f"E9 {name} x{sc} corrected rate", corr, row["corrected_rate"], 0.0005)
        if over is not None:
            add(f"E9 {name} x{sc} over-corrected", over, row["over_corrected_rate"], 0.0005)
        if p05 is not None:
            add(f"E9 {name} x{sc} ratio p05", p05, row["ratio_p05"], 0.0005)
            add(f"E9 {name} x{sc} ratio p95", p95, row["ratio_p95"], 0.0005)
    add("E9 target x1.0 under-corrected", 0.161, r9.loc[(tg, 1.0, NEWC), "under_corrected_rate"], 0.0005)
    add("E9 target x0.9 under-corrected", 0.173, r9.loc[(tg, 0.9, NEWC), "under_corrected_rate"], 0.0005)
    new_rows = r9.xs(NEWC, level="variant")
    add("E9 flat line, negative slope", 14, new_rows["flat_negative_slope"].sum(), 0)
    add("E9 flat line, too few readings", 0, new_rows["flat_few_readings"].sum(), 0)
    add("E9 flat line at x1.0", 0, new_rows.xs(1.0, level="sphincter_scaling")["flat_negative_slope"].sum(), 0)
    for thr, sc, u_off, u_old, u_new, v_off, v_old, v_new, fa in [
            (350, 1.0, 0.707, 0.993, 0.980, 489, 406, 347, 0.013), (350, 0.9, 0.480, 0.993, 0.987, 485, 402, 344, 0.007),
            (400, 1.0, 0.000, 0.873, 0.993, 558, 457, 393, 0.0), (400, 0.9, 0.000, 0.793, 0.993, 487, 462, 388, 0.0),
            (450, 1.0, 0.000, 0.407, 0.940, 626, 514, 439, 0.0), (450, 0.9, 0.000, 0.240, 0.900, None, 486, 445, 0.0)]:
        for label, variant, u, v in [("off", OFF, u_off, v_off), ("old", OLDC, u_old, v_old), ("new", NEWC, u_new, v_new)]:
            add(f"E9 target {thr} x{sc} useful, {label}", u, c9a.loc[(tg, thr, sc, variant), "useful_rate"], 0.0005)
            if v is not None:
                add(f"E9 target {thr} x{sc} volume, {label}", v,
                    c9a.loc[(tg, thr, sc, variant), "true_volume_at_alert_median_ml"], 0.5)
        add(f"E9 target {thr} x{sc} false alerts, new", fa, c9a.loc[(tg, thr, sc, NEWC), "false_alert_run_rate"], 0.0005)
        add(f"E9 target {thr} x{sc} false alerts, old", 0.0, c9a.loc[(tg, thr, sc, OLDC), "false_alert_run_rate"], 0)
    for name, off, old, new in [(tg, 0, 2, 4), ("mis_x0.5_at_4h", 0, 2, 4), ("mis_x0.85_at_4h", 2, 3, 3),
                                ("mis_x0.7_at_4h_gain_only", 0, 3, 5), ("mis_x0.7_at_6h", 2, 4, 4),
                                ("mis_x0.7_at_2h", 0, 0, 0), ("mis_dropout_only_at_4h", 6, 6, 6)]:
        add(f"E9 {name} cells off", off, w9[(name, OFF)], 0)
        add(f"E9 {name} cells old", old, w9[(name, OLDC)], 0)
        add(f"E9 {name} cells new", new, w9[(name, NEWC)], 0)
    none9 = a9[a9.kind == "none"].groupby("variant").cue_works_C1_C2_C3.sum()
    for variant in (OFF, OLDC, NEWC):
        add(f"E9 cells without misalignment working, {variant}", 54, none9[variant], 0)
    for name, thr, sc, variant, col, val in [
            ("mis_x0.5_at_4h", 450, 1.0, NEWC, "useful_rate", 0.933), ("mis_x0.5_at_4h", 450, 0.9, NEWC, "useful_rate", 0.900),
            ("mis_x0.5_at_4h", 350, 1.0, NEWC, "false_alert_run_rate", 0.020),
            ("mis_x0.5_at_4h", 350, 0.9, NEWC, "false_alert_run_rate", 0.033),
            ("mis_x0.85_at_4h", 350, 1.0, NEWC, "false_alert_run_rate", 0.020),
            ("mis_x0.85_at_4h", 350, 0.9, NEWC, "false_alert_run_rate", 0.007),
            ("mis_x0.7_at_2h", 350, 1.0, NEWC, "false_alert_run_rate", 0.060),
            ("mis_x0.7_at_2h", 350, 0.9, NEWC, "false_alert_run_rate", 0.053),
            ("mis_x0.7_at_2h", 400, 1.0, OLDC, "useful_rate", 0.273), ("mis_x0.7_at_2h", 400, 1.0, NEWC, "useful_rate", 0.847),
            ("mis_x0.7_at_6h", 450, 1.0, OLDC, "useful_rate", 0.620), ("mis_x0.7_at_6h", 450, 1.0, NEWC, "useful_rate", 0.940),
            ("mis_x0.7_at_6h", 450, 0.9, OLDC, "useful_rate", 0.527), ("mis_x0.7_at_6h", 450, 0.9, NEWC, "useful_rate", 0.913)]:
        add(f"E9 {name} {thr} x{sc} {variant} {col}", val, c9a.loc[(name, thr, sc, variant), col], 0.0005)
    pr7 = pd.read_csv(t7 / "probe_runs.csv")
    add("T7 probe runs", 12, len(pr7), 0)
    add("T7 probe errors", 0, pr7.error.fillna("").ne("").sum(), 0)
    an7, mi7 = pr7[pr7.probe == "anchor_new_correction"], pr7[pr7.probe == "misaligned_new_correction"]
    add("T7 probe anchor patch checks", 0, an7.n_patch_checks.sum(), 0)
    add("T7 probe anchor sessions", 12, an7.n_sessions.sum(), 0)
    add("T7 probe misaligned runs flagged", 6, (mi7.n_patch_checks > 0).sum(), 0)
    add("T7 probe misaligned first alert earliest h", 5.75, mi7.first_alert_h.min(), 0.05)
    add("T7 probe misaligned first alert latest h", 5.93, mi7.first_alert_h.max(), 0.05)
    add("T7 probe misaligned max volume low", 369, mi7.max_volume_ml.min(), 0.5)
    add("T7 probe misaligned max volume high", 453, mi7.max_volume_ml.max(), 0.5)
    add("T7 probe misaligned leak", 0.0, mi7.leaked_after_alert_ml.sum(), 0)
    ps7 = pd.read_csv(t7 / "probe_sessions.csv")
    ms7 = ps7[ps7.probe == "misaligned_new_correction"]
    add("T7 probe misaligned sessions", 12, len(ms7), 0)
    add("T7 probe misaligned sessions voiding 50%", 12, ms7.voided_ge_50pct.sum(), 0)
    add("T7 probe seed 42 first session volume", 387, ms7[ms7.phys_seed == 42].true_volume_before_ml.min(), 0.5)
    add("T7 probe seed 2 session volume low", 360, ms7[ms7.phys_seed == 2].true_volume_before_ml.min(), 0.5)
    add("T7 probe seed 2 session volume high", 369, ms7[ms7.phys_seed == 2].true_volume_before_ml.max(), 0.5)
    old_on = br[br.probe == "misaligned_monitor_on"].set_index(["sphincter_scaling", "phys_seed"]).first_alert_h
    earlier = old_on - mi7.set_index(["sphincter_scaling", "phys_seed"]).first_alert_h
    add("T7 probe alert earlier by, least h", 0.4, earlier.min(), 0.05)
    add("T7 probe alert earlier by, most h", 2.1, earlier.max(), 0.05)

    # Task 8: Experiment 10, sensor B and fusion rules (results/task8/SUMMARY.md, E117-E124)
    t8 = R / "task8"
    ck8 = json.load(open(t8 / "check.json"))
    add("T8 check open-loop rows", 900, ck8["open_loop"]["rows_task8"], 0)
    add("T8 check open-loop columns", 11, ck8["open_loop"]["columns_compared"], 0)
    add("T8 check closed-loop runs", 6, ck8["closed_loop"]["runs"]["rows_task6"], 0)
    add("T8 check closed-loop sessions", 12, ck8["closed_loop"]["sessions"]["rows_task6"], 0)
    add("T8 check closed-loop columns", 34 + 27, ck8["closed_loop"]["runs"]["columns_compared"]
        + ck8["closed_loop"]["sessions"]["columns_compared"], 0)
    add("T8 check differences", 0, len(ck8["open_loop"]["differences"]) + len(ck8["closed_loop"]["runs"]["differences"])
        + len(ck8["closed_loop"]["sessions"]["differences"]), 0)
    add("T8 check passed", 1, int(ck8["passed"]), 0)
    tm8 = json.load(open(t8 / "timing.json"))
    add("T8 timing projection min", 11.7, tm8["projected_main_sweep_min_at_15"], 0.05)
    add("T8 sensor seeds used", 15, tm8["sensor_reps_to_use"], 0)
    k8 = json.load(open(t8 / "exp10_key_numbers.json"))
    add("E10 main runs", 8100, k8["main"]["runs"], 0)
    add("E10 main flag rows", 81450, k8["main"]["flag_rows"], 0)
    add("E10 main alert rows", 537300, k8["main"]["alert_rows"], 0)
    add("E10 held-out runs", 1200, k8["heldout"]["runs"], 0)
    add("E10 rule (a) cells checked", 108 + 24, k8["main"]["rule_a_cells_checked"] + k8["heldout"]["rule_a_cells_checked"], 0)
    add("E10 rule (a) equals A alone", 2, int(k8["main"]["rule_a_alerts_equal_A_alone"])
        + int(k8["heldout"]["rule_a_alerts_equal_A_alone"]), 0)
    add("E10 job files", 2 * (540 + 80), len(list((t8 / "runs").glob("*.csv"))), 0)
    add("E10 held-out traces", 20, len(list((t8 / "heldout" / "physiology").glob("*.csv"))), 0)
    rq = pd.read_csv(t8 / "exp10_requirement.csv")
    add("E10 points fixed, main", 0, rq[rq.set == "main"].fixed.sum(), 0)
    add("E10 points fixed, held-out", 2, rq[rq.set == "heldout"].fixed.sum(), 0)
    B, C = "b_trust_b", "c_average"
    rqi = rq.set_index(["set", "scenario", "rule", "b_error", "independence"])
    errs, inds = [0.05, 0.1117, 0.2, 0.3, 0.4], [0.0, 0.25, 0.5, 0.75, 1.0]
    for rule, table in [(B, [[5, 4, 1, 0, 0], [6, 2, 0, 0, 0], [0] * 5, [0] * 5, [0] * 5]),
                        (C, [[3, 2, 2, 0, 0], [4, 2, 2, 0, 0], [4, 3, 2, 1, 0], [4, 3, 2, 1, 0], [3, 4, 2, 2, 0]])]:
        for e, row in zip(errs, table):
            for c, cells in zip(inds, row):
                add(f"E10 target cells {rule} e{e} c{c}", cells, rqi.loc[("main", tg, rule, e, c), "cells_working"], 0)
    for e, m2, on_time, hb, hc, gc in [(0.05, 0.760, 0.991, 0, 3, 16), (0.1117, 0.609, 0.982, 0, 2, 16),
                                       (0.2, 0.369, 0.484, 0, 0, 14), (0.3, 0.267, 0.027, 2, 5, 14),
                                       (0.4, 0.236, 0.000, 3, 16, 10)]:
        add(f"E10 M2 worst cell e{e}", m2, rqi.loc[("main", tg, B, e, 0.0), "M2_highest_flag_rate"], 0.0005)
        add(f"E10 M1 target e{e}", on_time, rqi.loc[("main", tg, B, e, 0.0), "on_time_rate_min"], 0.0005)
        add(f"E10 harmed rule b e{e}", hb, rqi.loc[("main", tg, B, e, 0.0), "M4_cells_harmed"], 0)
        add(f"E10 harmed rule c e{e}", hc, rqi.loc[("main", tg, C, e, 0.0), "M4_cells_harmed"], 0)
        add(f"E10 gained rule c e{e}", gc, rqi.loc[("main", tg, C, e, 0.0), "cells_gained_without_misalignment"], 0)
    add("E10 M2 cells", 28, rqi.loc[("main", tg, B, 0.05, 0.0), "M2_cells"], 0)
    add("E10 common-mode on time", 0.004, rqi.loc[("main", tg, B, 0.1117, 1.0), "on_time_rate_min"], 0.0005)
    add("E10 target cells, A alone", 0, rqi.loc[("main", tg, B, 0.1117, 0.0), "cells_working_A_alone"], 0)
    for name, alone, cells, on_time in [("mis_x0.7_at_2h", 0, 6, 0.973), ("mis_x0.7_at_4h_gain_only", 0, 6, 0.987),
                                        ("mis_x0.85_at_4h", 2, 3, 0.142)]:
        add(f"E10 {name} cells, A alone", alone, rqi.loc[("main", name, B, 0.1117, 0.0), "cells_working_A_alone"], 0)
        add(f"E10 {name} cells, rule b", cells, rqi.loc[("main", name, B, 0.1117, 0.0), "cells_working"], 0)
        add(f"E10 {name} on time", on_time, rqi.loc[("main", name, B, 0.1117, 0.0), "on_time_rate_min"], 0.0005)
    add("E10 x0.85 on time at B 0.05", 0.400, rqi.loc[("main", "mis_x0.85_at_4h", B, 0.05, 0.0), "on_time_rate_min"], 0.0005)
    add("E10 early false alerts at B 0.20", 0.071, rqi.loc[("main", "mis_x0.7_at_2h", B, 0.2, 0.0), "worst_false_alert_rate"], 0.0005)
    for e, fa in [(0.05, 0.000), (0.1117, 0.009), (0.2, 0.036)]:
        add(f"E10 target worst false alert e{e}", fa, rqi.loc[("main", tg, B, e, 0.0), "worst_false_alert_rate"], 0.0005)
    f8 = pd.read_csv(t8 / "exp10_main_flag_summary.csv")
    n8 = f8[(f8.kind == "none") & (f8.b_case == "main")]
    for e, over, no_delay in [(0.05, 7, 3), (0.1117, 9, 5), (0.2, 19, None), (0.3, 27, None), (0.4, 28, None)]:
        x = n8[(n8.b_error == e) & (n8.flag_rate > 0.05)]
        add(f"E10 cells over 5% e{e}", over, len(x), 0)
        if no_delay is not None:
            add(f"E10 cells over 5% without delay e{e}", no_delay, (~x.scenario.str.startswith("delay")).sum(), 0)
    n8i = n8.set_index(["scenario", "sphincter_scaling", "b_error"]).flag_rate
    for e, a10, a09 in [(0.05, 0.022, 0.018), (0.1117, 0.040, 0.036), (0.2, 0.067, 0.084), (0.3, 0.093, 0.116),
                        (0.4, 0.147, 0.156)]:
        add(f"E10 anchor flags x1.0 e{e}", a10, n8i[("anchor_11pct", 1.0, e)], 0.0005)
        add(f"E10 anchor flags x0.9 e{e}", a09, n8i[("anchor_11pct", 0.9, e)], 0.0005)
    d15 = n8[(n8.scenario == "delay_15min") & (n8.b_error <= 0.12)].flag_rate
    d5 = n8[(n8.scenario == "delay_5min") & (n8.b_error <= 0.12)].flag_rate
    add("E10 delay_15min flags low", 0.58, d15.min(), 0.005)
    add("E10 delay_15min flags high", 0.76, d15.max(), 0.005)
    add("E10 delay_5min flags low", 0.06, d5.min(), 0.005)
    add("E10 delay_5min flags high", 0.09, d5.max(), 0.005)
    s8 = f8[f8.b_case != "main"].set_index(["scenario", "b_case", "sphincter_scaling"])
    for case, a, b in [("gain_b_0.8", 0.991, 0.982), ("gain_b_1.2", 0.987, 0.982), ("drift_b_minus2ph", 0.964, 0.947),
                       ("drift_b_plus2ph", 0.991, 0.987), ("missing_b_50pct", 0.760, 0.720)]:
        add(f"E10 side {case} on time x1.0", a, s8.loc[(tg, case, 1.0), "on_time_rate"], 0.0005)
        add(f"E10 side {case} on time x0.9", b, s8.loc[(tg, case, 0.9), "on_time_rate"], 0.0005)
    add("E10 B moves on time x1.0", 0.991, s8.loc[("anchor_11pct", "b_moves", 1.0), "on_time_rate"], 0.0005)
    add("E10 B moves on time x0.9", 0.996, s8.loc[("anchor_11pct", "b_moves", 0.9), "on_time_rate"], 0.0005)
    add("E10 B moves flag rate", 1.0, s8.loc[("anchor_11pct", "b_moves", 1.0), "flag_rate"], 0)
    add("E10 anchor flags, B drifting down, x1.0", 0.098, s8.loc[("anchor_11pct", "drift_b_minus2ph", 1.0), "flag_rate"], 0.0005)
    add("E10 anchor flags, B drifting down, x0.9", 0.164, s8.loc[("anchor_11pct", "drift_b_minus2ph", 0.9), "flag_rate"], 0.0005)
    a8 = pd.read_csv(t8 / "exp10_main_alert_summary.csv")
    side = a8[~a8.b_case.isin(["main", "none"])].groupby(["scenario", "b_case", "rule"]).cue_works.sum()
    for case, target_cells in [("gain_b_0.8", 2), ("gain_b_1.2", 4), ("drift_b_minus2ph", 3), ("drift_b_plus2ph", 4),
                               ("missing_b_50pct", 2)]:
        add(f"E10 side {case} target cells", target_cells, side[(tg, case, B)], 0)
        add(f"E10 side {case} anchor cells", 6, side[("anchor_11pct", case, B)], 0)
    add("E10 B moves anchor cells, rule b", 0, side[("anchor_11pct", "b_moves", B)], 0)
    add("E10 B moves anchor cells, rule c", 3, side[("anchor_11pct", "b_moves", C)], 0)
    add("E10 anchor cells, A alone", 6, a8[(a8.rule == "A_alone") & (a8.scenario == "anchor_11pct")].cue_works.sum(), 0)
    a8i = a8.set_index(["scenario", "b_case", "b_error", "independence", "rule", "threshold_ml", "sphincter_scaling"])
    add("E10 B moves useful at 400 x1.0", 0.022, a8i.loc[("anchor_11pct", "b_moves", 0.1117, 0.0, B, 400, 1.0), "useful_rate"], 0.0005)
    add("E10 B 0.05 lead at 450 x0.9", 22.5, a8i.loc[(tg, "main", 0.05, 0.0, B, 450, 0.9), "median_lead_min"], 0.05)
    add("E10 B 0.05 useful at 450 x0.9", 1.0, a8i.loc[(tg, "main", 0.05, 0.0, B, 450, 0.9), "useful_rate"], 0)
    for e, med, p05 in [(0.05, 403, 380), (0.1117, 390, 359), (0.2, 391, 327)]:
        row = a8i.loc[(tg, "main", e, 0.0, B, 400, 1.0)]
        add(f"E10 alert volume median e{e}", med, row["true_volume_at_alert_median_ml"], 0.5)
        add(f"E10 alert volume p05 e{e}", p05, row["true_volume_at_alert_p05_ml"], 0.55)
    cell8 = ["scenario", "sphincter_scaling", "threshold_ml"]            # among the cells that worked with A alone
    worked8 = a8[a8.rule == "A_alone"].set_index(cell8).cue_works
    c40 = a8[(a8.kind == "none") & (a8.b_case == "main") & (a8.rule == C) & (a8.b_error == 0.4)].set_index(cell8)
    c40 = c40[worked8.reindex(c40.index).to_numpy() & ~c40.cue_works.to_numpy()]
    add("E10 rule c harmed cells at B 0.40", 16, len(c40), 0)
    add("E10 rule c worst false alert among harmed cells at B 0.40", 0.38, c40.false_alert_run_rate.max(), 0.005)
    for name, r0, r25, on_time in [("held_x0.7_at_4h", [5, 6, 0, 0, 0], [4, 3, 0, 0, 0], 0.980),
                                   ("held_x0.6_at_4h", [5, 6, 4, 0, 0], [3, 4, 0, 0, 0], 0.987),
                                   ("held_x0.8_at_4h", [3, 2, 2, 2, 2], [2, 2, 2, 2, 2], 0.467)]:
        for e, c0, c25 in zip(errs, r0, r25):
            add(f"E10 {name} cells e{e} c0", c0, rqi.loc[("heldout", name, B, e, 0.0), "cells_working"], 0)
            add(f"E10 {name} cells e{e} c0.25", c25, rqi.loc[("heldout", name, B, e, 0.25), "cells_working"], 0)
        add(f"E10 {name} on time", on_time, rqi.loc[("heldout", name, B, 0.1117, 0.0), "on_time_rate_min"], 0.0005)
    add("E10 held x0.6 on time at B 0.20", 0.907, rqi.loc[("heldout", "held_x0.6_at_4h", B, 0.2, 0.0), "on_time_rate_min"], 0.0005)
    add("E10 held x0.8 on time at B 0.05", 0.853, rqi.loc[("heldout", "held_x0.8_at_4h", B, 0.05, 0.0), "on_time_rate_min"], 0.0005)
    add("E10 held x0.8 cells, A alone", 2, rqi.loc[("heldout", "held_x0.8_at_4h", B, 0.05, 0.0), "cells_working_A_alone"], 0)
    h8 = pd.read_csv(t8 / "exp10_heldout_flag_summary.csv")
    h8 = h8[(h8.kind == "none") & (h8.b_case == "main")].set_index(["sphincter_scaling", "b_error"]).flag_rate
    for e, a10, a09 in [(0.05, 0.027, 0.053), (0.1117, 0.040, 0.027), (0.2, 0.087, 0.093), (0.4, 0.160, 0.200)]:
        add(f"E10 held-out anchor flags x1.0 e{e}", a10, h8[(1.0, e)], 0.0005)
        add(f"E10 held-out anchor flags x0.9 e{e}", a09, h8[(0.9, e)], 0.0005)
    p8 = pd.read_csv(t8 / "probe_runs.csv")
    add("T8 probe runs", 24, len(p8), 0)
    add("T8 probe errors", 0, p8.error.fillna("").ne("").sum(), 0)
    for probe, flagged, lo, hi, first_lo, first_hi in [("anchor_trust_b", 0, 391, 411, 5.5, 6.5),
                                                       ("misaligned_trust_b", 6, 391, 417, 5.7, 6.0),
                                                       ("misaligned_average", 6, 452, 484, 6.1, 7.4)]:
        x = p8[p8.probe == probe]
        add(f"T8 probe {probe} runs flagged", flagged, (x.n_fusion_flags > 0).sum(), 0)
        add(f"T8 probe {probe} max volume low", lo, x.max_volume_ml.min(), 0.5)
        add(f"T8 probe {probe} max volume high", hi, x.max_volume_ml.max(), 0.5)
        add(f"T8 probe {probe} first alert low", first_lo, x.first_alert_h.min(), 0.05)
        add(f"T8 probe {probe} first alert high", first_hi, x.first_alert_h.max(), 0.05)
    cm8 = p8[p8.probe == "misaligned_trust_b_common_mode"]
    add("T8 probe common-mode runs flagged", 0, (cm8.n_fusion_flags > 0).sum(), 0)
    add("T8 probe common-mode x0.9 runs without alert", 2, ((cm8.sphincter_scaling == 0.9) & (cm8.n_alerts == 0)).sum(), 0)
    add("T8 probe common-mode x1.0 max volume low", 549, cm8[cm8.sphincter_scaling == 1.0].max_volume_ml.min(), 0.5)
    add("T8 probe common-mode x1.0 max volume high", 600, cm8[cm8.sphincter_scaling == 1.0].max_volume_ml.max(), 0.5)
    add("T8 probe flag earliest h", 4.12, p8.fusion_flag_h.min(), 0.005)
    add("T8 probe flag latest h", 4.27, p8.fusion_flag_h.max(), 0.005)
    ps8 = pd.read_csv(t8 / "probe_sessions.csv").groupby("probe").voided_ge_50pct.agg(["size", "sum"])
    for probe, n, ge in [("anchor_trust_b", 12, 12), ("misaligned_trust_b", 12, 12), ("misaligned_average", 8, 8),
                         ("misaligned_trust_b_common_mode", 9, 4)]:
        add(f"T8 probe {probe} sessions", n, ps8.loc[probe, "size"], 0)
        add(f"T8 probe {probe} sessions voiding 50%", ge, ps8.loc[probe, "sum"], 0)
    return out


def main():
    rows = [{"check": n, "quoted": q, "recomputed": v, "allowed": t, "ok": abs(q - v) <= t + 1e-12}
            for n, q, v, t in checks()]
    t = pd.DataFrame(rows)
    t.to_csv(R / "doc_number_check.csv", index=False)
    print(f"{int(t.ok.sum())} of {len(t)} checks match")
    print(t[~t.ok].to_string(index=False))


if __name__ == "__main__":
    main()
