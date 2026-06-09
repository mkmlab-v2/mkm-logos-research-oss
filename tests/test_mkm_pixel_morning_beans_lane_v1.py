from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIXEL_LANG = ROOT / "docs/final/artifacts/MKM_PIXEL_LANGUAGE_V1.json"

REQUIRED_LANES = (
    "field_regime",
    "personal_wellness",
    "family_anchor",
    "learning",
    "place_activity",
    "logos_explain",
)


def test_mkm_pixel_language_morning_beans_lane_registry() -> None:
    doc = json.loads(PIXEL_LANG.read_text(encoding="utf-8"))
    assert doc.get("schema") == "mkm_pixel_language_v1"
    assert doc.get("version") == "1.1"
    registry = doc.get("morning_beans_lane_registry")
    assert isinstance(registry, dict)
    for lane in REQUIRED_LANES:
        entry = registry.get(lane)
        assert isinstance(entry, dict), lane
        assert entry.get("sprite_id", "").startswith("PB_SPR_MB_")
        assert entry.get("sprite_url", "").startswith("https://")
        assert entry.get("sasang_accent") in {"soyang", "taeyang", "taeeum", "soeum"}
