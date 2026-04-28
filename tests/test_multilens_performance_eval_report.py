# @MKM12-METADATA
# Type: Logic
# Purpose: Validate multi-lens performance evaluation report contract.
# Keywords: multilens, performance, compression, fusion

from __future__ import annotations

import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_REPORT = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V1.json"


def test_multilens_performance_report_contract() -> None:
    assert _REPORT.is_file(), f"missing report: {_REPORT}"
    r = json.loads(_REPORT.read_text(encoding="utf-8"))
    assert r.get("schema") == "multilens_performance_eval_report_v1"
    assert r.get("source_input") == "docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V1.json"

    c = r.get("compression_metrics", {})
    assert isinstance(c.get("case_count"), int)
    assert 0.0 <= float(c.get("global_token_saving_rate", -1)) <= 1.0
    assert 0.0 <= float(c.get("avg_reconstruction_fidelity_jaccard", -1)) <= 1.0
    assert isinstance(c.get("cases"), list)

    f = r.get("fusion_metrics", {})
    assert isinstance(f.get("case_count"), int)
    assert 0.0 <= float(f.get("avg_axis_coverage", -1)) <= 1.0
    assert 0.0 <= float(f.get("avg_personalization_coverage", -1)) <= 1.0
    assert isinstance(f.get("all_cases_fusion_possible"), bool)
    assert isinstance(f.get("cases"), list)


def test_multilens_case_metrics_ranges() -> None:
    r = json.loads(_REPORT.read_text(encoding="utf-8"))
    for row in r.get("compression_metrics", {}).get("cases", []):
        assert int(row.get("raw_tokens", -1)) >= 0
        assert int(row.get("compressed_tokens", -1)) >= 0
        assert 0.0 <= float(row.get("token_saving_rate", -1)) <= 1.0
        assert 0.0 <= float(row.get("compression_ratio", -1)) <= 1.0
        assert 0.0 <= float(row.get("reconstruction_fidelity_jaccard", -1)) <= 1.0
    for row in r.get("fusion_metrics", {}).get("cases", []):
        assert 0.0 <= float(row.get("axis_coverage", -1)) <= 1.0
        assert 0.0 <= float(row.get("personalization_coverage", -1)) <= 1.0
        assert isinstance(row.get("fusion_answer_possible"), bool)
