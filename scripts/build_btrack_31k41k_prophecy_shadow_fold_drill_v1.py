#!/usr/bin/env python3
"""Drill-down for worst fold / per-date overlay decisions (Phase 2 follow-up, research-only)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOLD = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_stability_v2b_strict_v1_latest.json"
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
DEFAULT_JSON_OUT = ROOT / "docs/final/artifacts/btrack_31k41k_prophecy_shadow_fold_drill_v1_latest.json"
DEFAULT_MD_OUT = ROOT / "reports/btrack_31k41k_prophecy_shadow_fold_drill_v1_latest.md"


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_md(out: dict[str, Any]) -> str:
    lines = [
        "# B-track 31k/41k shadow fold drill (research-only)",
        "",
        "Classification: `[HYPO]` · `NON_GATING` · no Track A merge.",
        "",
        f"- Worst fold index: **{out.get('worst_fold_index')}** (delta **{out.get('worst_fold_delta')}**)",
        f"- Dates in worst fold: {', '.join(out.get('worst_fold_test_dates') or [])}",
        "",
        "## Per-date rows (worst fold)",
        "",
        "| date | base | shadow | actual | applied | routing | base_hit | shadow_hit | Δhit |",
        "|------|------|--------|--------|---------|---------|----------|------------|------|",
    ]
    for r in out.get("per_date_rows") or []:
        if not isinstance(r, dict):
            continue
        lines.append(
            f"| {r.get('eval_date')} | {r.get('baseline_direction')} | {r.get('shadow_direction')} "
            f"| {r.get('actual_direction')} | {r.get('overlay_applied')} | {r.get('routing_path')} "
            f"| {r.get('baseline_hit')} | {r.get('shadow_hit')} | {r.get('delta_hit_vs_baseline_row')} |"
        )
    lines.extend(["", "## Operator lines", ""])
    for op in out.get("operator_lines") or []:
        lines.append(f"- {op}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fold-json", type=Path, default=DEFAULT_FOLD)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--fold-index", type=int, default=None, help="Default: auto worst delta fold.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON_OUT)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD_OUT)
    ap.add_argument("--logos-lens-json", type=Path, default=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json")
    ap.add_argument("--hypothesis-json", type=Path, default=ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    ap.add_argument("--logos-mapping-json", type=Path, default=ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json")
    ap.add_argument("--corpus-baseline-json", type=Path, default=ROOT / "docs/final/artifacts/corpus_counting_baseline_comparison_v1_latest.json")
    ap.add_argument("--conflict-max", type=float, default=0.35)
    ap.add_argument("--logos-confidence-min", type=float, default=0.15)
    ap.add_argument(
        "--routing-policy",
        choices=("v2", "v2c"),
        default="v2c",
        help="Overlay routing policy for per-date drill rows.",
    )
    args = ap.parse_args()

    feat_mod = _load("btrack_31k41k_shadow_features_v1", "scripts/btrack_31k41k_shadow_features_v1.py")
    fold_doc = _read(args.fold_json)
    folds = fold_doc.get("folds") if isinstance(fold_doc.get("folds"), list) else []
    if not folds:
        raise SystemExit(f"missing folds in {args.fold_json}")

    if args.fold_index is not None:
        worst = next((f for f in folds if isinstance(f, dict) and f.get("fold_index") == args.fold_index), None)
        if worst is None:
            raise SystemExit(f"fold_index {args.fold_index} not found")
    else:
        worst = min(
            (f for f in folds if isinstance(f, dict)),
            key=lambda f: float(f.get("delta_hit_rate") or 0),
        )

    test_dates = [str(d)[:10] for d in (worst.get("test_dates") or [])]
    score_doc = _read(args.score_json)
    rows = feat_mod.btc_score_rows(score_doc)
    features = feat_mod.compute_all_features(
        logos_mapping_path=args.logos_mapping_json,
        logos_lens_path=args.logos_lens_json,
        hypothesis_path=args.hypothesis_json,
        corpus_baseline_path=args.corpus_baseline_json,
    )
    logos_lens = _read(args.logos_lens_json)
    hypothesis = _read(args.hypothesis_json)
    logos_dir, logos_conf = feat_mod.logos_lens_direction(logos_lens)
    ensemble_dir = str((hypothesis.get("prediction") or {}).get("direction") or "neutral")

    def _fv(key: str, default: float) -> float:
        raw = (features.get(key) or {}).get("value")
        if raw is None:
            return default
        try:
            return float(raw)
        except (TypeError, ValueError):
            return default

    conflict_val = _fv("anchor_conflict_ratio_v1", 1.0)
    density_val = _fv("logos_anchor_density_31k_v1", 0.0)

    per_date: list[dict[str, Any]] = []
    for row in rows:
        ed = str(row.get("eval_date"))[:10]
        if ed not in test_dates:
            continue
        detail = feat_mod.overlay_decision_detail(
            row,
            ensemble_dir=ensemble_dir,
            logos_dir=logos_dir,
            logos_conf=logos_conf,
            conflict_val=conflict_val,
            density_val=density_val,
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
            routing_policy=args.routing_policy,
        )
        try:
            dr = float(row.get("daily_return") or 0)
        except (TypeError, ValueError):
            dr = 0.0
        detail["daily_return"] = dr
        per_date.append(detail)

    per_date.sort(key=lambda r: str(r.get("eval_date")))
    hurt_rows = [r for r in per_date if int(r.get("delta_hit_vs_baseline_row") or 0) < 0]
    helped_rows = [r for r in per_date if int(r.get("delta_hit_vs_baseline_row") or 0) > 0]

    out = {
        "schema": "btrack_31k41k_prophecy_shadow_fold_drill_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "non_gating": True,
        "inputs": {
            "fold_json": str(args.fold_json),
            "score_json": str(args.score_json),
            "fold_index_selected": worst.get("fold_index"),
        },
        "worst_fold_index": worst.get("fold_index"),
        "worst_fold_delta": worst.get("delta_hit_rate"),
        "worst_fold_test_dates": test_dates,
        "global_context": {
            "logos_direction": logos_dir,
            "ensemble_direction": ensemble_dir,
            "feature_summary": {k: (v.get("value") if isinstance(v, dict) else v) for k, v in features.items()},
        },
        "per_date_rows": per_date,
        "diagnosis": {
            "rows_hurt_count": len(hurt_rows),
            "rows_helped_count": len(helped_rows),
            "ensemble_align_applied_count": sum(
                1 for r in per_date if r.get("routing_path") == "align_ensemble_direction" and r.get("overlay_applied")
            ),
            "move_align_applied_count": sum(
                1 for r in per_date if r.get("routing_path") == "align_daily_move_sign" and r.get("overlay_applied")
            ),
            "primary_hypothesis": (
                "worst_fold_loss driven by ensemble_align bear overlay on days baseline was correct"
                if logos_dir == "bear"
                else "worst_fold_loss driven by overlay routing mismatch vs baseline"
            ),
        },
        "operator_lines": [
            "[MKM-31K41K-FOLD-DRILL]",
            f"[HYPO] research_only — fold drill overlay routing_policy={args.routing_policy}",
            f"- worst_fold={worst.get('fold_index')} delta={worst.get('delta_hit_rate')} hurt_rows={len(hurt_rows)}",
        ],
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(_render_md(out), encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"WROTE: {args.out_md}")
    print(f"worst_fold={worst.get('fold_index')} hurt_rows={len(hurt_rows)} helped_rows={len(helped_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
