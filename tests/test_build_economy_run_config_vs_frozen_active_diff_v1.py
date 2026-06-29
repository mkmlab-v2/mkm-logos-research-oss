from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "build_economy_run_config_vs_frozen_active_diff_v1.py"
FROZEN = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
ECONOMY = ROOT / "experiments" / "compression_pipeline_grid_sweep_v1" / "runs" / "profile_economy.json"


def test_config_diff_builds_when_artifacts_exist(tmp_path: Path) -> None:
    if not FROZEN.is_file() or not ECONOMY.is_file():
        return
    out = tmp_path / "config_diff.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "economy_run_config_vs_frozen_active_diff_v1"
    assert doc["promote_active"] is False
    assert doc["run_config_diff"]["changed_field_count"] >= 1
    assert "master_codebook_lexicon_path" in doc["run_config_diff"]["headline_deltas"]
