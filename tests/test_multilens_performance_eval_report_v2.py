# @MKM12-METADATA
# Type: Logic
# Purpose: Validate expanded V2 multi-lens performance report contract.
# Keywords: multilens, performance, v2, evaluation

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"


def test_multilens_v2_report_exists_and_links_input() -> None:
    assert _REPORT.is_file(), f"missing v2 report: {_REPORT}"
    r = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert r.get("schema") == "multilens_performance_eval_report_v1"
    assert r.get("source_input") == "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"


def test_multilens_v2_has_expanded_case_counts() -> None:
    r = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert int(r.get("compression_metrics", {}).get("case_count", 0)) >= 10
    assert int(r.get("fusion_metrics", {}).get("case_count", 0)) >= 10
    assert 0.0 <= float(r.get("compression_metrics", {}).get("global_token_saving_rate", -1)) <= 1.0
    assert 0.0 <= float(r.get("fusion_metrics", {}).get("avg_axis_coverage", -1)) <= 1.0
