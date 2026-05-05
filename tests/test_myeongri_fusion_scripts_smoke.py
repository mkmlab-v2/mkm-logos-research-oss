# -*- coding: utf-8 -*-
"""Smoke: MyeongriCompleteFusion returns 4D vector (B-track)."""

from __future__ import annotations

import pytest

from scripts.manseryeok_perfect_final import PerfectManseryeok
from scripts.myeongri_complete_fusion import MyeongriCompleteFusion


def test_myeongri_complete_fusion_vector_4d() -> None:
    doc = MyeongriCompleteFusion().calculate_complete_fusion(
        2000, 6, 15, 12, is_solar=True, is_male=True
    )
    v = doc.get("vector_4d") or {}
    for k in ("S", "L", "K", "M"):
        assert k in v
        assert isinstance(v[k], (int, float))
    jig = doc.get("jijangan_v1") or {}
    assert jig.get("schema") == "jijangan_overlay_v1"
    assert jig.get("lut_version")
    pillars = jig.get("pillars") or {}
    for pk in ("year", "month", "day", "hour"):
        p = pillars.get(pk) or {}
        assert "hidden_stems" in p
        ganji = (doc.get("saju") or {}).get(pk) or ""
        assert p.get("ji") == (ganji[1] if len(ganji) >= 2 else None)
        for row in p["hidden_stems"]:
            assert "gan" in row and "tier" in row
    ohj = doc.get("ohang_strength_jijangan_v1") or {}
    for k in (
        "wood_strength",
        "fire_strength",
        "earth_strength",
        "metal_strength",
        "water_strength",
    ):
        assert k in ohj
    vj = doc.get("vector_4d_jijangan_v1") or {}
    for k in ("S", "L", "K", "M"):
        assert k in vj
    dw = doc.get("daewoon_v1")
    assert isinstance(dw, list) and len(dw) >= 1
    assert dw[0].get("schema") == "daewoon_v1"
    assert dw[0].get("qiyun_applied") is True
    qm = doc.get("daewoon_qiyun_v1") or {}
    assert qm.get("schema") == "qiyun_v1"
    assert "qiyun_years_float" in qm
    vr = doc.get("vector_4d_rule_school_v1") or {}
    assert sum(vr.get(k, 0) for k in ("S", "L", "K", "M")) == pytest.approx(1.0)
    rs = doc.get("rule_school_mkm_4d_v1") or {}
    assert rs.get("version")
    assert rs.get("vector_4d_blend")


def test_fusion_precomputed_matches_direct() -> None:
    fus = MyeongriCompleteFusion()
    y, m, d, h = 2000, 6, 15, 12
    direct = fus.calculate_complete_fusion(y, m, d, h, is_solar=True, is_male=True)
    raw = PerfectManseryeok().calculate_full_saju_perfect(y, m, d, h, True, True)
    pre = fus.calculate_complete_fusion(
        y, m, d, h, is_solar=True, is_male=True, precomputed_full_saju=raw
    )
    for k in ("S", "L", "K", "M"):
        assert direct["vector_4d_rule_school_v1"][k] == pytest.approx(
            pre["vector_4d_rule_school_v1"][k]
        )
