# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for myeongni independent lens v1 extended contract.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def test_myeongni_lens_v1_emits_contract_with_fallback(tmp_path: Path) -> None:
    runner = _ROOT / "scripts/run_lens_myeongni.py"
    out = tmp_path / "myeongni_v1.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--emit-schema",
            "v1",
            "--allow-fallback",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "myeongni_independent_lens_v1"
    assert doc.get("engine_id") == "independent_lens_v1"
    scores = doc.get("scores") or {}
    assert -1.0 <= float(scores.get("direction_score", 0)) <= 1.0
    assert 0.0 <= float(scores.get("confidence", 0)) <= 1.0
    rep = doc.get("reproducibility") or {}
    idig = str(rep.get("input_digest_sha256", ""))
    assert idig.startswith("sha256:")
    assert len(idig) == len("sha256:") + 64
    adv = doc.get("advanced") or {}
    assert "slots" in adv and "coordinator" in adv


def test_myeongni_lens_v1_with_advanced_fixture(tmp_path: Path) -> None:
    runner = _ROOT / "scripts/run_lens_myeongni.py"
    fx = _ROOT / "tests/fixtures/myeongni_advanced_input_minimal_v1.json"
    out = tmp_path / "myeongni_v1_adv.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(runner),
            "--emit-schema",
            "v1",
            "--advanced-input",
            str(fx),
            "--allow-fallback",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    coord = (doc.get("advanced") or {}).get("coordinator") or {}
    assert len(coord.get("school_signals") or []) >= 1
    summ = ((doc.get("advanced") or {}).get("input_summary") or {}).get("status")
    assert summ == "ok"
