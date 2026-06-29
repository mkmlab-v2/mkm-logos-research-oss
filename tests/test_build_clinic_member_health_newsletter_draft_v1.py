from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_clinic_member_health_newsletter_draft_v1 import build_newsletter  # noqa: E402
from send_clinic_member_health_newsletter_telegram_v1 import build_text  # noqa: E402


def test_health_newsletter_has_wellness_bullets_and_disclaimer() -> None:
    weekly = {
        "generated_at_utc": "2026-06-23T12:00:00Z",
        "top_items": [],
        "track_wall": {"send_gate": "HOLD"},
    }
    cfg = json.loads(
        (ROOT / "docs/final/artifacts/clinic_member_health_newsletter_config_v1.default.json").read_text(
            encoding="utf-8-sig"
        )
    )
    doc = build_newsletter(weekly, cfg)
    md = doc["_md"]
    tg = doc["_telegram"]
    assert "비진단" in md or "참고" in md
    assert "진단·치료" in md or "진단" in tg
    assert doc["wellness_bullet_count"] >= 3
    assert doc["track_wall"].get("send_gate") == "HOLD" or weekly["track_wall"]["send_gate"] == "HOLD"


def test_health_newsletter_includes_clinic_refs() -> None:
    weekly = {
        "generated_at_utc": "2026-06-23T12:00:00Z",
        "top_items": [
            {
                "topic_id": "clinic_sns_content_benchmark",
                "title": "웰빙 릴스 포맷",
                "platform": "instagram",
                "url": "https://www.instagram.com/reel/example",
            }
        ],
    }
    cfg = json.loads(
        (ROOT / "docs/final/artifacts/clinic_member_health_newsletter_config_v1.default.json").read_text(
            encoding="utf-8-sig"
        )
    )
    doc = build_newsletter(weekly, cfg)
    assert doc["clinic_reference_count"] == 1
    assert "웰빙 릴스 포맷" in doc["_telegram"]
    assert "벤치마킹" in doc["_md"] or "참고" in doc["_md"]


def test_telegram_build_text_from_draft_json() -> None:
    draft = {
        "telegram_text": "🌿 테스트\n※ 면책 문구",
    }
    assert "테스트" in build_text(draft)
