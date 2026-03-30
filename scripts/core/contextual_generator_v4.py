from __future__ import annotations

import re
from dataclasses import dataclass


def _split_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+", text)


@dataclass(frozen=True)
class SlotPolicy:
    max_tokens: int
    must_terms: set[str]
    prefer_terms: set[str]


class ContextualGeneratorV4:
    """Slot-oriented serializer for aggressive but structured compression."""

    def __init__(self) -> None:
        common_must = {"state", "policy", "trigger", "boundary", "evidence", "manual", "strict", "체질", "명리", "성경"}
        conservative = SlotPolicy(
            max_tokens=9,
            must_terms=common_must | {"direct", "witness", "traceability", "증거", "직접"},
            prefer_terms={"review", "gate", "cadence", "alignment"},
        )
        expansion = SlotPolicy(
            max_tokens=8,
            must_terms=common_must | {"cadence", "alignment"},
            prefer_terms={"direct", "witness", "review"},
        )
        balanced = SlotPolicy(
            max_tokens=8,
            must_terms=common_must,
            prefer_terms={"alignment", "review"},
        )
        self._state_policy: dict[str, SlotPolicy] = {
            "conservative": conservative,
            "expansion": expansion,
            "balanced": balanced,
        }

    @staticmethod
    def _classify_state(state16: int | None) -> str:
        if state16 in {2, 8, 11, 14}:
            return "conservative"
        if state16 in {1, 4, 7, 10, 13, 16}:
            return "expansion"
        return "balanced"

    def generate(
        self,
        *,
        raw: str,
        state16: int | None,
        must_keep: set[str],
        strategy: str,  # kept for interface compatibility
        intensity: str,  # kept for interface compatibility
        use_hangul_principle: bool,  # kept for interface compatibility
    ) -> str:
        _ = strategy, intensity, use_hangul_principle
        tokens = _split_words(raw)
        if not tokens:
            return raw
        policy = self._state_policy[self._classify_state(state16)]
        must = set(must_keep) | policy.must_terms
        prefer = policy.prefer_terms

        selected: list[str] = []
        selected_l: set[str] = set()

        for t in tokens:
            tl = t.lower()
            if tl in must and tl not in selected_l:
                selected.append(t)
                selected_l.add(tl)
        for t in tokens:
            if len(selected) >= policy.max_tokens:
                break
            tl = t.lower()
            if tl in selected_l:
                continue
            if tl in prefer:
                selected.append(t)
                selected_l.add(tl)
        for t in tokens:
            if len(selected) >= policy.max_tokens:
                break
            tl = t.lower()
            if tl in selected_l:
                continue
            selected.append(t)
            selected_l.add(tl)

        return " ".join(selected[: policy.max_tokens])
