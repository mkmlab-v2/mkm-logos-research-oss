from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_backfill_dependence_monitor_v1.py"
COMPARE = ROOT / "docs" / "final" / "artifacts" / "logos_temporal_holdout_compare_backfill_latest.json"


def test_build_backfill_dependence_monitor_smoke(tmp_path: Path):
    out_json = tmp_path / "monitor.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--compare-json",
            str(COMPARE),
            "--output-json",
            str(out_json),
            "--max-allowed-delta",
            "0.2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_backfill_dependence_monitor_v1"
    assert "status" in doc
    assert "metrics" in doc

