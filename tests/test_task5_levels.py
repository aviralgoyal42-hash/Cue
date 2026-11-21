"""Tests for Task 5 (sphincter level during bursts). Plan: docs/TASK5_PLAN.md."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import stage6_experiments3_4 as s6  # noqa: E402
import task5_sphincter_levels as t5  # noqa: E402
import task5_analysis as ta  # noqa: E402

config = s6.config


def without(spec, *drop):
    return {k: v for k, v in spec.items() if k not in drop}


def test_levels_and_subset_are_the_frozen_ones():
    assert t5.LEVELS == (0.0, 0.1, 0.2, 0.3, 0.4, 0.5)
    assert t5.DETRUSOR == (0.6, 1.0) and t5.SCALINGS == (1.0, 0.9)
    assert (t5.CEILING_CMH2O, t5.THRESHOLD_ML, t5.MAX_DURATION_S, t5.US_INTERVAL_S) == (55.0, 400.0, 60.0, 60.0)
    assert t5.SEEDS == [42] + list(range(1, 15)) and t5.CHECK_SEEDS == [42, 1, 2]


def test_grid_sizes_match_the_plan():
    assert len(t5.cases()) == 360
    assert len(t5.cases(t5.REFERENCE_LEVELS, t5.CHECK_SEEDS)) == 24
    assert len({repr(c) for c in t5.cases()}) == 360


def test_new_patterns_change_only_the_sphincter_level():
    for d in t5.DETRUSOR:
        base = config.STIM_PATTERNS.value[f"e{d}_s0.0_5on5off"]
        for lv in t5.LEVELS:
            name, stim = t5.pattern(d, lv)
            assert name == f"e{d}_s{lv:.1f}_5on5off"
            assert without(stim, "sphincter_drive") == without(base, "sphincter_drive")
            assert stim["sphincter_drive"] == lv


def test_reference_levels_are_exactly_the_old_experiment3_cases():
    old = [c for c in s6.exp3_cases() if c["group"] == "main" and c["stim_name"].endswith("5on5off")
           and c["controller"]["pressure_ceiling_cmH2O"] == 55.0 and c["ultrasound_interval_during_stim_s"] == 60.0]
    new = t5.cases(t5.REFERENCE_LEVELS, t5.CHECK_SEEDS)
    assert sorted(repr(without(c, "group")) for c in new) == sorted(repr(without(c, "group")) for c in old)


def test_threshold_and_max_duration_come_from_the_unchanged_defaults():
    case = s6.rig_mod.default_case(**without(t5.cases()[0], "group"))
    assert case["threshold_ml"] == t5.THRESHOLD_ML
    assert case["controller"]["max_duration_s"] == t5.MAX_DURATION_S
    assert case["guard"] is None
    assert case["sensor_name"] == "anchor_11pct" and case["user_name"] == "prompt" and case["pressure_name"] == "ok"


def test_config_is_left_alone():
    t5.cases()
    assert len(config.STIM_PATTERNS.value) == 8
    assert not any(n.startswith(("e0.6_s0.1", "e1.0_s0.1")) for n in config.STIM_PATTERNS.value)
    assert config.value(config.EXPERIMENT3, "physiology_seeds") == [42, 1, 2]


def test_outputs_go_to_the_task5_folder_only():
    assert t5.RESULTS.name == "task5" and t5.CHECK.parent == t5.RESULTS
    assert t5.TASK4.name == "task4"
    assert t5.RESULTS not in t5.TASK4.parents and t5.TASK4 not in t5.RESULTS.parents


def test_save_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "x.csv"
    t5.save([{"a": 1}], path)
    assert pd.read_csv(path).a.tolist() == [1]
    assert list(tmp_path.iterdir()) == [path]


def test_emptying_time_on_a_made_up_trace():
    # 0.1 s steps; volume 300 mL, falls 10 mL/s from t = 100 s to t = 120 s, then stays at 100 mL
    t = np.round(np.arange(0, 400, 0.1), 1)
    v = np.where(t < 100, 300.0, np.where(t < 120, 300.0 - 10.0 * (t - 100), 100.0))
    data = pd.DataFrame({"t": t, "V_B_ml": v})
    rig = SimpleNamespace(controller=SimpleNamespace(sessions=[{"start_s": 100.0, "stop_s": 110.0}]))
    out = t5.emptying_times(data, rig)[0]
    assert out["emptying_duration_s"] == 20.0
    assert out["within_1ml_of_lowest_s"] == 20.0
    assert out["flow_s_after_stim_stop"] == 10


def test_same_values_compares_by_value():
    a = pd.DataFrame({"x": [2, np.nan], "y": ["a", None]})
    b = pd.DataFrame({"x": [2.0, np.nan], "y": ["a", None]})
    assert t5.same_values(a, b) == {}
    assert t5.same_values(a, b.assign(x=[2.0000001, np.nan])) == {"x": 1}


def test_highest_level_reports_gaps_as_found():
    table = pd.DataFrame({"detrusor_drive": [1.0] * 4, "sphincter_scaling": [1.0] * 4,
                          "level": [0.0, 0.1, 0.2, 0.3], "works": [True, False, True, False]})
    h = ta.highest_levels(table)["e1.0_x1.0"]
    assert h["levels_that_work"] == [0.0, 0.2] and h["highest_level_that_works"] == 0.2
    assert h["working_levels_form_one_block_from_0"] is False
