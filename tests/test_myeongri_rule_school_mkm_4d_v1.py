# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion
from scripts.myeongri_rule_school_mkm_4d_v1 import (
    blend_vector_4d_rule_school,
    load_rule_school_mkm_4d_v1,
)


def test_load_policy_default_ok():
    doc = load_rule_school_mkm_4d_v1()
    assert doc["vector_4d_blend"]["w_surface"] > 0


def test_bad_blend_sum_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            {
                "schema": "rule_school_mkm_4d_v1",
                "version": "0",
                "vector_4d_blend": {"w_surface": 0.5, "w_jijangan": 0.4},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="sum"):
        load_rule_school_mkm_4d_v1(p)


def test_blend_extremes(tmp_path: Path) -> None:
    vs = {"S": 1.0, "L": 0.0, "K": 0.0, "M": 0.0}
    vj = {"S": 0.0, "L": 1.0, "K": 0.0, "M": 0.0}
    assert blend_vector_4d_rule_school(vs, vj, 1.0, 0.0)["S"] == pytest.approx(1.0)
    b = blend_vector_4d_rule_school(vs, vj, 0.5, 0.5)
    assert b["S"] == pytest.approx(0.5)
    assert b["L"] == pytest.approx(0.5)


def test_fusion_rule_blend_matches_weights(tmp_path: Path) -> None:
    pol = tmp_path / "pol.json"
    pol.write_text(
        json.dumps(
            {
                "schema": "rule_school_mkm_4d_v1",
                "version": "test",
                "vector_4d_blend": {"w_surface": 1.0, "w_jijangan": 0.0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    fus = MyeongriCompleteFusion(rule_school_policy_path=pol)
    doc = fus.calculate_complete_fusion(2000, 6, 15, 12, is_solar=True, is_male=True)
    for k in ("S", "L", "K", "M"):
        assert doc["vector_4d_rule_school_v1"][k] == pytest.approx(doc["vector_4d"][k])
    meta = doc["rule_school_mkm_4d_v1"]
    assert meta["version"] == "test"
