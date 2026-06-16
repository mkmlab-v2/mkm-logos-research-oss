"""rib55 + COORD passive audit chain."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_rib55_coord_passive_audit_v1.py"
OUT = ROOT / "docs/final/artifacts/rib55_coord_passive_audit_v1_latest.json"


def test_rib55_coord_passive_audit_skip_pytest_exit0():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--skip-pytest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "rib55_coord_passive_audit_v1"
    assert doc["ok"] is True
    assert doc.get("infographic_field_present") is True
    step_names = [s.get("step") for s in doc["steps"]]
    assert "l0_l1_ablation" in step_names
    assert "coord_wire_example" in step_names
