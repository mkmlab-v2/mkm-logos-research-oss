"""Load PersonaDiary moment intent weights SSOT (shared by classify + assemble + gates)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SSOT = ROOT / "docs/final/artifacts/personadiary_moment_intent_weights_v1_latest.json"


@lru_cache(maxsize=1)
def load_ssot(path: str | None = None) -> dict:
    p = Path(path) if path else DEFAULT_SSOT
    doc = json.loads(p.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "personadiary_moment_intent_weights_v1":
        raise ValueError("schema must be personadiary_moment_intent_weights_v1")
    return doc


def intent_weights(path: str | None = None) -> dict[str, dict[str, float]]:
    return dict(load_ssot(path)["intent_weights"])


def intent_keywords(path: str | None = None) -> dict[str, tuple[str, ...]]:
    raw = load_ssot(path)["intent_keywords"]
    return {k: tuple(v) for k, v in raw.items()}


def intent_priority(path: str | None = None) -> tuple[str, ...]:
    return tuple(load_ssot(path)["intent_priority"])


def section_titles(path: str | None = None) -> dict[str, str]:
    return dict(load_ssot(path)["section_titles_ko"])


def non_gating_sections(path: str | None = None) -> tuple[str, ...]:
    return tuple(load_ssot(path)["non_gating_sections"])


def package_required_sections(path: str | None = None) -> dict[str, list[str]]:
    return dict(load_ssot(path)["package_required_sections"])


def validate_ssot(doc: dict, *, weight_sum_tol: float = 0.02) -> list[str]:
    errors: list[str] = []
    if doc.get("prophecy_vote") != "none":
        errors.append("prophecy_vote_must_be_none")
    for intent, weights in (doc.get("intent_weights") or {}).items():
        total = sum(float(v) for v in weights.values())
        if abs(total - 1.0) > weight_sum_tol:
            errors.append(f"weight_sum_not_1:{intent}:{total:.4f}")
    return errors
