# Keywords: turn_meta, continuity, mission_log, required_ssot

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
APPEND = ROOT / "scripts/append_mkm_cursor_turn_meta_v1.py"
BUILDER = ROOT / "scripts/build_mkm_cursor_deep_handoff_envelope_v1.py"
LOG = ROOT / "reports/mkm_cursor_turn_meta_log.jsonl"
CONTINUITY = "p4-continuity-smoke"


def test_envelope_includes_required_ssot_refs():
    proc = subprocess.run(
        [sys.executable, str(BUILDER), "--lane", "infra", "--continuity-id", "ssot-check"],
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
    assert doc.get("required_ssot_refs")
    paths = " ".join(doc.get("deep_fetch_next") or [])
    assert "MISSION_LOG.md" in paths
    assert "mkm_long_term_memory_graph_v1.json" in paths
    assert "mkm_chat_resume_pack_latest" in paths


def test_three_turn_preserves_deep_queue(tmp_path: Path):
    log = tmp_path / "turn_meta.jsonl"
    for turn in (1, 2, 3):
        proc = subprocess.run(
            [
                sys.executable,
                str(APPEND),
                "--lane",
                "infra",
                "--continuity-id",
                CONTINUITY,
                "--log",
                str(log),
                "--checkpoint-message",
                f"turn-{turn}",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout

    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    docs = [json.loads(ln) for ln in lines]
    assert all(d["continuity_id"] == CONTINUITY for d in docs)
    q1 = set(docs[0]["deep_fetch_next"])
    q3 = set(docs[2]["deep_fetch_next"])
    assert q1.issubset(q3)
    assert "MISSION_LOG.md" in q3
    assert docs[2].get("required_ssot_refs")
    assert docs[2].get("required_ssot_missing") == []


def test_athena_checkpoint_continuity_id_prefix():
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/athena_checkpoint.py",
            "--dry-run",
            "--continuity-id",
            "p4-test",
            "P4 smoke",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "continuity=p4-test" in proc.stdout
