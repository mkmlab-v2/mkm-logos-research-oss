#!/usr/bin/env python3
"""Hybrid query + retrieval knob sweep on human gold v1 (B-track, ST U index)."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_logos_rag_retrieval_eval_r3_v1 import (  # noqa: E402
    DEFAULT_MODEL,
    DEFAULT_MEDOIDS,
    DEFAULT_SQLITE,
    _hit_at_k,
    _load_items,
    _load_medoid_weights,
)
from scripts.run_logos_rag_retrieval_round_v1 import (  # noqa: E402
    _encode_query,
    _load_index,
    _retrieve_baseline,
    _retrieve_improved,
    _score_all,
    preprocess_query,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_GOLD = ROOT / "docs/final/artifacts/logos_semantic_query_gold_human_v1.json"
DEFAULT_OUT = PILOT / "comp_logos_rag_hybrid_improvement_sweep_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _items_human_gold(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        row = dict(it)
        row["gold_verse_ids"] = row.get("gold_verse_ids_human") or []
        out.append(row)
    return out


def _encode_dual_mean(model: Any, en: str, ko: str) -> list[float]:
    import numpy as np

    v1 = np.asarray(
        model.encode([preprocess_query(ko)], normalize_embeddings=True)[0], dtype=np.float32
    )
    v2 = np.asarray(model.encode([en.strip()], normalize_embeddings=True)[0], dtype=np.float32)
    m = (v1 + v2) * 0.5
    n = float(np.linalg.norm(m))
    if n > 0:
        m = m / n
    return m.tolist()


@dataclass(frozen=True)
class HybridVariant:
    name: str
    use_improved: bool
    floor_abs: float
    floor_ratio: float
    medoid_boost_cap: float
    top_k: int
    max_k: int


def _eval_variant(
    *,
    variant: HybridVariant,
    items: list[dict[str, Any]],
    model: Any,
    index_rows: list,
    dim: int,
    medoid_weights: dict[str, float],
    query_fn: Callable[[dict[str, Any]], tuple[str, str]],
) -> dict[str, Any]:
    hit1 = hit3 = gold_n = 0
    top1_scores: list[float] = []
    miss_ids: list[str] = []

    for it in items:
        gold_raw = it.get("gold_verse_ids") or []
        gold_set = {str(x) for x in gold_raw if isinstance(x, str) and x.strip()}
        if not gold_set:
            continue
        gold_n += 1
        q_eff, q_style = query_fn(it)
        qvec = _encode_query(model, q_eff) if q_style != "dual_mean" else _encode_dual_mean(
            model, str(it.get("query_en") or ""), str(it.get("query_ko") or "")
        )
        scored = _score_all(qvec, index_rows, dim)
        if variant.use_improved:
            hits, _meta = _retrieve_improved(
                scored,
                max_k=variant.max_k,
                floor_abs=variant.floor_abs,
                floor_ratio=variant.floor_ratio,
                medoid_weights=medoid_weights,
                medoid_boost_cap=variant.medoid_boost_cap,
            )
        else:
            hits = _retrieve_baseline(scored, variant.top_k)
        if _hit_at_k(hits, gold_set, 1):
            hit1 += 1
        else:
            miss_ids.append(str(it.get("id") or ""))
        if _hit_at_k(hits, gold_set, 3):
            hit3 += 1
        sc = hits[0].get("score") if hits else None
        if isinstance(sc, (int, float)):
            top1_scores.append(float(sc))

    mean_top1 = sum(top1_scores) / len(top1_scores) if top1_scores else None
    return {
        "variant": variant.name,
        "use_improved_retrieval": variant.use_improved,
        "floor_abs": variant.floor_abs,
        "floor_ratio": variant.floor_ratio,
        "medoid_boost_cap": variant.medoid_boost_cap,
        "human_gold_queries": gold_n,
        "human_gold_hit_at_1_rate": round(hit1 / gold_n, 9) if gold_n else None,
        "human_gold_hit_at_3_rate": round(hit3 / gold_n, 9) if gold_n else None,
        "mean_top1_cosine": None if mean_top1 is None else round(mean_top1, 9),
        "miss_at_1_ids": miss_ids,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold-json", type=Path, default=DEFAULT_GOLD)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    args = ap.parse_args()

    if not args.gold_json.is_file() or not args.sqlite.is_file():
        print("Missing gold or sqlite", file=sys.stderr)
        return 2

    items = _items_human_gold(_load_items(args.gold_json))
    index_rows, dim, mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)
    medoid_weights = _load_medoid_weights(args.medoids_json)

    improved_default = HybridVariant(
        "en_ko_improved_default",
        use_improved=True,
        floor_abs=0.12,
        floor_ratio=0.5,
        medoid_boost_cap=0.0,
        top_k=3,
        max_k=24,
    )
    variants = [
        improved_default,
        HybridVariant("ko_en_improved", True, 0.12, 0.5, 0.0, 3, 24),
        HybridVariant("ko_only_improved", True, 0.12, 0.5, 0.0, 3, 24),
        HybridVariant("en_ko_baseline_top3", False, 0.0, 0.0, 0.0, 3, 3),
        HybridVariant("ko_en_baseline_top3", False, 0.0, 0.0, 0.0, 3, 3),
        HybridVariant("en_ko_improved_cap0.04", True, 0.12, 0.5, 0.04, 3, 24),
        HybridVariant("en_ko_improved_fr0.35", True, 0.12, 0.35, 0.0, 3, 24),
        HybridVariant("dual_embed_mean_improved", True, 0.12, 0.5, 0.0, 3, 24),
    ]

    def en_ko_pp(it: dict[str, Any]) -> tuple[str, str]:
        en = str(it.get("query_en") or "").strip()
        ko = str(it.get("query_ko") or "").strip()
        return preprocess_query(f"{en}. {ko}"), "en_ko"

    def ko_en_pp(it: dict[str, Any]) -> tuple[str, str]:
        en = str(it.get("query_en") or "").strip()
        ko = str(it.get("query_ko") or "").strip()
        return preprocess_query(f"{ko}. {en}"), "ko_en"

    def ko_only_pp(it: dict[str, Any]) -> tuple[str, str]:
        return preprocess_query(str(it.get("query_ko") or "").strip()), "ko_only"

    def dual_mean(_it: dict[str, Any]) -> tuple[str, str]:
        return "", "dual_mean"

    query_fns: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
        "en_ko_improved_default": en_ko_pp,
        "ko_en_improved": ko_en_pp,
        "ko_only_improved": ko_only_pp,
        "en_ko_baseline_top3": en_ko_pp,
        "ko_en_baseline_top3": ko_en_pp,
        "en_ko_improved_cap0.04": en_ko_pp,
        "en_ko_improved_fr0.35": en_ko_pp,
        "dual_embed_mean_improved": dual_mean,
    }

    rows: list[dict[str, Any]] = []
    for v in variants:
        rows.append(
            _eval_variant(
                variant=v,
                items=items,
                model=model,
                index_rows=index_rows,
                dim=dim,
                medoid_weights=medoid_weights if v.use_improved else {},
                query_fn=query_fns[v.name],
            )
        )

    baseline_hit = next(
        (r["human_gold_hit_at_1_rate"] for r in rows if r["variant"] == "en_ko_improved_default"),
        None,
    )
    winner = max(
        rows,
        key=lambda r: (
            float(r["human_gold_hit_at_1_rate"] or -1),
            float(r["mean_top1_cosine"] or -1),
        ),
    )
    doc = {
        "schema": "comp_logos_rag_hybrid_improvement_sweep_v1",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "sqlite": str(args.sqlite.resolve()),
        "gold_json": str(args.gold_json.resolve()),
        "embedding_mode": mode,
        "baseline_variant": "en_ko_improved_default",
        "baseline_hit_at_1": baseline_hit,
        "winner": winner,
        "variants": rows,
        "track_wall": {"prophecy_promotion_gates_touch": False},
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.output_json),
                "baseline_hit_at_1": baseline_hit,
                "winner": winner.get("variant"),
                "winner_hit_at_1": winner.get("human_gold_hit_at_1_rate"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
