# -*- coding: utf-8 -*-
"""Smoke: MyeongriCompleteFusion returns 4D vector (B-track)."""

from __future__ import annotations

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion


def test_myeongri_complete_fusion_vector_4d() -> None:
    doc = MyeongriCompleteFusion().calculate_complete_fusion(
        2000, 6, 15, 12, is_solar=True, is_male=True
    )
    v = doc.get("vector_4d") or {}
    for k in ("S", "L", "K", "M"):
        assert k in v
        assert isinstance(v[k], (int, float))
