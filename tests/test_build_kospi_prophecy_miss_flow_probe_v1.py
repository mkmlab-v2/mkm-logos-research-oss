"""Smoke tests for build_kospi_prophecy_miss_flow_probe_v1.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_miss_flow_probe_writes_json_with_2026_05_29():
    out = ROOT / "reports/_test_kospi_miss_flow_probe_v1.json"
    if out.is_file():
        out.unlink()
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_kospi_prophecy_miss_flow_probe_v1.py"),
            "--output",
            str(out),
        ],
        cwd=str(ROOT),
        check=False,
    ).returncode
    assert rc == 0, "probe script failed"
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "kospi_prophecy_miss_flow_probe_v1"
    assert doc.get("research_only") is True
    assert doc.get("flow_join_path", {}).get("ensemble_per_date", {}).get("used") is False
    rows = doc.get("miss_days_with_flow") or []
    may29 = [r for r in rows if r.get("eval_date") == "2026-05-29"]
    assert len(may29) == 1
    row = may29[0]
    assert row.get("daily_flow_present") is True
    assert row.get("flow_score_monthly_rollup") == 10322.0
    assert any("May 2026 daily flow" in n for n in (doc.get("data_gaps") or []))
