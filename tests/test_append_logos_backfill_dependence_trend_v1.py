from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "append_logos_backfill_dependence_trend_v1.py"
MONITOR = ROOT / "docs" / "final" / "artifacts" / "logos_backfill_dependence_monitor_latest.json"


def test_append_backfill_dependence_trend_smoke(tmp_path: Path):
    log_jsonl = tmp_path / "trend.jsonl"
    cp = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--monitor-json",
            str(MONITOR),
            "--log-jsonl",
            str(log_jsonl),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    lines = [ln for ln in log_jsonl.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row.get("schema") == "logos_backfill_dependence_trend_record_v1"
    assert "delta_mixed_minus_pure" in row

