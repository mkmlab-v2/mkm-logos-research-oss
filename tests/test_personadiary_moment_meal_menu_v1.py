"""PersonaDiary moment meal menu v1 — menu type without venue."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryMomentMealMenuV1.ts"


def test_meal_menu_module_exports() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert "personadiary_moment_meal_menu_v1" in text
    assert "buildMomentMealMenuRecommendation" in text
    assert "stripLocationFromMealText" in text


def test_strip_location_from_meal_text_logic_present() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert "역" in text
    assert "골목" in text
    assert "pickHyperLocalPoi" not in text
