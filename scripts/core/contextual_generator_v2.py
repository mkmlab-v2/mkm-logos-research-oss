from __future__ import annotations

import re
from dataclasses import dataclass


def _split_words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_가-힣]+|[א-ת]+|[Α-Ωα-ωϛϟϡ]+", text)


def _has_hangul_syllable(word: str) -> bool:
    return any("가" <= ch <= "힣" for ch in word)


def _is_hangul_particle_like(word: str) -> bool:
    if not _has_hangul_syllable(word):
        return False
    endings = ("은", "는", "이", "가", "을", "를", "에", "의", "와", "과", "도", "로", "으로")
    return word in endings or any(word.endswith(e) for e in endings)


@dataclass(frozen=True)
class StateKeywordProfile:
    hard_terms: set[str]
    soft_terms: set[str]


class ContextualGeneratorV2:
    """State-aware compression candidate generator."""

    def __init__(self) -> None:
        self._profiles = self._build_profiles()

    @staticmethod
    def _build_profiles() -> dict[int, StateKeywordProfile]:
        conservative = StateKeywordProfile(
            hard_terms={"direct", "witness", "evidence", "manual", "strict", "traceability", "증거", "직접", "수동"},
            soft_terms={"policy", "boundary", "state", "trigger", "명리", "성경", "체질"},
        )
        expansion = StateKeywordProfile(
            hard_terms={"policy", "state", "trigger", "boundary", "cadence", "명리", "체질"},
            soft_terms={"evidence", "traceability", "manual", "strict", "성경"},
        )
        balanced = StateKeywordProfile(
            hard_terms={"체질", "명리", "성경"},
            soft_terms={"policy", "state", "evidence"},
        )
        out: dict[int, StateKeywordProfile] = {}
        for sid in (2, 8, 11, 14):
            out[sid] = conservative
        for sid in (1, 4, 7, 10, 13, 16):
            out[sid] = expansion
        for sid in (3, 5, 6, 9, 12, 15):
            out[sid] = balanced
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
        words = _split_words(raw)
        if not words:
            return raw
        profile = self._profiles.get(int(state16)) if state16 is not None else None
        hard_terms = set(must_keep)
        soft_terms: set[str] = set()
        if profile is not None:
            hard_terms.update(profile.hard_terms)
            soft_terms.update(profile.soft_terms)

        stride = {"high": 2, "ultra": 3, "extreme": 4}[intensity]
        strategy_offset = {"A": 0, "B": 1, "C": 2}[strategy]
        anchors = {0, 1, max(0, len(words) - 2), max(0, len(words) - 1), len(words) // 2}
        kept: list[str] = []
        for i, w in enumerate(words):
            lw = w.lower()
            if lw in hard_terms:
                kept.append(w)
                continue
            if use_hangul_principle and _is_hangul_particle_like(w):
                kept.append(w)
                continue
            if lw in soft_terms and (i % 2 == 0 or i in anchors):
                kept.append(w)
                continue
            if i in anchors:
                kept.append(w)
                continue
            if strategy == "A":
                if i < 2 or i % stride == 0:
                    kept.append(w)
            elif strategy == "B":
                if (i + strategy_offset) % stride == 0:
                    kept.append(w)
            else:
                if i < 3 or (i + strategy_offset) % stride == 0:
                    kept.append(w)
        return " ".join(kept)
