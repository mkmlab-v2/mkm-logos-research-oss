from __future__ import annotations

import json
from pathlib import Path

from scripts.report_multilens_performance_eval import evaluate_report


_ROOT = Path(__file__).resolve().parents[1]
_INPUT = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
_BASELINE = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gematria_metadata_default_off_preserves_contract() -> None:
    src = _load(_INPUT)
    baseline = _load(_BASELINE)
    baseline_avg_jaccard = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    report = evaluate_report(
        src,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy="B",
        intensity="extreme",
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=2.0,
        baseline_avg_jaccard=baseline_avg_jaccard,
        use_domain_router=True,
    )
    assert report.get("schema") == "multilens_performance_eval_report_v1"
    cases = report.get("compression_metrics", {}).get("cases", [])
    assert isinstance(cases, list)
    assert len(cases) > 0
    for row in cases:
        assert "gematria_metadata" not in row
        assert "compressed_text_effective" in row
        assert "reconstructed_text_effective" in row
        assert "token_saving_rate" in row
        assert "reconstruction_fidelity_jaccard" in row


def test_gematria_metadata_on_adds_fields_without_quality_gate_change() -> None:
    src = _load(_INPUT)
    baseline = _load(_BASELINE)
    baseline_avg_jaccard = float(
        baseline.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    kwargs = dict(
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy="B",
        intensity="extreme",
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=2.0,
        baseline_avg_jaccard=baseline_avg_jaccard,
        use_domain_router=True,
    )
    base = evaluate_report(src, include_gematria_metadata=False, **kwargs)
    enriched = evaluate_report(src, include_gematria_metadata=True, include_gematria_4d_bridge=True, **kwargs)

    assert base.get("quality_gate") == enriched.get("quality_gate")
    b_comp = base.get("compression_metrics", {})
    e_comp = enriched.get("compression_metrics", {})
    assert b_comp.get("global_token_saving_rate") == e_comp.get("global_token_saving_rate")
    assert b_comp.get("avg_reconstruction_fidelity_jaccard") == e_comp.get("avg_reconstruction_fidelity_jaccard")
    assert b_comp.get("avg_sensitive_integrity") == e_comp.get("avg_sensitive_integrity")
    b_cases = b_comp.get("cases", [])
    e_cases = e_comp.get("cases", [])
    assert len(b_cases) == len(e_cases)
    assert len(e_cases) > 0
    for row in e_cases:
        assert isinstance(row.get("gematria_metadata"), dict)
        assert isinstance(row.get("gematria_4d_bridge"), dict)
        assert isinstance(row.get("gematria_4d_bridge", {}).get("vector_4d"), dict)
        assert row.get("gematria_4d_bridge", {}).get("state16") is not None

