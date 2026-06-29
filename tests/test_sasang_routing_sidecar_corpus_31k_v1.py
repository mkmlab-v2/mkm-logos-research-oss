"""B-track: 31k Logos corpus sasang routing sidecar overlay (not Track A)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/logos_verse_4pipeline_minimal_manifest_v1.json"
MANIFEST = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_manifest_v1_latest.json"
JSONL = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
GATE = ROOT / "reports/sasang_routing_sidecar_corpus_31k_gate_v1_latest.json"
GRAPH = ROOT / "docs/final/artifacts/logos_corpus_sasang_routing_graph_bundle_v1_latest.json"
CHAIN = ROOT / "reports/sasang_routing_sidecar_corpus_31k_chain_v1_latest.json"


def test_corpus_build_fixture_limit3(tmp_path: Path) -> None:
    jsonl = tmp_path / "sidecar.jsonl"
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.json"
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/build_sasang_routing_sidecar_corpus_31k_v1.py",
            "--corpus",
            str(FIXTURE),
            "--limit",
            "3",
            "--jsonl",
            str(jsonl),
            "--manifest",
            str(manifest),
            "--report",
            str(report),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert manifest.is_file()
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["schema"] == "sasang_routing_sidecar_corpus_31k_manifest_v1"
    assert doc["verse_count"] == 3
    assert doc["send_gate"] == "HOLD"
    assert doc["track_a_blocked"] is True
    assert doc["track_a_promotion"] is False
    assert jsonl.is_file()


def test_corpus_gate_partial(tmp_path: Path) -> None:
    jsonl = tmp_path / "sidecar.jsonl"
    manifest = tmp_path / "manifest.json"
    report = tmp_path / "report.json"
    gate_out = tmp_path / "gate.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_sasang_routing_sidecar_corpus_31k_v1.py",
            "--corpus",
            str(FIXTURE),
            "--limit",
            "3",
            "--jsonl",
            str(jsonl),
            "--manifest",
            str(manifest),
            "--report",
            str(report),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/check_sasang_routing_sidecar_corpus_31k_v1.py",
            "--manifest",
            str(manifest),
            "--out",
            str(gate_out),
            "--allow-partial",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    assert gate_out.is_file()


def test_graph_bundle_after_fixture_build(tmp_path: Path) -> None:
    jsonl = tmp_path / "sidecar.jsonl"
    manifest = tmp_path / "manifest.json"
    graph_out = tmp_path / "graph.json"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_sasang_routing_sidecar_corpus_31k_v1.py",
            "--corpus",
            str(FIXTURE),
            "--limit",
            "3",
            "--jsonl",
            str(jsonl),
            "--manifest",
            str(manifest),
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            "scripts/build_logos_corpus_sasang_routing_graph_bundle_v1.py",
            "--manifest",
            str(manifest),
            "--jsonl",
            str(jsonl),
            "--out",
            str(graph_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    doc = json.loads(graph_out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_corpus_sasang_routing_graph_bundle_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["corpus_verse_count"] == 3


def test_corpus_full_build_and_gate() -> None:
    corpus = ROOT / "data/logos/verse_4pipeline_full_31102.json"
    if not corpus.is_file():
        return
    cp = subprocess.run(
        [sys.executable, "scripts/build_sasang_routing_sidecar_corpus_31k_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["verse_count"] == 31102

    cp = subprocess.run(
        [sys.executable, "scripts/check_sasang_routing_sidecar_corpus_31k_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    assert gate["g2_substatus"] == "corpus_v1_complete"
