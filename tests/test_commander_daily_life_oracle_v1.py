"""Tests for commander_daily_life_oracle_v1 — rule-based life topics [HYPO]."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_life_oracle_pian_cai_topics() -> None:
    from scripts.commander_daily_life_oracle_v1 import build_life_oracle

    myeongni_lines = [
        "▸ 오늘 한 줄: 테스트 · 일운 기유 — 별축",
        "월운 6월 갑오(편재) — 기회·이동",
        "세운 병오(편관) — 압박",
        "오행 우세 토 / 약 화",
        "일간 경(금(陽))",
    ]
    lifestyle = {
        "weather_band": "mild",
        "meals": {"lunch_ko": "닭곰탕"},
        "weather_path": str(ROOT / "reports" / "commander_weather_seoul_latest.json"),
    }
    oracle = build_life_oracle(myeongni_lines=myeongni_lines, lifestyle=lifestyle)
    assert oracle["schema"] == "commander_daily_life_oracle_v1"
    topics = oracle["topics"]
    assert "편재" in topics["money_ko"] or "금전" in topics["money_ko"]
    assert topics["food_ko"]
    assert "차" in topics["traffic_ko"] or "이동" in topics["traffic_ko"]
    assert "계약" in topics["contract_ko"] or "서명" in topics["contract_ko"]
    assert "인연" in topics["social_ko"] or "반가운" in topics["social_ko"]
    compact = "\n".join(oracle.get("telegram_compact_lines") or [])
    assert "하루 예언" in compact
    assert "금전" in compact


def test_prophecy_digest_includes_personal_block(monkeypatch, tmp_path: Path) -> None:
    import scripts.send_telegram_minimal_ops_digest_v1 as tg

    ws = tmp_path
    art = ws / "docs/final/artifacts"
    art.mkdir(parents=True)
    for name in (
        "internal_kospi_morning_brief_onepager_latest.json",
        "trackc_prophecy_dual_leg_brief_latest.json",
        "btrack_hypothesis_prophecy_latest.json",
        "prophecy_hit_rate_eval_latest.json",
    ):
        (art / name).write_text("{}", encoding="utf-8")
    rep = ws / "reports"
    rep.mkdir(parents=True)
    (rep / "commander_daily_fortune_latest.json").write_text(
        json.dumps(
            {
                "schema": "commander_daily_fortune_v1_1",
                "telegram_append_lines": [
                    "",
                    "▸ 하루 예언 (명리·생활) [가설]",
                    "  명리: 테스트 한 줄",
                    "  금전: 금전 테스트",
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MKM_TELEGRAM_PROPHECY_INCLUDE_FORTUNE", "1")
    text = tg.build_digest_prophecy(ws)
    assert "하루 예언" in text
    assert "테스트 한 줄" in text
