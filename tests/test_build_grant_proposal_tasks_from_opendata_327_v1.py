from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.build_grant_proposal_tasks_from_opendata_327_v1 import (
    CHECKLIST,
    build_opendata_327_tasks,
    build_open_innovation_stub_tasks,
)
from scripts.route_grant_proposal_model_lane_v1 import load_tasks_jsonl, route_task

ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "scripts/build_grant_proposal_tasks_from_opendata_327_v1.py"


@pytest.mark.skipif(not CHECKLIST.is_file(), reason="327 checklist SSOT missing")
def test_build_opendata_tasks_non_empty() -> None:
    rows = build_opendata_327_tasks()
    assert len(rows) >= 15
    kinds = {r["task_kind"] for r in rows}
    assert "grep_evidence" in kinds
    assert "human_only" not in kinds  # human maps to legal/qualification kinds
    assert any(r.get("owner") == "human" for r in rows)


@pytest.mark.skipif(not CHECKLIST.is_file(), reason="327 checklist SSOT missing")
def test_all_opendata_tasks_route() -> None:
    rows = build_opendata_327_tasks()
    for row in rows:
        route_task(row, dry_run=True)


def test_open_innovation_stub_routes() -> None:
    for row in build_open_innovation_stub_tasks():
        route_task(row, dry_run=True)


def test_builder_cli_writes_jsonl(tmp_path: Path) -> None:
    if not CHECKLIST.is_file():
        pytest.skip("327 checklist SSOT missing")
    out = tmp_path / "tasks.jsonl"
    manifest = tmp_path / "manifest.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--out",
            str(out),
            "--manifest-out",
            str(manifest),
            "--skip-open-innovation",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    rows = load_tasks_jsonl(out)
    assert len(rows) >= 15
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    assert doc["schema"] == "grant_proposal_tasks_manifest_v1"
