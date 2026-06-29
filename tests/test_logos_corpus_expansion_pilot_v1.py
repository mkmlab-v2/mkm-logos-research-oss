"""Corpus expansion Phase 0+1 — pilot, sidecar, human gate queue."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/logos_verse_4pipeline_minimal_manifest_v1.json"
PILOT = ROOT / "docs/final/artifacts/logos_corpus_expansion_pilot_v1_latest.json"
SIDECAR = ROOT / "data/logos/sidecar_apocrypha_dss_hypo_v1.jsonl"
QUEUE = ROOT / "docs/final/artifacts/logos_corpus_expansion_human_gate_queue_v1_latest.json"
REGISTRY = ROOT / "docs/final/artifacts/logos_motif_registry_top100_v1.json"


@pytest.fixture(scope="module")
def expansion_setup() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/run_logos_corpus_expansion_setup_v1.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_sidecar_container_exists(expansion_setup: None) -> None:
    assert SIDECAR.is_file()


def test_pilot_report_schema(expansion_setup: None) -> None:
    doc = json.loads(PILOT.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_corpus_expansion_pilot_v1"
    assert doc["materialize_batch"] is False
    scan = doc["tier1_scan"]
    assert scan["verse_count"] >= 30000
    assert scan["motif_lexicon_size"] >= 100
    assert "skew_warning" in scan


def test_human_gate_queue_build_wave1(expansion_setup: None) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_logos_corpus_expansion_human_gate_queue_v1.py",
            "--wave",
            "1",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    q = json.loads(QUEUE.read_text(encoding="utf-8"))
    assert q["schema"] == "logos_corpus_expansion_human_gate_queue_v1"
    assert q["wave"] == 1
    assert q["queue_count"] > 0
    assert all(e["status"] == "human_gate_proposed" for e in q["entries"])
    assert all(e["enabled"] is False for e in q["entries"])


def test_pilot_fixture_scan() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_logos_corpus_expansion_pilot_v1.py",
            "--corpus",
            str(FIXTURE),
            "--out",
            str(ROOT / "docs/final/artifacts/logos_corpus_expansion_pilot_fixture_v1.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/logos_corpus_expansion_pilot_fixture_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc["tier1_scan"]["verse_count"] == 3
