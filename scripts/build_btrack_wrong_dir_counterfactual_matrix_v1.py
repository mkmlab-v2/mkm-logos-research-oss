#!/usr/bin/env python3
"""[HYPO] Per-date counterfactual matrix for wrong-direction cohort × price-lens sweep variants."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SWEEP = ROOT / "reports/btrack_price_lens_bear_calibration_sweep_v1_latest.json"
DEFAULT_MISS = ROOT / "reports/btrack_headline_miss_report_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_wrong_dir_counterfactual_matrix_v1_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _btc_preds_by_date(per_date_path: Path) -> dict[str, str]:
    doc = _load(per_date_path)
    out: dict[str, str] = {}
    for r in doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").lower() != "btc":
            continue
        ed = str(r.get("eval_date") or "")[:10]
        out[ed] = str(r.get("predicted_direction") or "neutral").strip().lower()
    return out


def build_matrix(
    sweep_doc: dict[str, Any],
    *,
    wrong_dates: list[str],
    baseline_slug: str = "baseline",
) -> dict[str, Any]:
    variants = [v for v in (sweep_doc.get("variants") or []) if isinstance(v, dict) and v.get("per_date_path")]
    slug_to_preds: dict[str, dict[str, str]] = {}
    for v in variants:
        slug = str(v.get("slug") or "")
        p = Path(str(v.get("per_date_path") or ""))
        if slug and p.is_file():
            slug_to_preds[slug] = _btc_preds_by_date(p)

    if baseline_slug not in slug_to_preds:
        raise ValueError(f"baseline slug {baseline_slug!r} missing or per_date file not found")

    base_preds = slug_to_preds[baseline_slug]
    slugs = [str(v.get("slug")) for v in variants if str(v.get("slug")) in slug_to_preds]
    rows: list[dict[str, Any]] = []
    flip_by_slug: dict[str, list[str]] = {s: [] for s in slugs if s != baseline_slug}
    fix_by_slug: dict[str, list[str]] = {s: [] for s in slugs if s != baseline_slug}

    for ed in sorted(wrong_dates):
        actual = "bear"
        base_pred = base_preds.get(ed, "neutral")
        cells: dict[str, Any] = {}
        for slug in slugs:
            pred = slug_to_preds[slug].get(ed, "neutral")
            flipped = base_pred == "bull" and pred in ("bear", "neutral")
            would_fix = pred == actual
            cells[slug] = {
                "predicted_direction": pred,
                "vs_baseline": pred != base_pred,
                "flipped_off_bull": flipped,
                "would_fix_wrong_dir": would_fix,
            }
            if slug != baseline_slug:
                if flipped:
                    flip_by_slug[slug].append(ed)
                if would_fix:
                    fix_by_slug[slug].append(ed)
        rows.append(
            {
                "eval_date": ed,
                "actual_direction": actual,
                "baseline_predicted": base_pred,
                "cells": cells,
            }
        )

  # Compact lines for panel (one per wrong_dir date)
    date_lines: list[str] = []
    for row in rows:
        ed = row["eval_date"]
        changes = []
        for slug in slugs:
            if slug == baseline_slug:
                continue
            c = row["cells"][slug]
            if c.get("flipped_off_bull"):
                changes.append(f"{slug}→{c['predicted_direction']}")
        ch = ", ".join(changes) if changes else "no_flip"
        fix_slugs = [s for s in slugs if s != baseline_slug and row["cells"][s].get("would_fix_wrong_dir")]
        fix_note = f" fix={','.join(fix_slugs)}" if fix_slugs else ""
        date_lines.append(f"{ed}: baseline={row['baseline_predicted']} | {ch}{fix_note}")

    variant_summary = []
    for slug in slugs:
        if slug == baseline_slug:
            continue
        variant_summary.append(
            {
                "slug": slug,
                "n_flipped_off_bull": len(flip_by_slug[slug]),
                "n_would_fix_wrong_dir": len(fix_by_slug[slug]),
                "flipped_dates": flip_by_slug[slug],
                "fix_dates": fix_by_slug[slug],
            }
        )

    best_flip = (
        max(variant_summary, key=lambda x: x["n_flipped_off_bull"]) if variant_summary else None
    )
    best_fix = (
        max(variant_summary, key=lambda x: x["n_would_fix_wrong_dir"]) if variant_summary else None
    )
    n_dates_any_flip = sum(
        1
        for row in rows
        if any(
            row["cells"][s].get("flipped_off_bull")
            for s in slugs
            if s != baseline_slug and s in row["cells"]
        )
    )
    op = (
        f"- [MKM-WRONG-DIR-CF] cohort n={len(wrong_dates)}; "
        f"bear_fix=0/{len(wrong_dates)} (no variant called bear); "
        f"dates_with_neutral_flip={n_dates_any_flip}; "
        f"best_neutral_flip={best_flip['slug']} {best_flip['n_flipped_off_bull']}/{len(wrong_dates)}"
        if best_flip
        else f"- [MKM-WRONG-DIR-CF] cohort n={len(wrong_dates)}; no flips"
    )

    return {
        "schema": "btrack_wrong_dir_counterfactual_matrix_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "baseline_slug": baseline_slug,
        "variant_slugs": slugs,
        "wrong_direction_dates": sorted(wrong_dates),
        "matrix_rows": rows,
        "variant_summary": variant_summary,
        "summary": {
            "n_wrong_direction_dates": len(wrong_dates),
            "n_bear_fix_any_variant": sum(v["n_would_fix_wrong_dir"] for v in variant_summary),
            "n_dates_with_any_neutral_flip": n_dates_any_flip,
            "best_neutral_flip_slug": best_flip["slug"] if best_flip else None,
            "best_neutral_flip_count": best_flip["n_flipped_off_bull"] if best_flip else 0,
        },
        "panel_date_lines": date_lines,
        "operator_line": op,
        "operator_lines": [op] + [f"- [MKM-WRONG-DIR-CF] {line}" for line in date_lines[:7]],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sweep-json", type=Path, default=DEFAULT_SWEEP)
    ap.add_argument("--miss-report", type=Path, default=DEFAULT_MISS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--baseline-slug", default="baseline")
    args = ap.parse_args()
    if not args.sweep_json.is_file():
        print(f"Missing sweep JSON: {args.sweep_json}", file=sys.stderr)
        return 2

    sweep_doc = _load(args.sweep_json)
    wrong_dates = list(sweep_doc.get("wrong_dir_dates") or [])
    if not wrong_dates and args.miss_report.is_file():
        miss = _load(args.miss_report)
        wrong_dates = sorted(
            {
                str(m.get("eval_date"))[:10]
                for m in (miss.get("misses") or [])
                if isinstance(m, dict) and m.get("miss_kind") == "wrong_direction"
            }
        )

    if not wrong_dates:
        print("No wrong_direction dates found.", file=sys.stderr)
        return 2

    try:
        report = build_matrix(sweep_doc, wrong_dates=wrong_dates, baseline_slug=args.baseline_slug)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for line in report.get("operator_lines") or []:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
