from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_compression_bridge_size_walkforward_eval_smoke(tmp_path: Path) -> None:
    out = tmp_path / "walkforward.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_compression_bridge_size_walkforward_eval_v1.py"),
            "--start-days",
            "10",
            "--stop-days",
            "30",
            "--step-days",
            "10",
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
    assert doc.get("schema") == "compression_bridge_size_walkforward_eval_v1"
    summary = doc.get("summary") if isinstance(doc.get("summary"), dict) else {}
    assert int(summary.get("ok_rows", 0)) >= 1

