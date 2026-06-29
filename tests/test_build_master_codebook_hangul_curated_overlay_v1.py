"""Curated Hangul overlay — manifest cap and overlay row count."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/hangul_lexicon_curated_lemma_manifest_v1.json"
OVERLAY = (
    ROOT
    / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_hangul_curated_overlay.json"
)


def test_manifest_lemma_count_at_most_50():
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lemmas = doc.get("lemmas") or doc.get("entries") or []
    assert len(lemmas) <= 50
    assert len(lemmas) >= 1


def test_curated_overlay_has_ko_rows_when_built():
    if not OVERLAY.is_file():
        return
    doc = json.loads(OVERLAY.read_text(encoding="utf-8"))
    rows = doc.get("entries") if isinstance(doc, dict) else doc
    assert isinstance(rows, list)
    ko = [r for r in rows if str(r.get("lang", "")).lower() == "ko"]
    assert len(ko) >= 1
