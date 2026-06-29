#!/usr/bin/env python3
"""Build shadow eval artifact for 31k/41k anchor uplift probe (research-only)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE_HIT = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_kpi_b_shadow_v1_latest.json"
DEFAULT_BASELINE_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
DEFAULT_OUT_V1 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v1_latest.json"
DEFAULT_OUT_V2 = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2_latest.json"
DEFAULT_OUT_V2C = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2c_latest.json"
DEFAULT_OUT_V2B = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2b_latest.json"
DEFAULT_OUT_V2B_STRICT = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_eval_v2b_strict_latest.json"
DEFAULT_PANEL = ROOT / "docs/final/artifacts/btrack_31k41k_daily_anchor_panel_v1_latest.json"
DEFAULT_OUT = DEFAULT_OUT_V2B_STRICT


def _load_module(rel: str, name: str | None = None):
    path = ROOT / rel
    mod_name = name or path.stem
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_features_mod():
    return _load_module("scripts/btrack_31k41k_shadow_features_v1.py")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-hit-json", type=Path, default=DEFAULT_BASELINE_HIT)
    ap.add_argument("--baseline-score-json", type=Path, default=DEFAULT_BASELINE_SCORE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-evaluated-min", type=int, default=30)
    ap.add_argument("--delta-hit-rate-threshold", type=float, default=0.0)
    ap.add_argument(
        "--assume-anchor-uplift-delta",
        type=float,
        default=None,
        help="Manual additive delta (skips row overlay). For dry experimentation only.",
    )
    ap.add_argument("--conflict-max", type=float, default=0.35)
    ap.add_argument("--logos-confidence-min", type=float, default=0.15)
    ap.add_argument("--logos-lens-json", type=Path, default=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json")
    ap.add_argument("--hypothesis-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    ap.add_argument("--logos-mapping-json", type=Path, default=ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json")
    ap.add_argument("--corpus-baseline-json", type=Path, default=ROOT / "docs/final/artifacts/corpus_counting_baseline_comparison_v1_latest.json")
    ap.add_argument(
        "--overlay-version",
        choices=("v1", "v2", "v2c", "v2b", "v2b_strict"),
        default="v2b_strict",
        help="SSOT default v2b_strict; v2b = max(panel,global) diagnostic only.",
    )
    ap.add_argument(
        "--panel-json",
        type=Path,
        default=DEFAULT_PANEL,
        help="Required for v2b (timeseries_ready panel).",
    )
    args = ap.parse_args()

    if args.out_json in (DEFAULT_OUT, DEFAULT_OUT_V2B, DEFAULT_OUT_V2B_STRICT, DEFAULT_OUT_V2C, DEFAULT_OUT_V2):
        if args.overlay_version == "v2b_strict":
            args.out_json = DEFAULT_OUT_V2B_STRICT
        elif args.overlay_version == "v2b":
            args.out_json = DEFAULT_OUT_V2B
        elif args.overlay_version == "v2c":
            args.out_json = DEFAULT_OUT_V2C
        elif args.overlay_version == "v2":
            args.out_json = DEFAULT_OUT_V2
        else:
            args.out_json = DEFAULT_OUT_V1

    feat_mod = _load_features_mod()
    features = feat_mod.compute_all_features(
        logos_mapping_path=args.logos_mapping_json,
        logos_lens_path=args.logos_lens_json,
        hypothesis_path=args.hypothesis_json,
        corpus_baseline_path=args.corpus_baseline_json,
    )

    hit_doc = _read_json(args.baseline_hit_json)
    score_doc = _read_json(args.baseline_score_json)
    logos_lens = _read_json(args.logos_lens_json)
    hypothesis = _read_json(args.hypothesis_json)

    metrics = hit_doc.get("metrics") if isinstance(hit_doc.get("metrics"), dict) else {}
    baseline_hit_rate = _as_float(metrics.get("price_directional_hit_rate"))
    n_evaluated = _as_int(metrics.get("n_evaluated"))

    rows = feat_mod.btc_score_rows(score_doc)
    row_baseline_rate, row_baseline_hits, row_n = feat_mod.hit_rate_for_predictions(rows, "predicted_direction")

    if row_n > 0:
        baseline_hit_rate = row_baseline_rate
        n_evaluated = row_n

    manual_delta = args.assume_anchor_uplift_delta
    overlay_rows: list[dict[str, Any]] = []
    shadow_hits = 0
    overlay_applied_count = 0
    panel_doc_for_summary: dict[str, Any] | None = None

    if manual_delta is not None:
        anchor_probe_hit_rate = baseline_hit_rate + float(manual_delta)
        probe_mode = "manual_delta_stub"
    elif args.overlay_version in ("v2", "v2c", "v2b", "v2b_strict"):
        panel_by_date: dict[str, dict[str, Any]] = {}
        panel_to_features = None
        panel_merge_policy = "max_per_row_global"
        if args.overlay_version in ("v2b", "v2b_strict"):
            if args.overlay_version == "v2b_strict":
                panel_merge_policy = "per_row_strict"
            panel_doc = _read_json(args.panel_json)
            if not panel_doc:
                raise SystemExit(f"missing panel for v2b: {args.panel_json}")
            panel_mode = str(panel_doc.get("feature_mode") or "")
            if not panel_doc.get("timeseries_ready") and panel_mode != "static_global_proxy":
                raise SystemExit(
                    f"panel timeseries_ready=false at {args.panel_json}; "
                    "run build_btrack_31k41k_daily_anchor_panel_v1.py --feature-mode timeseries_v2"
                )
            ts_mod_obj = _load_module("scripts/btrack_31k41k_daily_anchor_timeseries_v1.py")
            panel_to_features = lambda pr: ts_mod_obj.panel_row_to_overlay_features(
                pr, features, merge_policy=panel_merge_policy
            )
            panel_doc_for_summary = panel_doc
            for pr in panel_doc.get("rows") or []:
                if isinstance(pr, dict) and pr.get("eval_date"):
                    panel_by_date[str(pr["eval_date"])[:10]] = pr
            overlay_rows = feat_mod.apply_shadow_overlay_v2b(
                rows,
                logos_lens=logos_lens,
                features=features,
                hypothesis=hypothesis,
                panel_by_date=panel_by_date,
                panel_to_features=panel_to_features,
                conflict_max=float(args.conflict_max),
                logos_confidence_min=float(args.logos_confidence_min),
            )
            probe_mode = (
                "logos_anchor_overlay_v2b_strict"
                if args.overlay_version == "v2b_strict"
                else "logos_anchor_overlay_v2b"
            )
        elif args.overlay_version == "v2c":
            overlay_rows = feat_mod.apply_shadow_overlay_v2c(
                rows,
                logos_lens=logos_lens,
                features=features,
                hypothesis=hypothesis,
                conflict_max=float(args.conflict_max),
                logos_confidence_min=float(args.logos_confidence_min),
            )
            probe_mode = "logos_anchor_overlay_v2c"
        else:
            overlay_rows = feat_mod.apply_shadow_overlay_v2(
                rows,
                logos_lens=logos_lens,
                features=features,
                hypothesis=hypothesis,
                conflict_max=float(args.conflict_max),
                logos_confidence_min=float(args.logos_confidence_min),
            )
            probe_mode = "logos_anchor_overlay_v2"
        anchor_probe_hit_rate, shadow_hits, row_n2 = feat_mod.hit_rate_for_predictions(
            overlay_rows, "shadow_predicted_direction"
        )
        if row_n2 > 0:
            n_evaluated = row_n2
        overlay_applied_count = sum(1 for r in overlay_rows if r.get("shadow_overlay_applied"))
    else:
        overlay_rows = feat_mod.apply_shadow_overlay(
            rows,
            logos_lens=logos_lens,
            features=features,
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
        )
        anchor_probe_hit_rate, shadow_hits, row_n2 = feat_mod.hit_rate_for_predictions(
            overlay_rows, "shadow_predicted_direction"
        )
        if row_n2 > 0:
            n_evaluated = row_n2
        overlay_applied_count = sum(1 for r in overlay_rows if r.get("shadow_overlay_applied"))
        probe_mode = "logos_anchor_overlay_v1"

    delta = anchor_probe_hit_rate - baseline_hit_rate

    min_n_ok = n_evaluated >= int(args.n_evaluated_min)
    delta_ok = delta >= float(args.delta_hit_rate_threshold)

    feature_summary = {
        k: (v.get("value") if isinstance(v, dict) else v) for k, v in features.items()
    }

    panel_summary: dict[str, Any] | None = None
    if panel_doc_for_summary:
        panel_inputs = (
            panel_doc_for_summary.get("inputs")
            if isinstance(panel_doc_for_summary.get("inputs"), dict)
            else {}
        )
        row_densities = [
            float((r.get("logos_anchor_density_31k_v1") or {}).get("value") or 0.0)
            for r in (panel_doc_for_summary.get("rows") or [])
            if isinstance(r, dict)
        ]
        panel_summary = {
            "feature_mode": panel_doc_for_summary.get("feature_mode"),
            "rolling_sample_size": panel_inputs.get("rolling_sample_size"),
            "n_distinct_density_values": panel_inputs.get("n_distinct_density_values"),
            "per_row_density_min": min(row_densities) if row_densities else None,
            "per_row_density_max": max(row_densities) if row_densities else None,
        }

    daily_overlay = args.overlay_version in ("v2", "v2c", "v2b", "v2b_strict") and manual_delta is None
    v2c_routing = args.overlay_version in ("v2c", "v2b", "v2b_strict") and manual_delta is None
    v2b_panel = args.overlay_version in ("v2b", "v2b_strict") and manual_delta is None
    if args.overlay_version == "v2b_strict" and manual_delta is None:
        schema = "btrack_31k41k_prophecy_shadow_eval_v2b_strict"
    elif args.overlay_version == "v2b" and manual_delta is None:
        schema = "btrack_31k41k_prophecy_shadow_eval_v2b"
    elif args.overlay_version == "v2c" and manual_delta is None:
        schema = "btrack_31k41k_prophecy_shadow_eval_v2c"
    elif args.overlay_version == "v2" and manual_delta is None:
        schema = "btrack_31k41k_prophecy_shadow_eval_v2"
    else:
        schema = "btrack_31k41k_prophecy_shadow_eval_v1"
    control_flags = {
        "global_overlay_disengaged": daily_overlay,
        "daily_routing_v2_enabled": daily_overlay,
        "daily_routing_v2c_enabled": v2c_routing,
        "daily_panel_v2b_enabled": v2b_panel,
        "panel_merge_policy": (
            "per_row_strict"
            if args.overlay_version == "v2b_strict" and manual_delta is None
            else ("max_per_row_global" if args.overlay_version == "v2b" and manual_delta is None else None)
        ),
        "ensemble_align_requires_move_base_mismatch": v2c_routing,
        "v1_global_overlay_deprecated": args.overlay_version in ("v2", "v2c", "v2b", "v2b_strict"),
    }

    out = {
        "schema": schema,
        "generated_at_utc": _iso_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "control_flags": control_flags,
        "inputs": {
            "baseline_hit_json": str(args.baseline_hit_json),
            "baseline_score_json": str(args.baseline_score_json),
            "n_evaluated_min": int(args.n_evaluated_min),
            "delta_hit_rate_threshold": float(args.delta_hit_rate_threshold),
            "assume_anchor_uplift_delta": manual_delta,
            "conflict_max": float(args.conflict_max),
            "logos_confidence_min": float(args.logos_confidence_min),
            "overlay_version": args.overlay_version,
            "panel_json": str(args.panel_json) if v2b_panel else None,
            "panel_merge_policy": control_flags.get("panel_merge_policy"),
            "probe_mode": probe_mode,
        },
        "features": features,
        "feature_summary": feature_summary,
        "panel_summary": panel_summary,
        "baseline": {
            "price_directional_hit_rate": round(baseline_hit_rate, 6),
            "n_evaluated": n_evaluated,
            "price_hits": row_baseline_hits if row_n else _as_int(metrics.get("price_hits")),
            "score_generated_at_utc": score_doc.get("generated_at_utc"),
        },
        "shadow_probe": {
            "price_directional_hit_rate": round(anchor_probe_hit_rate, 6),
            "delta_hit_rate": round(delta, 6),
            "price_hits": shadow_hits if manual_delta is None else None,
            "overlay_applied_count": overlay_applied_count,
            "overlay_applied_fraction": (
                round(overlay_applied_count / n_evaluated, 6) if n_evaluated and manual_delta is None else None
            ),
            "logos_direction": feat_mod.logos_lens_direction(logos_lens)[0],
            "ensemble_direction": str((hypothesis.get("prediction") or {}).get("direction") or ""),
        },
        "checks": {
            "min_n_ok": min_n_ok,
            "delta_ok": delta_ok,
        },
        "summary": {
            "shadow_delta_positive": bool(delta_ok),
            "ready_for_gate_check": bool(min_n_ok),
            "status": "READY_FOR_GATE_CHECK" if min_n_ok else "INSUFFICIENT_N",
        },
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(
        f"status={out['summary']['status']} delta_hit_rate={delta:.6f} n={n_evaluated} "
        f"probe_mode={probe_mode} features={feature_summary}"
    )
    return 0 if min_n_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
