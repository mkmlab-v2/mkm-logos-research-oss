#!/usr/bin/env python3
"""q01 theology adjudication pack: human thematic gold vs harness top-1 ([HYPO], B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_ROUTER = ROOT / "docs/final/artifacts/logos_subgraph_graphrag_router_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_rag_q01_theology_adjudication_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item(gold: dict[str, Any], qid: str) -> dict[str, Any] | None:
    for it in gold.get("items") or []:
        if isinstance(it, dict) and str(it.get("id")) == qid:
            return it
    return None


def build_report(
    *,
    gold_path: Path,
    router_path: Path | None,
) -> dict[str, Any]:
    gold = json.loads(gold_path.read_text(encoding="utf-8-sig"))
    q01 = _item(gold, "q01")
    if not q01:
        raise SystemExit("q01 missing in gold human JSON")

    human = list(q01.get("gold_verse_ids_human") or [])
    harness = list(q01.get("gold_verse_ids_harness_top1") or [])
    overlap = sorted(set(human) & set(harness))
    human_only = sorted(set(human) - set(harness))
    harness_only = sorted(set(harness) - set(human))

    router_verses: list[str] = []
    if router_path and router_path.is_file():
        router = json.loads(router_path.read_text(encoding="utf-8-sig"))
        router_verses = list(router.get("verse_ids") or [])

    harness_top = harness[0] if harness else None
    dual_track_union = bool(harness_top and harness_top in human)
    covenant_human_primary = [v for v in human if v != harness_top]
    theology_split_documented = bool(harness_top and len(covenant_human_primary) >= 2)
    theology_primary = bool(q01.get("theology_primary_no_harness_union")) or str(
        q01.get("adjudication_status") or ""
    ).startswith("commander_theology_primary")
    commander_action_required = (
        not theology_primary
        and dual_track_union
        and bool(human)
        and human[0] == harness_top
    )
    recommendation = (
        "Keep dual-track: gold_verse_ids_human for thematic covenant set (Ps/Jer); "
        "gold_verse_ids_harness_top1 for retrieval-align eval (Job.24.19). "
        "If Job.24.19 is first in human list, commander may reorder to Ps.89.28 for display-only theology primary."
    )

    return {
        "schema": "logos_rag_q01_theology_adjudication_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query_id": "q01",
        "query_ko": q01.get("query_ko"),
        "query_en": q01.get("query_en"),
        "gold_verse_ids_human": human,
        "gold_verse_ids_harness_top1": harness,
        "overlap_verse_ids": overlap,
        "human_only_verse_ids": human_only,
        "harness_only_verse_ids": harness_only,
        "covenant_human_without_harness_top": covenant_human_primary,
        "dual_track_union_active": dual_track_union,
        "subgraph_router_verse_ids": router_verses,
        "adjudication_status": q01.get("adjudication_status"),
        "adjudication_note": q01.get("adjudication_note"),
        "theology_split_documented": theology_split_documented,
        "commander_action_required": commander_action_required,
        "recommendation_ko": recommendation,
        "eval_policy": {
            "thematic_hit_at_1_uses": "gold_verse_ids_human (+ union/harness align B-track only)",
            "do_not_run": ["Run-LogosRagThematicPrecision_v1.ps1 bootstrap after union"],
        },
        "known_limitations": [
            "This artifact documents eval alignment; not a theological truth claim.",
            "Bridge router verses are GraphRAG demo paths, separate from RAG gold.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_report(gold_path=args.gold_json, router_path=args.router_json)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "theology_split_documented": doc["theology_split_documented"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
