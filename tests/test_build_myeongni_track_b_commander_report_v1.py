# -*- coding: utf-8 -*-
from __future__ import annotations

from scripts.build_myeongni_track_b_commander_report_v1 import build_report_payload


def test_report_payload_schema_and_labels():
    p = build_report_payload(
        birth_year=2000,
        birth_month=6,
        birth_day=15,
        birth_hour=12,
        is_solar=True,
        is_male=True,
        precomputed_full_saju=None,
    )
    assert p["schema"] == "myeongni_track_b_commander_report_v1"
    assert "TRACK_B" in p["labels"]
    assert p["envelope"]["human_review_required"] is True
    assert p["axes_snapshot"]["four_pillars_ganji"]
    assert p["axes_snapshot"]["vector_4d_rule_school_v1"]
    assert "full_fusion_payload" in p
    assert p["commander_notes"] is None
    assert p["handoff"]["schema_contract"] == "myeongni_track_b_commander_report_v1"
    assert "NotebookLM_sources_manifest.md" in p["handoff"]["notebooklm"]["manifest_pointer"]


def test_report_commander_notes_optional():
    p = build_report_payload(
        birth_year=2000,
        birth_month=1,
        birth_day=1,
        birth_hour=0,
        is_solar=False,
        is_male=False,
        precomputed_full_saju=None,
        commander_notes="검토 메모 테스트",
    )
    assert p["commander_notes"] == "검토 메모 테스트"
    assert p["version"] == "1.1.0"


def test_report_with_precomputed(tmp_path):
    from scripts.manseryeok_perfect_final import PerfectManseryeok

    raw = PerfectManseryeok().calculate_full_saju_perfect(1992, 3, 12, 17, True, True)
    path = tmp_path / "raw.json"
    import json

    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    pre = json.loads(path.read_text(encoding="utf-8"))
    p = build_report_payload(
        birth_year=1992,
        birth_month=3,
        birth_day=12,
        birth_hour=17,
        is_solar=True,
        is_male=True,
        precomputed_full_saju=pre,
    )
    assert p["birth_input"]["precomputed_manseryeok"] is True
