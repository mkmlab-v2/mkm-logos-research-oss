# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test directional impact sweep runner.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_compression_bridge_directional_impact_sweep_smoke(tmp_path: Path) -> None:
    out = tmp_path / "dir_sweep.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_compression_bridge_directional_impact_sweep_v1.py"),
            "--recent-trading-days",
            "5",
            "--signal-scales",
            "0,5",
            "--negative-caps",
            "0.02",
            "--tie-break-margins",
            "0.03,0.12",
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
    assert doc.get("schema") == "compression_bridge_directional_impact_sweep_v1"
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    assert int(summary.get("ok_rows", 0)) >= 1

