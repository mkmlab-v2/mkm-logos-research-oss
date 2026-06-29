from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_compression_pipeline_grid_sweep_triage_v1.py"
SUMMARY = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1" / "results" / "compression_pipeline_grid_sweep_v1_latest.json"


def test_triage_builds_from_existing_sweep_artifacts(tmp_path: Path) -> None:
    if not SUMMARY.is_file():
        return
    out = tmp_path / "triage.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "compression_pipeline_grid_sweep_triage_v1"
    assert doc["promote_active"] is False
    assert "profile_economy" in doc["profile_triage"]
    assert doc["cost_sim_cross_check"]["delta_saving_pp"] is not None
