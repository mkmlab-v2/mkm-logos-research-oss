"""WTT pilot intake bootstrap."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_spicy_masked_sessions_v1.py"
BOOT = ROOT / "scripts/bootstrap_wtt_pilot_intake_v1.py"


def test_bootstrap_synthetic_dev(tmp_path: Path) -> None:
    jsonl = tmp_path / "sessions.jsonl"
    subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(jsonl)],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(BOOT),
            "--tenant-id",
            "test-wtt-dev-v1",
            "--source-jsonl",
            str(jsonl),
            "--max-sessions",
            "25",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    corpus = ROOT / "data/wtt/intake/wtt_pilot_test-wtt-dev-v1_v1.jsonl"
    assert corpus.is_file()
    lines = [ln for ln in corpus.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 25
    row = json.loads(lines[0])
    assert row["tenant_id"] == "test-wtt-dev-v1"
    assert row["send_gate"] == "HOLD"


def test_bootstrap_stub_template(tmp_path: Path) -> None:
    jsonl = tmp_path / "stub.jsonl"
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_wtt_customer_masked_stub_v1.py"), "--out-jsonl", str(jsonl)],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(BOOT),
            "--tenant-id",
            "stub-template-v1",
            "--source-jsonl",
            str(jsonl),
            "--stub-template",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    row = json.loads(
        (ROOT / "data/wtt/intake/wtt_pilot_stub-template-v1_v1.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert row["customer_provided"] is False
    assert "synthetic_stub" in row["labels"]


def test_bootstrap_rejects_synthetic_when_customer_masked(tmp_path: Path) -> None:
    jsonl = tmp_path / "sessions.jsonl"
    subprocess.run(
        [sys.executable, str(BUILD), "--out-jsonl", str(jsonl)],
        cwd=str(ROOT),
        check=True,
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(BOOT),
            "--tenant-id",
            "bad-customer-v1",
            "--source-jsonl",
            str(jsonl),
            "--customer-masked",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
