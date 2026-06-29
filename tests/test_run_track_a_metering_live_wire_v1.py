"""Smoke: Track A metering live wire appends band-valid rows."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_metering_live_wire_appends_band_valid_rows(root: Path, tmp_path, monkeypatch):
    from scripts.run_track_a_metering_live_wire_v1 import run_live_wire

    log = tmp_path / "meter_live_wire.jsonl"
    monkeypatch.setenv("TRACK_A_METERING_LOG_PATH", str(log))

    input_json = root / "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
    doc = run_live_wire(
        workspace_root=root,
        input_json=input_json,
        case_limit=3,
        client_prefix="test-live-wire",
    )
    assert doc["status"] == "pass"
    assert doc["meter_log_appended_count"] == 3
    assert doc["band_valid_count"] == 3

    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 3
    for ln in lines:
        row = json.loads(ln)
        assert row.get("notes") == "from_compress_eval_context_meter_log"
        assert int(row["tokens_before"]) > 0
        assert int(row["tokens_after"]) <= int(row["tokens_before"])
