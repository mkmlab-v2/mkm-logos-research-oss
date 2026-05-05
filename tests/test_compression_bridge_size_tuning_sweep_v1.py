from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_compression_bridge_size_tuning_sweep_smoke(tmp_path: Path) -> None:
    out = tmp_path / "size_tune_sweep.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "run_compression_bridge_size_tuning_sweep_v1.py"),
            "--signal-scales",
            "1.0",
            "--negative-caps",
            "0.0,0.02",
            "--quality-bonus-scales",
            "0.2",
            "--policy-gap-penalty-scales",
            "0.2,0.4",
            "--windows",
            "10,20",
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
    assert doc.get("schema") == "compression_bridge_size_tuning_sweep_v1"
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    assert len(rows) >= 1

