from __future__ import annotations

from scripts.report_multilens_performance_eval import evaluate_report


def test_evaluate_report_includes_cee_core_when_enabled() -> None:
    doc = {
        "compression_cases": [
            {
                "id": "x",
                "raw_text": "בראשית",
                "compressed_text": "ברא",
                "reconstructed_text": "בראשית",
            }
        ],
        "fusion_answer_cases": [],
    }
    report = evaluate_report(
        doc,
        source_input="dummy.json",
        include_cee_core=True,
    )
    cases = report["compression_metrics"]["cases"]
    assert len(cases) == 1
    cee = cases[0].get("cee_core")
    assert isinstance(cee, dict)
    assert cee.get("schema") == "cee_logic_core_v1"
    assert 1 <= int(cee.get("state_id")) <= 16
    shadow = report.get("cee_shadow_summary")
    assert isinstance(shadow, dict)
    assert shadow.get("enabled") is True
    assert int(shadow.get("case_count")) == 1
