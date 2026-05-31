"""Contract tests for ENTRY_07 source hunt log and summary."""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_LOG = _ROOT / "docs" / "final" / "artifacts" / "entry07_source_hunt_log.jsonl"
_SUMMARY = _ROOT / "docs" / "final" / "artifacts" / "entry07_source_hunt_summary_latest.json"

_REQUIRED_LOG_KEYS = {
    "source_url",
    "source_title",
    "manuscript_id",
    "line_anchor",
    "xlvi_xlvii_direct_witness",
    "confidence",
    "access_mode",
}


def test_entry07_source_hunt_log_exists_and_contract() -> None:
    assert _LOG.is_file(), f"missing {_LOG}"
    rows = []
    for line in _LOG.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s:
            rows.append(json.loads(s))
    assert len(rows) >= 3
    for row in rows:
        assert _REQUIRED_LOG_KEYS <= set(row.keys())
        assert row["xlvi_xlvii_direct_witness"] in {"yes", "no", "unknown"}


def test_entry07_source_hunt_summary_contract() -> None:
    assert _SUMMARY.is_file()
    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    assert summary["schema"] == "entry07_source_hunt_summary_v1"
    assert summary["cross_ref_entry"] == "ENTRY_07"
    assert summary["has_xlvi_xlvii_direct_witness"] is False
    assert summary["ssot_mutation"] is False
    assert summary["research_only"] is True
