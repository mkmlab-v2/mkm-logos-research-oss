# -*- coding: utf-8 -*-
"""Intersect verse_id sets from four regime-primary TOP-K reports (regime_map keys).

Default inputs: backtest_results/LOGOS_RESONANCE_REGIME_{imf,it_bubble,lehman,covid}_TOP100.json
Reuses ``build_intersection`` from ``compute_logos_regime_intersections.py`` (same schema).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_intersection_builder():
    root = _workspace_root()
    path = root / "scripts" / "compute_logos_regime_intersections.py"
    spec = importlib.util.spec_from_file_location("logos_regime_intersections", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    root = _workspace_root()
    bt = root / "backtest_results"
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--imf",
        type=Path,
        default=bt / "LOGOS_RESONANCE_REGIME_imf_TOP100.json",
    )
    ap.add_argument(
        "--it-bubble",
        type=Path,
        dest="it_bubble",
        default=bt / "LOGOS_RESONANCE_REGIME_it_bubble_TOP100.json",
    )
    ap.add_argument(
        "--lehman",
        type=Path,
        default=bt / "LOGOS_RESONANCE_REGIME_lehman_TOP100.json",
    )
    ap.add_argument(
        "--covid",
        type=Path,
        default=bt / "LOGOS_RESONANCE_REGIME_covid_TOP100.json",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=bt / "LOGOS_RESONANCE_QUAD_FUSION_REGIMES_INTERSECTION_TOP100.json",
    )
    args = ap.parse_args()

    regime_to_path = {
        "imf": args.imf,
        "it_bubble": args.it_bubble,
        "lehman": args.lehman,
        "covid": args.covid,
    }
    for k, p in regime_to_path.items():
        if not p.is_file():
            print(f"ERROR: missing {k}: {p}", file=sys.stderr)
            return 2

    mod = _load_intersection_builder()
    doc = mod.build_intersection(regime_to_path=regime_to_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    s = doc["summary"]
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "count_all_four": doc["count_all_four"],
                "any_pairwise": s["any_pairwise_non_empty"],
                "any_triple": s["any_triple_non_empty"],
                "all_four_non_empty": s["all_four_non_empty"],
                "count_relaxed": int(doc.get("relaxed_gate", {}).get("count", 0)),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
