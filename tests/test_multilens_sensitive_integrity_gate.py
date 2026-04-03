# @MKM12-METADATA
# Type: Logic
# Purpose: Regression for quality_gate.sensitive_integrity_ok (L1 must-keep).
# Keywords: multilens, sensitive_integrity, must_keep, B-track gate

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_INPUT_V2 = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
_BASELINE_V2 = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json"
_DECISION = _ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"


def test_sensitive_violation_and_safety_net_for_must_keep() -> None:
    """Unit-level L1: leak detection + _ensure_sensitive_tokens_preserved append behavior."""
    from scripts.report_multilens_performance_eval import (
        _ensure_sensitive_tokens_preserved,
        _sensitive_violation,
    )

    raw = "alpha beta gamma delta"
    cand_missing = "alpha beta delta"
    mk = {"gamma"}
    assert _sensitive_violation(raw, cand_missing, mk) is True
    fixed = _ensure_sensitive_tokens_preserved(raw, cand_missing, mk)
    assert _sensitive_violation(raw, fixed, mk) is False
    assert "gamma" in fixed.lower()


def test_experimental_must_keep_zero_leak_minimal() -> None:
    """Fast path: 1 case, explicit must_keep; _ensure_sensitive_tokens_preserved must close leaks."""
    from scripts.report_multilens_performance_eval import evaluate_report

    doc = {
        "compression_cases": [
            {
                "id": "integrity_min_001",
                "raw_text": "alpha beta gamma delta epsilon",
                "compressed_text": "placeholder",
                "reconstructed_text": "alpha beta gamma delta epsilon",
            }
        ],
        "fusion_answer_cases": [],
    }
    report = evaluate_report(
        doc,
        source_input="inline:test_multilens_sensitive_integrity_gate",
        mode="experimental",
        strategy="A",
        intensity="extreme",
        must_keep={"alpha", "gamma"},
        use_domain_router=False,
        use_master_codebook_lexicon_v1=False,
        general_max_saving_rate=0.54,
        sensitive_max_saving_rate=0.5,
    )
    qg = report.get("quality_gate") or {}
    cm = report.get("compression_metrics") or {}
    assert qg.get("sensitive_integrity_ok") is True
    assert int(cm.get("sensitive_violation_count", -1)) == 0
    assert float(cm.get("avg_sensitive_integrity", 0.0)) >= 0.999
    assert float(cm.get("min_sensitive_integrity", 0.0)) >= 0.999


@pytest.mark.skipif(not _INPUT_V2.is_file(), reason="MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json missing")
@pytest.mark.skipif(not _BASELINE_V2.is_file(), reason="MULTILENS_PERFORMANCE_EVAL_REPORT_V2.json missing")
@pytest.mark.skipif(not _DECISION.is_file(), reason="MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json missing")
def test_v2_active_profile_sensitive_integrity_ok_matches_ultra_default() -> None:
    """Integration: same evaluate_report contract as scripts/run_ultra_compression_default.py."""
    from scripts.report_multilens_performance_eval import evaluate_report

    src_doc = json.loads(_INPUT_V2.read_text(encoding="utf-8"))
    baseline_doc = json.loads(_BASELINE_V2.read_text(encoding="utf-8"))
    decision_doc = json.loads(_DECISION.read_text(encoding="utf-8"))
    selected = decision_doc.get("selected_candidate") or {}
    strategy = str(selected.get("strategy", "B"))
    intensity = str(selected.get("intensity", "extreme"))
    g = selected.get("general_max_saving_rate")
    s = selected.get("sensitive_max_saving_rate")
    h = selected.get("hangul_max_saving_rate")
    general_max_saving_rate = float(g) if g is not None else None
    sensitive_max_saving_rate = float(s) if s is not None else None
    hangul_max_saving_rate = float(h) if h is not None else None
    baseline_avg_jaccard = float(
        baseline_doc.get("compression_metrics", {}).get("avg_reconstruction_fidelity_jaccard", 0.0)
    )
    threshold_pp = float(decision_doc.get("target", {}).get("jaccard_drop_threshold_pp", 2.0))

    report = evaluate_report(
        src_doc,
        source_input="docs/final/artifacts/MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json",
        mode="experimental",
        strategy=strategy,
        intensity=intensity,
        must_keep={"사상의학", "체질", "sasang", "myeongri", "bible"},
        jaccard_drop_threshold_pp=threshold_pp,
        baseline_avg_jaccard=baseline_avg_jaccard,
        general_max_saving_rate=general_max_saving_rate,
        sensitive_max_saving_rate=sensitive_max_saving_rate,
        hangul_max_saving_rate=hangul_max_saving_rate,
        use_domain_router=True,
        use_master_codebook_lexicon_v1=True,
        include_gematria_metadata=True,
        include_gematria_4d_bridge=True,
        include_cee_core=True,
    )
    qg = report.get("quality_gate") or {}
    cm = report.get("compression_metrics") or {}
    assert qg.get("sensitive_integrity_ok") is True, qg
    assert int(cm.get("sensitive_violation_count", -1)) == 0
    assert float(cm.get("avg_sensitive_integrity", 0.0)) >= 0.999
    assert float(cm.get("min_sensitive_integrity", 0.0)) >= 0.999
