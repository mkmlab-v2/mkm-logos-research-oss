"""PersonaDiary daily response package assembler."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assemble_personadiary_daily_response_package_v1 as pd  # noqa: E402


def test_assemble_from_fortune_fixture() -> None:
    fortune = {
        "schema": "commander_daily_fortune_v1_1",
        "calendar_kst": "2026-05-22",
        "city_default": "Seoul",
        "telegram_append_lines": [
            "",
            "▸ 개인 일운 (명리)",
            "  ▸ 오늘 한 줄: 월운 상관 테스트",
            "",
            "▸ 개인 일운 (MKM 4AI)",
            "  ▸ 태양 AI: 결단",
            "",
            "▸ 오늘 라이프 (명리×날씨×체질) [가설]",
            "  점심 추천: 닭곰탕",
            "",
            "▸ 성경 앵커 (Logos) [NON_GATING][가설]",
            "  앵커: 잠언 3:5 — 신뢰하라",
        ],
        "logos_daily_anchor": {
            "golden_anchor": {"ref": "잠언 3:5", "text": "신뢰하라"},
        },
        "world_pulse_fusion": {
            "fusion_one_liner_ko": "오늘 세계 뉴스 × 지휘관 명리 융합 한 줄 [가설]",
        },
        "hypothesis_stream": {
            "synthesis_ko": "뉴스 흐름과 나의 일운이 교차하는 관측 [HYPO]",
            "branches": [{"label_ko": "매크로", "note_ko": "금리"}],
        },
    }
    pkg = pd.assemble_package(fortune, fortune_path=Path("reports/x.json"))
    assert pkg["schema"] == "personadiary_daily_response_package_v1"
    assert pkg["product"] == "personadiary.com"
    assert len(pkg["sections"]) >= 3
    assert any(b["type"] == "verse" for b in pkg["ui_blocks"])
    news = next(b for b in pkg["ui_blocks"] if b["type"] == "news_me_hypo")
    assert "오늘의 뉴스 × 나" in news["title_ko"]
    assert news.get("mkmlife_href", "").startswith("https://mkmlife.com")
    assert pkg["upstream"].get("kernel_skins_ref")
    assert "{user}" in pkg["reflect_template_ko"]
