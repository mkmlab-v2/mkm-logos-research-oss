from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_scheduler_kpi_artifact_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "build_genius_governance_scheduler_kpi_v1.py"
    out = root / "docs" / "final" / "artifacts" / "genius_governance_scheduler_kpi_latest.json"
    r = subprocess.run([sys.executable, str(script)], cwd=str(root), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "genius_governance_scheduler_kpi_v1"
    assert "last_24h" in (doc.get("kpi") or {})
    assert "last_7d" in (doc.get("kpi") or {})


def test_forced_hold_drill_contract() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "run_genius_governance_scheduler_forced_hold_drill_v1.py"
    out = root / "docs" / "final" / "artifacts" / "genius_governance_scheduler_forced_hold_drill_latest.json"
    r = subprocess.run([sys.executable, str(script)], cwd=str(root), capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "genius_governance_scheduler_forced_hold_drill_v1"
    assert isinstance(doc.get("pass"), bool)
