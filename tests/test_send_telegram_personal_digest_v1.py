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


def test_resolve_style_default_personal(monkeypatch) -> None:
    monkeypatch.delenv("MKM_TELEGRAM_DIGEST_STYLE", raising=False)
    assert tg._resolve_style(None) == "personal"
