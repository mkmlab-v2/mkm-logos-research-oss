from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_sasang_12state_timeframe_friction_factcheck_smoke(tmp_path: Path) -> None:
    out = tmp_path / "friction_report.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "run_sasang_12state_timeframe_friction_factcheck_v1.py"),
            "--out-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "sasang_12state_timeframe_friction_factcheck_v1"
    tfs = doc.get("timeframes")
    assert isinstance(tfs, list) and len(tfs) == 2
    names = {row.get("timeframe") for row in tfs if isinstance(row, dict)}
    assert names == {"4h", "15m"}

