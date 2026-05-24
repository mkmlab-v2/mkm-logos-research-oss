#!/usr/bin/env python3
"""B-track [HYPO] v2: richer lexicon features (prefix bucket + ascii ratio + polar on 3D)."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LEXICON = ROOT / "reports/constitution/btrack_pilot/master_codebook_lexicon_v1_41658_rows_latest.json"
DEFAULT_POOL = ROOT / "reports/golden_40_expansion_pool_compare_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/polar_coord_compression_hypo_v2_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atom_prefix(atom_id: str) -> str:
    if atom_id.startswith("greek::"):
        return "greek"
    if atom_id.startswith("hebrew::"):
        return "hebrew"
    if atom_id.startswith("other::"):
        return "other"
    return "other"


def _features_v2(atom_id: str, normalized_form: str) -> tuple[float, float, float]:
    nf = normalized_form or atom_id.split("::", 1)[-1]
    length = float(min(len(nf), 64))
    non_ascii = sum(1 for ch in nf if ord(ch) > 127)
    ascii_ratio = 1.0 - (non_ascii / max(len(nf), 1))
    stem = atom_id.split("::", 1)[-1]
    bucket = float(sum(ord(c) for c in stem[:8]) % 97) / 97.0
    return length, ascii_ratio, bucket


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
    tier = None
    for row in mixed.get("tier_summary") or []:
        if int(row.get("target") or 0) == 400:
            tier = row
            break
    if not tier:
        return {"found": False}
    return {
        "found": True,
        "jaccard": tier.get("jaccard"),
        "golden_core_jaccard": tier.get("golden_core_jaccard"),
        "floor_ok": tier.get("floor_ok"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Polar coord compression hypo v2 (B-track)")
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--pool-compare", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.lexicon.is_file():
        print(f"missing lexicon: {args.lexicon}", file=sys.stderr)
        return 2

    entries = (_load_json(args.lexicon).get("entries") or [])
    cart_other: list[tuple[float, float, float]] = []
    cart_rest: list[tuple[float, float, float]] = []
    polar_other: list[tuple[float, float, float]] = []
    polar_rest: list[tuple[float, float, float]] = []
    counts = {"greek": 0, "hebrew": 0, "other": 0}

    for row in entries:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id") or row.get("id") or "")
        if not atom_id:
            continue
        prefix = _atom_prefix(atom_id)
        counts[prefix] = counts.get(prefix, 0) + 1
        nf = str(row.get("normalized_form") or "")
        x, y, z = _features_v2(atom_id, nf)
        r, theta, phi = _to_polar3(x, y, z)
        pt_cart = (x, y, z)
        pt_polar = (r, theta, phi)
        if prefix == "other":
            cart_other.append(pt_cart)
            polar_other.append(pt_polar)
        else:
            cart_rest.append(pt_cart)
            polar_rest.append(pt_polar)

    cart_sep = _separation(cart_other, cart_rest)
    polar_sep = _separation(polar_other, polar_rest)
    polar_wins = polar_sep["separation_ratio"] > cart_sep["separation_ratio"]

    pool_facts: dict[str, Any] = {"found": False}
    if args.pool_compare.is_file():
        pool_facts = _n400_facts(_load_json(args.pool_compare))

    doc: dict[str, Any] = {
        "schema": "polar_coord_compression_hypo_v2",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "feature_set": "length + ascii_ratio + stem_hash_bucket (3D cartesian -> polar)",
        "atom_counts": counts,
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
