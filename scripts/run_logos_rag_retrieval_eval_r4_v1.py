#!/usr/bin/env python3
"""R4: human gold hit@k when gold_verse_ids_human filled; KO user-query sim via pilot route."""
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

from scripts.logos_rag_query_route_v1 import build_retrieval_query, detect_query_route  # noqa: E402
from scripts.run_logos_rag_retrieval_eval_r3_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_MEDOIDS,
    DEFAULT_SQLITE,
    _eval_mode,
    _load_index,
    _load_items,
    _load_medoid_weights,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_eval_r4_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _items_for_user_query_sim(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Simulate end-user typing query_ko only (R4 pilot default)."""
    out: list[dict[str, Any]] = []
    for it in items:
        ko = str(it.get("query_ko") or "").strip()
        row = dict(it)
        row["query_en"] = ko
        row["user_query_sim"] = ko
        out.append(row)
    return out


def _human_gold_eval(
    *,
    items: list[dict[str, Any]],
    model: Any,
    index_rows: list,
    dim: int,
    medoid_weights: dict[str, float],
) -> dict[str, Any]:
    from scripts.run_logos_rag_retrieval_eval_r3_v1 import _hit_at_k
    from scripts.run_logos_rag_retrieval_round_v1 import (
        _encode_query,
        _retrieve_baseline,
        _score_all,
        preprocess_query,
    )

    hit1 = hit3 = gold_n = 0
    rows: list[dict[str, Any]] = []
    for it in items:
        gold_raw = it.get("gold_verse_ids_human") or []
        gold_set = {str(x) for x in gold_raw if isinstance(x, str) and x.strip()}
        if not gold_set:
            continue
        gold_n += 1
        uq = str(it.get("query_ko") or it.get("user_query_sim") or "").strip()
        route = detect_query_route(uq, policy="auto")
        rq, _ = build_retrieval_query(uq, route)
        qvec = _encode_query(model, rq)
        scored = _score_all(qvec, index_rows, dim)
        hits = _retrieve_baseline(scored, 3)
        if _hit_at_k(hits, gold_set, 1):
            hit1 += 1
        if _hit_at_k(hits, gold_set, 3):
            hit3 += 1
        rows.append(
            {
                "id": it.get("id"),
                "route": route,
                "retrieval_query": rq,
                "top_match": hits[0] if hits else None,
                "hit_at_1": _hit_at_k(hits, gold_set, 1),
                "hit_at_3": _hit_at_k(hits, gold_set, 3),
            }
        )
    return {
        "adjudicated_queries": gold_n,
        "hit_at_1_rate": round(hit1 / gold_n, 9) if gold_n else None,
        "hit_at_3_rate": round(hit3 / gold_n, 9) if gold_n else None,
        "rows": rows,
        "pending": sum(
            1
            for it in items
            if not (it.get("gold_verse_ids_human") and len(it.get("gold_verse_ids_human")) > 0)
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    items = _load_items(args.gold_json)
    index_rows, dim, mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)
    medoid_weights = _load_medoid_weights(args.medoids_json)

    sim_items = _items_for_user_query_sim(items)
    ko_user = _eval_mode(
        label="ko_user_query_auto_route",
        items=sim_items,
        model=model,
        index_rows=index_rows,
        dim=dim,
        medoid_weights=medoid_weights,
        use_improved=True,
        query_field="query_en",
    )
    human = _human_gold_eval(
        items=items,
        model=model,
        index_rows=index_rows,
        dim=dim,
        medoid_weights=medoid_weights,
    )

    doc = {
        "schema": "comp_logos_rag_retrieval_eval_r4",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "sqlite": str(args.sqlite.resolve()),
        "gold_json": str(args.gold_json.resolve()),
        "ko_user_query_profile": ko_user,
        "human_gold_eval": human,
        "summary": {
            "mean_top1_ko_user_sim": ko_user.get("mean_top1_cosine"),
            "human_hit_at_1": human.get("hit_at_1_rate"),
            "human_adjudicated_n": human.get("adjudicated_queries"),
            "human_pending_n": human.get("pending"),
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
