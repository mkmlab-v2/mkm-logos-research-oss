from __future__ import annotations

from scripts.core.contextual_generator_v2 import ContextualGeneratorV2


def test_contextual_generator_keeps_state_keywords() -> None:
    gen = ContextualGeneratorV2()
    raw = "state transition requires strict evidence traceability and manual review boundary"
    out = gen.generate(
        raw=raw,
        state16=2,
        must_keep=set(),
        strategy="A",
        intensity="extreme",
        use_hangul_principle=False,
    ).lower()
    assert "strict" in out
    assert "evidence" in out
    assert "manual" in out
