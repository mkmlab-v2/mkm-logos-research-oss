# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.2, L:0.65, K:0.5, M:0.35}
# Balance: 82
# Purpose: Rank verses in a triple intersection by mean cosine vs three regime fingerprints; emit Top-N report.
# Keywords: logos, regime, tri-intersection, resonance, btc-ext
"""Tri-intersection mean resonance report (bear ∩ bull ∩ sideways by default).

Uses ``cosine_to_regime_fingerprint_4d`` from each regime-primary probe JSON as the per-regime
score; ``mean_resonance`` = arithmetic mean of the three cosines (not λ from policy — label only).

Example:
  py scripts/report_tri_intersection_top_mean_resonance.py \\
    --intersection backtest_results/LOGOS_RESONANCE_BTC_EXT_INTERSECTION_TOP10000.json \\
    --top-n 100
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _cosine_map(path: Path) -> Dict[str, float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, float] = {}
    for h in data.get("hits") or []:
        vid = h.get("verse_id")
        if vid is None or not str(vid).strip():
            continue
        c = h.get("cosine_to_regime_fingerprint_4d")
        if c is None:
            continue
        out[str(vid).strip()] = float(c)
    return out


def _text_preview_map(path: Path) -> Dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for h in data.get("hits") or []:
        vid = h.get("verse_id")
        if vid is None or not str(vid).strip():
            continue
        prev = h.get("text_preview") or ""
        out[str(vid).strip()] = str(prev)
    return out


def _parse_args() -> argparse.Namespace:
    root = _root()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--intersection",
        type=Path,
        default=root / "backtest_results" / "LOGOS_RESONANCE_BTC_EXT_INTERSECTION_TOP10000.json",
        help="Intersection JSON (must contain triple.*.verse_ids)",
    )
    p.add_argument(
        "--triple-key",
        type=str,
        default="bear_trend|bull_pump|sideways_accumulation",
        help="Key under intersection['triple']",
    )
    p.add_argument(
        "--bear-report",
        type=Path,
        default=None,
        help="bear_trend probe JSON (default: from intersection source_reports)",
    )
    p.add_argument(
        "--bull-report",
        type=Path,
        default=None,
        help="bull_pump probe JSON",
    )
    p.add_argument(
        "--sideways-report",
        type=Path,
        default=None,
        help="sideways_accumulation probe JSON",
    )
    p.add_argument("--top-n", type=int, default=100, help="How many verses to keep (default 100)")
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON (default: backtest_results/TRI_MEAN_RESONANCE_TOP{n}_*.json)",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    root = _root()
    inter_path = args.intersection
    if not inter_path.is_file():
        raise FileNotFoundError(str(inter_path))

    doc = json.loads(inter_path.read_text(encoding="utf-8"))
    src = doc.get("source_reports") or {}
    bear_p = args.bear_report or Path(src.get("bear_trend", ""))
    bull_p = args.bull_report or Path(src.get("bull_pump", ""))
    side_p = args.sideways_report or Path(src.get("sideways_accumulation", ""))
    for label, pth in (("bear_trend", bear_p), ("bull_pump", bull_p), ("sideways_accumulation", side_p)):
        if not pth.is_file():
            raise FileNotFoundError(f"{label}: {pth}")

    triple_block = (doc.get("triple") or {}).get(args.triple_key)
    if not triple_block:
        raise SystemExit(f"triple key not found: {args.triple_key!r}")
    verse_ids: List[str] = list(triple_block.get("verse_ids") or [])
    if not verse_ids:
        raise SystemExit("empty verse_ids for triple")

    m_bear = _cosine_map(bear_p)
    m_bull = _cosine_map(bull_p)
    m_side = _cosine_map(side_p)
    previews = _text_preview_map(bull_p)

    rows: List[Tuple[float, Dict[str, Any]]] = []
    missing: List[str] = []
    for vid in verse_ids:
        if vid not in m_bear or vid not in m_bull or vid not in m_side:
            missing.append(vid)
            continue
        cb, cu, cs = m_bear[vid], m_bull[vid], m_side[vid]
        mean_r = (cb + cu + cs) / 3.0
        rows.append(
            (
                mean_r,
                {
                    "verse_id": vid,
                    "cosine_bear_trend": round(cb, 6),
                    "cosine_bull_pump": round(cu, 6),
                    "cosine_sideways_accumulation": round(cs, 6),
                    "mean_resonance_tri": round(mean_r, 6),
                    "text_preview": previews.get(vid, "")[:400],
                },
            )
        )

    rows.sort(key=lambda x: -x[0])
    top = [r[1] for r in rows[: max(1, int(args.top_n))]]

    out_path = args.output
    if out_path is None:
        out_path = (
            root
            / "backtest_results"
            / f"TRI_MEAN_RESONANCE_TOP{int(args.top_n)}_{args.triple_key.replace('|', '_')}.json"
        )

    payload: Dict[str, Any] = {
        "schema": "tri_intersection_mean_resonance_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "definition": {
            "triple_key": args.triple_key,
            "mean_resonance_tri": "mean(cosine_to_regime_fingerprint_4d over bear, bull, sideways probes)",
            "rank_order": "descending mean_resonance_tri",
        },
        "inputs": {
            "intersection": str(inter_path.resolve()),
            "bear_trend": str(bear_p.resolve()),
            "bull_pump": str(bull_p.resolve()),
            "sideways_accumulation": str(side_p.resolve()),
        },
        "triple_verse_count": len(verse_ids),
        "ranked_count": len(rows),
        "missing_in_any_probe": len(missing),
        "top_n": int(args.top_n),
        "hits": top,
    }
    if missing and len(missing) <= 20:
        payload["missing_sample"] = missing[:20]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(out_path), "hits": len(top)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
