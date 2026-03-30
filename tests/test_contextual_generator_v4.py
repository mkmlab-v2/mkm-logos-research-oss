from __future__ import annotations

from scripts.core.contextual_generator_v4 import ContextualGeneratorV4


def test_contextual_generator_v4_slot_limits_and_must_terms() -> None:
    gen = ContextualGeneratorV4()
    raw = "state policy trigger boundary evidence manual strict direct witness traceability review cadence alignment"
    out = gen.generate(
        raw=raw,
        state16=2,
        must_keep=set(),
        strategy="A",
        intensity="extreme",
        use_hangul_principle=False,
    )
    words = out.lower().split()
    assert len(words) <= 9
    assert "state" in words
    assert "policy" in words
