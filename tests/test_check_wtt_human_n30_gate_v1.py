"""WTT human n30 gate checker."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_wtt_human_n30_gate_v1.py"


def test_gate_not_met_by_default(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(GATE), "--out", str(out), "--no-sync-pack", "--no-intake-scan"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["human_n30_gate_met"] is False
    assert report["target_n_participants"] >= 30


def test_gate_counts_active_tenant_intake(tmp_path: Path) -> None:
    intake = ROOT / "data/wtt/intake/wtt-customer-live-v1.jsonl"
    if not intake.is_file():
        import pytest

        pytest.skip("wtt-customer-live-v1 intake missing")
    out = tmp_path / "gate_live.json"
    proc = subprocess.run(
        [sys.executable, str(GATE), "--out", str(out), "--no-sync-pack"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report.get("intake_dir_customer_rows", 0) >= 30
    assert report.get("human_n30_gate_met") is True


def test_gate_strict_exits_one(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--out",
            str(tmp_path / "g.json"),
            "--strict",
            "--no-sync-pack",
            "--no-intake-scan",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
