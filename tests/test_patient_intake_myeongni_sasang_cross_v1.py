# -*- coding: utf-8 -*-
"""[HYPO] myeongni × clinical sasang cross-check v1."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MYE_FIXTURE = ROOT / "reports" / "tmp_soeum_myeongni.json"


def test_soeum_clinical_cross_uses_element_surface():
    from scripts.core.patient_intake_myeongni_sasang_cross_v1 import assess_myeongni_sasang_cross

    if not MYE_FIXTURE.is_file():
        return
    report = json.loads(MYE_FIXTURE.read_text(encoding="utf-8-sig"))
    doc = assess_myeongni_sasang_cross(report, "소음인")
    assert doc["constitution_id"] == "soeum_in"
    assert doc["status"] in ("match", "partial", "mismatch", "insufficient")
    assert doc["element_surface"]["dominant_visible"]


def test_cross_markdown_contains_hypo_label():
    from scripts.core.patient_intake_myeongni_sasang_cross_v1 import render_cross_check_markdown

    report = {
        "structure_analysis": {
            "element_profile": {
                "element_counts_visible": {"목": 1, "화": 1, "토": 3, "금": 0, "수": 1},
                "dominant_element_visible": "토",
                "weakest_element_visible": "금",
            }
        },
        "day_master": {"stem_element_hint": "토(陽)"},
    }
    md = render_cross_check_markdown(report, "소음인")
    assert "교차검증" in md
    assert "[HYPO]" in md
