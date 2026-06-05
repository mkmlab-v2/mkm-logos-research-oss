"""Lemma-verse edges Phase 1 stub."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_lemma_verse_edges_v1.py"
MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"


def test_build_logos_lemma_verse_edges_v1():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_lemma_verse_edges_v1"
    assert doc["edge_count"] >= 10


def test_build_logos_lemma_verse_edges_registry():
    registry = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--registry-json",
            str(registry),
            "--no-graph-heuristic",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert doc.get("bridge_sources_count", 0) >= 5
    assert doc["edge_count"] >= 40
    jsonl = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"
    first = json.loads(jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert first.get("edge_type") == "CONTAIN"
