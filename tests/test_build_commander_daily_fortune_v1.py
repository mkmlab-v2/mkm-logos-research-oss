"""Smoke tests for commander daily fortune telegram lines."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_commander_daily_fortune_v1 as m


def test_build_payload_uses_profile_and_report(tmp_path: Path) -> None:
    profile = {
        "schema": "commander_profile_v1",
        "birth_anchor": {
            "birth_instant_utc": "1973-12-09T19:30:00Z",
            "iana_tz": "Asia/Seoul",
            "is_male": True,
        },
        "myeongni_fact_ref": {
            "daewoon_pillar_label": "기미",
            "school_decision_engine": "hybrid_guarded",
        },
        "sasang_reference": {"label": "태양인"},
        "cognition_hypothesis": {"patterns": ["패턴 A [HYPO]"]},
        "assist_coaching_v1": {"energy_preservation": ["에너지 보존 [HYPO]"]},
    }
    prof_path = tmp_path / "profile.json"
    prof_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")

    report = {
        "pillars": {"year": "계축", "month": "갑자", "day": "경진", "hour": "무인"},
        "day_master": {"stem_hangul": "경", "stem_element_hint": "금(陽)"},
        "structure_analysis": {
            "day_master_strength_hint": {"strength_label": "중약"},
            "element_profile": {"dominant_element_visible": "토", "weakest_element_visible": "화"},
        },
        "annual_fortune": {
            "rows": [
                {
                    "year": 2026,
                    "sewoon_pillar": "병오",
                    "sewoon_stem_ten_god": "편관",
                }
            ]
        },
        "monthly_fortune": {
            "rows": [
                {
                    "year": 2026,
                    "month": 5,
                    "wolwoon_pillar": "계사",
                    "wolwoon_stem_ten_god": "상관",
                }
            ]
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    mission_stub = tmp_path / "MISSION_LOG.md"
    mission_stub.write_text("57.3% ACTIVE O-P29b · 파수 + 상용 · gates **reject**", encoding="utf-8")

    payload = m.build_payload(
        profile_path=prof_path,
        skip_regenerate=True,
        include_lens=False,
        report_cache=report_path,
        mission_log=mission_stub,
    )
    assert payload["schema"] in ("commander_daily_fortune_v1", "commander_daily_fortune_v1_1")
    assert any("명리" in ln for ln in payload["telegram_append_lines"])
    assert any("MKM 4AI" in ln for ln in payload["telegram_append_lines"])
    assert any("태양" in ln for ln in payload["mkm_ai_lines"])
