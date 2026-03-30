# @MKM12-METADATA
# Type: Logic
# Purpose: Validate Myeongni 16-state topflows report contract.
# Keywords: myeongni, 16-state, topflows, report

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TOPFLOWS_V1.json"


def test_topflows_report_exists_and_schema() -> None:
    assert _REPORT.is_file(), f"missing report: {_REPORT}"
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert report.get("schema") == "myeongni_16_state_topflows_v1"
    assert report.get("source_transition_report") == "docs/final/artifacts/MYEONGNI_16_STATE_TRANSITION_V1.json"
    rows = report.get("state_flow_summary")
    assert isinstance(rows, list)
    assert len(rows) == 16


def test_each_state_has_top3_bounds() -> None:
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    for row in report.get("state_flow_summary", []):
        state_id = row.get("state_id")
        assert isinstance(state_id, int) and 1 <= state_id <= 16
        for key in ("outbound_top3", "inbound_top3"):
            flows = row.get(key, [])
            assert isinstance(flows, list)
            assert len(flows) <= 3
            prev = None
            for f in flows:
                assert isinstance(f.get("from_state"), int)
                assert isinstance(f.get("to_state"), int)
                assert isinstance(f.get("count"), int) and f["count"] >= 0
                assert isinstance(f.get("probability"), (float, int))
                score = (f["count"], float(f["probability"]))
                if prev is not None:
                    assert prev >= score, f"{key} is not sorted desc for state {state_id}"
                prev = score
