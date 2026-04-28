# @MKM12-METADATA
# Type: Logic
# Purpose: Validate multi-lens performance evaluation report contract.
# Keywords: multilens, performance, compression, fusion

from __future__ import annotations

import json
from pathlib import Path

from scripts.report_multilens_performance_eval import evaluate_report


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


def test_evaluate_report_emit_semantic_pointer_smoke() -> None:
    doc = {
        "compression_cases": [
            {
                "id": "sp1",
                "raw_text": "State 3 to in bootstrap but this is read only and cannot trigger track policy",
                "compressed_text": "State to in bootstrap but this is read only and 3 cannot policy track trigger",
                "reconstructed_text": "State 3 to in bootstrap but this is read only and cannot trigger track policy",
            }
        ],
        "fusion_answer_cases": [],
    }
    report = evaluate_report(doc, source_input="fixture.json", mode="baseline", emit_semantic_pointer=True)
    assert report["run_config"].get("emit_semantic_pointer") is True
    ch = report["compression_metrics"].get("semantic_pointer_channel")
    assert isinstance(ch, dict)
    assert ch.get("enabled") is True
    row = report["compression_metrics"]["cases"][0]
    sp = row.get("semantic_pointer")
    assert isinstance(sp, dict)
    assert sp.get("schema") == "semantic_pointer_v1"
    assert sp.get("case_id") == "sp1"


def test_evaluate_report_default_has_no_semantic_pointer_per_case() -> None:
    doc = {
        "compression_cases": [
            {
                "id": "x",
                "raw_text": "hello world",
                "compressed_text": "hello",
                "reconstructed_text": "hello world",
            }
        ],
        "fusion_answer_cases": [],
    }
    report = evaluate_report(doc, source_input="fixture.json", mode="baseline")
    assert report["run_config"].get("emit_semantic_pointer") is False
    assert report["compression_metrics"]["semantic_pointer_channel"]["enabled"] is False
    assert "semantic_pointer" not in report["compression_metrics"]["cases"][0]
