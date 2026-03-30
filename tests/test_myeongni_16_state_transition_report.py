# @MKM12-METADATA
# Type: Logic
# Purpose: Validate Myeongni 16-state transition report contract.
# Keywords: myeongni, 16-state, transition, report

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "docs" / "final" / "artifacts" / "MYEONGNI_16_STATE_TRANSITION_V1.json"


def test_transition_report_exists_and_schema() -> None:
    assert _REPORT.is_file(), f"missing report: {_REPORT}"
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert report.get("schema") == "myeongni_16_state_transition_report_v1"
    assert report.get("source_log") == "data/myeongni/myeongni_16_state_experiment_v1.jsonl"
    assert isinstance(report.get("total_rows"), int)
    assert isinstance(report.get("state_rows"), int)
    assert isinstance(report.get("transition_count"), int)
    assert isinstance(report.get("unique_states_observed"), list)


def test_transition_probability_rows_are_normalized() -> None:
    report = json.loads(_REPORT.read_text(encoding="utf-8"))
    probs = report.get("probability_matrix", {})
    assert isinstance(probs, dict)
    for src, dsts in probs.items():
        assert src.startswith("state_")
        assert isinstance(dsts, dict)
        row_sum = 0.0
        for dst, p in dsts.items():
            assert dst.startswith("state_")
            assert isinstance(p, (float, int))
            assert 0.0 <= float(p) <= 1.0
            row_sum += float(p)
        assert row_sum <= 1.000001, f"probability row sum > 1: {src}"
