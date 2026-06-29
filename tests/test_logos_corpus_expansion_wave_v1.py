"""Corpus expansion wave1 merge + dual-gate."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXPANSION = ROOT / "docs/final/artifacts/logos_corpus_expansion_extensions_v1.json"
DUAL = ROOT / "docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"


@pytest.fixture(scope="module")
def wave_chain() -> None:
    """Assumes disk SSOT already built by run_logos_corpus_expansion_wave_chain_v1.py."""
    assert EXPANSION.is_file()
    assert REGISTRY.is_file()


def test_expansion_extensions_wave3(wave_chain: None) -> None:
    doc = json.loads(EXPANSION.read_text(encoding="utf-8"))
    assert doc["entry_count"] == 239
    assert doc.get("wave_last") == 3
    assert 3 in doc.get("waves_present", [])


def test_registry_339_enabled(wave_chain: None) -> None:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    assert reg["enabled_count"] == 339
    assert reg["corpus_expansion_extension_count"] == 239


def test_dual_gate_still_passes_research(wave_chain: None) -> None:
    dual = json.loads(DUAL.read_text(encoding="utf-8"))
    assert dual["wave25_pass"]["all_research_gates"] is True
    assert float(dual["gates"]["gate_a_ranking_production"]["harmony_top1_share"]) <= 0.65
