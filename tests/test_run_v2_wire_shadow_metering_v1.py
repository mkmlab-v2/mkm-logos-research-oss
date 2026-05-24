# @MKM12-METADATA
# Type: Test
# Purpose: v2 wire shadow metering bench + summarize (B-track, no active writes).

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_v2_wire_shadow_metering_bench_and_summary(tmp_path: Path) -> None:
    log = tmp_path / "shadow.jsonl"
    out = tmp_path / "summary.json"
    bench = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_v2_wire_shadow_metering_bench_v1.py"),
            "--max-cases",
            "1",
            "--case-ids",
            "cmp2_004",
            "--out-jsonl",
            str(log),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert bench.returncode == 0, bench.stderr
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["meter_schema"] == "v2_wire_shadow_metering_v1"
    assert row["sla_track"] == "B_v2_wire_shadow"

    summ = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/summarize_v2_wire_shadow_metering_v1.py"),
            "--log-jsonl",
            str(log),
            "--out-json",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert summ.returncode == 0, summ.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "comp_v2_wire_shadow_metering_summary_v1"
    assert doc["case_pairs"] == 1
    assert doc["track_wall"]["active_report_write"] is False
