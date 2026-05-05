# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test compression bridge adjustment sweep runner.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_compression_bridge_adjustment_sweep_smoke(tmp_path: Path) -> None:
    out = tmp_path / "sweep.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_compression_bridge_adjustment_sweep_v1.py"),
            "--recent-trading-days",
            "5",
            "--signal-scales",
            "0.0,1.0",
            "--positive-caps",
            "0.01",
            "--output",
            str(out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "compression_bridge_adjustment_sweep_v1"
    rows = doc.get("rows")
    assert isinstance(rows, list) and len(rows) == 2

