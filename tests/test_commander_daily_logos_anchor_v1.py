"""Logos daily anchor — theme pick from fusion context."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import commander_daily_logos_anchor_v1 as logos  # noqa: E402


def test_score_theme_stems_month_ten_god() -> None:
    map_doc = json.loads(
        (ROOT / "data/lifestyle/logos_daily_theme_map_v1.json").read_text(encoding="utf-8")
    )
    stem, reasons, _ = logos._score_theme_stems(
        map_doc=map_doc,
        mo_tg="상관",
        weather_band="mild",
        sasang="태양인",
        weak_el="화",
        calendar_kst="2026-05-22",
    )
    assert stem in map_doc["ten_god_month"]["상관"]
    assert any("ten_god_month" in r for r in reasons)


def test_build_logos_anchor_telegram_has_non_gating(tmp_path: Path) -> None:
    profile = {
        "schema": "commander_profile_v1",
        "sasang_reference": {"label": "태양인"},
    }
    report = {
        "monthly_fortune": {
            "rows": [
                {
                    "year": 2026,
                    "month": 5,
                    "wolwoon_stem_ten_god": "상관",
                    "wolwoon_pillar": "계사",
                }
            ]
        },
        "structure_analysis": {
            "element_profile": {
                "dominant_element_visible": "토",
                "weakest_element_visible": "화",
            }
        },
    }
    lifestyle = {"weather_band": "rain", "sasang_label": "태양인"}
    payload = logos.build_logos_anchor(
        profile,
        report,
        lifestyle=lifestyle,
        myeongni_headline_ko="월운 상관 과부하",
        use_ann=False,
    )
    text = "\n".join(payload.get("telegram_append_lines") or [])
    assert "[NON_GATING]" in text
    assert "앵커:" in text
    assert payload.get("golden_anchor", {}).get("ref")
