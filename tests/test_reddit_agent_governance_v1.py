"""Offline tests for reddit_agent_governance_lib_v1 (R1–R6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.reddit_agent_governance_lib_v1 import (
    RedditGovernanceError,
    base_report_v1,
    count_reddit_submit_tabs,
    enforce_send_gate_for_live,
    enforce_submit_tab_invariant_v1,
    finalize_exit,
    write_artifact_v1,
)


class _FakePage:
    def __init__(self, url: str) -> None:
        self.url = url


def test_send_gate_blocks_live_without_ack():
    with pytest.raises(RedditGovernanceError, match="send_gate_hold"):
        enforce_send_gate_for_live(live_post=True, acknowledge_send=False)


def test_submit_tab_invariant_fails_when_too_many():
    pages = [_FakePage("https://www.reddit.com/r/x/submit"), _FakePage("https://www.reddit.com/r/y/submit")]
    with pytest.raises(RedditGovernanceError, match="submit_tab_invariant"):
        enforce_submit_tab_invariant_v1(pages, cleanup_fn=None)


def test_submit_tab_invariant_after_cleanup():
    pages = [_FakePage("https://www.reddit.com/r/x/submit"), _FakePage("https://www.reddit.com/r/y/submit")]

    def cleanup() -> int:
        pages.pop()
        return 1

    inv = enforce_submit_tab_invariant_v1(pages, cleanup_fn=cleanup)
    assert inv["submit_tabs_after"] == 1
    assert count_reddit_submit_tabs(pages) == 1


def test_base_report_btrack_hold():
    doc = base_report_v1(action="preflight")
    assert doc["send_gate"] == "HOLD"
    assert doc["research_only"] is True
    assert doc["track"] == "B-track"


def test_write_artifact(tmp_path: Path):
    out = tmp_path / "reddit_agent_run_v1_latest.json"
    doc = base_report_v1(action="test")
    doc["ok"] = True
    write_artifact_v1(doc, out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["schema"] == "reddit_agent_run_v1"
    assert finalize_exit(loaded, out=out) == 0
