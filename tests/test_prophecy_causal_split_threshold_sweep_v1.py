# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.5, K:0.2, M:0.2}
# Balance: 92
# Purpose: Smoke test for causal split-threshold sweep
# Keywords: pytest, prophecy, sweep, split
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_causal_split_threshold_sweep_runs() -> None:
    ws = Path(__file__).resolve().parents[1]
    out = ws / "docs" / "final" / "artifacts" / "_tmp_prophecy_causal_split_threshold_sweep_test.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(ws / "scripts" / "run_prophecy_causal_split_threshold_sweep_v1.py"),
            "--output",
            str(out),
            "--top-k",
            "3",
        ],
        cwd=str(ws),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "prophecy_causal_split_threshold_sweep_v1"
    assert isinstance(doc.get("best_candidate"), dict)
