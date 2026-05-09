from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_general_prophecy_holdout_failure_drill_v1.py"


def test_holdout_failure_drill_smoke(tmp_path: Path):
    out = tmp_path / "drill.json"
    cp = subprocess.run(
        [sys.executable, str(SCRIPT), "--output-json", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "general_prophecy_holdout_failure_drill_v1"
    assert doc["all_ok"] is True
    assert doc["steps"]["gate"]["decision"] == "WARN_HOLDOUT_DRIFT_RISK"
    assert doc["steps"]["alert"]["dispatch_result"] == "dry_run"
    assert doc["steps"]["failure_summary"]["exit_code"] == 2
