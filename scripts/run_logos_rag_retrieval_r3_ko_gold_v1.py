#!/usr/bin/env python3
"""P15 R3 — KO queries + proxy gold eval + medoid AB (B-track only).

Proxy gold: top-3 verse_id from EN improved profile in comp_logos_rag_retrieval_v1 (same index order as v3_ko).
Does not touch Track A, prophecy gates, VPS, or production logos_vector_index_ann_lite_v1.sqlite.
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

from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    DEFAULT_BUILD_REPORT,
    DEFAULT_MEDOIDS,
    DEFAULT_MODEL,
    DEFAULT_SQLITE,
    DEFAULT_VERSE_JSONL,
    _eval_profile,
    _load_index,
    _load_medoid_weights,
    _load_queries,
    _maybe_build_index,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_KO_SET = ROOT / "docs" / "final" / "artifacts" / "logos_semantic_query_set_v3_ko.json"
DEFAULT_EN_SET = ROOT / "docs" / "final" / "artifacts" / "logos_semantic_query_set_v3.json"
DEFAULT_EN_RAG = PILOT / "comp_logos_rag_retrieval_v1_latest.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_r3_ko_gold_v1_latest.json"

SCHEMA = "comp_logos_rag_retrieval_r3_ko_gold_v1"
VERSION = "1.0.0"
BARRIER = 0.27


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_proxy_gold(en_rag: Path, en_set: Path, ko_set: Path) -> list[dict[str, Any]]:
    en_doc = json.loads(en_rag.read_text(encoding="utf-8"))
    after_rows = (en_doc.get("after") or {}).get("rows") or []
    en_queries = _load_queries(en_set)
    ko_queries = _load_queries(ko_set)
    n = min(len(after_rows), len(en_queries), len(ko_queries))
    items: list[dict[str, Any]] = []
    for i in range(n):
        row = after_rows[i]
        hits = row.get("top_hits") or []
        gold_ids = [h["verse_id"] for h in hits[:3] if isinstance(h, dict) and h.get("verse_id")]
        items.append(
            {
                "index": i,
                "query_en": en_queries[i],
                "query_ko": ko_queries[i],
                "gold_verse_ids": gold_ids,
                "gold_source": "proxy_en_improved_top3",
                "en_top1_cosine": row.get("top_match_cosine"),
            }
        )
    return items


def _gold_metrics(profile: dict[str, Any], gold_items: list[dict[str, Any]]) -> dict[str, Any]:
    rows = profile.get("rows") or []
    n = min(len(rows), len(gold_items))
    hit1 = hit3 = above_barrier = 0
    for i in range(n):
        pred = rows[i].get("top_match_verse_id")
        gold = set(gold_items[i].get("gold_verse_ids") or [])
        if not pred or not gold:
            continue
        if pred in gold:
            hit1 += 1
        top_hits = rows[i].get("top_hits") or []
        top3_ids = {h.get("verse_id") for h in top_hits[:3] if isinstance(h, dict)}
        if gold & top3_ids:
            hit3 += 1
        cos = rows[i].get("top_match_cosine")
        if isinstance(cos, (int, float)) and float(cos) >= BARRIER:
            above_barrier += 1
    denom = n or 1
    return {
        "pairs_evaluated": n,
        "hit_at_1": round(hit1 / denom, 6),
        "hit_at_3": round(hit3 / denom, 6),
        "top1_at_or_above_barrier_0_27": round(above_barrier / denom, 6),
        "barrier": BARRIER,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verse-jsonl", type=Path, default=DEFAULT_VERSE_JSONL)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--build-report", type=Path, default=DEFAULT_BUILD_REPORT)
    ap.add_argument("--ko-query-set-json", type=Path, default=DEFAULT_KO_SET)
    ap.add_argument("--en-query-set-json", type=Path, default=DEFAULT_EN_SET)
    ap.add_argument("--en-rag-json", type=Path, default=DEFAULT_EN_RAG)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--baseline-top-k", type=int, default=3)
    ap.add_argument("--improved-max-k", type=int, default=24)
    ap.add_argument("--score-floor-abs", type=float, default=0.12)
    ap.add_argument("--score-floor-ratio", type=float, default=0.62)
    ap.add_argument("--medoid-boost-cap", type=float, default=0.08)
    args = ap.parse_args()

    for p, label in [
        (args.ko_query_set_json, "KO query set"),
        (args.en_query_set_json, "EN query set"),
        (args.en_rag_json, "EN RAG report"),
    ]:
        if not p.is_file():
            print(f"Missing {label}: {p}", file=sys.stderr)
            return 2

    build_step = _maybe_build_index(
        verse_jsonl=args.verse_jsonl,
        sqlite_out=args.sqlite,
        build_report=args.build_report,
        model_id=args.sentence_transformer_model,
        max_verses=0,
        skip_build=args.skip_build,
    )
    if build_step.get("exit_code", 0) != 0:
        print(json.dumps({"ok": False, "build": build_step}, ensure_ascii=False), file=sys.stderr)
        return int(build_step.get("exit_code") or 1)

    try:
        index_rows, dim, mode = _load_index(args.sqlite)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 3

    try:
        model = load_sentence_transformer(args.sentence_transformer_model)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 6

    ko_queries = _load_queries(args.ko_query_set_json)
    gold_items = _build_proxy_gold(args.en_rag_json, args.en_query_set_json, args.ko_query_set_json)
    medoid_weights = _load_medoid_weights(args.medoids_json)

    ko_before = _eval_profile(
        label="ko_before_baseline",
        queries=ko_queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=False,
        improved=False,
        top_k=args.baseline_top_k,
        max_k=args.baseline_top_k,
        floor_abs=0.0,
        floor_ratio=0.0,
        medoid_weights={},
        medoid_boost_cap=0.0,
    )
    ko_after_no_medoid = _eval_profile(
        label="ko_after_improved_medoid_off",
        queries=ko_queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=True,
        improved=True,
        top_k=args.baseline_top_k,
        max_k=args.improved_max_k,
        floor_abs=args.score_floor_abs,
        floor_ratio=args.score_floor_ratio,
        medoid_weights=medoid_weights,
        medoid_boost_cap=0.0,
    )
    ko_after_medoid = _eval_profile(
        label="ko_after_improved_medoid_on",
        queries=ko_queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=True,
        improved=True,
        top_k=args.baseline_top_k,
        max_k=args.improved_max_k,
        floor_abs=args.score_floor_abs,
        floor_ratio=args.score_floor_ratio,
        medoid_weights=medoid_weights,
        medoid_boost_cap=args.medoid_boost_cap,
    )

    m_before = _gold_metrics(ko_before, gold_items)
    m_no_med = _gold_metrics(ko_after_no_medoid, gold_items)
    m_med = _gold_metrics(ko_after_medoid, gold_items)

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
            "sqlite": str(args.sqlite.resolve()),
            "ko_query_set_json": str(args.ko_query_set_json.resolve()),
            "en_rag_proxy_gold_json": str(args.en_rag_json.resolve()),
            "medoids_json": str(args.medoids_json.resolve()) if args.medoids_json.is_file() else None,
            "index_rows": len(index_rows),
            "embedding_mode": mode,
        },
        "proxy_gold": {
            "method": "en_improved_top3_same_index",
            "caveat": "[HYPO] proxy gold — not human-curated theme anchors",
            "items": gold_items,
        },
        "medoid_ab": {
            "cap_off": {"profile": "ko_after_improved_medoid_off", "metrics": m_no_med},
            "cap_on": {
                "profile": "ko_after_improved_medoid_on",
                "medoid_boost_cap": args.medoid_boost_cap,
                "metrics": m_med,
            },
            "delta_hit_at_1": round(m_med["hit_at_1"] - m_no_med["hit_at_1"], 6),
            "delta_mean_top1": None,
        },
        "ko_before": ko_before,
        "ko_after_no_medoid": ko_after_no_medoid,
        "ko_after_medoid": ko_after_medoid,
        "gold_eval": {
            "ko_before": m_before,
            "ko_after_no_medoid": m_no_med,
            "ko_after_medoid": m_med,
        },
        "summary": {
            "mean_top1_ko_before": ko_before.get("mean_top1_cosine"),
            "mean_top1_ko_after_no_medoid": ko_after_no_medoid.get("mean_top1_cosine"),
            "mean_top1_ko_after_medoid": ko_after_medoid.get("mean_top1_cosine"),
            "barrier_0_27": BARRIER,
            "note": "barrier applies to top1 cosine; proxy gold hit uses EN-improved top3 labels.",
        },
        "build_step": build_step,
    }
    b_mean = ko_before.get("mean_top1_cosine")
    a0 = ko_after_no_medoid.get("mean_top1_cosine")
    a1 = ko_after_medoid.get("mean_top1_cosine")
    if isinstance(a0, (int, float)) and isinstance(a1, (int, float)):
        doc["medoid_ab"]["delta_mean_top1"] = round(float(a1) - float(a0), 9)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.output_json),
                "mean_ko_after_medoid": a1,
                "hit_at_1_medoid_on": m_med["hit_at_1"],
                "above_barrier_rate": m_med["top1_at_or_above_barrier_0_27"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
