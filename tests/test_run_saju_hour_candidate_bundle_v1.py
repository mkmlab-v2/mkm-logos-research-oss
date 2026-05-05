# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_saju_hour_candidate_bundle_v1 import build_bundle


def test_uniform_twelve_sum_to_one():
    b = build_bundle(1992, 3, 12, "Asia/Seoul")
    assert b["schema"] == "saju_hour_uncertainty_v1"
    assert len(b["hour_distribution"]) == 12
    s = sum(x["probability"] for x in b["hour_distribution"])
    assert abs(s - 1.0) < 1e-9
    for x in b["hour_distribution"]:
        assert x["source_prior"] == "uniform"
        assert abs(x["probability"] - 1 / 12) < 1e-12


def test_window_filter_renormalizes():
    b = build_bundle(1992, 3, 12, "Asia/Seoul", branches_filter={0, 2})
    s = sum(x["probability"] for x in b["hour_distribution"])
    assert abs(s - 1.0) < 1e-9
    pos = [x for x in b["hour_distribution"] if x["probability"] > 0]
    assert len(pos) == 2
    assert all(abs(x["probability"] - 0.5) < 1e-12 for x in pos)


def test_fixed_saju_present():
    b = build_bundle(1973, 12, 10, "Asia/Seoul")
    assert "year" in b["fixed_saju"] and "month" in b["fixed_saju"] and "day" in b["fixed_saju"]


def test_schema_file_exists():
    p = Path(__file__).resolve().parents[1] / "docs/final/schemas/saju_hour_uncertainty_v1.schema.json"
    assert p.is_file()
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw.get("properties", {}).get("schema", {}).get("const") == "saju_hour_uncertainty_v1"


def test_invalid_branch_token_raises():
    from scripts.run_saju_hour_candidate_bundle_v1 import _parse_branches_filter

    with pytest.raises(ValueError, match="unknown branch"):
        _parse_branches_filter("자,invalid")
