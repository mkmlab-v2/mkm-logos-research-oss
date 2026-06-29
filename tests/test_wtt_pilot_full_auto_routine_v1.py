"""WTT full auto routine report builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_pilot_full_auto_routine_report_v1.py"


def test_full_auto_report_builder(tmp_path: Path) -> None:
    out = tmp_path / "full_auto.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "wtt_pilot_full_auto_routine_v1"
    assert doc.get("send_gate") == "HOLD"
    assert "gates" in doc
