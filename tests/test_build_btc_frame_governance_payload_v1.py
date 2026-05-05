from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_BUILD = _ROOT / "scripts" / "build_btc_frame_governance_payload_v1.py"
_VALIDATE = _ROOT / "scripts" / "validate_btc_frame_governance_payload_v1.py"
_RISK = _ROOT / "tests" / "fixtures" / "risk_profile_fact_safe_gate_pass_minimal_v1.json"
_APPROVAL = _ROOT / "tests" / "fixtures" / "trading_human_execution_approval_gate_fixture_GO.json"


def test_build_frame_payload_and_validate_live_eligible(tmp_path: Path) -> None:
    out = tmp_path / "frame_payload.json"
    cmd_build = [
        sys.executable,
        str(_BUILD),
        "--risk-json",
        str(_RISK),
        "--approval-json",
        str(_APPROVAL),
        "--action",
        "go",
        "--execution-mode",
        "live",
        "--out",
        str(out),
    ]
    build_proc = subprocess.run(cmd_build, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert build_proc.returncode == 0, build_proc.stderr + build_proc.stdout
    assert out.is_file()

    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "btc_frame_governance_stage_payload_v1"
    assert doc["stage"] == "gate"
    assert doc["outputs"]["action"] == "go"

    cmd_validate = [
        sys.executable,
        str(_VALIDATE),
        "--payload",
        str(out),
        "--risk-json",
        str(_RISK),
        "--approval-json",
        str(_APPROVAL),
        "--require-live-eligible",
    ]
    val_proc = subprocess.run(cmd_validate, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert val_proc.returncode == 0, val_proc.stderr + val_proc.stdout

