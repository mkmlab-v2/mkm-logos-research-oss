"""commander_wellness_advisory_v1 — BMI + sasang hints."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.commander_wellness_advisory_v1 import build_wellness_advisory


def test_wellness_170_80_taeyangin() -> None:
    profile = {
        "schema": "commander_profile_v1",
        "anthropometrics": {"height_cm": 170, "weight_kg": 80},
        "sasang_reference": {"label": "태양인"},
    }
    doc = build_wellness_advisory(profile)
    assert doc["schema"] == "commander_wellness_advisory_v1"
    anthro = doc["anthropometrics"]
    assert anthro["bmi"] == 27.7
    assert anthro["bmi_band_key"] == "over"
    tg = "\n".join(doc.get("telegram_append_lines") or [])
    assert "170cm/80kg" in tg
    assert "식이" in tg
    assert "운동" in tg


def test_build_fortune_includes_compact(tmp_path: Path) -> None:
    import scripts.build_commander_daily_fortune_v1 as m

    profile = {
        "schema": "commander_profile_v1",
        "birth_anchor": {
            "birth_instant_utc": "1973-12-09T19:30:00Z",
            "iana_tz": "Asia/Seoul",
            "is_male": True,
        },
        "anthropometrics": {"height_cm": 170, "weight_kg": 80},
        "myeongni_fact_ref": {"daewoon_pillar_label": "기미", "school_decision_engine": "hybrid_guarded"},
        "sasang_reference": {"label": "태양인"},
        "cognition_hypothesis": {"patterns": []},
        "assist_coaching_v1": {"energy_preservation": []},
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
            "rows": [{"year": 2026, "sewoon_pillar": "병오", "sewoon_stem_ten_god": "편관"}]
        },
        "monthly_fortune": {
            "rows": [{"year": 2026, "month": 6, "wolwoon_pillar": "갑오", "wolwoon_stem_ten_god": "편재"}]
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    mission_stub = tmp_path / "MISSION_LOG.md"
    mission_stub.write_text("57.3%", encoding="utf-8")

    payload = m.build_payload(
        profile_path=prof_path,
        skip_regenerate=True,
        include_lens=False,
        report_cache=report_path,
        mission_log=mission_stub,
    )
    compact = payload.get("telegram_compact_lines") or []
    text = "\n".join(compact)
    assert "이번 주 운세" in text
    assert "170cm/80kg" in text or "BMI" in text
    assert any("주간" in ln or "이번 주" in ln for ln in compact)
