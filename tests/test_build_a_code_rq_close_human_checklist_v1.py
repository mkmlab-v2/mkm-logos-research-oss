"""A-code RQ close human checklist tests."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_a_code_rq_close_human_checklist_v1.py"


def _load():
    spec = importlib.util.spec_from_file_location("human_checklist", BUILD)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_human_checklist_forbids_agent_auto_close() -> None:
    mod = _load()
    doc = mod.build_checklist(
        gate={
            "rq_ids": ["RQ-028", "RQ-029", "RQ-031"],
            "summary": {
                "decision": "CLOSE_CANDIDATE_AWAIT_HUMAN",
                "mechanical_close_candidate": True,
                "rq_close_allowed": False,
            },
        },
        conditions={},
    )
    assert doc["summary"]["agent_auto_close_forbidden"] is True
    research_step = next(s for s in doc["manual_steps"] if s["id"] == "edit_research_open_questions")
    assert research_step.get("agent_forbidden") is True


def test_human_checklist_cli(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "rq_ids": ["RQ-028"],
                "summary": {
                    "decision": "HOLD_RESEARCH",
                    "mechanical_close_candidate": False,
                    "rq_close_allowed": False,
                },
            }
        ),
        encoding="utf-8",
    )
    out_json = tmp_path / "checklist.json"
    out_md = tmp_path / "checklist.md"
    proc = subprocess.run(
        [
            sys.executable,
            str(BUILD),
            "--gate",
            str(gate),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out_json.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_rq_close_human_checklist_v1"
    assert out_md.is_file()
