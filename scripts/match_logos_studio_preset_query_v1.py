"""Mirror Logos Studio resolvePresetId scoring (keyword + lexical tier-1)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def normalize_query_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _lexical_resolve(query: str, index: dict[str, Any] | None) -> tuple[str | None, int]:
    if not index:
        return None, 0
    q = normalize_query_text(query)
    tokens = [t for t in q.split(" ") if len(t) >= 2]
    scores: dict[str, int] = {}
    for entry in index.get("inverted_index") or []:
        token = normalize_query_text(str(entry.get("token") or ""))
        if len(token) < 2:
            continue
        hit = token in q or any(token in t or t in token for t in tokens)
        if not hit:
            continue
        weight = 3 if len(token) >= 6 else 2
        for pid in entry.get("preset_ids") or []:
            scores[str(pid)] = scores.get(str(pid), 0) + weight
    if not scores:
        return None, 0
    best_id, best_score = max(scores.items(), key=lambda x: x[1])
    if best_score >= 2:
        return best_id, best_score
    return None, 0


def resolve_preset_id(
    presets: list[dict[str, Any]],
    *,
    preset_id: str | None = None,
    query: str | None = None,
    lexical_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if preset_id:
        for p in presets:
            if p.get("id") == preset_id:
                return {"preset_id": preset_id, "match": "id"}
    q = normalize_query_text(query or "")
    if not q:
        return {"preset_id": None, "match": "none"}
    for p in presets:
        if normalize_query_text(str(p.get("prompt_ko") or "")) == q:
            return {"preset_id": p["id"], "match": "text"}
    best: tuple[str, int] | None = None
    for preset in presets:
        prompt = normalize_query_text(str(preset.get("prompt_ko") or ""))
        score = 0
        if prompt and (prompt in q or q in prompt[: min(24, len(prompt))]):
            score += 3
        for token in q.split(" "):
            if len(token) >= 2 and token in prompt:
                score += 1
        for raw_kw in preset.get("keywords") or []:
            kw = normalize_query_text(str(raw_kw))
            if len(kw) >= 2 and kw in q:
                score += 2
            for token in q.split(" "):
                if len(token) >= 2 and token in kw:
                    score += 1
        if best is None or score > best[1]:
            best = (str(preset["id"]), score)
    if best and best[1] >= 2:
        return {"preset_id": best[0], "match": "text"}
    lex_id, _ = _lexical_resolve(q, lexical_index)
    if lex_id:
        return {"preset_id": lex_id, "match": "lexical"}
    return {"preset_id": None, "match": "none"}


def load_default_lexical_index() -> dict[str, Any]:
    path = ROOT / "docs/final/artifacts/logos_studio_semantic_router_lexical_index_v1_latest.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))

