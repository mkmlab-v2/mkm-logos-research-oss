from __future__ import annotations

from scripts.core.contextual_generator_v3 import ContextualGeneratorV3


def test_contextual_generator_v3_compacts_more_than_raw() -> None:
    gen = ContextualGeneratorV3()
    raw = "state transition requires strict evidence traceability and manual review boundary trigger policy"
    out = gen.generate(
        raw=raw,
        state16=1,
        must_keep=set(),
        strategy="A",
        intensity="extreme",
        use_hangul_principle=False,
    )
    assert len(out.split()) <= len(raw.split())
    assert "state" in out.lower()
