"""WTT customer-masked intake drill report."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "scripts/check_wtt_customer_masked_intake_drill_v1.py"
STUB = ROOT / "data/wtt/examples/wtt_customer_masked_stub_v1.example.jsonl"


def test_drill_missing_jsonl_exit2(tmp_path: Path) -> None:
    out = tmp_path / "drill.json"
    proc = subprocess.run(
        [sys.executable, str(DRILL), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["customer_masked_drill_ready"] is False
    assert "customer_masked_jsonl_missing" in report["blockers"]


def test_drill_solo_internal_rehearsal_exit0(tmp_path: Path) -> None:
    out = tmp_path / "solo.json"
    proc = subprocess.run(
        [sys.executable, str(DRILL), "--solo-internal-rehearsal", "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["solo_internal_rehearsal_ready"] is True
    assert report["customer_masked_drill_ready"] is False
    assert report["counsel_before_send"] is False


def test_drill_with_stub_path_exit0(tmp_path: Path) -> None:
    if not STUB.is_file():
        subprocess.run(
            [sys.executable, "scripts/build_wtt_customer_masked_stub_v1.py"],
            cwd=str(ROOT),
            check=True,
        )
    out = tmp_path / "drill2.json"
    proc = subprocess.run(
        [sys.executable, str(DRILL), "--session-jsonl", str(STUB), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["customer_masked_drill_ready"] is True
