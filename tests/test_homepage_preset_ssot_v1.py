"""jema-ai.com homepage preset SSOT — default stripe-linear when ?preset= absent."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESET_TS = ROOT / "projects" / "no1kmedi" / "src" / "lib" / "homepagePreset.ts"


def test_homepage_preset_ts_exists() -> None:
    assert PRESET_TS.is_file(), f"missing SSOT: {PRESET_TS}"


def test_default_preset_is_stripe_linear() -> None:
    text = PRESET_TS.read_text(encoding="utf-8")
    assert 'DEFAULT_HOMEPAGE_PRESET = "stripe-linear"' in text
    assert "return homepagePresetClassMap[DEFAULT_HOMEPAGE_PRESET]" in text


def test_page_uses_resolve_homepage_preset() -> None:
    page = ROOT / "projects" / "no1kmedi" / "src" / "app" / "page.tsx"
    text = page.read_text(encoding="utf-8")
    assert "resolveHomepagePresetClass" in text
    assert 'from "@/lib/homepagePreset"' in text
