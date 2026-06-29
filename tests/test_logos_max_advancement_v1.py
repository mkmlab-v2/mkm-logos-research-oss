"""Logos corpus enrichment + max advancement chain smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/final/artifacts/logos_motif_corpus_enrichment_report_v1_latest.json"
OVERLAY = ROOT / "docs/final/artifacts/logos_motif_corpus_enriched_overlay_v1.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"


@pytest.fixture(scope="module")
def advancement_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_max_advancement_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_corpus_enrichment_hit_rate(advancement_chain: None) -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    if report["targets"] == 0:
        assert overlay["entry_count"] >= 55
    else:
        assert report["hits"] >= 55
        assert report["hit_rate"] >= 0.9


def test_overlay_has_verse_level_raw(advancement_chain: None) -> None:
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    fire = next(e for e in overlay["entries"] if e["slot_id"] == "motif_041")
    raw = fire["gematria_texts"]["raw"]
    assert len(raw) > len(fire["gematria_texts"]["compressed"])
    assert fire["corpus_enrichment_v1"]["corpus_verse_id"] == "Heb.12.29"


def test_registry_motif_041_verse_unit(advancement_chain: None) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    row = next(e for e in reg["entries"] if e["slot_id"] == "motif_041")
    assert row["corpus_enrichment_v1"]["unit"] == "verse"
    assert len(row["gematria_texts"]["raw"]) > 10
