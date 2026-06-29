"""PersonaDiary ritual draw LUT v1 — schema and deck size."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LUT = ROOT / "projects/no1kmedi/public/data/personadiary_ritual_draw_lut_major22_v1.json"


def test_lut_schema_and_major22_deck() -> None:
    doc = json.loads(LUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "personadiary_ritual_draw_lut_major22_v1"
    assert doc.get("preview_only") is True
    cards = doc["cards"]
    assert len(cards) == 22
    ids = {c["card_id"] for c in cards}
    assert len(ids) == 22
    for c in cards:
        assert c["atom_id"].startswith("pd_atom_")
        assert c["reflect_prompt_ko"]
        assert "[NON_GATING]" in c["logos_hint_ko"]
        assert "[HYPO]" in c["sasang_metaphor_ko"]
        blob = json.dumps(c, ensure_ascii=False)
        assert "위장" not in blob
        assert "간장" not in blob
