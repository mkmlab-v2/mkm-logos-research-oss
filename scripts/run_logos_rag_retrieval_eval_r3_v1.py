#!/usr/bin/env python3
"""R3: KO/EN/hybrid query eval + weak-gold hit@k on ST U index (B-track only)."""
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
    DEFAULT_MODEL,
    DEFAULT_MEDOIDS,
    DEFAULT_SQLITE,
    _encode_query,
    _load_index,
    _load_medoid_weights,
    _retrieve_baseline,
    _retrieve_improved,
    _score_all,
    preprocess_query,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402
from scripts.logos_rag_hybrid_query_v1 import HybridStyle, build_hybrid_text_query, encode_hybrid_query  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_QUERY_SET = ROOT / "docs/final/artifacts/logos_semantic_query_set_v4_ko_en_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_eval_r3_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_items(path: Path) -> list[dict[str, Any]]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    items = doc.get("items")
    if not isinstance(items, list):
        raise ValueError(f"items[] required: {path}")
    return [x for x in items if isinstance(x, dict)]


def _hit_at_k(hits: list[dict[str, Any]], gold: set[str], k: int) -> bool:
    for row in hits[:k]:
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid in gold:
            return True
    return False


def _eval_mode(
    *,
    label: str,
    items: list[dict[str, Any]],
    model: Any,
    index_rows: list[tuple[str, bytes]],
    dim: int,
    medoid_weights: dict[str, float],
    use_improved: bool,
    query_field: str,
    hybrid_style: HybridStyle = "dual_embed_mean",
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    top1_scores: list[float] = []
    hit1 = 0
    hit3 = 0
    gold_n = 0

    for it in items:
        qid = it.get("id")
        if query_field == "query_en":
            raw = str(it.get("query_en") or "").strip()
            q_eff = raw if not use_improved else preprocess_query(raw)
        elif query_field == "query_ko":
            raw = str(it.get("query_ko") or "").strip()
            q_eff = raw if not use_improved else preprocess_query(raw)
        else:
            en = str(it.get("query_en") or "").strip()
            ko = str(it.get("query_ko") or "").strip()
            q_eff, _hybrid_applied = build_hybrid_text_query(en, ko, style=hybrid_style)

        gold_raw = it.get("gold_verse_ids_weak") or it.get("gold_verse_ids") or []
        gold_set = {str(x) for x in gold_raw if isinstance(x, str) and x.strip()}
        if gold_set:
            gold_n += 1

        try:
            if query_field == "hybrid":
                qvec = encode_hybrid_query(
                    model,
                    str(it.get("query_en") or ""),
                    str(it.get("query_ko") or ""),
                    style=hybrid_style,
                )
            else:
                qvec = _encode_query(model, q_eff)
            scored = _score_all(qvec, index_rows, dim)
            if use_improved:
                hits, _meta = _retrieve_improved(
                    scored,
                    max_k=24,
                    floor_abs=0.12,
                    floor_ratio=0.5,
                    medoid_weights=medoid_weights,
                    medoid_boost_cap=0.0,
                )
            else:
                hits = _retrieve_baseline(scored, 3)
            top1 = hits[0] if hits else {}
            sc = top1.get("score")
            if isinstance(sc, (int, float)):
                top1_scores.append(float(sc))
            if gold_set:
                if _hit_at_k(hits, gold_set, 1):
                    hit1 += 1
                if _hit_at_k(hits, gold_set, 3):
                    hit3 += 1
            rows.append(
                {
                    "id": qid,
                    "query_effective": q_eff,
                    "top_match_verse_id": top1.get("verse_id"),
                    "top_match_cosine": sc,
                    "status": "ok",
                    "weak_gold_hit_at_1": _hit_at_k(hits, gold_set, 1) if gold_set else None,
                    "weak_gold_hit_at_3": _hit_at_k(hits, gold_set, 3) if gold_set else None,
                }
            )
        except Exception as e:
            rows.append({"id": qid, "status": "error", "error": str(e)[:200]})

    mean_top1 = sum(top1_scores) / len(top1_scores) if top1_scores else None
    return {
        "mode": label,
        "query_field": query_field,
        "use_improved_retrieval": use_improved,
        "queries_ok": sum(1 for r in rows if r.get("status") == "ok"),
        "mean_top1_cosine": None if mean_top1 is None else round(mean_top1, 9),
        "weak_gold_queries": gold_n,
        "weak_gold_hit_at_1_rate": round(hit1 / gold_n, 9) if gold_n else None,
        "weak_gold_hit_at_3_rate": round(hit3 / gold_n, 9) if gold_n else None,
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query-set-json", type=Path, default=DEFAULT_QUERY_SET)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--hybrid-style",
        choices=(
            "dual_embed_mean",
            "en_ko_concat",
            "ko_en_concat",
            "ko_primary",
        ),
        default="dual_embed_mean",
        help="Hybrid lane query encoding (default: dual_embed_mean per P15 sweep)",
    )
    args = ap.parse_args()
    hybrid_style: HybridStyle = args.hybrid_style  # type: ignore[assignment]

    if not args.sqlite.is_file():
        print(f"Missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2
    if not args.query_set_json.is_file():
        print(f"Missing query set: {args.query_set_json}", file=sys.stderr)
        return 2

    index_rows, dim, mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)
    items = _load_items(args.query_set_json)
    medoid_weights = _load_medoid_weights(args.medoids_json)

    profiles = [
        _eval_mode(
            label="en_baseline_top3",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights={},
            use_improved=False,
            query_field="query_en",
        ),
        _eval_mode(
            label="ko_baseline_top3",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights={},
            use_improved=False,
            query_field="query_ko",
        ),
        _eval_mode(
            label="hybrid_baseline_top3",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights={},
            use_improved=False,
            query_field="hybrid",
            hybrid_style=hybrid_style,
        ),
        _eval_mode(
            label="hybrid_improved_r2",
            items=items,
            model=model,
            index_rows=index_rows,
            dim=dim,
            medoid_weights=medoid_weights,
            use_improved=True,
            query_field="hybrid",
            hybrid_style=hybrid_style,
        ),
    ]

    en_m = profiles[0].get("mean_top1_cosine")
    hy_m = profiles[2].get("mean_top1_cosine")
    imp_m = profiles[3].get("mean_top1_cosine")

    doc = {
        "schema": "comp_logos_rag_retrieval_eval_r3",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "sqlite": str(args.sqlite.resolve()),
        "embedding_mode": mode,
        "index_rows": len(index_rows),
        "query_set_json": str(args.query_set_json.resolve()),
        "hybrid_style": hybrid_style,
        "profiles": profiles,
        "summary": {
            "mean_top1_en": en_m,
            "mean_top1_ko": profiles[1].get("mean_top1_cosine"),
            "mean_top1_hybrid": hy_m,
            "mean_top1_hybrid_improved": imp_m,
            "delta_hybrid_vs_en": (
                round(float(hy_m) - float(en_m), 9)
                if isinstance(hy_m, (int, float)) and isinstance(en_m, (int, float))
                else None
            ),
            "delta_improved_vs_hybrid": (
                round(float(imp_m) - float(hy_m), 9)
                if isinstance(imp_m, (int, float)) and isinstance(hy_m, (int, float))
                else None
            ),
            "weak_gold_hit_at_1_en": profiles[0].get("weak_gold_hit_at_1_rate"),
            "weak_gold_hit_at_1_hybrid": profiles[2].get("weak_gold_hit_at_1_rate"),
            "weak_gold_hit_at_1_hybrid_improved": profiles[3].get("weak_gold_hit_at_1_rate"),
            "weak_gold_disclaimer": "[HYPO] gold_verse_ids_weak are thematic stubs, not adjudicated labels.",
        },
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.output_json), "summary": doc["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
