# @MKM12-METADATA
# Purpose: Grant proposal model lane router v0 (dry-run, research_only).
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.route_grant_proposal_model_lane_v1 import (
    LANE_MAP,
    build_report,
    load_tasks_jsonl,
    route_task,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/grant_proposal_router_tasks_v1.example.jsonl"
SCRIPT = ROOT / "scripts/route_grant_proposal_model_lane_v1.py"


def test_lane_map_covers_backlog_task_kinds() -> None:
    for kind in (
        "outline",
        "table_fill",
        "grep_evidence",
        "narrative_section",
        "risk_legal",
        "fact_lock_claim",
        "legal_guarantee",
    ):
        assert kind in LANE_MAP


def test_route_task_dry_run_never_invokes_llm() -> None:
    r = route_task(
        {"task_id": "t1", "task_kind": "narrative_section", "grant_program": "opendata_327"},
        dry_run=True,
    )
    assert r["model_tier"] == "tier_premium"
    assert r["invoke_llm"] is False
    assert r["invoke_llm_planned"] is True
    assert r["dry_run"] is True


def test_script_only_and_human_only() -> None:
    grep = route_task(
        {"task_id": "g", "task_kind": "grep_evidence", "grant_program": "generic"},
        dry_run=True,
    )
    assert grep["requires_script_gate"] is True
    assert grep["invoke_llm_planned"] is False

    human = route_task(
        {"task_id": "h", "task_kind": "legal_guarantee", "grant_program": "generic"},
        dry_run=True,
    )
    assert human["requires_human"] is True
    assert human["model_tier"] == "human_only"


def test_unknown_task_kind_raises() -> None:
    with pytest.raises(ValueError, match="unknown task_kind"):
        route_task({"task_id": "x", "task_kind": "magic_wand"}, dry_run=True)


def test_fixture_jsonl_loads() -> None:
    rows = load_tasks_jsonl(FIXTURE)
    assert len(rows) >= 7


def test_build_report_tier_counts() -> None:
    rows = load_tasks_jsonl(FIXTURE)
    routes = [route_task(r, dry_run=True) for r in rows]
    report = build_report(routes, dry_run=True, tasks_path=FIXTURE)
    assert report["ok"] is True
    assert report["task_count"] == len(rows)
    assert sum(report["tier_counts"].values()) == len(rows)


def test_cli_exit_zero(tmp_path: Path) -> None:
    out = tmp_path / "route_latest.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--tasks-jsonl",
            str(FIXTURE),
            "--out",
            str(out),
            "--no-append-jsonl",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "grant_proposal_model_route_v1"
    assert doc["dry_run"] is True
    assert doc["research_only"] is True
    assert "hwp_pms_auto_submit" in doc["forbidden"]
