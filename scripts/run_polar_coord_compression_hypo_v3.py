#!/usr/bin/env python3
"""B-track [HYPO] v3: bigram co-occurrence affinity + rest-centroid drift (other:: separation)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_POOL = ROOT / "reports/golden_40_expansion_pool_compare_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/polar_coord_compression_hypo_v3_latest.json"
BIGRAM_DIM = 32


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atom_prefix(atom_id: str) -> str:
    if atom_id.startswith("greek::"):
        return "greek"
    if atom_id.startswith("hebrew::"):
        return "hebrew"
    return "other"


def _bigram_vec(nf: str) -> list[float]:
    v = [0.0] * BIGRAM_DIM
    text = (nf or "").strip().lower()
    for i in range(max(0, len(text) - 1)):
        h = (ord(text[i]) * 31 + ord(text[i + 1])) % BIGRAM_DIM
        v[h] += 1.0
    s = sum(v) or 1.0
    return [x / s for x in v]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return dot / (na * nb)


def _mean_vec(vecs: list[list[float]]) -> list[float]:
    if not vecs:
        return [0.0] * BIGRAM_DIM
    out = [0.0] * BIGRAM_DIM
    for v in vecs:
        for i, x in enumerate(v):
            out[i] += x
    n = float(len(vecs))
    return [x / n for x in out]


def _ascii_ratio(nf: str) -> float:
    if not nf:
        return 1.0
    non_ascii = sum(1 for ch in nf if ord(ch) > 127)
    return 1.0 - (non_ascii / len(nf))


def _punct_digit_ratio(stem: str) -> float:
    if not stem:
        return 0.0
    special = sum(1 for ch in stem if not ch.isalpha())
    return special / len(stem)


def _to_polar3(x: float, y: float, z: float) -> tuple[float, float, float]:
    r = math.sqrt(x * x + y * y + z * z)
    theta = math.atan2(y, x) if r > 1e-12 else 0.0
    phi = math.acos(max(-1.0, min(1.0, z / r))) if r > 1e-12 else 0.0
    return r, theta, phi


def _centroid(points: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    if not points:
        return 0.0, 0.0, 0.0
    n = float(len(points))
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def _mean_radius(points: list[tuple[float, float, float]], center: tuple[float, float, float]) -> float:
    if not points:
        return 0.0
    cx, cy, cz = center
    return sum(math.sqrt((p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2) for p in points) / float(
        len(points)
    )


def _separation(other_pts: list[tuple[float, float, float]], rest_pts: list[tuple[float, float, float]]) -> dict[str, float]:
    if not other_pts or not rest_pts:
        return {"between_center_distance": 0.0, "other_mean_radius": 0.0, "rest_mean_radius": 0.0, "separation_ratio": 0.0}
    o_c = _centroid(other_pts)
    r_c = _centroid(rest_pts)
    between = math.sqrt((o_c[0] - r_c[0]) ** 2 + (o_c[1] - r_c[1]) ** 2 + (o_c[2] - r_c[2]) ** 2)
    o_r = _mean_radius(other_pts, o_c)
    r_r = _mean_radius(rest_pts, r_c)
    denom = o_r + r_r + 1e-9
    return {
        "between_center_distance": round(between, 6),
        "other_mean_radius": round(o_r, 6),
        "rest_mean_radius": round(r_r, 6),
        "separation_ratio": round(between / denom, 6),
    }


def _n400_facts(pool_doc: dict[str, Any]) -> dict[str, Any]:
    mixed = (pool_doc.get("pools") or {}).get("mixed_matrix") or {}
    for row in mixed.get("tier_summary") or []:
        if int(row.get("target") or 0) == 400:
            return {
                "found": True,
                "jaccard": row.get("jaccard"),
                "golden_core_jaccard": row.get("golden_core_jaccard"),
                "floor_ok": row.get("floor_ok"),
            }
    return {"found": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Polar coord compression hypo v3 (B-track)")
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--pool-compare", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.lexicon.is_file():
        print(f"missing lexicon: {args.lexicon}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str, str]] = []
    counts = {"greek": 0, "hebrew": 0, "other": 0}
    for row in _load_json(args.lexicon).get("entries") or []:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id") or row.get("id") or "")
        if not atom_id:
            continue
        prefix = _atom_prefix(atom_id)
        counts[prefix] = counts.get(prefix, 0) + 1
        nf = str(row.get("normalized_form") or "")
        stem = atom_id.split("::", 1)[-1]
        rows.append((prefix, nf, stem))

    other_vecs = [_bigram_vec(nf) for prefix, nf, _ in rows if prefix == "other"]
    rest_vecs = [_bigram_vec(nf) for prefix, nf, _ in rows if prefix != "other"]
    other_mean = _mean_vec(other_vecs)
    rest_mean = _mean_vec(rest_vecs)

    rest_lengths: list[float] = []
    rest_ascii: list[float] = []
    for prefix, nf, _ in rows:
        if prefix != "other":
            rest_lengths.append(float(min(len(nf), 64)))
            rest_ascii.append(_ascii_ratio(nf))
    rest_len_c = sum(rest_lengths) / max(len(rest_lengths), 1)
    rest_ascii_c = sum(rest_ascii) / max(len(rest_ascii), 1)

    cart_other: list[tuple[float, float, float]] = []
    cart_rest: list[tuple[float, float, float]] = []
    polar_other: list[tuple[float, float, float]] = []
    polar_rest: list[tuple[float, float, float]] = []
    affinity_other_sum = 0.0
    affinity_rest_sum = 0.0
    n_other = 0
    n_rest = 0

    for prefix, nf, stem in rows:
        vec = _bigram_vec(nf)
        cooc_affinity = _cosine(vec, other_mean) - _cosine(vec, rest_mean)
        length = float(min(len(nf), 64))
        ascii_r = _ascii_ratio(nf)
        drift_len = abs(length - rest_len_c) / 64.0
        drift_ascii = abs(ascii_r - rest_ascii_c)
        punct_r = _punct_digit_ratio(stem) if prefix == "other" else 0.0
        x = cooc_affinity * 4.0
        y = drift_len + drift_ascii + punct_r * 0.5
        z = length / 64.0
        pt_cart = (x, y, z)
        r, theta, phi = _to_polar3(x, y, z)
        pt_polar = (r, theta, phi)
        if prefix == "other":
            cart_other.append(pt_cart)
            polar_other.append(pt_polar)
            affinity_other_sum += cooc_affinity
            n_other += 1
        else:
            cart_rest.append(pt_cart)
            polar_rest.append(pt_polar)
            affinity_rest_sum += cooc_affinity
            n_rest += 1

    cart_sep = _separation(cart_other, cart_rest)
    polar_sep = _separation(polar_other, polar_rest)
    polar_wins = polar_sep["separation_ratio"] > cart_sep["separation_ratio"]

    pool_facts: dict[str, Any] = {"found": False}
    if args.pool_compare.is_file():
        pool_facts = _n400_facts(_load_json(args.pool_compare))

    doc: dict[str, Any] = {
        "schema": "polar_coord_compression_hypo_v3",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "feature_set": "bigram_cooc_affinity + rest_centroid_drift + length (3D -> polar)",
        "atom_counts": counts,
        "cooc_affinity_mean": {
            "other": round(affinity_other_sum / max(n_other, 1), 6),
            "rest": round(affinity_rest_sum / max(n_rest, 1), 6),
            "delta_other_minus_rest": round(
                (affinity_other_sum / max(n_other, 1)) - (affinity_rest_sum / max(n_rest, 1)), 6
            ),
        },
        "separation_cartesian": cart_sep,
        "separation_polar": polar_sep,
        "polar_separation_improved_vs_cartesian": polar_wins,
        "golden40_n400_context": pool_facts,
        "proceed_to_dryrun_hook": polar_wins,
        "promotion": "HOLD — no Track A / ACTIVE / MS KPI update",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out} polar_wins={polar_wins} proceed_hook={polar_wins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
