#!/usr/bin/env python3
"""Eval KO/hybrid vs thematic gold and vs harness top-1 (dual-track, B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_logos_rag_retrieval_eval_r3_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_SQLITE,
    _eval_mode,
    _load_index,
    _load_items,
    _load_medoid_weights,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

PILOT = ROOT / "reports/constitution/btrack_pilot"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_dual_gold_eval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _items_with_gold(items: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        row = dict(it)
        row["gold_verse_ids"] = row.get(field) or []
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    args = ap.parse_args()

    if not args.gold_json.is_file() or not args.sqlite.is_file():
        print("Missing gold or sqlite", file=sys.stderr)
        return 2

    raw_items = _load_items(args.gold_json)
    thematic_items = _items_with_gold(raw_items, "gold_verse_ids_human")
    harness_items = _items_with_gold(raw_items, "gold_verse_ids_harness_top1")

    index_rows, dim, mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)
    medoid_weights = _load_medoid_weights(
        ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json"
    )

    profiles = [
        _eval_mode(
            label="ko_improved_vs_thematic_gold",
            items=thematic_items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="query_ko",
            hybrid_style="dual_embed_mean",
        ),
        _eval_mode(
            label="ko_improved_vs_harness_top1",
            items=harness_items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="query_ko",
            hybrid_style="dual_embed_mean",
        ),
        _eval_mode(
            label="hybrid_dual_vs_thematic_gold",
            items=thematic_items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="hybrid",
            hybrid_style="dual_embed_mean",
        ),
        _eval_mode(
            label="hybrid_dual_vs_harness_top1",
            items=harness_items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="hybrid",
            hybrid_style="dual_embed_mean",
        ),
    ]

    doc = {
        "schema": "comp_logos_rag_dual_gold_eval_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "gold_json": str(args.gold_json.resolve()),
        "profiles": profiles,
        "summary": {
            "thematic_hit_at_1_ko_improved": profiles[0].get("weak_gold_hit_at_1_rate"),
            "harness_hit_at_1_ko_improved": profiles[1].get("weak_gold_hit_at_1_rate"),
            "thematic_hit_at_1_hybrid_dual": profiles[2].get("weak_gold_hit_at_1_rate"),
            "harness_hit_at_1_hybrid_dual": profiles[3].get("weak_gold_hit_at_1_rate"),
            "signoff": "commander_approved_dual_track",
            "interpretation": (
                "harness_hit@1 measures regression alignment to KO top-1 only; "
                "thematic_hit@1 measures adjudicated thematic labels."
            ),
        },
        "track_wall": {"prophecy_promotion_gates_touch": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json), "summary": doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
