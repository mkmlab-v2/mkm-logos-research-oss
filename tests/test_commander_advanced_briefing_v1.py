"""Advanced briefing + evening score rail."""

from __future__ import annotations

import json
from pathlib import Path

import scripts.build_commander_telegram_advanced_briefing_v1 as adv


def test_build_advanced_briefing_has_predictions(tmp_path: Path) -> None:
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "myeongni_lines": ["▸ 오늘 한 줄: 테스트"],
        "mkm_ai_lines": [],
        "world_pulse_fusion": {
            "fusion_one_liner_ko": "융합",
            "kospi": {"today_action": "WATCH"},
            "body_lines": [],
        },
        "hypothesis_stream": {
            "synthesis_ko": "초론",
            "market_tone": "caution",
            "branches": [
                {
                    "branch_id": "test",
                    "trigger_ko": "t",
                    "predicted_bias_ko": "b",
                    "confidence": "mid",
                }
            ],
        },
        "user_condition": {},
        "telegram_append_lines": [],
    }
    fpath = tmp_path / "fortune.json"
    fpath.write_text(json.dumps(fortune), encoding="utf-8")
    doc = adv.build_advanced_briefing_doc(tmp_path, fortune_path=fpath)
    assert doc["schema"] == "commander_telegram_advanced_briefing_v1"
    assert doc["n_predictions"] >= 2
    assert doc.get("briefing_id")
    text = adv.build_telegram_text(doc)
    assert "찰나의 나라" in text
    assert "오늘 3액션" in text
    assert "20:30 채점" in text
    assert "I-c. cross-lens RAG" in text or "cross-lens RAG" in text
    assert "I-d. 4RAG" in text or "4RAG" in text


def test_evening_score_prediction_outcomes() -> None:
    import scripts.score_commander_evening_briefing_v1 as ev

    pred = {
        "prediction_id": "btrack:hypothesis_prophecy",
        "kind": "btrack_price_hypo",
        "direction_proxy": "up",
    }
    s = ev._score_prediction(pred, market_direction="up")
    assert s["outcome"] == "aligned"
