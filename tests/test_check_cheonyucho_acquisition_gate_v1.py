"""Tests for cheonyucho acquisition HOLD gate (B-track, research_only)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "check_cheonyucho_acquisition_gate_v1.py"
PROBE = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_gate_v1_latest.json"


def test_cheonyucho_acquisition_gate_hold_pass() -> None:
    cp = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = json.loads(cp.stdout.strip().splitlines()[-1])
    assert out["ok"] is True
    assert out["decision"] == "PASS"
    assert out["send_gate"] == "HOLD"

    report = json.loads(OUT.read_text(encoding="utf-8"))
    assert report["schema"] == "cheonyucho_acquisition_gate_v1"
    assert report["send_gate"] == "HOLD"
    assert report["promotion_allowed"] is False
    assert report["research_only"] is True
    assert report["physical_verified"] is False


def test_cheonyucho_gate_fails_on_premature_physical_verified(tmp_path: Path) -> None:
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    probe["physical_verified"] = True
    bad = tmp_path / "bad_probe.json"
    bad.write_text(json.dumps(probe, ensure_ascii=False), encoding="utf-8")

    cp = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--probe",
            str(bad),
            "--out",
            str(tmp_path / "gate_fail.json"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 1, cp.stderr or cp.stdout
    merged = (cp.stdout + cp.stderr).strip()
    line = [ln for ln in merged.splitlines() if ln.strip().startswith("{")][-1]
    out = json.loads(line)
    assert out["ok"] is False
