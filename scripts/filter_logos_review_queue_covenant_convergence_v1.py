#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filter human review queue → covenant-convergence subset (ann_lite primary, N≤15). [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
DEFAULT_LEXICON = ROOT / "docs/final/fixtures/logos_ann_typology_lexicon_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_review_queue_covenant_convergence_v1_latest.json"

COVENANT_THEME_IDS = frozenset(
    {
        "judgment_covenant_remnant",
        "covenant_judgment_restoration",
        "covenant_faithfulness_in_crisis",
        "covenant_love_forgiveness",
    }
)
COVENANT_BOOK_PREFIXES = frozenset(
    {"Jer", "Rom", "Hos", "Isa", "Ps", "Deut", "Heb", "Exod", "Lev", "Num", "1Sam", "2Sam"}
)
VERSE_REF_RE = re.compile(r"::([A-Za-z0-9]+\.[0-9]+\.[0-9]+)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _verse_from_node(node_id: str) -> str | None:
    m = VERSE_REF_RE.search(str(node_id or ""))
    return m.group(1) if m else None


def _book_prefix(verse_ref: str) -> str:
    return verse_ref.split(".", 1)[0]


def _load_anchor_verses(lexicon_path: Path) -> set[str]:
    anchors: set[str] = set()
    lex = _read_json(lexicon_path)
    for entry in lex.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("theme_id") or "") not in COVENANT_THEME_IDS:
            continue
        for vid in entry.get("boost_verse_ids") or []:
            if isinstance(vid, str) and vid.strip():
                anchors.add(vid.strip())
    return anchors


def _item_matches_covenant_convergence(item: dict[str, Any], anchors: set[str]) -> bool:
    src = str(item.get("src_node_id") or "")
    dst = str(item.get("dst_node_id") or "")
    for node in (src, dst):
        ref = _verse_from_node(node)
        if not ref:
            continue
        if ref in anchors:
            return True
        if _book_prefix(ref) in COVENANT_BOOK_PREFIXES:
            return True
    return False


def build_filtered_queue(
    queue_doc: dict[str, Any],
    *,
    anchors: set[str],
    max_items: int = 15,
    lane_id: str = "ann_lite",
    priority: str = "primary",
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for item in queue_doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("lane_id") or "") != lane_id:
            continue
        if str(item.get("priority") or "") != priority:
            continue
        if not _item_matches_covenant_convergence(item, anchors):
            continue
        candidates.append(item)

    candidates.sort(
        key=lambda r: (
            -float(r.get("similarity") or 0),
            int(r.get("queue_rank") or 9999),
        )
    )
    selected = candidates[: max(0, max_items)]

    return {
        "schema": "logos_review_queue_covenant_convergence_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "merge_to_canonical_allowed": False,
        "human_signoff_required": True,
        "source_queue_schema": queue_doc.get("schema"),
        "filter": {
            "lane_id": lane_id,
            "priority": priority,
            "theme_ids": sorted(COVENANT_THEME_IDS),
            "max_items": max_items,
            "anchor_verse_count": len(anchors),
        },
        "stats": {
            "candidates_matched": len(candidates),
            "selected_count": len(selected),
            "pending_review": sum(1 for i in selected if i.get("review_decision") is None),
            "approved_count": sum(1 for i in selected if i.get("review_decision") == "approve"),
        },
        "items": selected,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--lexicon-json", type=Path, default=DEFAULT_LEXICON)
    ap.add_argument("--max-items", type=int, default=15)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    queue = _read_json(args.queue_json)
    if not queue.get("items"):
        print(json.dumps({"ok": False, "error": f"missing queue items: {args.queue_json}"}))
        return 1

    anchors = _load_anchor_verses(args.lexicon_json)
    doc = build_filtered_queue(queue, anchors=anchors, max_items=args.max_items)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.output_json),
                "selected": doc["stats"]["selected_count"],
                "candidates": doc["stats"]["candidates_matched"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
