"""A-code operator-assist lane build/gate tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_operator_assist_lane_v1.py"
GATE = ROOT / "scripts/check_a_code_operator_assist_lane_gate_v1.py"
MIGRATION = ROOT / "docs/final/artifacts/a_code_constitution_worklist_migration_draft_v1.json"
PROMOTION_RQ = ROOT / "reports/a_code_promotion_rq_readiness_v1_latest.json"


def _load_build():
    spec = importlib.util.spec_from_file_location("build_operator_lane", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_migration_draft_pointer_only() -> None:
    doc = json.loads(MIGRATION.read_text(encoding="utf-8"))
    assert doc.get("status") in ("draft_pointer_only", "pointer_row_applied_constitution_1_2_2")
    assert doc.get("human_pr_required") is True
    assert "Track A compression ACTIVE report" in (doc.get("explicit_not_migrated") or [])


@pytest.mark.skipif(not PROMOTION_RQ.is_file(), reason="promotion rq readiness missing")
def test_build_lane_operator_fixed_when_ready() -> None:
    mod = _load_build()
    doc = mod.build_lane_doc()
    if not (mod._read(PROMOTION_RQ).get("summary") or {}).get("operator_lane_ready"):
        pytest.skip("operator_lane_ready not true")
    assert doc.get("lane_status") == "OPERATOR_ASSIST_FIXED"
    assert doc.get("operator_lane_ready") is True
    assert doc.get("track_wall", {}).get("track_a_auto_promotion") is False


def test_lane_gate_cli(tmp_path: Path) -> None:
    lane = {
        "schema": "a_code_operator_assist_lane_v1",
        "research_only": True,
        "non_gating": True,
        "operator_lane_ready": True,
        "lane_status": "OPERATOR_ASSIST_FIXED",
        "track_wall": {"track_a_auto_promotion": False, "live_trading_auto_trigger": False},
    }
    lane_path = tmp_path / "lane.json"
    lane_path.write_text(json.dumps(lane), encoding="utf-8")
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [sys.executable, str(GATE), "--lane", str(lane_path), "--out", str(out)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    gate = json.loads(out.read_text(encoding="utf-8"))
    assert gate["summary"]["decision"] == "PASS_OPERATOR_ASSIST"
