"""Tests for Task 8 (abstract sensor B and three fusion rules). Plan: docs/TASK8_PLAN.md."""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))
import config  # noqa: E402
from sensors import Reading, SensorScenario, SyntheticUltrasoundSensor, sensor_b_values  # noqa: E402
from devices import SensorFusion  # noqa: E402
from devices.sensor_fusion import fused_value, RULES  # noqa: E402
import sci_test_rig as rig_mod  # noqa: E402
import task8_experiment10 as e10  # noqa: E402

A_SHIFT = config.SENSOR_SCENARIOS.value["misaligned_at_4h"]


def pairs(a_values, b_values, start=60.0, step=60.0):
    return [(Reading(start + i * step, a), Reading(start + i * step, b)) for i, (a, b) in enumerate(zip(a_values, b_values))]


def run(fusion, a_values, b_values, start=60.0):
    out = []
    for ra, rb in pairs(a_values, b_values, start):
        out.append(fusion.receive(ra, rb))
    return out


def filling(n, first=0, wobble=6.0, phase=0):
    return [150.0 + 1.5 * i + ((i + phase) % 2) * wobble for i in range(first, first + n)]


# ------------------------------------------------------------------ frozen values
def test_grid_and_settings_are_the_frozen_ones():
    assert e10.B_ERRORS == (0.05, 0.1117, 0.20, 0.30, 0.40)
    assert e10.INDEPENDENCE == (0.0, 0.25, 0.5, 0.75, 1.0)
    assert (e10.B_MISSING, e10.B_GAIN, e10.B_DRIFT, e10.REFERENCE_ERROR) == (0.10, 1.0, 0.0, 0.1117)
    assert e10.FUSION == {"now_s": 1200.0, "before_s": 5400.0, "min_now": 10, "min_before": 30, "k_noise": 4.0,
                          "min_change": 0.10, "min_ml": 100.0, "noise_n": 120, "noise_floor": 0.02}
    assert set(e10.SIDE_CASES) == {"gain_b_0.8", "gain_b_1.2", "drift_b_minus2ph", "drift_b_plus2ph", "missing_b_50pct"}
    assert e10.SENSOR_REPS == 15 and e10.FALLBACK_REPS == 10 and e10.TIME_LIMIT_MIN == 60.0
    assert e10.HELD_SEEDS == list(range(101, 111)) and e10.SEED_PREFIX == {"main": 3000, "heldout": 3100}
    assert not set(e10.HELD_SEEDS) & set(e10.SEEDS)
    assert e10.THRESHOLDS == [350.0, 400.0, 450.0]
    f = SensorFusion()                                    # the class defaults are the same values
    assert (f.now_s, f.before_s, f.min_now, f.min_before, f.k_noise, f.min_change, f.min_ml) == \
           (1200.0, 5400.0, 10, 30, 4.0, 0.10, 100.0)


def test_scenarios_and_grid_sizes_match_the_plan():
    main, held = e10.scenarios("main"), e10.scenarios("heldout")
    assert [k for _, k, _ in main].count("mis") == 4 and [k for _, k, _ in main].count("none") == 14
    assert main[0][0] == "misaligned_at_4h" and len(held) == 4
    assert {v["misalignment_gain"] for _, k, v in held if k == "mis"} == {0.6, 0.7, 0.8}
    assert len(e10.grid("mis", "mis_x0.7_at_2h")) == 25 and len(e10.grid("none", "mre_20pct")) == 5
    assert len(e10.grid("mis", "misaligned_at_4h")) == 30 and len(e10.grid("none", "anchor_11pct")) == 11
    assert len(e10.jobs("main", 15)) == 30 * 18 and len(e10.jobs("heldout", 15)) == 20 * 4
    files = [e10.job_files(j) for j in e10.jobs("main", 15) + e10.jobs("heldout", 15)]
    assert len({f for pair in files for f in pair}) == 2 * len(files)             # no two jobs share a file
    assert e10.OUT.name == "task8" and e10.RUNS.parent == e10.OUT
    assert len(config.SENSOR_SCENARIOS.value) == 15                                # config.py is left alone


# ------------------------------------------------------------------ sensor B
def test_independence_sets_how_much_of_the_patch_shift_hits_b():
    assert "misalignment_start_h" not in sensor_b_values(0.1117, 0.0, A_SHIFT)     # 0: B does not move at all
    full = sensor_b_values(0.1117, 1.0, A_SHIFT)                                   # 1: the same fault in full
    assert (full["misalignment_gain"], full["misalignment_missing_probability"], full["misalignment_start_h"]) == \
           (0.7, 0.30, 4.0)
    half = sensor_b_values(0.1117, 0.5, A_SHIFT)
    assert half["misalignment_gain"] == 0.85 and half["misalignment_missing_probability"] == 0.15
    assert [sensor_b_values(0.1, c, A_SHIFT).get("misalignment_gain", 1.0) for c in e10.INDEPENDENCE] == \
           [1.0, 0.925, 0.85, 0.775, 0.7]
    with pytest.raises(ValueError):
        sensor_b_values(0.1, 1.5, A_SHIFT)


def test_as_other_faults_never_touch_b():
    for name in ("gain_minus20", "drift_minus2ph", "delay_15min", "missing_50pct", "combined_bad"):
        b = sensor_b_values(0.2, 1.0, config.SENSOR_SCENARIOS.value[name], missing=0.10)
        assert b == {"mean_relative_error": 0.2, "gain_error": 0.0, "missing_probability": 0.10, "drift_per_hour": 0.0}


def test_b_settings_and_own_shift():
    b = sensor_b_values(0.3, 0.0, {}, gain_b=0.8, missing=0.5, drift_per_hour=-0.02, own_shift=(4.0, 0.7))
    assert b["gain_error"] == pytest.approx(-0.2) and b["missing_probability"] == 0.5 and b["drift_per_hour"] == -0.02
    assert b["misalignment_start_h"] == 4.0 and b["misalignment_gain"] == 0.7
    sensor = SyntheticUltrasoundSensor(SensorScenario.from_dict("sensor_b", sensor_b_values(0.0, 0.0, {}, gain_b=0.8,
                                                                                            missing=0.0)), 1)
    assert sensor.read(600.0, lambda t: 200.0).volume_ml == pytest.approx(160.0)


def test_b_uses_the_same_random_stream_at_every_grid_point():
    def readings(error, indep):
        s = SyntheticUltrasoundSensor(SensorScenario.from_dict("b", sensor_b_values(error, indep, A_SHIFT)), 7)
        return [s.read(60.0 * i, lambda t: 300.0) for i in range(1, 400)]
    a, b = readings(0.1117, 0.0), readings(0.1117, 1.0)
    assert [r.valid for r in a[:239]] == [r.valid for r in b[:239]]               # identical before the shift
    assert [r.volume_ml for r in a[:239]] == [r.volume_ml for r in b[:239]]


# ------------------------------------------------------------------ fusion: truth and rules
def test_fusion_file_never_references_ground_truth():
    tree = ast.parse((ROOT / "devices" / "sensor_fusion.py").read_text())
    imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    modules = {a.name for n in imports for a in n.names} | {getattr(n, "module", None) for n in imports}
    assert modules <= {"math", "collections", "deque", None}
    identifiers = {getattr(n, "id", None) or getattr(n, "attr", None) or getattr(n, "arg", None)
                   for n in ast.walk(tree) if isinstance(n, (ast.Name, ast.Attribute, ast.arg))}
    identifiers.discard(None)
    for name in identifiers:
        assert not any(bad in name.lower() for bad in ["v_b", "p_d", "true", "truth", "ground"]), name


def test_fused_value_for_each_rule():
    assert RULES == ("flag", "trust_b", "average")
    assert fused_value("flag", 300.0, 400.0, True) == 300.0                        # (a): always A
    assert fused_value("trust_b", 300.0, 400.0, False) == 300.0                    # (b): A until flagged ...
    assert fused_value("trust_b", 300.0, 400.0, True) == 400.0                     # ... then B
    assert fused_value("trust_b", 300.0, None, True) is None                       # B missing: nothing, not A
    assert fused_value("average", 300.0, 400.0, False) == 350.0                    # (c): the mean ...
    assert fused_value("average", None, 400.0, False) == 400.0                     # ... or the valid one
    assert fused_value("average", None, None, True) is None
    with pytest.raises(ValueError):
        SensorFusion(rule="majority")


def test_two_sensors_that_agree_are_never_flagged_even_while_filling_and_emptying():
    fusion = SensorFusion()
    a = filling(300) + [20.0 + i for i in range(300)]                              # fills, empties, fills again
    b = filling(300, phase=1) + [21.0 + i for i in range(300)]
    assert not any(fired for _, fired in run(fusion, a, b)) and fusion.flag is None


def test_a_constant_gain_error_is_not_a_disagreement():
    fusion = SensorFusion()
    assert not any(fired for _, fired in run(fusion, [0.8 * v for v in filling(400)], filling(400, phase=1)))


def test_a_patch_shift_is_flagged_with_its_size_and_direction():
    fusion = SensorFusion()
    run(fusion, filling(200), filling(200, phase=1))
    out = run(fusion, [0.7 * v for v in filling(60, first=200)], filling(60, first=200, phase=1), start=60.0 * 201)
    assert sum(fired for _, fired in out) == 1 and fusion.flagged                  # once only
    assert fusion.flag["change"] < -0.10                                           # A fell compared with B
    assert (fusion.flag["t_s"] - 60.0 * 201) / 60.0 <= 20                          # within the 20-minute window


def test_a_reads_high_is_flagged_too():
    fusion = SensorFusion()
    run(fusion, filling(200), filling(200, phase=1))
    run(fusion, [1.4 * v for v in filling(60, first=200)], filling(60, first=200, phase=1), start=60.0 * 201)
    assert fusion.flagged and fusion.flag["change"] > 0.10


def test_a_fault_that_hits_both_sensors_equally_is_invisible():
    fusion = SensorFusion()
    run(fusion, filling(200), filling(200, phase=1))
    out = run(fusion, [0.7 * v for v in filling(120, first=200)], [0.7 * v for v in filling(120, first=200, phase=1)],
              start=60.0 * 201)
    assert not any(fired for _, fired in out)


def test_small_changes_low_levels_and_too_few_readings_do_not_flag():
    small = SensorFusion()
    run(small, filling(200), filling(200, phase=1))
    assert not any(f for _, f in run(small, [0.95 * v for v in filling(60, first=200)],
                                     filling(60, first=200, phase=1), start=60.0 * 201))
    low = SensorFusion()
    run(low, [v / 6 for v in filling(200)], [v / 6 for v in filling(200, phase=1)])
    assert not any(f for _, f in run(low, [0.7 * v / 6 for v in filling(30, first=200)],
                                     [v / 6 for v in filling(30, first=200, phase=1)], start=60.0 * 201))
    blind = SensorFusion()                                                         # B hardly ever reads
    b = [v if i % 4 == 0 else None for i, v in enumerate(filling(260, phase=1))]
    a = filling(200) + [0.7 * v for v in filling(60, first=200)]
    assert not any(f for _, f in run(blind, a, b))


def test_a_noisier_pair_needs_a_bigger_disagreement():
    quiet, noisy = SensorFusion(), SensorFusion()
    run(quiet, filling(200), filling(200, phase=1))
    run(noisy, filling(200, wobble=150.0), filling(200, wobble=150.0, phase=1))
    assert noisy.noise(0) > 5 * quiet.noise(0)
    assert any(f for _, f in run(quiet, [0.85 * v for v in filling(60, first=200)], filling(60, first=200, phase=1),
                                 start=60.0 * 201))
    assert not any(f for _, f in run(noisy, [0.85 * v for v in filling(60, first=200, wobble=150.0)],
                                     filling(60, first=200, wobble=150.0, phase=1), start=60.0 * 201))


def test_each_rule_passes_on_the_right_readings_and_they_all_flag_alike():
    a = filling(200) + [0.7 * v for v in filling(60, first=200)]
    b = filling(260, phase=1)
    fusions = {rule: SensorFusion(rule=rule) for rule in RULES}
    out = {rule: run(f, a, b) for rule, f in fusions.items()}
    flags = [f.flag for f in fusions.values()]
    assert flags[0] is not None and flags[0] == flags[1] == flags[2]
    k = next(i for i, (_, fired) in enumerate(out["flag"]) if fired)
    assert [r.volume_ml for r, _ in out["flag"]] == a
    assert [r.volume_ml for r, _ in out["trust_b"]] == a[:k] + b[k:]               # switches at the flag itself
    assert [r.volume_ml for r, _ in out["average"]] == [(x + y) / 2 for x, y in zip(a, b)]


def test_the_experiment_shortcut_gives_the_same_streams_as_the_class():
    a = filling(200) + [0.7 * v for v in filling(60, first=200)]
    b = [v if i % 9 else None for i, v in enumerate(filling(260, phase=1))]
    ra, rb = zip(*pairs(a, b))
    flag = e10.run_pair(ra, rb)
    assert flag is not None
    for rule in ("trust_b", "average"):
        real = [r for r, _ in run(SensorFusion(rule=rule, **e10.FUSION), a, b)]
        assert e10.stream_for(rule, ra, rb, flag) == real
    assert e10.stream_for("trust_b", ra, rb, None) == list(ra)                     # no flag: A throughout


def test_pause_resume_and_reset():
    fusion = SensorFusion(rule="trust_b")
    run(fusion, filling(200), filling(200, phase=1))
    fusion.pause()
    out = run(fusion, [5.0] * 30, [400.0] * 30, start=60.0 * 201)                  # wild readings while paused
    assert not any(f for _, f in out) and out[0][0].volume_ml == 5.0               # still passed on, never tested
    fusion.resume()
    assert len(fusion._pairs) == 0
    run(fusion, filling(200), filling(200, phase=1), start=60.0 * 240)
    run(fusion, [0.6 * v for v in filling(60, first=200)], filling(60, first=200, phase=1), start=60.0 * 441)
    assert fusion.flagged
    fusion.reset()
    assert not fusion.flagged and fusion.rule == "trust_b" and fusion.flag is None


# ------------------------------------------------------------------ rig
def test_the_rig_is_unchanged_when_fusion_is_off():
    case = rig_mod.default_case()
    assert case["fusion"] is None
    rig = rig_mod.CueRig(case)
    assert rig.fusion is None and rig.sensor_b is None


def test_the_rig_builds_sensor_b_and_the_rule_when_asked():
    b = sensor_b_values(0.1117, 0.0, A_SHIFT)
    rig = rig_mod.CueRig(rig_mod.default_case(fusion={"rule": "average", "settings": e10.FUSION, "sensor_b": b,
                                                      "sensor_b_seed": 5}))
    assert rig.fusion.rule == "average" and rig.fusion.k_noise == 4.0
    assert rig.sensor_b.scenario.mean_relative_error == 0.1117


def test_probe_grid_matches_the_plan():
    cases = e10.probe_cases()
    assert len(cases) == 24
    assert {c["probe"] for c in cases} == {"anchor_trust_b", "misaligned_trust_b", "misaligned_average",
                                           "misaligned_trust_b_common_mode"}
    common = [c for c in cases if c["probe"].endswith("common_mode")]
    assert all(c["fusion"]["sensor_b"]["misalignment_gain"] == 0.7 for c in common)
    assert all("misalignment_gain" not in c["fusion"]["sensor_b"] for c in cases if c["probe"] == "misaligned_average")


def test_scoring_refuses_partial_files(tmp_path, monkeypatch):
    monkeypatch.setattr(e10, "OUT", tmp_path)
    monkeypatch.setattr(e10, "RUNS", tmp_path / "runs")
    (tmp_path / "timing.json").write_text('{"sensor_reps_to_use": 15}')
    with pytest.raises(SystemExit):
        e10.load("main")
