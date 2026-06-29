"""Tests for build_btrack_phase0_observe_only_status_v1."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_btrack_phase0_observe_only_status_v1.py"
APPLY = ROOT / "scripts" / "apply_btrack_btc_typea_guard_to_score_v1.py"


def test_phase0_status_builds(tmp_path: Path) -> None:
    out = tmp_path / "phase0.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode in (0, 1), proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btrack_phase0_observe_only_readiness_v1"
    assert "phase0_observe_only_ready" in doc
    assert doc["track_a_auto_promote"] is False
    assert isinstance(doc["checks"], list)


def test_promote_operational_requires_approval(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(APPLY),
            "--promote-operational",
            "--approval-json",
            str(tmp_path / "missing_approval.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode != 0
    assert "missing approval" in proc.stderr.lower() or "missing approval" in proc.stdout.lower()
