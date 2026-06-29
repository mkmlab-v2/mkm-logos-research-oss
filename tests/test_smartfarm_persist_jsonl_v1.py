"""JSONL persistence helper tests."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.smartfarm_persist_jsonl_v1 import append_jsonl


def test_append_jsonl_writes_line(tmp_path: Path) -> None:
    log = tmp_path / "events.jsonl"
    append_jsonl(log, {"event_type": "test", "zone_key": "a:b"})
    lines = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_type"] == "test"
    assert "logged_at_utc" in row
