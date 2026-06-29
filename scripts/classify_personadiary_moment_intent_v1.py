#!/usr/bin/env python3
"""PersonaDiary moment intent classifier v1 — deterministic keyword routing [HYPO].

B-track only. Reads no external APIs. Used by assemble_personadiary_moment_response_v1.
"""
from __future__ import annotations

import re
from typing import Any

from personadiary_moment_intent_weights_v1 import intent_keywords, intent_priority

INTENTS = ("meal", "weather_fit", "mood", "world_me", "reflect")

_INTENT_KEYWORDS = intent_keywords()
_PRIORITY = intent_priority()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def classify_intent(query: str) -> dict[str, Any]:
    """Return intent label, score, and matched keyword hints."""
    norm = _normalize(query)
    if not norm:
        return {
            "intent": "reflect",
            "score": 0,
            "matched_keywords": [],
            "lane": "research_only",
            "hypothesis_tier": "B",
        }

    scores: dict[str, int] = {k: 0 for k in _INTENT_KEYWORDS}
    matched: dict[str, list[str]] = {k: [] for k in _INTENT_KEYWORDS}
    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in norm:
                scores[intent] += 1
                matched[intent].append(kw)

    best_score = max(scores.values())
    if best_score == 0:
        return {
            "intent": "reflect",
            "score": 0,
            "matched_keywords": [],
            "lane": "research_only",
            "hypothesis_tier": "B",
        }

    winners = [i for i in _PRIORITY if scores[i] == best_score]
    if not winners:
        winners = [i for i in INTENTS if i != "reflect" and scores[i] == best_score]
    intent = winners[0] if winners else "reflect"
    return {
        "intent": intent,
        "score": best_score,
        "matched_keywords": matched.get(intent, [])[:5],
        "lane": "research_only",
        "hypothesis_tier": "B",
    }


def main() -> int:
    import argparse
    import json
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="?", default="")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    q = args.query or (sys.stdin.read() if not sys.stdin.isatty() else "")
    out = classify_intent(q)
    if args.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(out["intent"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
