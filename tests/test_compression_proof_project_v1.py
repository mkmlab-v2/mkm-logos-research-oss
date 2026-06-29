"""Proof Sprint Lv.3 project smoke tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_expand_open_corpus_128() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/expand_compression_open_structured_corpus_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    path = ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 100


def test_golden40_public_safe_corpus_strict() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_compression_golden40_public_safe_corpus_v1.py",
            "--strict",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    manifest = json.loads(
        (ROOT / "docs/final/artifacts/compression_golden40_public_safe_corpus_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest.get("case_count") == 40


@pytest.mark.slow
def test_evidence_chain_skip_handoff() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_compression_evidence_lv1_chain_v1.py",
            "--skip-handoff",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    chain = json.loads(
        (ROOT / "reports/compression_evidence_lv1_chain_v1_latest.json").read_text(encoding="utf-8")
    )
    assert chain.get("proof_sprint_level") == "lv3"
    assert chain.get("chain_ok") is True
