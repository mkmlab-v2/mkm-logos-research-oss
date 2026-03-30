# @MKM12-METADATA
# Type: Logic
# Purpose: Validate Myeongni topflow interpretation report contract.
# Keywords: myeongni, topflow, interpretation, report

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TOPFLOW_INTERPRETATION_V1.json"


def test_interpretation_report_exists_and_schema() -> None:
    assert _REPORT.is_file(), f"missing report: {_REPORT}"
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert report.get("schema") == "myeongni_16_state_topflow_interpretation_v1"
    assert report.get("source_topflows_report") == "docs/final/artifacts/MYEONGNI_16_STATE_TOPFLOWS_V1.json"
    assert isinstance(report.get("one_line_interpretation"), str)
    assert report["one_line_interpretation"].strip()
    assert isinstance(report.get("global_top5_flows"), list)


def test_interpretation_report_keeps_btrack_boundary() -> None:
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    q = report.get("quality_gate", {})
    assert isinstance(q.get("sufficient_for_signal"), bool)
    assert isinstance(q.get("current_stage"), str)
    assert isinstance(q.get("min_rows_for_signal"), int)
    note = str(report.get("boundary_note", ""))
    assert "B-track only" in note
