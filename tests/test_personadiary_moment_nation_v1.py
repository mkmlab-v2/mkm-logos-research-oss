"""PersonaDiary moment nation hero parser."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryMomentNationV1.ts"
HERO = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryMomentNationHero.tsx"


def test_moment_nation_artifacts_exist() -> None:
    assert LIB.is_file()
    assert HERO.is_file()
    assert "buildMomentNationView" in LIB.read_text(encoding="utf-8")
    assert "pd-moment-nation-hero" in HERO.read_text(encoding="utf-8")
    assert "pd-acode-persona-v1" in HERO.read_text(encoding="utf-8")


def test_daily_package_has_world_pulse_section() -> None:
    doc = json.loads(PKG.read_text(encoding="utf-8"))
    ids = {s.get("id") for s in doc.get("sections") or []}
    types = {b.get("type") for b in doc.get("ui_blocks") or []}
    assert "world_pulse" in ids
    assert "world_pulse" in types
    hero = next(b for b in doc["ui_blocks"] if b["type"] == "hero")
    assert "찰나의 나라" in hero["title_ko"]
