"""Logos inquiry S4 stream v1 — P0-1b SSE sequence smoke."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from core.logos_inquiry_stream_v1 import (  # noqa: E402
    STREAM_SCHEMA,
    build_stream_sequence_from_payload,
    chunk_s4_body,
    iter_stream_events,
)
from core.logos_inquiry_report_v1 import build_inquiry_report  # noqa: E402


def test_chunk_s4_body_sentence_aware():
    text = "첫 문장입니다. 둘째 문장은 깁니다. 셋째."
    chunks = chunk_s4_body(text, chunk_chars=20)
    assert len(chunks) >= 2
    assert "".join(chunks).replace(" ", "") == text.replace(" ", "")


def test_stream_event_sequence_order():
    payload = {
        "answer": "Alpha. Beta gamma.",
        "path": {"verse_refs": ["Job.1.21"], "steps": [], "node_ids": []},
        "conflict_context": {"groups": []},
    }
    report = build_inquiry_report(payload, query="sample query long enough")
    events = list(iter_stream_events(report, chunk_chars=10))
    assert events[0]["event"] == "snapshot"
    assert events[0]["snapshot"]["S5"]["signoff_status"] == "provisional"
    assert events[0]["snapshot"]["S5"]["sections_payload_sha256"] is None
    assert any(e["event"] == "s4_delta" for e in events)
    assert events[-1]["event"] == "done"
    final_s5 = events[-1]["report"]["sections"]["S5"]
    assert final_s5["sections_payload_sha256"]


def test_freeze_stream_contract_exit_zero():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_inquiry_stream_schema_freeze_v1.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    freeze = json.loads(
        (ROOT / "reports/logos_inquiry_stream_schema_freeze_v1_latest.json").read_text(encoding="utf-8")
    )
    contract = json.loads(
        (ROOT / "docs/final/artifacts/logos_inquiry_stream_contract_v1_latest.json").read_text(encoding="utf-8")
    )
    sample = json.loads(
        (ROOT / "reports/logos_inquiry_stream_sample_events_v1_latest.json").read_text(encoding="utf-8")
    )
    assert freeze["ok"] is True
    assert freeze["stream_schema"] == STREAM_SCHEMA
    assert contract["phase"] == "P0-1b"
    assert contract["event_sequence"] == ["snapshot", "s4_delta", "s4_done", "done"]
    assert sample[0]["schema"] == STREAM_SCHEMA
