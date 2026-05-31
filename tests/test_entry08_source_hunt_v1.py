"""Contract tests for ENTRY_08 source hunt log and summary."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / "docs" / "final" / "artifacts" / "entry08_source_hunt_log.jsonl"
_SUMMARY = _ROOT / "docs" / "final" / "artifacts" / "entry08_source_hunt_summary_latest.json"

_REQUIRED = {
    "source_url",
    "source_title",
    "manuscript_id",
    "line_anchor",
    "fragment_line_direct_witness",
    "confidence",
    "access_mode",
}


def test_entry08_log_and_summary() -> None:
    assert _LOG.is_file()
    rows = [json.loads(s) for s in _LOG.read_text(encoding="utf-8").splitlines() if s.strip()]
    assert len(rows) >= 4
    for row in rows:
        assert _REQUIRED <= set(row.keys())
        assert row["fragment_line_direct_witness"] in {"yes", "no", "unknown"}

    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    assert summary["schema"] == "entry08_source_hunt_summary_v1"
    assert summary["cross_ref_entry"] == "ENTRY_08"
    assert summary["has_fragment_line_direct_witness"] is False
    assert summary["ssot_mutation"] is False
