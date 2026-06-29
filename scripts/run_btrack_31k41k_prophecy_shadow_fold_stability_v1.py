#!/usr/bin/env python3
"""Blocked walk-forward fold stability for 31k/41k shadow overlay v2 (research-only)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
DEFAULT_OUT_V2B_MAX = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v1_latest.json"
DEFAULT_OUT_V2 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2_v1_latest.json"
DEFAULT_OUT_V2C = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2c_v1_latest.json"
DEFAULT_OUT_V2B_STRICT = (
    ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_v1_latest.json"
)
DEFAULT_OUT = DEFAULT_OUT_V2B_STRICT


def resolve_default_fold_out(overlay_version: str, out_json: Path) -> Path:
    """When --out-json is SSOT default, route overlay version to versioned fold paths."""
    if out_json != DEFAULT_OUT:
        return out_json
    by_version = {
        "v2": DEFAULT_OUT_V2,
        "v2c": DEFAULT_OUT_V2C,
        "v2b": DEFAULT_OUT_V2B_MAX,
        "v2b_strict": DEFAULT_OUT_V2B_STRICT,
    }
    return by_version.get(overlay_version, DEFAULT_OUT_V2B_STRICT)


def _load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hit_rate(rows: list[dict[str, Any]], pred_key: str) -> tuple[float, int, int]:
    hits = 0
    n = 0
    for row in rows:
        pred = str(row.get(pred_key) or "").strip().lower()
        actual = str(row.get("actual_direction") or "").strip().lower()
        if pred not in ("bull", "bear") or actual not in ("bull", "bear"):
            continue
        n += 1
        if pred == actual:
            hits += 1
    if n == 0:
        return 0.0, 0, 0
    return hits / n, hits, n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-folds", type=int, default=6, help="Date blocks; produces n_folds-1 test windows.")
    ap.add_argument("--min-effective-folds", type=int, default=5, help="Require at least this many test folds.")
    ap.add_argument("--min-positive-delta-folds", type=int, default=2)
    ap.add_argument("--worst-fold-delta-floor", type=float, default=0.0)
    ap.add_argument("--logos-lens-json", type=Path, default=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json")
    ap.add_argument("--hypothesis-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    ap.add_argument("--logos-mapping-json", type=Path, default=ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json")
    ap.add_argument("--corpus-baseline-json", type=Path, default=ROOT / "docs/final/artifacts/corpus_counting_baseline_comparison_v1_latest.json")
    ap.add_argument("--conflict-max", type=float, default=0.35)
    ap.add_argument("--logos-confidence-min", type=float, default=0.15)
    ap.add_argument(
        "--overlay-version",
        choices=("v2", "v2c", "v2b", "v2b_strict"),
        default="v2b_strict",
        help="SSOT default v2b_strict; must match eval overlay policy.",
    )
    ap.add_argument(
        "--panel-json",
        type=Path,
        default=ROOT / "docs/final/artifacts/btrack_31k41k_daily_anchor_panel_v1_latest.json",
    )
    args = ap.parse_args()

    args.out_json = resolve_default_fold_out(args.overlay_version, args.out_json)

    feat_mod = _load_module("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    wf_mod = _load_module("prophecy_per_date_combo_wf", "scripts/run_prophecy_per_date_combo_walkforward_v1.py")

    score_doc = _read_json(args.score_json)
    rows = feat_mod.btc_score_rows(score_doc)
    if not rows:
        raise SystemExit(f"no btc rows in {args.score_json}")

    dates = sorted({str(r.get("eval_date"))[:10] for r in rows})
    n_dates = len(dates)
    n_folds_requested = int(args.n_folds)
    n_folds_effective = max(2, min(n_folds_requested, n_dates))

    features = feat_mod.compute_all_features(
        logos_mapping_path=args.logos_mapping_json,
        logos_lens_path=args.logos_lens_json,
        hypothesis_path=args.hypothesis_json,
        corpus_baseline_path=args.corpus_baseline_json,
    )
    logos_lens = _read_json(args.logos_lens_json)
    hypothesis = _read_json(args.hypothesis_json)

    if args.overlay_version in ("v2b", "v2b_strict"):
        panel_merge = (
            "per_row_strict" if args.overlay_version == "v2b_strict" else "max_per_row_global"
        )
        panel_doc = _read_json(args.panel_json)
        panel_mode = str(panel_doc.get("feature_mode") or "")
        if not panel_doc.get("timeseries_ready") and panel_mode != "static_global_proxy":
            raise SystemExit(f"panel not timeseries_ready: {args.panel_json}")
        ts_mod = _load_module(
            "btrack_31k41k_daily_anchor_timeseries_v1",
            "scripts/btrack_31k41k_daily_anchor_timeseries_v1.py",
        )
        panel_by_date = {
            str(pr["eval_date"])[:10]: pr
            for pr in (panel_doc.get("rows") or [])
            if isinstance(pr, dict) and pr.get("eval_date")
        }
        overlaid_all = feat_mod.apply_shadow_overlay_v2b(
            rows,
            logos_lens=logos_lens,
            features=features,
            hypothesis=hypothesis,
            panel_by_date=panel_by_date,
            panel_to_features=lambda pr: ts_mod.panel_row_to_overlay_features(
                pr, features, merge_policy=panel_merge
            ),
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
        )
        probe_mode = (
            "logos_anchor_overlay_v2b_strict"
            if args.overlay_version == "v2b_strict"
            else "logos_anchor_overlay_v2b"
        )
    elif args.overlay_version == "v2c":
        overlaid_all = feat_mod.apply_shadow_overlay_v2c(
            rows,
            logos_lens=logos_lens,
            features=features,
            hypothesis=hypothesis,
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
        )
        probe_mode = "logos_anchor_overlay_v2c"
    else:
        overlaid_all = feat_mod.apply_shadow_overlay_v2(
            rows,
            logos_lens=logos_lens,
            features=features,
            hypothesis=hypothesis,
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
        )
        probe_mode = "logos_anchor_overlay_v2"
    by_date = {str(r.get("eval_date"))[:10]: r for r in overlaid_all}

    fold_specs = wf_mod._blocked_walkforward_folds(dates, n_folds_effective)
    fold_rows: list[dict[str, Any]] = []
    deltas: list[float] = []

    for fi, (_train_dates, test_dates) in enumerate(fold_specs):
        test_rows = [by_date[d] for d in test_dates if d in by_date]
        base_rate, base_hits, base_n = _hit_rate(test_rows, "predicted_direction")
        shadow_rate, shadow_hits, shadow_n = _hit_rate(test_rows, "shadow_predicted_direction")
        delta = shadow_rate - base_rate if base_n else 0.0
        deltas.append(delta)
        fold_rows.append(
            {
                "fold_index": fi,
                "test_dates": test_dates,
                "n_test": shadow_n,
                "baseline_hit_rate": round(base_rate, 6),
                "shadow_hit_rate": round(shadow_rate, 6),
                "delta_hit_rate": round(delta, 6),
                "baseline_hits": base_hits,
                "shadow_hits": shadow_hits,
            }
        )

    effective_folds = len(fold_rows)
    positive_delta_folds = sum(1 for d in deltas if d > 0)
    worst_fold_delta = min(deltas) if deltas else -1.0
    mean_fold_delta = sum(deltas) / len(deltas) if deltas else 0.0

    folds_ok = effective_folds >= int(args.min_effective_folds)
    multi_window_ok = positive_delta_folds >= int(args.min_positive_delta_folds)
    worst_ok = worst_fold_delta >= float(args.worst_fold_delta_floor)
    stability_not_worse = folds_ok and multi_window_ok and worst_ok

    pooled_base, _, pooled_n = _hit_rate(overlaid_all, "predicted_direction")
    pooled_shadow, _, _ = _hit_rate(overlaid_all, "shadow_predicted_direction")
    pooled_delta = pooled_shadow - pooled_base

    out = {
        "schema": "btrack_31k41k_prophecy_shadow_fold_stability_v1",
        "generated_at_utc": _iso_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "inputs": {
            "score_json": str(args.score_json),
            "n_folds_requested": n_folds_requested,
            "n_folds_effective": n_folds_effective,
            "n_distinct_dates": n_dates,
            "min_effective_folds": int(args.min_effective_folds),
            "min_positive_delta_folds": int(args.min_positive_delta_folds),
            "worst_fold_delta_floor": float(args.worst_fold_delta_floor),
            "overlay_version": args.overlay_version,
            "panel_merge_policy": (
                "per_row_strict"
                if args.overlay_version == "v2b_strict"
                else ("max_per_row_global" if args.overlay_version == "v2b" else None)
            ),
            "probe_mode": probe_mode,
        },
        "pooled_panel": {
            "baseline_hit_rate": round(pooled_base, 6),
            "shadow_hit_rate": round(pooled_shadow, 6),
            "delta_hit_rate": round(pooled_delta, 6),
            "n_evaluated": pooled_n,
        },
        "folds": fold_rows,
        "aggregates": {
            "effective_folds": effective_folds,
            "positive_delta_folds": positive_delta_folds,
            "worst_fold_delta": round(worst_fold_delta, 6),
            "mean_fold_delta": round(mean_fold_delta, 6),
            "delta_stddev": round(
                (sum((d - mean_fold_delta) ** 2 for d in deltas) / len(deltas)) ** 0.5, 6
            )
            if len(deltas) > 1
            else 0.0,
        },
        "checks": {
            "folds_count_ok": folds_ok,
            "multi_window_positive_ok": multi_window_ok,
            "worst_fold_not_worse_ok": worst_ok,
            "stability_not_worse": stability_not_worse,
        },
        "summary": {
            "status": "STABILITY_OK" if stability_not_worse else "STABILITY_FAIL",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(
        f"status={out['summary']['status']} effective_folds={effective_folds} "
        f"positive_delta_folds={positive_delta_folds} worst_fold_delta={worst_fold_delta:.6f} "
        f"pooled_delta={pooled_delta:.6f}"
    )
    return 0 if stability_not_worse else 1


if __name__ == "__main__":
    raise SystemExit(main())
