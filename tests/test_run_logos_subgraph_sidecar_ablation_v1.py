"""Sidecar ablation smoke (limit=1, CPU)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ABLATION = ROOT / "scripts/run_logos_subgraph_sidecar_ablation_v1.py"


def test_sidecar_ablation_limit_one(tmp_path: Path) -> None:
    out = tmp_path / "ablation.json"
    scratch = tmp_path / "scratch"
    proc = subprocess.run(
        [
            sys.executable,
            str(ABLATION),
            "--out",
            str(out),
            "--scratch-dir",
            str(scratch),
            "--limit",
            "1",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_subgraph_sidecar_ablation_v1"
    assert doc["send_gate"] == "HOLD"
    assert len(doc["configs"]) == 6
    assert doc["all_ok"] is True
