#!/usr/bin/env python3
"""R2 parallel knob sweep on existing ST U index (B-track, no rebuild)."""
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
    DEFAULT_QUERY_SET,
    DEFAULT_SQLITE,
    _eval_profile,
    _load_index,
    _load_medoid_weights,
    _load_queries,
    preprocess_query,
)
from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer  # noqa: E402

PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_OUT = PILOT / "comp_logos_rag_retrieval_sweep_r2_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", type=Path, default=DEFAULT_SQLITE)
    ap.add_argument("--query-set-json", type=Path, default=DEFAULT_QUERY_SET)
    ap.add_argument("--medoids-json", type=Path, default=DEFAULT_MEDOIDS)
    ap.add_argument("--sentence-transformer-model", type=str, default=DEFAULT_MODEL)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.sqlite.is_file():
        print(f"Missing sqlite: {args.sqlite}", file=sys.stderr)
        return 2

    index_rows, dim, mode = _load_index(args.sqlite)
    model = load_sentence_transformer(args.sentence_transformer_model)
    queries = _load_queries(args.query_set_json)
    medoid_weights = _load_medoid_weights(args.medoids_json)

    before = _eval_profile(
        label="baseline_fixed_top3",
        queries=queries,
        model=model,
        index_rows=index_rows,
        dim=dim,
        preprocess=False,
        improved=False,
        top_k=3,
        max_k=3,
        floor_abs=0.0,
        floor_ratio=0.0,
        medoid_weights={},
        medoid_boost_cap=0.0,
    )

    medoid_caps = [0.0, 0.02, 0.04, 0.06, 0.08]
    floor_ratios = [0.5, 0.62, 0.75]
    grid: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None

    for cap in medoid_caps:
        for fr in floor_ratios:
            prof = _eval_profile(
                label=f"improved_cap{cap}_fr{fr}",
                queries=queries,
                model=model,
                index_rows=index_rows,
                dim=dim,
                preprocess=True,
                improved=True,
                top_k=3,
                max_k=24,
                floor_abs=0.12,
                floor_ratio=fr,
                medoid_weights=medoid_weights,
                medoid_boost_cap=cap,
            )
            row = {
                "medoid_boost_cap": cap,
                "score_floor_ratio": fr,
                "mean_top1_cosine": prof.get("mean_top1_cosine"),
                "queries_ok": prof.get("queries_ok"),
            }
            grid.append(row)
            m = row.get("mean_top1_cosine")
            if isinstance(m, (int, float)):
                if best is None or float(m) > float(best.get("mean_top1_cosine") or -1):
                    best = {**row, "profile": prof.get("profile")}

    b_mean = before.get("mean_top1_cosine")
    best_mean = best.get("mean_top1_cosine") if best else None
    delta = None
    if isinstance(b_mean, (int, float)) and isinstance(best_mean, (int, float)):
        delta = round(float(best_mean) - float(b_mean), 9)

    doc = {
        "schema": "comp_logos_rag_retrieval_sweep_r2",
        "version": "1.0.0",
        "ts_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "sqlite": str(args.sqlite.resolve()),
        "embedding_mode": mode,
        "index_rows": len(index_rows),
        "baseline": before,
        "grid": grid,
        "best": best,
        "summary": {
            "mean_top1_baseline": b_mean,
            "mean_top1_best": best_mean,
            "mean_top1_delta": delta,
        },
        "track_wall": {
            "prophecy_promotion_gates_touch": False,
            "track_a_compression_touch": False,
            "use_gematria_4d_bridge": False,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "out": str(args.output_json), "best": best, "delta": delta},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
