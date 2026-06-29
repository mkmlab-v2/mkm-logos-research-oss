"""Smoke: Logos Graph Studio pilot session recorder."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def test_record_pilot_session_hold_gate(tmp_path: Path, monkeypatch) -> None:
    import scripts.record_logos_graph_studio_pilot_session_v1 as mod

    latest = tmp_path / "session_latest.json"
    log = tmp_path / "session_log.jsonl"
    monkeypatch.setattr(mod, "OUT_LATEST", latest)
    monkeypatch.setattr(mod, "OUT_LOG", log)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "record_logos_graph_studio_pilot_session_v1.py",
            "--outcome",
            "deferred",
            "--notes",
            "internal dry run",
        ],
    )
    assert mod.main() == 0
    doc = json.loads(latest.read_text(encoding="utf-8"))
    assert doc["send_gate"] == "HOLD"
    assert doc["ready_for_external_send"] is False
    assert doc["outcome"] == "deferred"
    assert log.read_text(encoding="utf-8").strip()
