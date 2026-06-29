# Keywords: continuity_bench, deep_fetch_preservation, resume_cycle

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "scripts/run_mkm_cursor_continuity_bench_v1.py"
OUT = ROOT / "reports/mkm_cursor_continuity_bench_v1_latest.json"


def test_continuity_bench_exit0_and_preservation():
    log = ROOT / "reports/mkm_cursor_continuity_bench_fixture_log.jsonl"
    if log.is_file():
        log.unlink()
    proc = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--lane",
            "infra",
            "--continuity-id",
            "p5-smoke-fixture",
            "--log",
            str(log),
            "--skip-repro",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc["schema"] == "mkm_cursor_continuity_bench_v1"
    agg = doc["aggregate"]
    assert agg["preservation_pass"] is True
    assert agg["deep_fetch_preservation_rate"] >= 0.8
    assert agg["required_ssot_pass"] is True
    assert len(doc["cycles"]) == 3


def test_continuity_bench_with_repro_subset():
    proc = subprocess.run(
        [
            sys.executable,
            str(BENCH),
            "--lane",
            "infra",
            "--continuity-id",
            "p5-repro-fixture",
            "--log",
            str(ROOT / "reports/mkm_cursor_continuity_bench_repro_log.jsonl"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    assert doc.get("bench_repro_subset")
    assert all(step["ok"] for step in doc["bench_repro_subset"])
