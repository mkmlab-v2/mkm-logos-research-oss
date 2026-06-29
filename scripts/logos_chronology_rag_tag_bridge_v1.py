"""RAG-assisted tag bridge for era blind eval PoC ([HYPO], NON_GATING).

Merges text_blind keyword tags with GraphRAG topic-router enrichment tags.
Does not call live LLM; uses disk SSOT topic catalog + text triggers only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from logos_chronology_map_core_v1 import infer_tags_from_text, load_json

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPHRAG_TOPICS = ROOT / "reports/logos_topic_graphrag_seed_retrieval_v1_latest.json"

# Text needles (lowercase) -> graphrag topic_id (from logos_topic_graphrag_seed_retrieval_v1).
TEXT_TOPIC_TRIGGERS: list[tuple[tuple[str, ...], str]] = [
    (("risk-off", "volatility rises", "credit spread"), "risk_off_overnight"),
    (("geopolitical", "liquidity thin"), "collapse_warn"),
    (("fear_greed", "btc public"), "excess_unwind"),
    (("macro trend", "dff latest", "fedfunds"), "regime_watch"),
    (("trend=up score", "momentum check", "sentiment overlay"), "risk_off_overnight"),
]

# Topic -> extra regime_map-style tags (observational; boosts judges/caution path).
TOPIC_EXTRA_TAGS: dict[str, list[str]] = {
    "risk_off_overnight": ["caution"],
    "collapse_warn": ["caution"],
    "excess_unwind": ["caution"],
    "regime_watch": ["stability"],
    "election_20260603": ["caution"],
    "ai_hubris_trade": ["it_bubble"],
}

# Verse-router themes (offline) -> tags when topic matched.
TOPIC_THEME_TAGS: dict[str, list[str]] = {
    "collapse_warn": ["risk"],
    "excess_unwind": ["risk"],
}


def _match_topics(text: str) -> list[str]:
    low = (text or "").lower()
    hits: list[str] = []
    for needles, topic_id in TEXT_TOPIC_TRIGGERS:
        if any(n in low for n in needles):
            hits.append(topic_id)
    return hits


def infer_tags_rag_assisted(
    text: str,
    *,
    graphrag_topics_json: Path | None = None,
) -> tuple[list[str], dict[str, Any]]:
    """Return merged tags + trace metadata for eval rows."""
    base = infer_tags_from_text(text)
    topics = _match_topics(text)
    extra: set[str] = set(base)
    topic_tags_added: list[str] = []

    path = graphrag_topics_json or DEFAULT_GRAPHRAG_TOPICS
    graphrag_loaded = path.is_file()
    known_topics: set[str] = set()
    if graphrag_loaded:
        doc = load_json(path)
        for row in doc.get("topics") or []:
            if isinstance(row, dict) and row.get("topic_id"):
                known_topics.add(str(row["topic_id"]))

    for tid in topics:
        if known_topics and tid not in known_topics:
            continue
        for tag in TOPIC_EXTRA_TAGS.get(tid, []):
            if tag not in extra:
                extra.add(tag)
                topic_tags_added.append(tag)
        for tag in TOPIC_THEME_TAGS.get(tid, []):
            if tag not in extra:
                extra.add(tag)
                topic_tags_added.append(tag)

    trace = {
        "tag_mode": "rag_assisted",
        "text_blind_tags": base,
        "matched_topic_ids": topics,
        "topic_tags_added": sorted(set(topic_tags_added)),
        "graphrag_topics_loaded": graphrag_loaded,
        "graphrag_topics_path": str(path.name) if graphrag_loaded else None,
    }
    return sorted(extra), trace


def build_rag_tag_sidecar_for_gold_events(
    events: list[dict[str, Any]],
    *,
    graphrag_topics_json: Path | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for ev in events:
        text = str(ev.get("canonical_text") or ev.get("headline_ko") or "")
        tags, trace = infer_tags_rag_assisted(text, graphrag_topics_json=graphrag_topics_json)
        rows.append(
            {
                "observation_id": ev.get("observation_id"),
                "event_id": ev.get("event_id"),
                "inferred_regime_tags_rag_assisted": tags,
                "rag_trace": trace,
            }
        )
    return {
        "schema": "logos_chronology_rag_tag_sidecar_v1",
        "hypothesis_tier": "[HYPO]",
        "policy": {"research_only": True, "non_gating": True},
        "n_events": len(rows),
        "rows": rows,
    }


if __name__ == "__main__":
    import argparse
    import sys

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, required=True)
    ap.add_argument("--output-json", type=Path, required=True)
    ap.add_argument("--graphrag-topics-json", type=Path, default=DEFAULT_GRAPHRAG_TOPICS)
    args = ap.parse_args()

    gold_path = args.gold_json if args.gold_json.is_absolute() else ROOT / args.gold_json
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    if not gold_path.is_file():
        print(f"MISSING {gold_path}", file=sys.stderr)
        raise SystemExit(2)

    gold = load_json(gold_path)
    doc = build_rag_tag_sidecar_for_gold_events(
        list(gold.get("events") or []),
        graphrag_topics_json=args.graphrag_topics_json,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out} n={doc['n_events']}")
