"""Tests for merge_logos_chronology_era_presets_v1."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.merge_logos_chronology_era_presets_v1 import merge_presets


def test_merge_presets_adds_five_eras(tmp_path: Path) -> None:
    chrono = {
        "eras": [
            {"era_id": "exodus_passage", "label_ko": "출애굽", "verse_refs": ["aramaic::Exod.12.13"], "notes_ko": "note"},
            {"era_id": "babel_dispersion", "label_ko": "바벨", "verse_refs": [], "theme_tags": ["confusion"]},
        ],
        "modern_bridges": [
            {"era_id": "exodus_passage", "rationale_ko": "bridge one"},
        ],
    }
    doc = {"presets": [{"id": "p1", "prompt_ko": "x", "answer_ko": "y", "highlight_node_ids": []}]}
    merged, added = merge_presets(doc, chrono)
    assert added == 2
    ids = {p["id"] for p in merged["presets"]}
    assert "era_exodus_passage" in ids
    assert "era_babel_dispersion" in ids
    ex = next(p for p in merged["presets"] if p["id"] == "era_exodus_passage")
    assert "bridge one" in ex["answer_ko"]
    assert "era::exodus_passage" in ex["highlight_node_ids"]


def test_merge_idempotent(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    chrono_path = root / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_chronology_overlay_v1.json"
    if not chrono_path.is_file():
        return
    chrono = json.loads(chrono_path.read_text(encoding="utf-8"))
    doc = {"presets": []}
    merged1, a1 = merge_presets(doc, chrono)
    merged2, a2 = merge_presets(merged1, chrono)
    assert a2 == 0
    assert len(merged1["presets"]) == len(merged2["presets"])
