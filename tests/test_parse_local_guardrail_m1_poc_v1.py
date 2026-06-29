"""Smoke tests for local M1 guardrail PoC."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "parse_local_guardrail_m1_poc.py"
BRIDGE_OUT = ROOT / "reports" / "tmp" / "pet_companion_bridge_request_poc_latest.json"
BENCH_OUT = ROOT / "reports" / "edge_m1_guardrail_bench_latest.json"


def test_parse_local_guardrail_m1_poc_runs():
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--bench"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert BRIDGE_OUT.is_file()
    bridge = json.loads(BRIDGE_OUT.read_text(encoding="utf-8"))
    assert bridge["schema"] == "pet_companion_device_memory_bridge_request_v1"
    assert bridge["research_only"] is True
    masked = bridge["raw_user_question_masked"]
    assert "010-1234-5678" not in masked
    assert "홍길동" not in masked
    assert BENCH_OUT.is_file()
    bench = json.loads(BENCH_OUT.read_text(encoding="utf-8"))
    assert bench["schema"] == "edge_m1_guardrail_bench_v1"
    assert bench["masked_utf8_bytes"] <= bench["raw_utf8_bytes"]
