#!/usr/bin/env python3
"""B-track [HYPO]: polar vs cartesian separation for other:: lexicon atoms (Golden40 context).

Does not modify ACTIVE report, lexicon production SSOT, or compression pipeline.
Reads 41658 lexicon + golden_40 expansion pool compare for N=400 dilution facts.
"""

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
DEFAULT_OUT = ROOT / "reports/polar_coord_compression_hypo_v1_latest.json"


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


def _features(atom_id: str, normalized_form: str) -> tuple[float, float]:
    """2D pseudo-feature: length + char-code energy (stdlib only)."""
    nf = normalized_form or atom_id.split("::", 1)[-1]
    length = float(min(len(nf), 64))
    energy = 0.0
    for i, ch in enumerate(nf[:128]):
        energy += float((ord(ch) % 256)) / (256.0 * (i + 1))
    return length, energy


def _to_polar(x: float, y: float) -> tuple[float, float]:
    r = math.hypot(x, y)
    theta = math.atan2(y, x) if r > 1e-12 else 0.0
    return r, theta


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    if not points:
        return 0.0, 0.0
    n = float(len(points))
    return sum(p[0] for p in points) / n, sum(p[1] for p in points) / n


def _mean_radius(points: list[tuple[float, float]], center: tuple[float, float]) -> float:
    if not points:
        return 0.0
    cx, cy = center
    return sum(math.hypot(p[0] - cx, p[1] - cy) for p in points) / float(len(points))


def _separation_score(
    other_pts: list[tuple[float, float]],
    rest_pts: list[tuple[float, float]],
) -> dict[str, float]:
    if not other_pts or not rest_pts:
        return {"between_center_distance": 0.0, "other_mean_radius": 0.0, "rest_mean_radius": 0.0, "separation_ratio": 0.0}
    o_c = _centroid(other_pts)
    r_c = _centroid(rest_pts)
    between = math.hypot(o_c[0] - r_c[0], o_c[1] - r_c[1])
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
    pools = pool_doc.get("pools") or {}
    mixed = pools.get("mixed_matrix") or {}
    tier = None
    for row in mixed.get("tier_summary") or []:
        if int(row.get("target") or 0) == 400:
            tier = row
            break
    if not tier:
        return {"found": False}
    return {
        "found": True,
        "artifact": mixed.get("artifact"),
        "jaccard": tier.get("jaccard"),
        "golden_core_jaccard": tier.get("golden_core_jaccard"),
        "floor_ok": tier.get("floor_ok"),
        "expansion_dilution": mixed.get("expansion_dilution"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Polar coord compression hypo (B-track)")
    parser.add_argument("--lexicon", type=Path, default=DEFAULT_LEXICON)
    parser.add_argument("--pool-compare", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.lexicon.is_file():
        print(f"missing lexicon: {args.lexicon}", file=sys.stderr)
        return 2

    lex = _load_json(args.lexicon)
    entries = lex.get("entries") or []
    cart_other: list[tuple[float, float]] = []
    cart_rest: list[tuple[float, float]] = []
    polar_other: list[tuple[float, float]] = []
    polar_rest: list[tuple[float, float]] = []
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
        x, y = _features(atom_id, nf)
        r, theta = _to_polar(x, y)
        if prefix == "other":
            cart_other.append((x, y))
            polar_other.append((r, theta))
        else:
            cart_rest.append((x, y))
            polar_rest.append((r, theta))

    cart_sep = _separation_score(cart_other, cart_rest)
    polar_sep = _separation_score(polar_other, polar_rest)
    polar_wins = polar_sep["separation_ratio"] > cart_sep["separation_ratio"]

    pool_facts: dict[str, Any] = {"found": False}
    if args.pool_compare.is_file():
        pool_facts = _n400_facts(_load_json(args.pool_compare))

    doc: dict[str, Any] = {
        "schema": "polar_coord_compression_hypo_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": "Pseudo 2D features on lexicon atoms — not full TurboQuant/KV pipeline.",
        "lexicon_path": str(args.lexicon.relative_to(ROOT)).replace("\\", "/"),
        "atom_counts": counts,
        "separation_cartesian": cart_sep,
        "separation_polar": polar_sep,
        "polar_separation_improved_vs_cartesian": polar_wins,
        "golden40_n400_context": pool_facts,
        "interpretation": {
            "ko": (
                "극좌표 분리비가 직교보다 크면 other:: 격리 가설을 다음 단계(dryrun 훅)로 넘길 worthiness."
                if polar_wins
                else "1차 pseudo-feature에서는 극좌표 이점 미확인 — 실제 압축 경로 훅 전 재설계 필요."
            ),
            "next_step": (
                "Design --hypo-polar-preprocess hook on run_golden40_expansion_dryrun_v1.py; re-bench N=400 floor."
                if polar_wins
                else "Refine features (e.g. co-occurrence / embedding slice) before pipeline hook."
            ),
        },
        "promotion": "HOLD — no Track A / ACTIVE / MS KPI update",
        "pointers": {
            "research_doc": "docs/research/ANCIENT_CORPUS_COMPRESSION_SRE_BRIDGE_V1.md",
            "bridge_pointer": "docs/final/artifacts/ancient_corpus_compression_sre_bridge_pointer_v1_latest.json",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK: {args.out} polar_wins={polar_wins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
