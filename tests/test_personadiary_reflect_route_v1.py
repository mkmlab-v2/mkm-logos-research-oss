"""PersonaDiary reflect template — server-side text builder parity."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assemble_personadiary_daily_response_package_v1 as pd  # noqa: E402


def test_reflect_template_substitutes_user() -> None:
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "city_default": "Seoul",
        "telegram_append_lines": [
            "▸ 개인 일운 (명리)",
            "  한 줄 테스트",
            "▸ 오늘 라이프 (명리×날씨×체질) [가설]",
            "  점심: 국밥",
        ],
        "logos_daily_anchor": {},
    }
    pkg = pd.assemble_package(fortune, fortune_path=Path("x.json"))
    tpl = pkg["reflect_template_ko"]
    out = tpl.replace("{user}", "오늘 마음")
    assert "오늘 마음" in out
    assert "{user}" not in out
