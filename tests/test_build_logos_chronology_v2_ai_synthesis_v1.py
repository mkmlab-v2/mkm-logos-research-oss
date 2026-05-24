"""Schema smoke for AI-synthesized chronology v2."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.build_logos_chronology_v2_ai_synthesis_v1 import build_document, _validate


def test_v2_synthesis_schema_and_counts() -> None:
    doc = build_document()
    _validate(doc)
    assert doc["schema"] == "logos_chronology_v1"
    assert doc["hypothesis_tier"] == "[HYPO]"
    assert len(doc["eras"]) == 11
    assert len(doc["modern_bridges"]) >= 18
    era_ids = {e["era_id"] for e in doc["eras"]}
    assert "modern_observational_field" in era_ids
    for e in doc["eras"]:
        assert e["interpretation_class"] == "[HYPO]"


def test_v2_fixture_on_disk_if_present() -> None:
    path = Path(__file__).resolve().parents[1] / "docs/final/artifacts/logos_chronology_v2_ai_synthesis_v1.json"
    if not path.is_file():
        return
    doc = json.loads(path.read_text(encoding="utf-8"))
    _validate(doc)
    assert len(doc["eras"]) == 11
