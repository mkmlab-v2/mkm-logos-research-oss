# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.2, L:0.7, K:0.4, M:0.3}
# Balance: 82
# Purpose: Compute pairwise/triple/4-way verse_id intersections across regime-primary Logos reports.
# Keywords: logos, regime, intersection, verse_id, backtest
"""Compute logos_regime_verse_intersection_v1 from four regime-primary probe JSON reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Set


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _verse_ids_from_report(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    hits = data.get("hits") or []
    out: List[str] = []
    for h in hits:
        vid = h.get("verse_id")
        if vid is not None and str(vid).strip():
            out.append(str(vid).strip())
    return out


def _fmt_pair(a: str, b: str) -> str:
    x, y = sorted((a, b))
    return f"{x}|{y}"


def _fmt_trip(a: str, b: str, c: str) -> str:
    return "|".join(sorted((a, b, c)))


def build_intersection(
    *,
    regime_to_path: Mapping[str, Path],
    distinctive: bool = True,
) -> Dict[str, Any]:
    regime_ids = tuple(sorted(regime_to_path.keys()))
    if len(regime_ids) != 4:
        raise ValueError(f"Expected exactly 4 regimes, got {len(regime_ids)}: {regime_ids}")

    sets: Dict[str, Set[str]] = {}
    ordered_lists: Dict[str, List[str]] = {}
    for rid in regime_ids:
        p = regime_to_path[rid]
        if not p.is_file():
            raise FileNotFoundError(str(p))
        lst = _verse_ids_from_report(p)
        ordered_lists[rid] = lst
        sets[rid] = set(lst)

    source_reports = {rid: str(regime_to_path[rid].resolve()) for rid in regime_ids}
    counts = {rid: len(ordered_lists[rid]) for rid in regime_ids}

    all_four = sets[regime_ids[0]].copy()
    for rid in regime_ids[1:]:
        all_four &= sets[rid]
    all_four_sorted = sorted(all_four)

    pairwise_out: Dict[str, Any] = {}
    for a, b in combinations(regime_ids, 2):
        key = _fmt_pair(a, b)
        inter = sets[a] & sets[b]
        pairwise_out[key] = {"count": len(inter), "verse_ids": sorted(inter)}

    triple_out: Dict[str, Any] = {}
    for a, b, c in combinations(regime_ids, 3):
        key = _fmt_trip(a, b, c)
        inter = sets[a] & sets[b] & sets[c]
        triple_out[key] = {"count": len(inter), "verse_ids": sorted(inter)}

    out: Dict[str, Any] = {
        "schema": "logos_regime_verse_intersection_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_reports": source_reports,
        "counts": counts,
        "regime_key_order": list(regime_ids),
        "intersection_all_four_verse_ids": all_four_sorted,
        "count_all_four": len(all_four_sorted),
        "pairwise": pairwise_out,
        "triple": triple_out,
    }

    if distinctive:
        # Verses that appear in exactly one regime's top-k (among these four lists).
        distinctive_block: Dict[str, Any] = {}
        for rid in regime_ids:
            only_here: List[str] = []
            for vid in ordered_lists[rid]:
                n = sum(1 for r2 in regime_ids if vid in sets[r2])
                if n == 1:
                    only_here.append(vid)
            distinctive_block[rid] = {"count": len(only_here), "verse_ids": only_here}
        out["distinctive_topk_only_in_regime"] = distinctive_block

    # Summary flags for sweep scripts
    out["summary"] = {
        "any_pairwise_non_empty": any(
            pairwise_out[k]["count"] > 0 for k in pairwise_out
        ),
        "any_triple_non_empty": any(triple_out[k]["count"] > 0 for k in triple_out),
        "all_four_non_empty": len(all_four_sorted) > 0,
    }
    return out


def _parse_args() -> argparse.Namespace:
    root = _workspace_root()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--bull-pump",
        type=Path,
        required=True,
        metavar="JSON",
        help="Report JSON for bull_pump",
    )
    p.add_argument(
        "--sideways",
        type=Path,
        required=True,
        metavar="JSON",
        help="Report JSON for sideways_accumulation",
    )
    p.add_argument(
        "--bear",
        type=Path,
        required=True,
        metavar="JSON",
        help="Report JSON for bear_trend",
    )
    p.add_argument(
        "--capitulation",
        type=Path,
        required=True,
        metavar="JSON",
        help="Report JSON for capitulation",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=root / "backtest_results" / "LOGOS_RESONANCE_REGIME_INTERSECTION.json",
    )
    p.add_argument(
        "--no-distinctive",
        action="store_true",
        help="Omit distinctive_topk_only_in_regime (smaller JSON).",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    regime_to_path = {
        "bull_pump": args.bull_pump,
        "sideways_accumulation": args.sideways,
        "bear_trend": args.bear,
        "capitulation": args.capitulation,
    }
    doc = build_intersection(regime_to_path=regime_to_path, distinctive=not args.no_distinctive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    s = doc["summary"]
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "any_pairwise": s["any_pairwise_non_empty"],
                "any_triple": s["any_triple_non_empty"],
                "all_four": s["all_four_non_empty"],
                "count_all_four": doc["count_all_four"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
