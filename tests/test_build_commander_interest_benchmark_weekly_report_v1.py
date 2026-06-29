from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_commander_ai_native_briefing_pack_v1 import build_pack  # noqa: E402
from build_commander_interest_benchmark_weekly_report_v1 import build_payload  # noqa: E402
from commander_interest_benchmark_v1_lib import EXAMPLE_LOG  # noqa: E402


def test_weekly_report_ranks_by_engagement(tmp_path: Path) -> None:
    log_path = tmp_path / "signals.jsonl"
    rows = [
        {
            "schema": "commander_interest_signal_v1",
            "observed_at_utc": "2026-06-22T09:15:00Z",
            "topic_id": "ai_native_systems",
            "platform": "blog",
            "title": "High",
            "url": "https://cursor.com/changelog",
            "engagement_score": 100.0,
        },
        {
            "schema": "commander_interest_signal_v1",
            "observed_at_utc": "2026-06-21T14:30:00Z",
            "topic_id": "business_automation",
            "platform": "web",
            "title": "Low",
            "url": "https://n8n.io/",
            "engagement_score": 10.0,
        },
    ]
    log_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    cfg = ROOT / "docs/final/artifacts/commander_interest_benchmark_config_v1.default.json"
    payload = build_payload(config_path=cfg, log_path=log_path, window_days=30, top_n=3)
    assert payload["schema"] == "commander_interest_benchmark_weekly_v1"
    assert payload["signals_in_window"] == 2
    top = payload["top_items"]
    assert len(top) == 2
    assert top[0]["engagement_score"] >= top[1]["engagement_score"]


def test_weekly_report_excludes_example_urls(tmp_path: Path) -> None:
    log_path = tmp_path / "signals.jsonl"
    log_path.write_text(EXAMPLE_LOG.read_text(encoding="utf-8-sig"), encoding="utf-8")
    cfg = ROOT / "docs/final/artifacts/commander_interest_benchmark_config_v1.default.json"
    payload = build_payload(config_path=cfg, log_path=log_path, window_days=30, top_n=20)
    urls = [str(i.get("url") or "") for i in payload["top_items"]]
    assert not any("example.com" in u for u in urls)
    assert payload["signals_in_window"] == 0


def test_clinic_sns_topic_label_resolves(tmp_path: Path) -> None:
    log_path = tmp_path / "signals.jsonl"
    row = {
        "schema": "commander_interest_signal_v1",
        "observed_at_utc": "2026-06-21T18:00:00Z",
        "topic_id": "clinic_sns_content_benchmark",
        "platform": "instagram",
        "title": "클리닉 웰빙 릴스",
        "url": "https://www.instagram.com/reel/example",
        "engagement_score": 100.0,
    }
    log_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    cfg = ROOT / "docs/final/artifacts/commander_interest_benchmark_config_v1.default.json"
    payload = build_payload(config_path=cfg, log_path=log_path, window_days=30, top_n=10)
    clinic = [i for i in payload["top_items"] if i["topic_id"] == "clinic_sns_content_benchmark"]
    assert len(clinic) == 1
    assert clinic[0]["topic_label_ko"] == "한의원·클리닉 SNS 콘텐츠"


def test_briefing_pack_writes_three_md_sections() -> None:
    weekly = {
        "generated_at_utc": "2026-06-23T12:00:00Z",
        "top_items": [
            {
                "topic_id": "ai_native_systems",
                "topic_label_ko": "AI 네이티브",
                "platform": "youtube",
                "title": "Sample title",
                "engagement_score": 100.0,
                "likes": 10,
                "comments": 2,
            }
        ],
        "track_wall": {"send_gate": "HOLD"},
        "disclaimer_ko": "test",
    }
    pack = build_pack(weekly, max_cards=1)
    assert pack["schema"] == "commander_ai_native_briefing_pack_v1"
    assert "Sample title" in pack["_md"]["briefing"]
    assert "카드 1" in pack["_md"]["card_news"]
    assert "오프닝" in pack["_md"]["podcast_script"]
