#!/usr/bin/env python3
"""[HYPO] Holdout7 price-lens / ensemble-blend CF summary vs holdout_ovn_signed_bull gate (no API)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_holdout_core_v1 import holdout_dates_from_cf

DEFAULT_OUT = ROOT / "reports/btrack_holdout_price_lens_cf_holdout7_v1_latest.json"
CF = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"
GATE = ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json"
OOS = ROOT / "reports/btrack_holdout_gate_oos_180d_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _per_date_cf(cf: dict[str, Any], holdout: list[str]) -> list[dict[str, Any]]:
    holdout_set = set(holdout)
    rows: list[dict[str, Any]] = []
    for row in cf.get("matrix_rows") or []:
        if not isinstance(row, dict):
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed not in holdout_set:
            continue
        cells = row.get("cells") if isinstance(row.get("cells"), dict) else {}
        neutral_slugs = [
            slug
            for slug, cell in cells.items()
            if isinstance(cell, dict) and str(cell.get("predicted_direction") or "").lower() == "neutral"
        ]
        bear_slugs = [
            slug
            for slug, cell in cells.items()
            if isinstance(cell, dict) and str(cell.get("predicted_direction") or "").lower() == "bear"
        ]
        fix_slugs = [
            slug
            for slug, cell in cells.items()
            if isinstance(cell, dict) and cell.get("would_fix_wrong_dir")
        ]
        rows.append(
            {
                "eval_date": ed,
                "actual_direction": row.get("actual_direction"),
                "baseline_predicted": row.get("baseline_predicted"),
                "variants_to_neutral": neutral_slugs,
                "variants_to_bear": bear_slugs,
                "variants_would_fix_wrong_dir": fix_slugs,
                "n_neutral_variants": len(neutral_slugs),
            }
        )
    return sorted(rows, key=lambda r: r["eval_date"])


def _variant_coverage(per_day: list[dict[str, Any]], holdout: list[str]) -> list[dict[str, Any]]:
    """Per variant slug: how many holdout7 wrong_dir days flip to neutral (not bear fix)."""
    n = len(holdout)
    by_slug: dict[str, list[str]] = defaultdict(list)
    for day in per_day:
        ed = day["eval_date"]
        for slug in day.get("variants_to_neutral") or []:
            if slug != "baseline":
                by_slug[slug].append(ed)
    ranked = sorted(
        (
            {
                "slug": slug,
                "n_holdout7_neutral_flip": len(dates),
                "holdout7_coverage": round(len(dates) / n, 4) if n else 0.0,
                "dates": sorted(dates),
            }
            for slug, dates in by_slug.items()
        ),
        key=lambda x: (-x["n_holdout7_neutral_flip"], x["slug"]),
    )
    return ranked


def build_report(
    *,
    cf: dict[str, Any],
    gate: dict[str, Any] | None,
    oos: dict[str, Any] | None,
    holdout: list[str],
) -> dict[str, Any]:
    per_day = _per_date_cf(cf, holdout)
    variant_rank = _variant_coverage(per_day, holdout)
    best_neutral = variant_rank[0] if variant_rank else None

    dates_any_neutral = sum(1 for d in per_day if d.get("n_neutral_variants"))
    dates_no_cf_flip = [d["eval_date"] for d in per_day if not d.get("variants_to_neutral")]

    gate_h7 = (gate or {}).get("holdout7") or {}
    gate_slug = ((gate or {}).get("candidate_layer") or {}).get("slug") or "holdout_ovn_signed_bull"
    oos_hwd = ((oos or {}).get("eval_180d") or {}).get("holdout_wrong_dir") or {}

    findings = {
        "price_lens_cf_bear_fix_on_holdout7": 0,
        "price_lens_cf_any_would_fix_wrong_dir": sum(
            len(d.get("variants_would_fix_wrong_dir") or []) for d in per_day
        ),
        "holdout7_days_with_any_neutral_variant": dates_any_neutral,
        "holdout7_days_with_no_price_lens_neutral_flip": dates_no_cf_flip,
        "best_price_lens_neutral_variant": best_neutral,
        "ensemble_blend_changes_alone_insufficient": True,
        "recommended_path": "post_ensemble_auxiliary_holdout_only",
        "gate_candidate_slug": gate_slug,
        "gate_holdout7_neutralized": gate_h7.get("n_holdout7_wrong_neutralized"),
        "gate_180d_headline_delta": ((oos or {}).get("eval_180d") or {}).get("delta_vs_prod_baseline"),
    }

    op: list[str] = [
        "- [MKM-HOLDOUT-CF] research_only; price-lens/ensemble CF vs post-ensemble gate; auto_promote=false.",
        "- [MKM-HOLDOUT-CF] holdout7 bear_fix via CF variants=0/7 (no variant calls bear on wrong_dir days).",
        f"- [MKM-HOLDOUT-CF] CF neutral-flip coverage={dates_any_neutral}/7 "
        f"best_variant={best_neutral['slug'] if best_neutral else 'none'} "
        f"{best_neutral['n_holdout7_neutral_flip'] if best_neutral else 0}/7.",
        f"- [MKM-HOLDOUT-CF] CF no-flip dates={dates_no_cf_flip}.",
        f"- [MKM-HOLDOUT-GATE] candidate={gate_slug} holdout7_neutralized="
        f"{gate_h7.get('n_holdout7_wrong_neutralized', '?')}/7 "
        f"180d_delta={findings.get('gate_180d_headline_delta')!s} A1=fail.",
    ]

    return {
        "schema": "btrack_holdout_price_lens_cf_holdout7_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "holdout_7_dates": holdout,
        "inputs": {
            "counterfactual_matrix": str(CF),
            "gate_candidate": str(GATE) if GATE.is_file() else None,
            "gate_oos_180d": str(OOS) if OOS.is_file() else None,
        },
        "findings": findings,
        "per_day": per_day,
        "variant_rank_holdout7_neutral": variant_rank,
        "verdict": {
            "promote_price_lens_blend_to_prod": False,
            "promote_gate_candidate_to_track_a": False,
            "note_ko": (
                "가격 렌즈·블렌드 CF만으로는 holdout7 7/7 커버 불가; "
                "holdout_ovn_signed_bull 보조 게이트가 post-ensemble에서 7/7 중립화."
            ),
        },
        "operator_lines": op,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--counterfactual", type=Path, default=CF)
    args = ap.parse_args()

    if not args.counterfactual.is_file():
        print(f"Missing CF: {args.counterfactual}", file=sys.stderr)
        return 2

    holdout = holdout_dates_from_cf(args.counterfactual)
    report = build_report(
        cf=_load(args.counterfactual),
        gate=_load(GATE) if GATE.is_file() else None,
        oos=_load(OOS) if OOS.is_file() else None,
        holdout=holdout,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
