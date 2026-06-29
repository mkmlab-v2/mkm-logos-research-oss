"""Premium CS cross-lane status builder."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_wtt_premium_cs_cross_lane_status_v1.py"


def test_cross_lane_status_builder(tmp_path: Path) -> None:
    human = ROOT / "reports/wtt_human_n30_gate_v1_latest.json"
    intake = ROOT / "data/wtt/intake/wtt-customer-live-v1.jsonl"
    if not human.is_file() or not intake.is_file():
        import pytest

        pytest.skip("premium CS intake artifacts missing")

    out = tmp_path / "cross.json"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "wtt_premium_cs_cross_lane_status_v1"
    assert doc.get("send_gate") == "HOLD"
    assert doc.get("wtt_lane", {}).get("session_count") >= 30
    cust_lane = doc.get("customer_provided_compression_lane") or {}
    if (ROOT / "data/wtt/intake/wtt-premium-cs-customer-live-v1.jsonl").is_file():
        assert cust_lane.get("session_count") >= 20
    poc_path = ROOT / "reports/customer_compression_stateless_poc_wtt-premium-cs-customer-v1_v1_latest.json"
    if poc_path.is_file():
        assert cust_lane.get("poc_cases_passed") is not None
