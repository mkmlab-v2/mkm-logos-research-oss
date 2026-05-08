from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_conditional_go_market_inputs_v1.py"
FIXTURE = ROOT / "tests" / "fixtures" / "conditional_go_market_inputs_sample_v1.json"


def test_build_conditional_go_market_inputs_with_sample_and_override(tmp_path: Path) -> None:
    out = tmp_path / "inputs.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-json",
            str(out),
            "--sample-json",
            str(FIXTURE),
            "--foreign-flow-turn",
            "true",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "conditional_go_market_inputs_v1"
    assert doc["checks"]["foreign_flow_turn"] is True
    assert doc["checks"]["kospi_structure_hold"] is True
    assert doc["checks"]["semi_leader_recovery"] is True
    assert doc["confidence_0_1"] >= 0.62

