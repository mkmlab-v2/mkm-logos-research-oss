"""Sidecar ablation v2 smoke (limit=1, quick pairwise)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ABLATION = ROOT / "scripts/run_logos_subgraph_sidecar_ablation_v2_v1.py"


def test_sidecar_ablation_v2_quick_limit_one(tmp_path: Path) -> None:
    out = tmp_path / "ablation_v2.json"
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
            "--quick",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "logos_subgraph_sidecar_ablation_v2"
    assert doc["send_gate"] == "HOLD"
    assert doc["config_count"] == 8
    assert doc["all_ok"] is True
    assert doc["no_hit_at_1_regression"] is True
