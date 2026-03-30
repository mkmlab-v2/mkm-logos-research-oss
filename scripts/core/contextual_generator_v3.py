from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.core.contextual_generator_v2 import ContextualGeneratorV2


def _split_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+", text)


@dataclass(frozen=True)
class RewritePolicy:
    max_tokens_ratio: float
    dedupe: bool


class ContextualGeneratorV3:
    """State-aware generator + lightweight rewrite compactor."""

    def __init__(self) -> None:
        self._v2 = ContextualGeneratorV2()
        self._policy = {
            "conservative": RewritePolicy(max_tokens_ratio=0.62, dedupe=False),
            "expansion": RewritePolicy(max_tokens_ratio=0.55, dedupe=True),
            "balanced": RewritePolicy(max_tokens_ratio=0.58, dedupe=True),
        }

    @staticmethod
    def _classify_state(state16: int | None) -> str:
        if state16 in {2, 8, 11, 14}:
            return "conservative"
        if state16 in {1, 4, 7, 10, 13, 16}:
            return "expansion"
        return "balanced"

    @staticmethod
    def _compact(tokens: list[str], *, dedupe: bool, target_tokens: int) -> list[str]:
        if not tokens:
            return tokens
        out: list[str] = []
        seen: set[str] = set()
        for t in tokens:
            lw = t.lower()
            if dedupe and lw in seen and len(out) >= target_tokens:
                continue
            if dedupe:
                seen.add(lw)
            out.append(t)
            if len(out) >= target_tokens:
                break
        return out

    def generate(
        self,
        *,
        raw: str,
        state16: int | None,
        must_keep: set[str],
        strategy: str,
        intensity: str,
        use_hangul_principle: bool,
    ) -> str:
        base = self._v2.generate(
            raw=raw,
            state16=state16,
            must_keep=must_keep,
            strategy=strategy,
            intensity=intensity,
            use_hangul_principle=use_hangul_principle,
        )
        raw_tokens = _split_words(raw)
        base_tokens = _split_words(base)
        state_kind = self._classify_state(state16)
        policy = self._policy[state_kind]
        target_tokens = max(1, int(len(raw_tokens) * policy.max_tokens_ratio))
        compacted = self._compact(base_tokens, dedupe=policy.dedupe, target_tokens=target_tokens)
        return " ".join(compacted) if compacted else base
