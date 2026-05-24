"""KO morphology helpers for inter-agent lexicon experiments (research_only, [HYPO])."""

from __future__ import annotations

from typing import Any, Literal

MorphologyBackend = Literal["kiwi", "heuristic_syllable", "word"]

_HEALTH_PARTICLE_SUFFIXES = (
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "처럼",
    "보다",
    "하고",
    "이며",
    "이고",
)


def available_backends() -> list[str]:
    backends = ["heuristic_syllable", "word"]
    try:
        import kiwipiepy  # noqa: F401

        backends.insert(0, "kiwi")
    except ImportError:
        pass
    return backends


def morph_tokenize(text: str, *, prefer: MorphologyBackend | None = None) -> tuple[list[str], dict[str, Any]]:
    """Return morpheme-like tokens + metadata (backend used)."""
    from scripts.mkm_inter_agent_ko_tokenization_v1 import tokenize

    backends = available_backends()
    backend = prefer if prefer and prefer in backends else backends[0]

    if backend == "kiwi":
        from kiwipiepy import Kiwi

        kiwi = Kiwi()
        forms = [t.form for t in kiwi.tokenize(text) if t.form.strip()]
        return forms, {"backend": "kiwi", "token_count": len(forms)}

    if backend == "heuristic_syllable":
        syllables = tokenize(text, "hangul_syllable")
        morphemes: list[str] = []
        for tok in syllables:
            stripped = tok
            for suf in _HEALTH_PARTICLE_SUFFIXES:
                if len(stripped) > len(suf) + 1 and stripped.endswith(suf):
                    morphemes.append(stripped[: -len(suf)])
                    morphemes.append(suf)
                    stripped = ""
                    break
            if stripped:
                morphemes.append(stripped)
        return morphemes, {"backend": "heuristic_syllable", "token_count": len(morphemes)}

    words = tokenize(text, "word")
    return words, {"backend": "word", "token_count": len(words)}
