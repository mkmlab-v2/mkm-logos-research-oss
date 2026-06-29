"""PersonaDiary Ollama polish hook [HYPO]."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import polish_personadiary_moment_copy_v1 as polish  # noqa: E402
import assemble_personadiary_moment_response_v1 as asm  # noqa: E402


def _pkg() -> dict:
    return {
        "schema": "personadiary_daily_response_package_v1",
        "calendar_kst": "2026-06-06",
        "sections": [
            {
                "id": "lifestyle",
                "title_ko": "라이프",
                "lines": ["점심 추천: 닭곰탕", "날씨·서울: 16°C"],
            },
            {"id": "myeongni", "title_ko": "명리", "lines": ["일운 한 줄"]},
        ],
        "ui_blocks": [
            {
                "type": "hero",
                "title_ko": "가이드",
                "body_ko": "날씨 · 서울: 16°C · 양호",
            }
        ],
        "disclaimer_ko": "테스트",
    }


def test_polish_disabled_returns_none() -> None:
    with patch.object(polish, "polish_enabled", return_value=False):
        out, meta = polish.ollama_polish_summary("점심 추천: 국밥", intent="meal", query="점심?")
    assert out is None
    assert meta.get("reason") == "disabled"


def test_enrich_package_attaches_preset_block() -> None:
    pkg = _pkg()
    with patch.object(
        polish,
        "ollama_polish_summary",
        side_effect=lambda summary, **kw: (f"다듬음:{summary[:12]}", {"applied": True}),
    ):
        polish.enrich_package_with_preset_polish(pkg, force=True)
    block = pkg.get("moment_preset_polish_v1") or {}
    assert block.get("schema") == "personadiary_moment_preset_polish_v1"
    assert "meal" in (block.get("presets") or {})
    assert block["presets"]["meal"]["summary_ko_polished"].startswith("다듬음:")


def test_ts_mirror_preset_match_logic_via_assembler() -> None:
    """Python-side: canonical meal query routes to meal intent with menu summary."""
    pkg = _pkg()
    moment = asm.assemble_moment_response(pkg, polish.PRESET_QUERIES["meal"])
    assert moment["intent"] == "meal"
    summary = moment["summary_ko"]
    assert any(k in summary for k in ("곰탕", "국밥", "닭곰탕", "점심", "메뉴"))
