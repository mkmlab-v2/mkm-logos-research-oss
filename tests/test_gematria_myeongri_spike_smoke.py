# -*- coding: utf-8 -*-
"""Smoke: gematria + myeongri spike blend metrics and schema keys."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.spike_gematria_myeongri_blend_v0 import run_spike


def test_run_spike_yeshua_ad4_default() -> None:
    heb = "\u05d9\u05e9\u05d5\u05e2"
    doc = run_spike(
        hebrew_text=heb,
        birth_year=4,
        birth_month=1,
        birth_day=1,
        birth_hour=12,
        is_solar=True,
        is_male=True,
        blend_weight_myeongri=0.5,
    )
    assert doc["schema"] == "gematria_myeongri_spike_blend_v0"
    m = doc["metrics"]
    assert "l2_vanilla_myeongri" in m and "cosine_vanilla_hybrid" in m
    v = doc["vector_4d"]
    for k in ("vanilla", "myeongri", "hybrid"):
        assert abs(sum(v[k][a] for a in ("S", "L", "K", "M")) - 1.0) < 1e-5
    assert doc["fact_lock"]["independent_lens_fusion_stub_has_consistency_rate"] is False
