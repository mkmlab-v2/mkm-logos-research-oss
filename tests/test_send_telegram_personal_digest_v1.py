"""Personal-only Telegram digest — no prophecy English blocks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import send_telegram_minimal_ops_digest_v1 as tg  # noqa: E402


def test_build_digest_personal_only_fortune(tmp_path: Path) -> None:
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "telegram_append_lines": [
            "",
            "▸ 개인 일운 (명리)",
            "  일운 병신",
            "",
            "▸ 오늘 라이프 [HYPO]",
            "  점심: 닭곰탕",
        ],
    }
    (tmp_path / "reports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reports" / "commander_daily_fortune_latest.json").write_text(
        json.dumps(fortune, ensure_ascii=False), encoding="utf-8"
    )
    text = tg.build_digest_personal(tmp_path)
    assert "지휘관 오늘 일운" in text
    assert "KOSPI" not in text
    assert "BTC" not in text
    assert "예언 브리핑" not in text
    assert "닭곰탕" in text
    assert "일운 병신" in text


def test_build_digest_prophecy_korean_no_fortune(tmp_path: Path) -> None:
    art = tmp_path / "docs" / "final" / "artifacts"
    art.mkdir(parents=True, exist_ok=True)
    (art / "internal_kospi_morning_brief_onepager_latest.json").write_text(
        json.dumps(
            {
                "today_action": "HOLD",
                "confidence_0_100": 40,
                "market_session_ko": "휴장(주말)",
                "dual_leg_kospi_n_evaluated": 15,
                "dual_leg_kospi_hit_rate": 0.533333,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (art / "trackc_prophecy_dual_leg_brief_latest.json").write_text(
        json.dumps({"legs": {"btc": {"n_evaluated": 0, "price_directional_hit_rate": None}}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "btrack_hypothesis_prophecy_latest.json").write_text(
        json.dumps({"prediction": {"instrument": "kospi", "direction": "bull", "confidence": 0.71}}, ensure_ascii=False),
        encoding="utf-8",
    )
    (art / "prophecy_hit_rate_eval_latest.json").write_text(
        json.dumps({"metrics": {"price_directional_hit_rate": 0.666667, "n_evaluated": 15}}, ensure_ascii=False),
        encoding="utf-8",
    )
    fortune = tmp_path / "reports" / "commander_daily_fortune_latest.json"
    fortune.parent.mkdir(parents=True, exist_ok=True)
    fortune.write_text(
        json.dumps({"schema": "commander_daily_fortune_v1", "telegram_append_lines": ["▸ 개인 일운"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    text = tg.build_digest_prophecy(tmp_path)
    assert "MKM 장전 예언 브리핑" in text
    assert "관망" in text
    assert "코스피" in text
    assert "상승" in text
    assert "개인 일운" not in text
    assert "R-IBL" not in text
    assert "BTC" not in text
    assert "HYPO" not in text
    assert "Internal brief" not in text
    assert "B-track" not in text
    assert "US prior" not in text


def test_resolve_style_default_prophecy(monkeypatch) -> None:
    monkeypatch.delenv("MKM_TELEGRAM_DIGEST_STYLE", raising=False)
    assert tg._resolve_style(None) == "prophecy"


def test_morning_blocks_evening_review_style(monkeypatch) -> None:
    monkeypatch.setenv("MKM_TELEGRAM_MORNING_KOSPI_ONLY", "1")
    monkeypatch.setattr(tg, "_morning_kospi_only_window", lambda: True)
    assert tg._resolve_style("evening_review") == "evening_review"
