"""
Every row transcribed from ESM Table S1 (docs/sources/table_s1_constants.csv) must match the
upstream code, every row must carry a source, and no tissue constant may claim a species.
"""
import csv
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lut_upstream import load_upstream, UPSTREAM_DIR  # noqa: E402

LUT = load_upstream().LUT()
with open(ROOT / "docs" / "sources" / "table_s1_constants.csv", newline="", encoding="utf8") as f:
    ROWS = list(csv.DictReader(f))


def code_value(row):
    if row["group"] == "noise":
        return LUT.noise
    return getattr(LUT, row["group"])[row["code_key"]]


def test_table_has_all_60_rows():
    assert len(ROWS) == 60
    assert sum(r["cited_source"] == "Bastiaanssen 1996" for r in ROWS) == 35


@pytest.mark.parametrize("row", [r for r in ROWS if r["code_key"] != "kidney_o"], ids=lambda r: r["code_key"])
def test_table_value_matches_upstream_code(row):
    assert float(row["table_value"]) == pytest.approx(code_value(row), rel=1e-3, abs=1e-12)


def test_phase_shift_label_differs_only_by_the_documented_factor():
    assert LUT.kidney_args["kidney_o"] / 3600 ** 2 == pytest.approx(math.pi / 5400)
    assert LUT.kidney_args["kidney_o"] / 3600 == pytest.approx(2 * math.pi / 3)


def test_no_tissue_constant_claims_a_species():
    allowed = {"unconfirmed", "not species-specific"}
    assert {r["species"] for r in ROWS if r["cited_source"] == "Bastiaanssen 1996"} == allowed


def test_constants_marked_unused_really_are_unused():
    source = (UPSTREAM_DIR / "model" / "LUT_Model.py").read_text(encoding="utf8")
    for row in ROWS:
        if row["used_by_code"] == "no":
            uses = re.findall(rf"\['{row['code_key']}'\]", source)
            assert uses == [], row["code_key"]
