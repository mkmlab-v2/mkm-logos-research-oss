"""Wave 2.5 spread-tuning dual-gate tests (B-track sandbox)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DUAL_GATE = ROOT / "docs/final/artifacts/logos_anchor_resonance_dual_gate_latest.json"
SANDBOX_STATS = ROOT / "docs/final/artifacts/logos_anchor_resonance_stats_sandbox_latest.json"
PROD_STATS = ROOT / "docs/final/artifacts/logos_anchor_resonance_stats_latest.json"


def _run_chain() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_spread_tuning_chain_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


@pytest.fixture(scope="module")
def wave25_chain() -> None:
    _run_chain()


def test_sandbox_bridge_spread_exceeds_production() -> None:
    from scripts.core.gematria_engine import build_gematria_metadata
    from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge
    from scripts.core.gematria_to_4d_bridge_sandbox_v1 import (
        build_gematria_4d_bridge_sandbox,
        vector_spread_4d,
    )

    meta = build_gematria_metadata(
        raw_text="σπερμα αμην λεγω",
        compressed_text="σπερμα",
        reconstructed_text="κοκκος σιτου",
    )
    prod = build_gematria_4d_bridge(gematria_metadata=meta)["vector_4d"]
    sand = build_gematria_4d_bridge_sandbox(gematria_metadata=meta)["vector_4d"]
    assert vector_spread_4d(sand) > vector_spread_4d(prod)


def test_dual_gate_artifacts(wave25_chain: None) -> None:
    dual = json.loads(DUAL_GATE.read_text(encoding="utf-8"))
    assert dual["schema"] == "logos_anchor_resonance_dual_gate_v1"
    assert "gate_a_ranking_production" in dual["gates"]
    assert "gate_b_prime_geometry_sandbox" in dual["gates"]


def test_gate_a_ranking_passes(wave25_chain: None) -> None:
    dual = json.loads(DUAL_GATE.read_text(encoding="utf-8"))
    assert dual["wave25_pass"]["ranking_production"] is True
    prod = json.loads(PROD_STATS.read_text(encoding="utf-8"))
    assert prod["summary"]["gate_ranking"]["pass"] is True
    assert float(prod["summary"]["harmony_top1_share"]) <= 0.65


def test_gate_b_prime_sandbox_spread_passes(wave25_chain: None) -> None:
    dual = json.loads(DUAL_GATE.read_text(encoding="utf-8"))
    assert dual["wave25_pass"]["geometry_sandbox"] is True
    sand = json.loads(SANDBOX_STATS.read_text(encoding="utf-8"))
    assert sand["bridge_layer"] == "sandbox"
    assert sand["recipe_id"] == "gematria_bridge_sandbox_v1"
    assert float(sand["summary"]["mean_spread_4d"]) >= 0.08


def test_all_research_gates_pass(wave25_chain: None) -> None:
    dual = json.loads(DUAL_GATE.read_text(encoding="utf-8"))
    assert dual["wave25_pass"]["all_research_gates"] is True


def test_human_gate_motifs_enabled_count(wave25_chain: None) -> None:
    reg = json.loads(
        (ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert reg["enabled_count"] >= 100
    extension = int(reg.get("corpus_expansion_extension_count") or 0)
    if extension:
        assert extension >= 100
        assert reg["enabled_count"] >= 100 + extension
    assert reg["placeholder_count"] == 0
    wave25 = [
        e.get("primitive_bias")
        for e in reg["entries"]
        if e.get("source") == "human_gate_wave25"
    ]
    assert wave25.count("pathology") == 5
    assert wave25.count("survival") == 5
    merged = [
        e
        for e in reg["entries"]
        if e.get("source")
        in (
            "human_gate_queue_v1_merged",
            "human_gate_queue_v1_corpus_enriched",
        )
    ]
    assert len(merged) == 60
    expansion_enabled = [
        e for e in reg["entries"] if e.get("enabled") and int(e["slot_id"].split("_")[1]) >= 101
    ]
    assert len(expansion_enabled) == reg.get("corpus_expansion_extension_count", 100)
