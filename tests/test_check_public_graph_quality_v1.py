from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_public_graph_quality_v1.py"


def test_check_public_graph_quality_v1_passes_on_latest(tmp_path: Path) -> None:
    out = tmp_path / "gate.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-json",
            str(ROOT / "docs" / "final" / "artifacts" / "public_graph_response_v1_latest.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "public_graph_quality_gate_v1"
    assert doc["all_pass"] is True
