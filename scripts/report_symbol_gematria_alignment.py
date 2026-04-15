#!/usr/bin/env python3
"""Build pilot alignment report between symbol vectors and gematria bridge."""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.gematria_engine import build_gematria_metadata
from scripts.core.gematria_to_4d_bridge import build_gematria_4d_bridge

IN_JSONL = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_candidates_with_vector4d_latest.jsonl"
OUT_JSON = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_gematria_alignment_test.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _clip01(x: float) -> float:
    if x < 0.0:
        return 0.0
    if x > 1.0:
        return 1.0
    return x


def _sum_to_1(v: dict[str, float]) -> dict[str, float]:
    total = float(v["S"] + v["L"] + v["K"] + v["M"])
    if total <= 0:
        return {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    return {k: float(v[k] / total) for k in ("S", "L", "K", "M")}


def _symbol_vector_from_row(row: dict[str, Any]) -> tuple[dict[str, float], str]:
    # Prefer upstream vector if present; fallback is a documented pilot heuristic.
    v = row.get("vector_4d")
    if isinstance(v, dict):
        if all(isinstance(v.get(k), (int, float)) for k in ("S", "L", "K", "M")):
            vec = {k: float(v[k]) for k in ("S", "L", "K", "M")}
            return _sum_to_1(vec), "input_vector_4d"

    score = float(row.get("score_tfidf_like", 0.0) or 0.0)
    doc_freq = float(row.get("doc_freq", 0.0) or 0.0)
    term_freq = float(row.get("term_freq", 0.0) or 0.0)
    mix = row.get("source_mix", {})
    if not isinstance(mix, dict):
        mix = {}
    dss = float(mix.get("dss", 0.0) or 0.0)
    apo = float(mix.get("apocrypha", 0.0) or 0.0)
    total = dss + apo
    dss_ratio = (dss / total) if total > 0 else 0.0
    apo_ratio = (apo / total) if total > 0 else 0.0

    # Pilot 4D mapping:
    # - S: frequency pressure (term/doc)
    # - L: lexical signal strength (score scale)
    # - K: DSS ratio
    # - M: apocrypha ratio + balancing term
    s = _clip01((term_freq / max(1.0, doc_freq)) / 5.0)
    l = _clip01(score / 1200.0)
    k = _clip01(dss_ratio)
    m = _clip01(apo_ratio * 0.8 + 0.2)
    vec = _sum_to_1({"S": s, "L": l, "K": k, "M": m})
    return vec, "heuristic_score_source_mix_v1"


def _distance(a: dict[str, float], b: dict[str, float]) -> float:
    return (
        (a["S"] - b["S"]) ** 2
        + (a["L"] - b["L"]) ** 2
        + (a["K"] - b["K"]) ** 2
        + (a["M"] - b["M"]) ** 2
    ) ** 0.5


def _dot(a: dict[str, float], b: dict[str, float]) -> float:
    return a["S"] * b["S"] + a["L"] * b["L"] + a["K"] * b["K"] + a["M"] * b["M"]


def _norm(a: dict[str, float]) -> float:
    return (a["S"] ** 2 + a["L"] ** 2 + a["K"] ** 2 + a["M"] ** 2) ** 0.5


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    den = _norm(a) * _norm(b)
    if den <= 0.0:
        return 0.0
    return _dot(a, b) / den


def _normalize_l2(v: dict[str, float]) -> dict[str, float]:
    n = _norm(v)
    if n <= 0.0:
        return dict(v)
    return {k: float(v[k] / n) for k in ("S", "L", "K", "M")}


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0.0 or vy <= 0.0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / (vx**0.5 * vy**0.5)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pilot gematria-symbol alignment report")
    ap.add_argument("--input", default=str(IN_JSONL))
    ap.add_argument("--out", default=str(OUT_JSON))
    ap.add_argument("--sample-size", type=int, default=100)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--resonance-threshold", type=float, default=0.85, help="Cosine threshold")
    ap.add_argument(
        "--sample-mode",
        choices=("random", "gematria_nonzero"),
        default="random",
        help="random: sample all rows; gematria_nonzero: sample rows with nonzero gematria only",
    )
    ap.add_argument(
        "--pre-normalization",
        choices=("none", "l2_only"),
        default="none",
        help="Optional vector pre-normalization before distance/cosine",
    )
    args = ap.parse_args()

    in_path = _abs(args.input)
    out_path = _abs(args.out)
    if not in_path.is_file():
        print(f"ERROR: missing input: {in_path}")
        return 2

    rows = list(_iter_jsonl(in_path))
    if not rows:
        print(f"ERROR: empty input: {in_path}")
        return 2

    rng = random.Random(args.seed)
    if args.sample_mode == "gematria_nonzero":
        filtered: list[dict[str, Any]] = []
        for r in rows:
            symbol = str(r.get("symbol", "")).strip()
            if not symbol:
                continue
            meta = build_gematria_metadata(raw_text=symbol, compressed_text=symbol, reconstructed_text=symbol)
            if int(meta.get("raw_combined_sum", 0)) > 0:
                filtered.append(r)
        rows_for_sampling = filtered
    else:
        rows_for_sampling = rows

    if not rows_for_sampling:
        print("ERROR: no rows available for selected sample-mode")
        return 2
    n = max(1, min(args.sample_size, len(rows_for_sampling)))
    sample = rng.sample(rows_for_sampling, n) if n < len(rows_for_sampling) else rows_for_sampling

    details: list[dict[str, Any]] = []
    dist_values: list[float] = []
    cos_values: list[float] = []
    state_match_count = 0
    axis_corr: dict[str, list[float]] = {
        "S_a": [],
        "L_a": [],
        "K_a": [],
        "M_a": [],
        "S_b": [],
        "L_b": [],
        "K_b": [],
        "M_b": [],
    }
    vec_source_hist: dict[str, int] = {}

    for row in sample:
        symbol = str(row.get("symbol", "")).strip()
        if not symbol:
            continue
        vec_a, vec_source = _symbol_vector_from_row(row)
        vec_source_hist[vec_source] = vec_source_hist.get(vec_source, 0) + 1
        meta = build_gematria_metadata(raw_text=symbol, compressed_text=symbol, reconstructed_text=symbol)
        bridge = build_gematria_4d_bridge(gematria_metadata=meta)
        vec_b = bridge.get("vector_4d", {})
        if not isinstance(vec_b, dict):
            continue
        if not all(isinstance(vec_b.get(k), (int, float)) for k in ("S", "L", "K", "M")):
            continue
        vec_b = {k: float(vec_b[k]) for k in ("S", "L", "K", "M")}
        if args.pre_normalization == "l2_only":
            vec_a = _normalize_l2(vec_a)
            vec_b = _normalize_l2(vec_b)
        dist = _distance(vec_a, vec_b)
        cos = _cosine(vec_a, vec_b)
        dist_values.append(dist)
        cos_values.append(cos)
        axis_corr["S_a"].append(vec_a["S"])
        axis_corr["L_a"].append(vec_a["L"])
        axis_corr["K_a"].append(vec_a["K"])
        axis_corr["M_a"].append(vec_a["M"])
        axis_corr["S_b"].append(vec_b["S"])
        axis_corr["L_b"].append(vec_b["L"])
        axis_corr["K_b"].append(vec_b["K"])
        axis_corr["M_b"].append(vec_b["M"])
        if isinstance(row.get("state16"), (int, float)) and isinstance(bridge.get("state16"), (int, float)):
            if int(row["state16"]) == int(bridge["state16"]):
                state_match_count += 1
        details.append(
            {
                "symbol": symbol,
                "rank": row.get("rank"),
                "vector_source": vec_source,
                "vector_4d_symbol": vec_a,
                "gematria_metadata": meta,
                "gematria_4d_bridge": bridge,
                "distance_symbol_vs_gematria_4d": round(dist, 6),
                "cosine_symbol_vs_gematria_4d": round(cos, 6),
                "resonant": bool(cos >= args.resonance_threshold),
            }
        )

    used = len(details)
    if used == 0:
        print("ERROR: no usable sampled rows")
        return 2

    resonant_count = sum(1 for d in details if d["resonant"])
    axis_pearson = {
        "S": _pearson(axis_corr["S_a"], axis_corr["S_b"]),
        "L": _pearson(axis_corr["L_a"], axis_corr["L_b"]),
        "K": _pearson(axis_corr["K_a"], axis_corr["K_b"]),
        "M": _pearson(axis_corr["M_a"], axis_corr["M_b"]),
    }
    valid_corr = [v for v in axis_pearson.values() if isinstance(v, float)]
    mean_axis_corr = (sum(valid_corr) / len(valid_corr)) if valid_corr else None

    report = {
        "schema": "symbol_gematria_alignment_test_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "input_jsonl": str(in_path),
            "sample_mode": args.sample_mode,
            "sampling_pool_size": len(rows_for_sampling),
            "requested_sample_size": args.sample_size,
            "effective_sample_size": used,
            "seed": args.seed,
            "resonance_threshold_cosine": args.resonance_threshold,
            "pre_normalization": args.pre_normalization,
        },
        "summary": {
            "avg_distance_symbol_vs_gematria_4d": round(sum(dist_values) / used, 6),
            "min_distance_symbol_vs_gematria_4d": round(min(dist_values), 6),
            "max_distance_symbol_vs_gematria_4d": round(max(dist_values), 6),
            "avg_cosine_symbol_vs_gematria_4d": round(sum(cos_values) / used, 6),
            "resonance_rate": round(resonant_count / used, 6),
            "resonance_count": resonant_count,
            "state16_match_count_when_both_present": state_match_count,
            "vector_source_histogram": vec_source_hist,
            "axis_pearson": {
                k: (round(v, 6) if isinstance(v, float) else None) for k, v in axis_pearson.items()
            },
            "mean_axis_pearson": (round(mean_axis_corr, 6) if isinstance(mean_axis_corr, float) else None),
        },
        "policy_gate": {
            "target_resonance_rate_gte": 0.85,
            "pass": (resonant_count / used) >= 0.85,
            "note": "Pilot gate for symbol-gematria bridge alignment only; not production trading gate.",
        },
        "boundaries": {
            "fact": [
                "Gematria values are computed by scripts/core/gematria_engine.py.",
                "Gematria-to-4D bridge is computed by scripts/core/gematria_to_4d_bridge.py.",
            ],
            "hypothesis": [
                "When input rows lack vector_4d, symbol vectors are estimated by heuristic_score_source_mix_v1.",
                "This report validates bridge alignment in B-track pilot scope only.",
            ],
        },
        "cases": details,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol gematria alignment report generated")
    print(f"out={out_path}")
    print(f"effective_sample_size={used} resonance_rate={resonant_count / used:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
