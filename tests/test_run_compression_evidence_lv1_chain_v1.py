"""Smoke for compression evidence Lv1/Lv2 chain runner."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CHAIN = ROOT / "scripts" / "run_compression_evidence_lv1_chain_v1.py"
REPRODUCE = ROOT / "scripts" / "build_compression_public_reproduce_pack_v1.py"
CORPUS = ROOT / "scripts" / "build_compression_open_structured_corpus_v1.py"


def test_open_structured_corpus_manifest_strict() -> None:
    proc = subprocess.run(
        [sys.executable, str(CORPUS), "--strict"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_reproduce_pack_builder_smoke() -> None:
    proc = subprocess.run(
        [sys.executable, str(REPRODUCE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_public_reproduce_pack_v1"
    assert doc["send_gate"] == "HOLD"


@pytest.mark.slow
def test_evidence_lv1_chain_skip_handoff(tmp_path: Path) -> None:
    out = tmp_path / "chain.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(CHAIN),
            "--skip-handoff",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["chain_ok"] is True
