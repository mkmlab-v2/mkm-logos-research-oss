"""Smoke for open-bench onboard runner (fast paths)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONBOARD = ROOT / "scripts" / "run_compression_open_bench_onboard_smoke_v1.py"


def test_onboard_smoke_dry_run(tmp_path: Path) -> None:
    out = tmp_path / "onboard.json"
    proc = subprocess.run(
        [sys.executable, str(ONBOARD), "--dry-run", "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_open_bench_onboard_smoke_v1"
    assert doc["ok"] is True
    assert doc["send_gate"] == "HOLD"
    assert "mirror push" in doc["boundary_ack"].lower() or "customer n50" in doc["boundary_ack"].lower()
    assert len(doc["next_steps"]) >= 3


def test_onboard_smoke_validate_only(tmp_path: Path) -> None:
    out = tmp_path / "onboard.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ONBOARD),
            "--skip-evidence-chain",
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["ok"] is True
    step_ids = [s["id"] for s in doc["steps"]]
    assert "compression_validate" in step_ids
    assert "evidence_lv1_chain" not in step_ids
