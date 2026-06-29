#!/usr/bin/env python3
"""Per-row routing A/B: overlay v2 vs v2c on same B-track shadow score panel (research-only)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCORE = ROOT / "docs/final/artifacts/btrack_prophecy_score_kpi_b_shadow_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_31k41k_v2_v2c_routing_ab_v1_latest.json"


def _load_features():
    path = ROOT / "scripts" / "btrack_31k41k_shadow_features_v1.py"
    spec = importlib.util.spec_from_file_location("btrack_31k41k_shadow_features_v1", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules["btrack_31k41k_shadow_features_v1"] = mod
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_paths(details: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for d in details:
        c[str(d.get("routing_path") or "none")] += 1
    return dict(sorted(c.items(), key=lambda x: (-x[1], x[0])))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--conflict-max", type=float, default=0.35)
    ap.add_argument("--logos-confidence-min", type=float, default=0.15)
    args = ap.parse_args()

    feat = _load_features()
    score_doc = _read(args.score_json)
    rows = feat.btc_score_rows(score_doc)
    if not rows:
        raise SystemExit(f"no score rows in {args.score_json}")

    logos_lens = _read(ROOT / "docs/final/artifacts/logos_independent_lens_latest.json")
    hypothesis = _read(ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json")
    features = feat.compute_all_features(
        logos_mapping_path=ROOT / "docs/final/artifacts/LOGOS_STATE_MAPPING_V1.json",
        logos_lens_path=ROOT / "docs/final/artifacts/logos_independent_lens_latest.json",
        hypothesis_path=ROOT / "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
        corpus_baseline_path=ROOT / "docs/final/artifacts/corpus_counting_baseline_comparison_v1_latest.json",
    )
    logos_dir, logos_conf = feat.logos_lens_direction(logos_lens)
    ensemble_dir = str((hypothesis.get("prediction") or {}).get("direction") or "neutral")

    def _fv(key: str, default: float) -> float:
        raw = (features.get(key) or {}).get("value")
        try:
            return float(raw) if raw is not None else default
        except (TypeError, ValueError):
            return default

    conflict_val = _fv("anchor_conflict_ratio_v1", 1.0)
    density_val = _fv("logos_anchor_density_31k_v1", 0.0)

    v2_details: list[dict[str, Any]] = []
    v2c_details: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []

    for row in rows:
        d2 = feat.overlay_decision_detail(
            row,
            ensemble_dir=ensemble_dir,
            logos_dir=logos_dir,
            logos_conf=logos_conf,
            conflict_val=conflict_val,
            density_val=density_val,
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
            routing_policy="v2",
        )
        d2c = feat.overlay_decision_detail(
            row,
            ensemble_dir=ensemble_dir,
            logos_dir=logos_dir,
            logos_conf=logos_conf,
            conflict_val=conflict_val,
            density_val=density_val,
            conflict_max=float(args.conflict_max),
            logos_confidence_min=float(args.logos_confidence_min),
            routing_policy="v2c",
        )
        v2_details.append(d2)
        v2c_details.append(d2c)
        if (
            d2.get("overlay_applied") != d2c.get("overlay_applied")
            or d2.get("shadow_direction") != d2c.get("shadow_direction")
            or d2.get("routing_path") != d2c.get("routing_path")
        ):
            disagreements.append(
                {
                    "eval_date": d2.get("eval_date"),
                    "baseline_direction": d2.get("baseline_direction"),
                    "v2": {
                        "routing_path": d2.get("routing_path"),
                        "overlay_applied": d2.get("overlay_applied"),
                        "shadow_direction": d2.get("shadow_direction"),
                        "delta_hit": d2.get("delta_hit_vs_baseline_row"),
                    },
                    "v2c": {
                        "routing_path": d2c.get("routing_path"),
                        "overlay_applied": d2c.get("overlay_applied"),
                        "shadow_direction": d2c.get("shadow_direction"),
                        "delta_hit": d2c.get("delta_hit_vs_baseline_row"),
                    },
                }
            )

    def _panel_stats(details: list[dict[str, Any]], policy: str) -> dict[str, Any]:
        n = len(details)
        applied = sum(1 for d in details if d.get("overlay_applied"))
        base_hits = sum(1 for d in details if d.get("baseline_hit"))
        shadow_hits = sum(1 for d in details if d.get("shadow_hit"))
        return {
            "routing_policy": policy,
            "n_rows": n,
            "overlay_applied_count": applied,
            "overlay_applied_fraction": round(applied / n, 6) if n else 0.0,
            "baseline_hits": base_hits,
            "shadow_hits": shadow_hits,
            "baseline_hit_rate": round(base_hits / n, 6) if n else 0.0,
            "shadow_hit_rate": round(shadow_hits / n, 6) if n else 0.0,
            "delta_hit_rate": round((shadow_hits - base_hits) / n, 6) if n else 0.0,
            "routing_path_counts": _count_paths(details),
        }

    v2_stats = _panel_stats(v2_details, "v2")
    v2c_stats = _panel_stats(v2c_details, "v2c")

    out = {
        "schema": "btrack_31k41k_v2_v2c_routing_ab_v1",
        "generated_at_utc": _iso_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "inputs": {
            "score_json": str(args.score_json.relative_to(ROOT))
            if args.score_json.is_relative_to(ROOT)
            else str(args.score_json),
            "conflict_max": float(args.conflict_max),
            "logos_confidence_min": float(args.logos_confidence_min),
            "logos_direction": logos_dir,
            "ensemble_direction": ensemble_dir,
        },
        "v2": v2_stats,
        "v2c": v2c_stats,
        "ab_summary": {
            "disagreement_row_count": len(disagreements),
            "disagreement_fraction": round(len(disagreements) / len(rows), 6) if rows else 0.0,
            "pooled_hit_rate_delta_v2c_minus_v2": round(
                v2c_stats["shadow_hit_rate"] - v2_stats["shadow_hit_rate"], 6
            ),
            "overlay_fraction_delta_v2c_minus_v2": round(
                v2c_stats["overlay_applied_fraction"] - v2_stats["overlay_applied_fraction"],
                6,
            ),
            "v2_only_ensemble_align_rows": v2_stats["routing_path_counts"].get(
                "align_ensemble_direction", 0
            )
            - v2c_stats["routing_path_counts"].get("align_ensemble_direction", 0),
            "v2c_ensemble_skipped_rows": v2c_stats["routing_path_counts"].get(
                "ensemble_skipped_move_matches_baseline", 0
            ),
        },
        "disagreement_rows": disagreements,
        "operator_lines": [
            "[MKM-31K41K-ROUTING-AB]",
            "[HYPO] research_only — v2 allows ensemble_align when move!=baseline gate off; v2c skips ensemble when move_sign==baseline",
            f"- disagreement_rows={len(disagreements)}/{len(rows)}",
        ],
        "track_wall": "No Track A / live / Track C ingress product claims",
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(
        f"v2 hit={v2_stats['shadow_hit_rate']:.4f} apply={v2_stats['overlay_applied_fraction']:.4f} "
        f"v2c hit={v2c_stats['shadow_hit_rate']:.4f} apply={v2c_stats['overlay_applied_fraction']:.4f} "
        f"disagreements={len(disagreements)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
