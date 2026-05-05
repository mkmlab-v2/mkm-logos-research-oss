#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.92, L:0.87, K:0.72, M:0.45}
# Balance: 90
# Purpose: Fit symbolic mapping weights over anchor-term pairs using v1 loss contract.
# Keywords: symbolic, gematria, 4d, quaternion, mapping, loss, fit
"""Run symbolic math mapping fit v1.

Input JSONL row format:
{
  "source_id": "...",
  "target_id": "...",
  "source_vec4d": [S,L,K,M],
  "target_vec4d": [S,L,K,M]
}
"""

from __future__ import annotations

import argparse
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _l2(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def _mean(v: list[float]) -> float:
    return sum(v) / len(v) if v else 0.0


def _consistency_penalty(a: list[float], b: list[float]) -> float:
    # Lightweight proxy: difference between vector means.
    return abs(_mean(a) - _mean(b))


def _mapping_loss(a: list[float], b: list[float], w_dist: float, w_consistency: float) -> float:
    return (w_dist * _l2(a, b)) + (w_consistency * _consistency_penalty(a, b))


def _load_pairs(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if not isinstance(obj, dict):
                continue
            a = obj.get("source_vec4d")
            b = obj.get("target_vec4d")
            if (
                isinstance(a, list)
                and isinstance(b, list)
                and len(a) == 4
                and len(b) == 4
            ):
                rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Fit symbolic mapping weights on 4D anchor-term pairs.")
    ap.add_argument(
        "--pairs-jsonl",
        type=Path,
        default=Path("tests/fixtures/symbolic_mapping_demo_pairs_v1.jsonl"),
    )
    ap.add_argument("--w-dist-grid", type=str, default="0.5,0.6,0.7,0.8")
    ap.add_argument("--w-consistency-grid", type=str, default="0.2,0.3,0.4,0.5")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/symbolic_math_mapping_fit_v1_latest.json"),
    )
    ns = ap.parse_args()

    pairs = _load_pairs(ns.pairs_jsonl)
    if not pairs:
        raise SystemExit("No valid pairs found.")

    w_dist_grid = [float(x.strip()) for x in ns.w_dist_grid.split(",") if x.strip()]
    w_cons_grid = [float(x.strip()) for x in ns.w_consistency_grid.split(",") if x.strip()]
    combos = list(itertools.product(w_dist_grid, w_cons_grid))
    rows: list[dict[str, Any]] = []
    for wd, wc in combos:
        losses: list[float] = []
        for row in pairs:
            a = [float(x) for x in row["source_vec4d"]]
            b = [float(x) for x in row["target_vec4d"]]
            losses.append(_mapping_loss(a, b, wd, wc))
        mean_loss = sum(losses) / len(losses)
        rows.append(
            {
                "weights": {"w_dist": wd, "w_consistency": wc},
                "mean_mapping_loss": mean_loss,
                "max_mapping_loss": max(losses),
                "min_mapping_loss": min(losses),
            }
        )
    rows = sorted(rows, key=lambda r: (r["mean_mapping_loss"], r["max_mapping_loss"]))
    top_k = max(1, int(ns.top_k))
    best = rows[0]

    payload = {
        "schema": "symbolic_math_mapping_fit_v1",
        "generated_at_utc": _utc_now(),
        "track": "B_TRACK",
        "governance": {
            "research_only": True,
            "non_gating": True,
            "human_review_required": True,
        },
        "inputs": {
            "pairs_jsonl": str(ns.pairs_jsonl.resolve()),
            "pair_count": len(pairs),
            "w_dist_grid": w_dist_grid,
            "w_consistency_grid": w_cons_grid,
        },
        "summary": {
            "candidate_count": len(rows),
            "best_weights": best["weights"],
            "best_mean_mapping_loss": best["mean_mapping_loss"],
        },
        "top_candidates": rows[:top_k],
    }

    ns.out.parent.mkdir(parents=True, exist_ok=True)
    ns.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {ns.out.resolve()} best_mean_loss={best['mean_mapping_loss']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
