"""Lemma-verse edges Phase 1 — isolated tmp outputs (must not mutate production SSOT)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_lemma_verse_edges_v1.py"
PROD_MANIFEST = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1_latest.json"
PROD_JSONL = ROOT / "docs/final/artifacts/logos_lemma_verse_edges_v1.jsonl"


def _prod_snapshot() -> tuple[str | None, int | None]:
    if not PROD_MANIFEST.is_file():
        return None, None
    doc = json.loads(PROD_MANIFEST.read_text(encoding="utf-8"))
    edge_count = int(doc.get("edge_count") or 0)
    lines = 0
    if PROD_JSONL.is_file():
        lines = sum(1 for line in PROD_JSONL.open(encoding="utf-8") if line.strip())
    return doc.get("generated_at_utc"), max(edge_count, lines)


def test_build_logos_lemma_verse_edges_v1(tmp_path: Path) -> None:
    before_ts, before_edges = _prod_snapshot()
    out_jsonl = tmp_path / "edges.jsonl"
    manifest = tmp_path / "manifest.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--out-jsonl",
            str(out_jsonl),
            "--manifest-json",
            str(manifest),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_lemma_verse_edges_v1"
    assert doc["edge_count"] >= 10
    assert out_jsonl.is_file()

    after_ts, after_edges = _prod_snapshot()
    assert after_ts == before_ts
    assert after_edges == before_edges


def test_build_logos_lemma_verse_edges_registry(tmp_path: Path) -> None:
    before_ts, before_edges = _prod_snapshot()
    registry = ROOT / "docs/final/artifacts/logos_concept_bridge_registry_v1_latest.json"
    out_jsonl = tmp_path / "edges_reg.jsonl"
    manifest = tmp_path / "manifest_reg.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--registry-json",
            str(registry),
            "--no-graph-heuristic",
            "--out-jsonl",
            str(out_jsonl),
            "--manifest-json",
            str(manifest),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc.get("bridge_sources_count", 0) >= 5
    assert doc["edge_count"] >= 40
    first = json.loads(out_jsonl.read_text(encoding="utf-8").splitlines()[0])
    assert first.get("edge_type") == "CONTAIN"

    after_ts, after_edges = _prod_snapshot()
    assert after_ts == before_ts
    assert after_edges == before_edges
