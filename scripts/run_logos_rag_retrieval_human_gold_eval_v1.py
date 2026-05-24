#!/usr/bin/env python3
"""Human-gold sample eval (5 pairs) on ST U index — B-track only."""
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
from scripts.logos_rag_hybrid_query_v1 import HybridStyle  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_QUERY_SET = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_human_gold_eval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _items_with_human_gold(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        row = dict(it)
        human = row.get("gold_verse_ids_human") or []
        row["gold_verse_ids"] = human
        row["gold_verse_ids_weak"] = row.get("gold_verse_ids_weak") or []
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query-set-json", type=Path, default=DEFAULT_QUERY_SET)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument(
        "--hybrid-style",
        choices=("dual_embed_mean", "en_ko_concat", "ko_en_concat", "ko_primary"),
        default="dual_embed_mean",
    )
    args = ap.parse_args()
    hybrid_style: HybridStyle = args.hybrid_style  # type: ignore[assignment]

    if not args.sqlite.is_file() or not args.query_set_json.is_file():
        print("Missing sqlite or query set", file=sys.stderr)
        return 2

    gold_doc = json.loads(args.query_set_json.read_text(encoding="utf-8-sig"))
    items = _items_with_human_gold(_load_items(args.query_set_json))
    gold_signoff = str(gold_doc.get("signoff") or "")
    index_rows, dim, mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)
    medoid_weights = _load_medoid_weights(
        ROOT / "docs/final/artifacts/logos_verse_4d_medoids_v1_latest.json"
    )

    profiles = [
        _eval_mode(
            label="ko_baseline_human_gold",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights={},
            use_improved=False,
            query_field="query_ko",
        ),
        _eval_mode(
            label="ko_improved_human_gold",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="query_ko",
        ),
        _eval_mode(
            label="hybrid_improved_human_gold",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="hybrid",
            hybrid_style=hybrid_style,
        ),
        _eval_mode(
            label="hybrid_ko_primary_improved_human_gold",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="hybrid",
            hybrid_style="ko_primary",
        ),
    ]

    doc = {
        "schema": "comp_logos_rag_retrieval_human_gold_eval_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "pairs": len(items),
        "sqlite": str(args.sqlite.resolve()),
        "embedding_mode": mode,
        "query_set_json": str(args.query_set_json.resolve()),
        "profiles": profiles,
        "summary": {
            "human_gold_hit_at_1_ko_baseline": profiles[0].get("weak_gold_hit_at_1_rate"),
            "human_gold_hit_at_1_ko_improved": profiles[1].get("weak_gold_hit_at_1_rate"),
            "human_gold_hit_at_1_hybrid_improved": profiles[2].get("weak_gold_hit_at_1_rate"),
            "human_gold_hit_at_1_hybrid_ko_primary": profiles[3].get("weak_gold_hit_at_1_rate"),
            "hybrid_style_default": hybrid_style,
            "signoff": (
                "commander_approved_dual_track"
                if gold_signoff == "commander_approved"
                else "pending_commander"
            ),
            "disclaimer": "gold_verse_ids_human includes thematic + selective KO top1 anchors for eval harness.",
        },
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json), "summary": doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
