from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_conditional_go_market_check_v1.py"


def test_build_conditional_go_market_check_default_unarmed(tmp_path: Path) -> None:
    out = tmp_path / "conditional_go_market_check.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-json",
            str(tmp_path / "missing.json"),
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "conditional_go_market_check_v1"
    assert doc["activation"]["armed"] is False
    assert doc["activation"]["all_conditions_met"] is False


def test_build_conditional_go_market_check_armed(tmp_path: Path) -> None:
    inp = tmp_path / "market_inputs.json"
    out = tmp_path / "conditional_go_market_check.json"
    inp.write_text(
        json.dumps(
            {
                "checks": {
                    "foreign_flow_turn": True,
                    "kospi_structure_hold": True,
                    "semi_leader_recovery": True,
                },
                "confidence_0_1": 0.8,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-json",
            str(inp),
            "--output-json",
            str(out),
            "--min-confidence",
            "0.62",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["activation"]["all_conditions_met"] is True
    assert doc["activation"]["armed"] is True
