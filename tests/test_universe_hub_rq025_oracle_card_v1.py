"""RQ-025 oracle card fixture for universe hub (no forbidden headline metrics on surface)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARD = ROOT / "projects/no1kmedi/public/data/universe_hub_rq025_oracle_card_v1.json"
FORBIDDEN_SURFACE = ("56.5%", "47.5%", "0.890")


def test_rq025_card_schema_and_last_updated() -> None:
    assert CARD.is_file(), CARD
    doc = json.loads(CARD.read_text(encoding="utf-8"))
    assert doc["schema"] == "universe_hub_rq025_oracle_card_v1"
    assert doc.get("last_updated_utc")
    assert doc.get("research_only") is True
    assert doc.get("hypothesis_tag") == "[HYPO]"


def test_rq025_card_no_forbidden_headline_in_rendered_fields() -> None:
    doc = json.loads(CARD.read_text(encoding="utf-8"))
    render_fields = [
        doc.get("title_ko", ""),
        doc.get("summary_ko", ""),
        doc.get("arms_label_ko", ""),
        doc.get("discovery_note_ko", ""),
    ]
    blob = " ".join(str(x) for x in render_fields)
    for banned in FORBIDDEN_SURFACE:
        assert banned not in blob, f"forbidden {banned} in rendered card fields"
