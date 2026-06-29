"""Smoke: chat shim plan + in-process message transform."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_chat_shim_plan_writes_when_chain_ready() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_local_cursor_chat_shim_v1.py"), "--write-plan"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    out = ROOT / "reports/local_cursor_chat_shim_plan_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8"))
    prereq = doc.get("prerequisites", {})
    assert prereq.get("chain_ready") is True
    signoff_ok = prereq.get("cursor_override_signoff_approved") and prereq.get(
        "human_cursor_session_completed"
    )
    if signoff_ok:
        assert doc.get("ready_for_cursor_override") is True
    else:
        assert doc.get("ready_for_cursor_override") is False


def test_transform_messages_structured_preserve() -> None:
    os.environ["COMPRESSION_HARDENING_CONFIG_PATH"] = "data/btrack/compression_coding_proxy_hardening_v1.json"
    from scripts.cursor_chat_shim_v1 import ChatMessage, _transform_messages

    text = (
        "Task: add scripts/foo.py. "
        "Constraints: B-track research_only, no active report mutation, pytest smoke. "
        "Files: scripts/*.py, data/btrack/*.jsonl. "
        "Verify with py -m pytest -q."
    )
    msgs, audit = _transform_messages(
        [ChatMessage(role="system", content=text), ChatMessage(role="user", content="hi")]
    )
    assert "research_only" in msgs[0]["content"]
    assert "scripts/*.py" in msgs[0]["content"]
    assert any(a.get("structured_preserve") for a in audit)
