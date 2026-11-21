"""Tests for the 15-seed rerun of Experiments 3 and 4: same grid, more seeds, old folders untouched."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import stage6_experiments3_4 as s6  # noqa: E402
import task4_rerun_exp3_4 as t4  # noqa: E402

config = s6.config


def old_grid():
    return {"exp3": s6.exp3_cases(), "exp4": s6.exp4_cases()}


def without_seed(spec):
    drop = ("phys_seed", "sensor_seed", "user_seed", "pressure_seed")
    return {k: v for k, v in spec.items() if k not in drop}


def test_seed_list_starts_with_the_old_seeds():
    assert t4.SEEDS == [42] + list(range(1, 15))
    assert len(set(t4.SEEDS)) == 15
    assert t4.SEEDS[:3] == t4.OLD_SEEDS


def test_grid_sizes_match_the_plan():
    grids = t4.cases()
    assert len(grids["exp3"]) == 1560
    assert len(grids["exp4"]) == 1620
    assert sum(c["group"] == "main" for c in grids["exp3"]) == 1440


def test_only_the_seeds_differ_from_the_old_grid():
    old, new = old_grid(), t4.cases()
    for label in ["exp3", "exp4"]:
        first_three = [c for c in new[label] if c["phys_seed"] in t4.OLD_SEEDS]
        assert first_three == old[label]
        assert {repr(without_seed(c)) for c in new[label]} == {repr(without_seed(c)) for c in old[label]}


def test_all_four_random_streams_follow_the_seed_as_before():
    for grid in t4.cases().values():
        for c in grid:
            assert c["phys_seed"] == c["sensor_seed"] == c["user_seed"] == c["pressure_seed"]


def test_config_and_old_module_are_left_alone():
    t4.cases()
    assert config.value(config.EXPERIMENT3, "physiology_seeds") == [42, 1, 2]
    assert s6.SEEDS == [42, 1, 2]
    assert s6.RESULTS.name == "stage6"


def test_session_guard_stays_off():
    for grid in t4.cases().values():
        assert not any(c.get("guard") for c in grid)


def test_workers_write_to_the_new_folder_only(monkeypatch):
    seen = {}
    monkeypatch.setattr(s6, "run_one", lambda spec: seen.update(folder=s6.RESULTS) or ({}, []))
    monkeypatch.setattr(s6, "RESULTS", s6.RESULTS)      # undone after the test
    t4.run_one({})
    assert seen["folder"] == t4.RESULTS


def test_manifest_covers_old_results_but_not_the_new_folder():
    files = t4.old_result_files()
    assert any(p.parent.name == "stage6" for p in files)
    assert not any(t4.RESULTS in p.parents for p in files)


def test_save_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "x.csv"
    t4.save([{"a": 1}], path)
    assert pd.read_csv(path).a.tolist() == [1]
    assert list(tmp_path.iterdir()) == [path]
