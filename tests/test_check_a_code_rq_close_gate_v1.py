"""A-code RQ close gate tests ([HYPO] · no auto RQ CLOSED)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/check_a_code_rq_close_gate_v1.py"
CONDITIONS = ROOT / "experiments/a_code_12ai_v2/specs/a_code_rq_close_conditions_v1.json"


def _load():
    spec = importlib.util.spec_from_file_location("rq_close_gate", GATE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_conditions_spec_track_wall() -> None:
    doc = json.loads(CONDITIONS.read_text(encoding="utf-8"))
    assert doc.get("rq_close_allowed_default") is False
    assert doc.get("track_a_auto_promotion") is False
    assert "rq_close_human_approval" in json.dumps(doc.get("human_gates_required_for_close"))


def test_close_gate_mechanical_candidate_without_human() -> None:
    mod = _load()
    report = mod.evaluate_gate(
        archive={
            "archive_ready": True,
            "rq_close_allowed": False,
            "track_a_auto_promotion": False,
        },
        lane_gate={"summary": {"decision": "PASS_OPERATOR_ASSIST"}},
        pointer={"summary": {"decision": "PASS_POINTER_ROW"}},
        smoke_script_exists=True,
        human_close_approved=False,
    )
    assert report["summary"]["mechanical_close_candidate"] is True
    assert report["summary"]["rq_close_allowed"] is False
    assert report["summary"]["decision"] == "CLOSE_CANDIDATE_AWAIT_HUMAN"


def test_close_gate_human_approved_still_research_only() -> None:
    mod = _load()
    report = mod.evaluate_gate(
        archive={
            "archive_ready": True,
            "rq_close_allowed": False,
            "track_a_auto_promotion": False,
        },
        lane_gate={"summary": {"decision": "PASS_OPERATOR_ASSIST"}},
        pointer={"summary": {"decision": "PASS_POINTER_ROW"}},
        smoke_script_exists=True,
        human_close_approved=True,
    )
    assert report["summary"]["rq_close_allowed"] is True
    assert report["research_only"] is True
    assert report["track_wall"]["agent_auto_rq_closed_forbidden"] is True


def test_close_gate_cli(tmp_path: Path) -> None:
    archive = tmp_path / "archive.json"
    archive.write_text(
        json.dumps(
            {
                "archive_ready": True,
                "rq_close_allowed": False,
                "track_a_auto_promotion": False,
            }
        ),
        encoding="utf-8",
    )
    lane_gate = tmp_path / "lane_gate.json"
    lane_gate.write_text(
        json.dumps({"summary": {"decision": "PASS_OPERATOR_ASSIST"}}),
        encoding="utf-8",
    )
    pointer = tmp_path / "pointer.json"
    pointer.write_text(
        json.dumps({"summary": {"decision": "PASS_POINTER_ROW"}}),
        encoding="utf-8",
    )
    out = tmp_path / "gate.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--archive",
            str(archive),
            "--lane-gate",
            str(lane_gate),
            "--pointer",
            str(pointer),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "a_code_rq_close_gate_v1"
