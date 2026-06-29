# Keywords: self_audit, suspect_first, session_end, checkpoint hook

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF_AUDIT_LIB = ROOT / "scripts/mkm_cursor_self_audit_lib_v1.py"
SESSION_END = ROOT / "scripts/run_mkm_cursor_session_end_v1.py"
BUILDER = ROOT / "scripts/build_mkm_cursor_deep_handoff_envelope_v1.py"
APPEND = ROOT / "scripts/append_mkm_cursor_turn_meta_v1.py"
CHECKPOINT = ROOT / "scripts/athena_checkpoint.py"


def _load_self_audit():
    import importlib.util

    spec = importlib.util.spec_from_file_location("mkm_cursor_self_audit_lib_v1", SELF_AUDIT_LIB)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_lane_default_topic_query_infra_non_empty():
    mod = _load_self_audit()
    q = mod.lane_default_topic_query("infra")
    assert "infra" in q.lower() or "scheduler" in q.lower()


def test_envelope_includes_agent_self_check():
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--lane", "infra", "--continuity-id", "self-audit-check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(
        (ROOT / "docs/final/artifacts/mkm_cursor_deep_handoff_envelope_v1_latest.json").read_text(
            encoding="utf-8"
        )
    )
    assert doc.get("agent_self_check", {}).get("contract") == "suspect_first"
    assert doc.get("ltm_topic_query")
    assert len(doc.get("ltm_concept_ids") or []) >= 2


def test_append_includes_self_audit(tmp_path: Path):
    log = tmp_path / "turn_meta.jsonl"
    proc = subprocess.run(
        [
            sys.executable,
            str(APPEND),
            "--lane",
            "infra",
            "--continuity-id",
            "self-audit-append",
            "--log",
            str(log),
            "--checkpoint-message",
            "smoke",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    line = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert line.get("self_audit", {}).get("suspect_first") is True
    assert "Doubt" in (line.get("self_audit", {}).get("rules") or [""])[0]


def test_session_end_dry_run():
    proc = subprocess.run(
        [
            sys.executable,
            str(SESSION_END),
            "--lane",
            "infra",
            "--continuity-id",
            "session-end-dry",
            "--dry-run",
            "--message",
            "done: smoke",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "DRY:" in proc.stdout


def test_checkpoint_dry_run_with_continuity_invokes_turn_meta_dry():
    proc = subprocess.run(
        [
            sys.executable,
            str(CHECKPOINT),
            "--dry-run",
            "--continuity-id",
            "cp-hook-dry",
            "--lane",
            "infra",
            "done: hook smoke",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "Would append turn_meta" in proc.stdout
