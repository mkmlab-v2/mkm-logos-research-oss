"""PersonaDiary A-Code public persona layer contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "projects/no1kmedi/src/lib/personadiaryAcodeProfileV1.ts"


def test_acode_persona_module_exports() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert "personadiary_acode_persona_v1" in text
    assert "derivePersonadiaryAcodeProfile" in text
    assert "AC-" in text


def test_moment_intent_section_titles_consumer_safe() -> None:
    import json

    weights = json.loads(
        (ROOT / "projects/no1kmedi/public/data/personadiary_moment_intent_weights_v1.json").read_text(
            encoding="utf-8"
        )
    )
    titles = weights.get("section_titles_ko") or {}
    joined = " ".join(titles.values())
    assert "명리" not in joined
    assert "4AI" not in joined
    assert "체질" not in joined

