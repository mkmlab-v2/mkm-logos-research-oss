"""Appendix CB dashboard vs pilot JSONL cross-check."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_han_vocology_appendix_cb_dashboard_vs_pilot_v1.py"
OUT = ROOT / "docs/final/artifacts/han_vocology_cb_dashboard_pilot_crosscheck_v1_latest.json"


def test_cb_dashboard_pilot_crosscheck() -> None:
    proc = subprocess.run(
        [sys.executable, str(CHECK)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    assert payload.get("ok") is True
