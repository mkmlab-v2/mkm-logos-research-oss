from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_dss_scheduler_plan_artifact_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "ops" / "register_dss_slot_mapping_task.py"
    out = root / "reports" / "constitution" / "btrack_pilot" / "btrack_dss_scheduler_plan_latest.json"
    r = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "btrack_dss_scheduler_plan_v1"
    assert doc.get("planned_only") is True
    assert doc.get("applied") is False
    cmd = doc.get("planned_command", [])
    assert isinstance(cmd, list) and "schtasks" in cmd
