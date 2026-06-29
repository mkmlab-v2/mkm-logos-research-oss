"""Corpus Calibration Pack smoke tests."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TENANT = "prospect-rehearsal-01"


def test_extract_must_keep_overlay() -> None:
    corpus = ROOT / f"data/compression/stateless_poc_prospect_{TENANT}_v1.jsonl"
    if not corpus.is_file():
        subprocess.run(
            [
                sys.executable,
                "scripts/run_compression_pilot_roi_chain_v1.py",
                "--tenant-id",
                TENANT,
                "--max-cases",
                "10",
            ],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
        )
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/extract_tenant_must_keep_from_corpus_v1.py",
            "--tenant-id",
            TENANT,
            "--input-jsonl",
            corpus.relative_to(ROOT).as_posix(),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = ROOT / f"docs/final/artifacts/tenant_{TENANT}_must_keep_overlay_v1.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_tenant_must_keep_overlay_v1"
    assert isinstance(doc.get("must_keep_hard_terms"), list)


def test_calibration_pack_accepts_relative_input_jsonl() -> None:
    rel = f"data/compression/stateless_poc_prospect_{TENANT}_v1.jsonl"
    corpus = ROOT / rel
    if not corpus.is_file():
        pytest.skip("prospect corpus missing")
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_compression_calibration_pack_v1.py",
            "--tenant-id",
            TENANT,
            "--input-jsonl",
            rel,
            "--max-cases",
            "5",
            "--skip-dollar-roi",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


@pytest.mark.slow
def test_calibration_pack_rehearsal_chain() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_compression_calibration_pack_v1.py",
            "--tenant-id",
            TENANT,
            "--skip-dollar-roi",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    chain = json.loads(
        (ROOT / f"reports/compression_calibration_pack_{TENANT}_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert chain.get("chain_ok") is True
    hydrate = ROOT / f"reports/compression_pilot_hydrate_compare_{TENANT}_v1_latest.json"
    assert hydrate.is_file()
