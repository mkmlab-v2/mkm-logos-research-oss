from __future__ import annotations

import json

from scripts.run_myeongri_deterministic_lora_inference_eval_v1 import (
    _finalize_interpret_completion,
    _strip_trailing_role_leakage,
)


def _minimal_envelope(insight: str) -> str:
    return json.dumps(
        {
            "schema": "myeongri_ai_interpretation_envelope_v1",
            "version": "1.0.0",
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "human_review_required": True,
            "mkm_advanced_insight": insight,
            "confidence_score": 0.95,
        },
        ensure_ascii=False,
    )


def test_finalize_trims_multilingual_tail_after_envelope() -> None:
    base = _minimal_envelope("[HYPO] 만세력 결과 요약.")
    raw = base + " 若要提供完整回答，请使用中文还是韩国语？\n\n{"
    out = _finalize_interpret_completion(raw)
    assert json.loads(out)["mkm_advanced_insight"].startswith("[HYPO]")
    assert "若要" not in out


def test_strip_trailing_role_leakage_drops_second_envelope() -> None:
    s = _minimal_envelope("[HYPO] ok") + '\n\n{"schema": "myeongri_ai_interpretation_envelope_v1"'
    trimmed = _strip_trailing_role_leakage(s)
    assert trimmed.count("{") == 1


def test_finalize_keeps_valid_envelope_only() -> None:
    base = _minimal_envelope("[HYPO] 년주 갑자.")
    raw = base + "\n### Instruction:\nrepeat"
    out = _finalize_interpret_completion(raw)
    obj = json.loads(out)
    assert obj["schema"] == "myeongri_ai_interpretation_envelope_v1"
