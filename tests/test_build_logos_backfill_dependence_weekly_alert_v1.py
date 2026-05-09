from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_logos_backfill_dependence_weekly_alert_v1.py"
LOG = ROOT / "reports" / "logos_backfill_dependence_trend_log.jsonl"


def test_build_backfill_dependence_weekly_alert_smoke(tmp_path: Path):
    out_json = tmp_path / "weekly_alert.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--log-jsonl",
            str(LOG),
            "--output-json",
            str(out_json),
            "--window-days",
            "7",
            "--delta-alert-threshold",
            "0.2",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_backfill_dependence_weekly_alert_v1"
    assert "window_summary" in doc
    assert "alert" in doc

