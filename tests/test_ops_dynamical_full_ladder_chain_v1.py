from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_ops_snapshot_chain_idempotent_second_run():
    proc1 = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_ops_snapshot_chain_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc1.returncode == 0, proc1.stderr
    doc1 = json.loads(proc1.stdout.strip().splitlines()[-1])
    proc2 = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_ops_snapshot_chain_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc2.returncode == 0
    doc2 = json.loads(proc2.stdout.strip().splitlines()[-1])
    if doc1.get("appended"):
        assert doc2.get("appended") is False
        assert doc2.get("reason") == "fingerprint_unchanged"


def test_full_ladder_chain_exit_0():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_ops_dynamical_full_ladder_chain_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    out_path = ROOT / "reports/ops_dynamical_full_ladder_chain_v1_latest.json"
    assert out_path.is_file(), proc.stderr or proc.stdout
    doc = json.loads(out_path.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "ops_dynamical_full_ladder_chain_v1"
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert doc["ok"] is True
