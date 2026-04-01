"""
Build data/regimes/btc_regime_map.json from Quad-Fusion uft_v2_timeline yearly vectors.

BTC cycle labels (calendar-year bundles) are documented means of unified_4d_vector
from the SSOT quad fusion file — not a separate on-chain model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence

_WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_QUAD = _WORKSPACE_ROOT / "data" / "quad_fusion_training" / "quad_fusion_result_20260401_125917.json"
_DEFAULT_OUT = _WORKSPACE_ROOT / "data" / "regimes" / "btc_regime_map.json"

# Default year bundles (BTC-style labels on global Quad-Fusion yearly composites).
_DEFAULT_BUNDLES: Mapping[str, Sequence[int]] = {
    "bull": (2017, 2021),
    "bear": (2018, 2022),
    "sideways": (2015, 2019, 2023),
}

# Measurement anchor (QF / Divine Centroid); blend target when SSOT row is one-hot degenerate.
_DIVINE_CENTROID_4D: Mapping[str, float] = {
    "S": 0.25,
    "L": 0.25,
    "K": 0.25,
    "M": 0.25,
}


def _index_timeline(data: Mapping[str, Any]) -> Dict[int, Mapping[str, Any]]:
    tl = data.get("uft_v2_timeline") or []
    out: Dict[int, Mapping[str, Any]] = {}
    for row in tl:
        y = int(row["year"])
        out[y] = row
    return out


def _mean_vec(years: Sequence[int], by_year: Mapping[int, Mapping[str, Any]]) -> Dict[str, float]:
    acc = {"S": 0.0, "L": 0.0, "K": 0.0, "M": 0.0}
    n = 0
    for y in years:
        row = by_year[y]
        u = row["unified_4d_vector"]
        for k in acc:
            acc[k] += float(u[k])
        n += 1
    return {k: acc[k] / n for k in acc}


def _mean_scalar(
    years: Sequence[int], by_year: Mapping[int, Mapping[str, Any]], key: str
) -> float:
    vals: List[float] = []
    for y in years:
        v = by_year[y].get(key)
        if v is None:
            continue
        vals.append(float(v))
    return sum(vals) / len(vals) if vals else 0.0


def _round_vec(v: Mapping[str, float], places: int = 6) -> Dict[str, float]:
    return {k: round(float(v[k]), places) for k in ("S", "L", "K", "M")}


def _is_degenerate_unified_4d(v: Mapping[str, float], *, max_axis: float = 0.99, others_max: float = 0.02) -> bool:
    """True if vector is effectively one-hot (e.g. SSOT (1,0,0,0)), harming 4D cosine spread."""
    s, l, k, m = float(v["S"]), float(v["L"]), float(v["K"]), float(v["M"])
    mx = max(s, l, k, m)
    if mx < max_axis:
        return False
    tot = s + l + k + m
    return (tot - mx) <= others_max


def _blend_with_centroid(
    v: Mapping[str, float],
    *,
    alpha: float,
    centroid: Mapping[str, float] = _DIVINE_CENTROID_4D,
) -> Dict[str, float]:
    a = max(0.0, min(1.0, float(alpha)))
    return {
        key: (1.0 - a) * float(v[key]) + a * float(centroid[key])
        for key in ("S", "L", "K", "M")
    }


def build_map(
    quad_path: Path,
    bundles: Mapping[str, Sequence[int]],
    *,
    degeneracy_blend_alpha: float = 0.2,
    apply_degeneracy_blend: bool = True,
) -> Dict[str, Any]:
    raw = json.loads(quad_path.read_text(encoding="utf-8"))
    by_year = _index_timeline(raw)
    regimes: Dict[str, Any] = {}
    for rid, years in bundles.items():
        missing = [y for y in years if y not in by_year]
        if missing:
            raise KeyError(f"Regime {rid!r}: years not in uft_v2_timeline: {missing}")
        y_list = list(years)
        u_raw = _mean_vec(y_list, by_year)
        blend_meta: Dict[str, Any] = {"applied": False, "alpha": float(degeneracy_blend_alpha)}
        u_final = dict(u_raw)
        if apply_degeneracy_blend and _is_degenerate_unified_4d(u_raw):
            u_final = _blend_with_centroid(u_raw, alpha=degeneracy_blend_alpha)
            blend_meta = {
                "applied": True,
                "alpha": round(float(degeneracy_blend_alpha), 6),
                "reason": "SSOT mean unified_4d_vector is one-hot-like; blend toward 0.25 anchor for 4D cosine probes.",
                "raw_unified_4d_vector": _round_vec(u_raw),
            }
        fp = {
            "unified_4d_vector": _round_vec(u_final),
            "degeneracy_blend": blend_meta,
            "lambda_entropy_mean": round(_mean_scalar(y_list, by_year, "lambda_entropy"), 6),
            "geumhwa_index_mean": round(_mean_scalar(y_list, by_year, "geumhwa_index"), 6),
            "distance_to_centroid_mean": round(
                _mean_scalar(y_list, by_year, "distance_to_centroid"), 6
            ),
            "n_years": len(y_list),
        }
        regimes[rid] = {
            "years": y_list,
            "fingerprint": fp,
            "n_entries": len(y_list),
        }

    return {
        "version": "1.0",
        "source": str(quad_path.relative_to(_WORKSPACE_ROOT)).replace("/", "\\"),
        "methodology": (
            "BTC cycle labels as calendar-year bundles; mean of uft_v2_timeline "
            "unified_4d_vector and scalar means per bundle (Quad-Fusion global "
            "composite, not on-chain BTC-specific physics). If the bundle mean is "
            "one-hot degenerate (e.g. SSOT years 2018/2022), optional blend toward "
            "the 0.25 measurement anchor restores full 4D spread for cosine probes; "
            "raw mean is preserved under fingerprint.degeneracy_blend when applied."
        ),
        "bundles": {k: list(v) for k, v in bundles.items()},
        "regimes": regimes,
    }


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build btc_regime_map.json from Quad-Fusion timeline.")
    p.add_argument("--quad-json", type=Path, default=_DEFAULT_QUAD)
    p.add_argument("--output", type=Path, default=_DEFAULT_OUT)
    p.add_argument(
        "--degeneracy-blend-alpha",
        type=float,
        default=0.2,
        help="When bundle mean is one-hot-like, blend this fraction toward 0.25 centroid (default 0.2).",
    )
    p.add_argument(
        "--no-degeneracy-blend",
        action="store_true",
        help="Disable centroid blend; write raw means only (bear may stay one-hot).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print JSON to stdout only; do not write file.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.quad_json.is_file():
        raise FileNotFoundError(args.quad_json)
    payload = build_map(
        args.quad_json,
        _DEFAULT_BUNDLES,
        degeneracy_blend_alpha=float(args.degeneracy_blend_alpha),
        apply_degeneracy_blend=not bool(args.no_degeneracy_blend),
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.dry_run:
        print(text)
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
