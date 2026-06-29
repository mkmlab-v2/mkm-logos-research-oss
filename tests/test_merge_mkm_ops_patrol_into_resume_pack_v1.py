"""merge_mkm_ops_patrol_into_resume_pack_v1 contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from merge_mkm_ops_patrol_into_resume_pack_v1 import (  # noqa: E402
    build_stop_sequence_hints,
    merge_patrol_into_resume,
)


def test_merge_adds_last_ops_patrol_field(tmp_path: Path) -> None:
    paste = tmp_path / "paste.json"
    resume = tmp_path / "resume.json"
    resume_md = tmp_path / "resume.md"
    paste.write_text(
        json.dumps(
            {
                "paste_line": "[DailyOpsPatrol] 2026-05-31 OK (P0:pass; opt_fail:0)",
                "package": "DailyOpsPatrol",
                "process_exit_code": 0,
            }
        ),
        encoding="utf-8",
    )
    resume.write_text(
        json.dumps({"schema": "mkm_chat_resume_pack_v1", "ops_memory_pins": []}),
        encoding="utf-8",
    )
    resume_md.write_text("# MKM Chat Resume Pack\n\n## Quick Refs\n", encoding="utf-8")

    assert merge_patrol_into_resume(
        paste_path=paste, resume_json=resume, resume_md=resume_md
    )
    data = json.loads(resume.read_text(encoding="utf-8"))
    assert data["last_ops_patrol"]["paste_line"].startswith("[DailyOpsPatrol]")
    assert "Last Ops Patrol" in resume_md.read_text(encoding="utf-8")


def test_build_stop_sequence_hints_from_reports(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    reports.joinpath("amsaeng_eosa_governance_cycle_latest.json").write_text(
        json.dumps({"worst_exit": 1, "phases": [{"name": "mcp_notebooklm_hygiene", "exit_code": 1}]}),
        encoding="utf-8",
    )
    reports.joinpath("mcp_hygiene_probe_latest.json").write_text(
        json.dumps(
            {
                "prereq_exit_code": 1,
                "stale_process_count_before": 2,
                "stale_process_count_after": 0,
                "repair_ran": True,
            }
        ),
        encoding="utf-8",
    )
    hints = build_stop_sequence_hints(workspace_root=tmp_path)
    assert hints["amsaeng_worst_exit"] == 1
    assert hints["notebooklm_stale_count_after"] == 0
    assert any("amsaeng_worst_exit" in line for line in hints["alert_lines"])


def test_merge_includes_stop_sequence_hints(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    reports.joinpath("amsaeng_eosa_governance_cycle_latest.json").write_text(
        json.dumps({"worst_exit": 0, "phases": []}),
        encoding="utf-8",
    )
    reports.joinpath("mcp_hygiene_probe_latest.json").write_text(
        json.dumps({"prereq_exit_code": 0, "stale_process_count_after": 1}),
        encoding="utf-8",
    )
    paste = tmp_path / "paste.json"
    resume = tmp_path / "resume.json"
    resume_md = tmp_path / "resume.md"
    paste.write_text(
        json.dumps({"paste_line": "[DailyOpsPatrol] OK", "package": "DailyOpsPatrol"}),
        encoding="utf-8",
    )
    resume.write_text(json.dumps({"schema": "mkm_chat_resume_pack_v1"}), encoding="utf-8")
    resume_md.write_text("# x\n\n## Quick Refs\n", encoding="utf-8")

    merge_patrol_into_resume(paste_path=paste, resume_json=resume, resume_md=resume_md, workspace_root=tmp_path)
    data = json.loads(resume.read_text(encoding="utf-8"))
    assert "stop_sequence_hints" in data["last_ops_patrol"]
    assert "notebooklm_stale_after=1" in data["last_ops_patrol"]["stop_sequence_hints"]["alert_lines"][0]
