#!/usr/bin/env python3
"""Shared token-overlap helpers for Logos / Pet subgraph routers ([HYPO], NON_GATING)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]+")


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in TOKEN_RE.finditer((text or "").lower()):
        t = m.group(0)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def score_token_overlap(query_tokens: list[str], *text_parts: str) -> int:
    hay = " ".join(str(p) for p in text_parts if p).lower()
    return sum(1 for t in query_tokens if t in hay)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def bridge_text_fields(bridge: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    q = bridge.get("query") if isinstance(bridge.get("query"), dict) else {}
    parts.append(str(q.get("label_ko") or ""))
    parts.append(str(q.get("concept_id") or ""))
    parts.append(str(q.get("gold_query_id") or ""))
    parts.append(str(q.get("scenario") or ""))
    for node in bridge.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        parts.append(str(node.get("label_ko") or ""))
        parts.append(str(node.get("label_en") or ""))
        parts.append(str(node.get("value") or ""))
        parts.append(str(node.get("rationale_ko") or ""))
    for kw in bridge.get("keywords") or []:
        parts.append(str(kw))
    return parts


def score_bridge(query_tokens: list[str], bridge: dict[str, Any]) -> int:
    return score_token_overlap(query_tokens, *bridge_text_fields(bridge))
