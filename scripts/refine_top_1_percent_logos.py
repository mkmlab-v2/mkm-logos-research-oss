# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.25, L:0.25, K:0.25, M:0.25}
# Balance: 80
# Purpose: Rank intersection verse_ids by mean cosine across four regime TOP6866 reports.
# Keywords: logos, intersection, mean_cosine, sweep_kmin_refine
"""Refine four-way intersection verses by mean cosine (mean_cosine) across regime reports.

Requires local (untracked) regime JSONs:
  backtest_results/sweep_kmin_refine/LOGOS_RESONANCE_BTC_EXT_{regime}_TOP6866.json

Intersection SSOT (tracked): LOGOS_RESONANCE_BTC_EXT_INTERSECTION_TOP6866.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


REGIMES: Sequence[str] = (
    "bear_trend",
    "bull_pump",
    "capitulation",
    "sideways_accumulation",
)


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _hits_cosine_map(path: Path) -> Dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, float] = {}
    for hit in data.get("hits") or []:
        vid = hit.get("verse_id")
        if vid is None:
            continue
        vid = str(vid).strip()
        c = hit.get("cosine_to_regime_fingerprint_4d")
        if c is None:
            continue
        out[vid] = float(c)
    return out


def refine_top_logos(
    *,
    workspace_root: Path,
    top_n: int | None,
    intersection_path: Path | None,
    output_path: Path | None,
) -> Dict[str, Any]:
    root = workspace_root
    refine_dir = root / "backtest_results" / "sweep_kmin_refine"
    inter_path = intersection_path or (
        refine_dir / "LOGOS_RESONANCE_BTC_EXT_INTERSECTION_TOP6866.json"
    )
    if not inter_path.is_file():
        raise FileNotFoundError(f"intersection file missing: {inter_path}")

    intersection_data = json.loads(inter_path.read_text(encoding="utf-8"))
    target_ids = [
        str(x).strip()
        for x in (intersection_data.get("intersection_all_four_verse_ids") or [])
        if str(x).strip()
    ]
    target_set = set(target_ids)

    regime_maps: Dict[str, Dict[str, float]] = {}
    missing_files: List[str] = []
    for r in REGIMES:
        r_path = refine_dir / f"LOGOS_RESONANCE_BTC_EXT_{r}_TOP6866.json"
        if not r_path.is_file():
            missing_files.append(str(r_path.name))
            continue
        regime_maps[r] = _hits_cosine_map(r_path)

    if len(regime_maps) != len(REGIMES):
        raise FileNotFoundError(
            "Missing one or more regime TOP6866 JSONs. "
            f"Need all of: {[f'LOGOS_RESONANCE_BTC_EXT_{r}_TOP6866.json' for r in REGIMES]}. "
            f"Absent: {missing_files}"
        )

    n_inter = len(target_set)
    if top_n is None:
        top_n = max(1, int(round(n_inter * 0.01)))

    results: List[Dict[str, Any]] = []
    incomplete: List[str] = []
    for vid in target_set:
        cos_by_r: Dict[str, float] = {}
        for r in REGIMES:
            m = regime_maps[r]
            if vid not in m:
                incomplete.append(vid)
                break
            cos_by_r[r] = m[vid]
        else:
            mean_cos = sum(cos_by_r[r] for r in REGIMES) / len(REGIMES)
            results.append(
                {
                    "verse_id": vid,
                    "mean_cosine": mean_cos,
                    "cosine_by_regime": {r: cos_by_r[r] for r in REGIMES},
                }
            )

    results.sort(key=lambda x: float(x["mean_cosine"]), reverse=True)
    top_hits = results[:top_n]

    out_doc: Dict[str, Any] = {
        "schema": "logos_intersection_mean_cosine_top_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "intersection_path": str(inter_path.resolve()),
        "regime_key_order": list(REGIMES),
        "regime_report_paths": {
            r: str((refine_dir / f"LOGOS_RESONANCE_BTC_EXT_{r}_TOP6866.json").resolve())
            for r in REGIMES
        },
        "total_intersection_count": n_inter,
        "ranked_with_all_four_cosines": len(results),
        "incomplete_across_regimes_count": len(set(incomplete)),
        "top_n_requested": top_n,
        "hits": top_hits,
    }

    out_path = output_path or (
        refine_dir / "LOGOS_RESONANCE_BTC_EXT_ABSOLUTE_TOP16.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    out_doc["_output_path"] = str(out_path.resolve())
    return out_doc


def _parse_args() -> argparse.Namespace:
    root = _workspace_root()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--workspace",
        type=Path,
        default=root,
        help="Workspace root (default: repo root)",
    )
    p.add_argument(
        "--top-n",
        type=int,
        default=None,
        metavar="N",
        help="How many top verses to keep (default: 1%% of intersection size, rounded)",
    )
    p.add_argument(
        "--intersection",
        type=Path,
        default=None,
        help="Override path to INTERSECTION_TOP6866.json",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path (default: .../LOGOS_RESONANCE_BTC_EXT_ABSOLUTE_TOP16.json)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    doc = refine_top_logos(
        workspace_root=args.workspace,
        top_n=args.top_n,
        intersection_path=args.intersection,
        output_path=args.output,
    )
    path = doc.pop("_output_path", "")
    print(
        json.dumps(
            {
                "ok": True,
                "output": path,
                "total_intersection_count": doc["total_intersection_count"],
                "ranked_with_all_four_cosines": doc["ranked_with_all_four_cosines"],
                "top_n": doc["top_n_requested"],
                "top_verse_id": doc["hits"][0]["verse_id"] if doc["hits"] else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
