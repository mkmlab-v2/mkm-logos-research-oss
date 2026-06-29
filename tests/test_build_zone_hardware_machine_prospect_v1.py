from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_zone_hardware_machine_prospect_v1.py"


def test_zone_hardware_machine_prospect_schema() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report = ROOT / "reports" / "zone_hardware_machine_prospect_v1_latest.json"
    prospect = ROOT / "codebook" / "templates" / "zone_hardware_machine_templates_prospect_v1.jsonl"
    assert report.is_file()
    assert prospect.is_file()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["schema"] == "zone_hardware_machine_prospect_v1"
    assert data["disclaimer"] == "research_only"
    assert data["prospect_count"] >= 1
