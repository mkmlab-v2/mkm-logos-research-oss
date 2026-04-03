# -*- coding: utf-8 -*-
"""
Rank cosine similarity between a Quad-Fusion ``uft_v2_timeline`` year vector (or manual SLKM)
and regime fingerprints (``regime_map.json`` / optional ``regime_map_btc_ext.json``).

Same L2-normalization as ``logos_vector_resonance_probe._load_regime_vector``.
Manual ``--slkm`` / ``--vector-json`` is for externally calibrated 4D (not asserted to be live KOSPI).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _l2n(u4: Dict[str, Any]) -> np.ndarray:
    arr = np.array(
        [float(u4.get("S", 0.0)), float(u4.get("L", 0.0)), float(u4.get("K", 0.0)), float(u4.get("M", 0.0))],
        dtype=np.float64,
    )
    n = np.linalg.norm(arr)
    return arr / (n + 1e-8)


def _rank(
    v_year: np.ndarray,
    regimes: Dict[str, Any],
) -> List[Tuple[str, float, Dict[str, float]]]:
    out: List[Tuple[str, float, Dict[str, float]]] = []
    for rid, entry in sorted(regimes.items()):
        fp = (entry.get("fingerprint") or {}).get("unified_4d_vector") or {}
        if not fp:
            continue
        v_r = _l2n(fp)
        sim = float(np.dot(v_year, v_r))
        out.append((rid, sim, {k: float(fp[k]) for k in ("S", "L", "K", "M") if k in fp}))
    out.sort(key=lambda x: -x[1])
    return out


def _build_ranking_doc(
    *,
    v_year: np.ndarray,
    u4_raw: Dict[str, float],
    vector_source: str,
    extra_meta: Dict[str, Any],
    regime_map: Path,
    btc_ext_map: Optional[Path],
    no_btc_ext: bool,
) -> Dict[str, Any]:
    hist = json.loads(regime_map.read_text(encoding="utf-8"))["regimes"]
    ranked_hist = _rank(v_year, hist)
    doc: Dict[str, Any] = {
        "schema": "quad_timeline_year_vs_regime_fingerprints_v1",
        "vector_source": vector_source,
        "current_unified_4d_vector_raw": u4_raw,
        "notes": [
            "cosine is dot(L2_norm(current), L2_norm(regime fingerprint)).",
            "If vector_source is manual, caller is responsible for calibration provenance.",
        ],
        **extra_meta,
        "historical_regimes_ranking": [
            {"regime_id": rid, "cosine_similarity": round(sim, 6), "fingerprint_slkm": fp}
            for rid, sim, fp in ranked_hist
        ],
        "primary_historical_regime": ranked_hist[0][0] if ranked_hist else None,
    }
    if not no_btc_ext and btc_ext_map and btc_ext_map.is_file():
        ext = json.loads(btc_ext_map.read_text(encoding="utf-8"))["regimes"]
        ranked_ext = _rank(v_year, ext)
        doc["btc_ext_hypothesis_ranking"] = [
            {"regime_id": rid, "cosine_similarity": round(sim, 6), "fingerprint_slkm": fp}
            for rid, sim, fp in ranked_ext
        ]
        doc["primary_btc_ext_regime"] = ranked_ext[0][0] if ranked_ext else None
    return doc


def _parse_slkm(s: str) -> Dict[str, float]:
    parts = [p.strip() for p in s.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise ValueError("Expected four comma-separated numbers: S,L,K,M")
    keys = ("S", "L", "K", "M")
    return {keys[i]: float(parts[i]) for i in range(4)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    r = _root()
    ap.add_argument(
        "--quad-json",
        type=Path,
        default=r / "data" / "quad_fusion_training" / "quad_fusion_result_20260308_230751.json",
        help="SSOT with uft_v2_timeline.",
    )
    ap.add_argument("--year", type=int, default=2026, help="Timeline year when not using manual vector.")
    ap.add_argument(
        "--slkm",
        type=str,
        default=None,
        metavar="S,L,K,M",
        help="Override timeline: four comma-separated floats (L2-normalized internally).",
    )
    ap.add_argument(
        "--vector-json",
        type=Path,
        default=None,
        help="JSON object with S,L,K,M keys; overrides timeline (and --slkm if both set: --slkm wins).",
    )
    ap.add_argument(
        "--compare-years",
        type=str,
        default=None,
        metavar="Y1,Y2,...",
        help="Emit multi-year report only (no single-file unless --output also used). Example: 2024,2025,2026",
    )
    ap.add_argument(
        "--regime-map",
        type=Path,
        default=r / "data" / "regimes" / "regime_map.json",
    )
    ap.add_argument(
        "--btc-ext-map",
        type=Path,
        default=r / "data" / "regimes" / "regime_map_btc_ext.json",
    )
    ap.add_argument("--no-btc-ext", action="store_true")
    ap.add_argument(
        "--output",
        type=Path,
        default=r / "backtest_results" / "QUAD_TIMELINE_YEAR_VS_REGIME_FINGERPRINTS_RANKING.json",
    )
    ap.add_argument(
        "--multi-output",
        type=Path,
        default=r / "backtest_results" / "QUAD_TIMELINE_MULTIYEAR_VS_REGIME_FINGERPRINTS_RANKING.json",
        help="Written when --compare-years is set.",
    )
    args = ap.parse_args()

    if not args.regime_map.is_file():
        print(f"ERROR: missing {args.regime_map}", file=sys.stderr)
        return 2

    btc_ext = None if args.no_btc_ext else args.btc_ext_map

    if args.compare_years:
        if not args.quad_json.is_file():
            print(f"ERROR: missing {args.quad_json}", file=sys.stderr)
            return 2
        quad = json.loads(args.quad_json.read_text(encoding="utf-8"))
        tl = quad.get("uft_v2_timeline") or []
        by_year: Dict[str, Any] = {}
        years = [int(x.strip()) for x in args.compare_years.split(",") if x.strip()]
        for yr in years:
            row = None
            for t in tl:
                if int(t.get("year", -1)) == yr:
                    row = t
                    break
            if row is None:
                print(f"ERROR: year {yr} not in uft_v2_timeline", file=sys.stderr)
                return 2
            u4 = row.get("unified_4d_vector") or {}
            u4_raw = {k: float(u4[k]) for k in ("S", "L", "K", "M") if k in u4}
            v_year = _l2n(u4)
            doc = _build_ranking_doc(
                v_year=v_year,
                u4_raw=u4_raw,
                vector_source=f"uft_v2_timeline:{yr}",
                extra_meta={"quad_json": str(args.quad_json.resolve()), "year": yr},
                regime_map=args.regime_map,
                btc_ext_map=btc_ext,
                no_btc_ext=args.no_btc_ext,
            )
            by_year[str(yr)] = {
                "primary_historical_regime": doc.get("primary_historical_regime"),
                "primary_btc_ext_regime": doc.get("primary_btc_ext_regime"),
                "full": doc,
            }
        multi = {
            "schema": "quad_timeline_multiyear_vs_regime_fingerprints_v1",
            "quad_json": str(args.quad_json.resolve()),
            "compare_years": years,
            "by_year": by_year,
        }
        args.multi_output.parent.mkdir(parents=True, exist_ok=True)
        args.multi_output.write_text(json.dumps(multi, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "output": str(args.multi_output), "summaries": {y: by_year[str(y)]["primary_historical_regime"] for y in years}}, indent=2))
        return 0

    u4_raw: Dict[str, float]
    vector_source: str
    extra_meta: Dict[str, Any] = {}

    if args.slkm:
        u4_raw = _parse_slkm(args.slkm)
        vector_source = "manual_slkm_cli"
    elif args.vector_json:
        if not args.vector_json.is_file():
            print(f"ERROR: missing {args.vector_json}", file=sys.stderr)
            return 2
        raw = json.loads(args.vector_json.read_text(encoding="utf-8"))
        u4_raw = {k: float(raw[k]) for k in ("S", "L", "K", "M") if k in raw}
        if len(u4_raw) != 4:
            print("ERROR: vector-json must contain S,L,K,M", file=sys.stderr)
            return 2
        vector_source = f"manual_file:{args.vector_json}"
    else:
        if not args.quad_json.is_file():
            print(f"ERROR: missing {args.quad_json}", file=sys.stderr)
            return 2
        quad = json.loads(args.quad_json.read_text(encoding="utf-8"))
        tl = quad.get("uft_v2_timeline") or []
        row = None
        for t in tl:
            if int(t.get("year", -1)) == int(args.year):
                row = t
                break
        if row is None:
            print(f"ERROR: year {args.year} not in uft_v2_timeline", file=sys.stderr)
            return 2
        u4 = row.get("unified_4d_vector") or {}
        u4_raw = {k: float(u4[k]) for k in ("S", "L", "K", "M") if k in u4}
        vector_source = f"uft_v2_timeline:{args.year}"
        extra_meta = {"quad_json": str(args.quad_json.resolve()), "year": int(args.year)}

    v_year = _l2n({k: u4_raw[k] for k in ("S", "L", "K", "M")})

    doc = _build_ranking_doc(
        v_year=v_year,
        u4_raw=u4_raw,
        vector_source=vector_source,
        extra_meta=extra_meta,
        regime_map=args.regime_map,
        btc_ext_map=btc_ext,
        no_btc_ext=args.no_btc_ext,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output), "primary_historical": doc.get("primary_historical_regime")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
