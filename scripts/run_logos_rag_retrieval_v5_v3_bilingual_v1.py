#!/usr/bin/env python3
"""R5: v3 EN probes vs mapped KO gloss — mean cosine uplift (B-track only).

Bridges logos_semantic_query_set_v3 (EN-only) with v4/human KO strings so the
~0.20 v3 bench is not misread as the only retrieval ceiling. Winner knobs from
hybrid sweep: ko_only_improved (floor_abs=0.12, floor_ratio=0.5, medoid_boost=0).

Does NOT touch Track A compression, prophecy gates, or gematria bridge.
"""
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

from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402
from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_MEDOIDS,
    DEFAULT_SQLITE,
    _eval_profile,
    _load_index,
    _load_medoid_weights,
    _load_queries,
    preprocess_query,
)

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_V3 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v3.json"
DEFAULT_V4 = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_v5_v3_bilingual_v1_latest.json"

SCHEMA = "comp_logos_rag_retrieval_v5_v3_bilingual_v1"
VERSION = "1.0.0"

# hybrid sweep winner (comp_logos_rag_hybrid_improvement_sweep_v1_latest.json)
KO_WINNER = {
    "floor_abs": 0.12,
    "floor_ratio": 0.5,
    "medoid_boost_cap": 0.0,
    "max_k": 24,
    "top_k": 3,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_v4_ko_by_en(path: Path) -> dict[str, str]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    items = doc.get("items")
    if not isinstance(items, list):
        raise ValueError(f"items[] required: {path}")
    out: dict[str, str] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        en = str(it.get("query_en") or "").strip()
        ko = str(it.get("query_ko") or "").strip()
        if en and ko:
            out[en] = ko
    return out


def _build_bilingual_items(
    en_queries: list[str], ko_by_en: dict[str, str]
) -> tuple[list[dict[str, Any]], list[str]]:
    items: list[dict[str, Any]] = []
    ko_queries: list[str] = []
    missing: list[str] = []
    for i, en in enumerate(en_queries, start=1):
        ko = ko_by_en.get(en)
        if not ko:
            missing.append(en)
            continue
        items.append(
            {
                "id": f"q{i:02d}",
                "query_en": en,
                "query_ko": ko,
            }
        )
        ko_queries.append(ko)
    return items, ko_queries


def _delta_mean(before: dict[str, Any] | None, after: dict[str, Any] | None) -> float | None:
    if not before or not after:
        return None
    b = before.get("mean_top1_cosine")
    a = after.get("mean_top1_cosine")
    if not isinstance(b, (int, float)) or not isinstance(a, (int, float)):
        return None
    return round(float(a) - float(b), 9)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query-set-v3", type=Path, default=DEFAULT_V3)
    ap.add_argument("--query-set-v4", type=Path, default=DEFAULT_V4)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--model-id", default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.sqlite.is_file():
        print(f"ERROR missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2

    en_queries = _load_queries(args.query_set_v3)
    ko_by_en = _load_v4_ko_by_en(args.query_set_v4)
    items, ko_queries = _build_bilingual_items(en_queries, ko_by_en)
    if len(ko_queries) != len(en_queries):
        print(
            f"WARN ko mapping incomplete: {len(ko_queries)}/{len(en_queries)}",
            file=sys.stderr,
        )

    index_rows, dim, mode = _load_index(args.sqlite)
    medoid_weights = _load_medoid_weights(args.medoids_json)
    model = load_sentence_transformer(args.model_id)

    en_before = _eval_profile(
        label="v3_en_baseline_top3",
        queries=en_queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=False,
        improved=False,
        top_k=KO_WINNER["top_k"],
        max_k=KO_WINNER["max_k"],
        floor_abs=0.0,
        floor_ratio=0.0,
        medoid_weights=medoid_weights,
        medoid_boost_cap=0.0,
    )
    en_after = _eval_profile(
        label="v3_en_improved",
        queries=en_queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=True,
        improved=True,
        top_k=KO_WINNER["top_k"],
        max_k=KO_WINNER["max_k"],
        floor_abs=KO_WINNER["floor_abs"],
        floor_ratio=KO_WINNER["floor_ratio"],
        medoid_weights=medoid_weights,
        medoid_boost_cap=KO_WINNER["medoid_boost_cap"],
    )
    ko_winner = _eval_profile(
        label="v3_ko_gloss_improved",
        queries=[preprocess_query(k) for k in ko_queries],
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=False,
        improved=True,
        top_k=KO_WINNER["top_k"],
        max_k=KO_WINNER["max_k"],
        floor_abs=KO_WINNER["floor_abs"],
        floor_ratio=KO_WINNER["floor_ratio"],
        medoid_weights=medoid_weights,
        medoid_boost_cap=KO_WINNER["medoid_boost_cap"],
    )

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating_ack": True,
        "track_wall": {
            "shadow_only": True,
            "auto_trade_enable": False,
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
        },
        "inputs": {
            "query_set_v3": str(args.query_set_v3),
            "query_set_v4_ko_map": str(args.query_set_v4),
            "sqlite": str(args.sqlite),
            "embedding_mode": mode,
            "index_rows": len(index_rows),
            "bilingual_items": len(items),
        },
        "knobs": KO_WINNER,
        "headline": {
            "v3_en_baseline_mean_top1_cosine": en_before.get("mean_top1_cosine"),
            "v3_en_improved_mean_top1_cosine": en_after.get("mean_top1_cosine"),
            "v3_ko_gloss_improved_mean_top1_cosine": ko_winner.get("mean_top1_cosine"),
            "delta_ko_minus_en_improved": _delta_mean(en_after, ko_winner),
            "interpretation_ko": (
                "v3 JSON is EN-only; KO gloss from v4 map. "
                "Report ~0.20 only on EN v3; KO route is separate metric."
            ),
        },
        "profiles": {
            "v3_en_baseline_top3": en_before,
            "v3_en_improved": en_after,
            "v3_ko_gloss_improved": ko_winner,
        },
        "bilingual_items": items,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    h = doc["headline"]
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output_json),
                "en_baseline": h.get("v3_en_baseline_mean_top1_cosine"),
                "en_improved": h.get("v3_en_improved_mean_top1_cosine"),
                "ko_improved": h.get("v3_ko_gloss_improved_mean_top1_cosine"),
                "delta_ko_minus_en": h.get("delta_ko_minus_en_improved"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
