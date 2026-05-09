#!/usr/bin/env python3
"""Sweep simple 4D weighting schemes for fractal-resonance vs performance fit."""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MATRIX = ART / "logos_fractal_archetype_4d_matrix_v1.json"
DEFAULT_OUT = ART / "logos_fractal_matrix_sweep_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _corr(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    mx, my = mean(xs), mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return round(num / (den_x * den_y), 6)


def _weighted_cosine(a: dict[str, float], b: dict[str, float], w: dict[str, float]) -> float:
    dims = ("S", "L", "K", "M")
    dot = sum(w[d] * a[d] * b[d] for d in dims)
    na = math.sqrt(sum(w[d] * a[d] * a[d] for d in dims))
    nb = math.sqrt(sum(w[d] * b[d] * b[d] for d in dims))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _tag_paths(tag: str) -> tuple[Path, Path]:
    if tag == "latest":
        return (
            ART / "logos_fractal_sign_reading_latest_latest.json",
            ART / "logos_symbolic_event_backtest_latest_latest.json",
        )
    return (
        ART / f"logos_fractal_sign_reading_{tag}_latest.json",
        ART / f"logos_symbolic_event_backtest_{tag}_latest.json",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Run matrix/weight sweep for fractal fit.")
    ap.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--random-samples", type=int, default=120)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    matrix = _load_json(args.matrix_json)
    archetypes = []
    for a in matrix.get("archetypes", []):
        vec = a.get("vector_slkm") or {}
        archetypes.append(
            {
                "id": str(a.get("id", "")),
                "vec": {
                    "S": float(vec.get("S", 0.5)),
                    "L": float(vec.get("L", 0.5)),
                    "K": float(vec.get("K", 0.5)),
                    "M": float(vec.get("M", 0.5)),
                },
            }
        )

    tags = [
        "latest",
        "contrastive_challenge",
        "contrastive_expanded",
        "split1",
        "split2",
        "split3",
        "blind_split",
        "blind_split_hardset",
    ]

    base_rows: list[dict[str, Any]] = []
    for t in tags:
        fpath, bpath = _tag_paths(t)
        if not fpath.exists() or not bpath.exists():
            continue
        fdoc = _load_json(fpath)
        bdoc = _load_json(bpath)
        cur = fdoc.get("current_vector_slkm") or {}
        summ = bdoc.get("summary") or {}
        ns = summ.get("non_synthetic_hit_rate")
        base_rows.append(
            {
                "tag": t,
                "cur": {
                    "S": float(cur.get("S", 0.5)),
                    "L": float(cur.get("L", 0.5)),
                    "K": float(cur.get("K", 0.5)),
                    "M": float(cur.get("M", 0.5)),
                },
                "hit_rate": float(summ.get("hit_rate") or 0.0),
                "non_synthetic_hit_rate": float(ns) if ns is not None else None,
            }
        )

    # Small deterministic baseline grid.
    weight_grid: list[dict[str, Any]] = [
        {"id": "balanced", "w": {"S": 1.0, "L": 1.0, "K": 1.0, "M": 1.0}},
        {"id": "kairos_heavy", "w": {"S": 0.8, "L": 0.9, "K": 1.5, "M": 0.8}},
        {"id": "material_heavy", "w": {"S": 0.8, "L": 0.8, "K": 0.9, "M": 1.6}},
        {"id": "logos_spirit_heavy", "w": {"S": 1.4, "L": 1.4, "K": 0.7, "M": 0.7}},
        {"id": "anti_kairos", "w": {"S": 1.0, "L": 1.1, "K": 0.5, "M": 1.1}},
    ]
    rng = random.Random(args.seed)
    for i in range(max(0, args.random_samples)):
        weight_grid.append(
            {
                "id": f"rand_{i+1:03d}",
                "w": {
                    "S": round(rng.uniform(0.5, 1.8), 3),
                    "L": round(rng.uniform(0.5, 1.8), 3),
                    "K": round(rng.uniform(0.5, 1.8), 3),
                    "M": round(rng.uniform(0.5, 1.8), 3),
                },
            }
        )

    candidates: list[dict[str, Any]] = []
    for g in weight_grid:
        x: list[float] = []
        y: list[float] = []
        y_ns: list[float] = []
        x_ns: list[float] = []
        for r in base_rows:
            best = -1.0
            best_id = "unknown"
            for a in archetypes:
                score = _weighted_cosine(r["cur"], a["vec"], g["w"])
                if score > best:
                    best = score
                    best_id = a["id"]
            x.append(best)
            y.append(r["hit_rate"])
            if r["non_synthetic_hit_rate"] is not None:
                x_ns.append(best)
                y_ns.append(float(r["non_synthetic_hit_rate"]))
        corr_hr = _corr(x, y)
        corr_ns = _corr(x_ns, y_ns)
        candidates.append(
            {
                "weight_id": g["id"],
                "weights_slkm": g["w"],
                "corr_resonance_vs_hit_rate": corr_hr,
                "corr_resonance_vs_non_synthetic_hit_rate": corr_ns,
                "objective": corr_ns if corr_ns is not None else -999.0,
            }
        )

    candidates.sort(key=lambda c: float(c["objective"]), reverse=True)
    best = candidates[0] if candidates else None

    out = {
        "schema": "logos_fractal_matrix_sweep_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "search_meta": {
            "random_samples": int(args.random_samples),
            "seed": int(args.seed),
            "candidate_count": len(candidates),
        },
        "input_run_count": len(base_rows),
        "candidates_top10": candidates[:10],
        "best_candidate": best,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "input_run_count": len(base_rows), "best": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

