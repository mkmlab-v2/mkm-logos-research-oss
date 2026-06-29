from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.build_opendata_327_script_gate_runbook_v1 import RUNBOOK

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "scripts/build_opendata_327_script_gate_runbook_v1.py"


def test_runbook_has_ten_steps() -> None:
    assert len(RUNBOOK) == 10
    ids = {r["task_id"] for r in RUNBOOK}
    assert len(ids) == 10


def test_builder_cli(tmp_path: Path) -> None:
    out_json = tmp_path / "rb.json"
    out_md = tmp_path / "rb.md"
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--out-json", str(out_json), "--out-md", str(out_md)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc["step_count"] == 10
    assert "Run-GrantProposalOpenData327ScriptGateB" in doc["one_shot_ps1"]
    assert out_md.read_text(encoding="utf-8").startswith("# OpenData 327")
