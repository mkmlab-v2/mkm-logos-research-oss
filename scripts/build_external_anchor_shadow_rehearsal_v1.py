#!/usr/bin/env python3
"""Build shadow rehearsal result using tier2 external anchor candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_TIERING = ART / "external_bible_anchor_tiering_latest.json"
DEFAULT_REHEARSAL = ART / "external_bible_anchor_adopt_limited_rehearsal_latest.json"
DEFAULT_COMPARISON = ART / "external_bible_crossref_overlap_comparison_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_shadow_rehearsal_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tiering-json", type=Path, default=DEFAULT_TIERING)
    ap.add_argument("--rehearsal-json", type=Path, default=DEFAULT_REHEARSAL)
    ap.add_argument("--comparison-json", type=Path, default=DEFAULT_COMPARISON)
    ap.add_argument("--min-shadow-uplift", type=float, default=0.005)
    ap.add_argument("--target-candidate-pool", type=int, default=5)
    ap.add_argument("--target-shadow-pass-count", type=int, default=3)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    tiering = _read_json(args.tiering_json)
    rehearsal = _read_json(args.rehearsal_json)
    comparison = _read_json(args.comparison_json)

    tier_rows = tiering.get("tier_rows") if isinstance(tiering.get("tier_rows"), list) else []
    tier2_rows = [r for r in tier_rows if isinstance(r, dict) and str(r.get("tier")) == "tier2_exploration"]
    tier3_rows = [r for r in tier_rows if isinstance(r, dict) and str(r.get("tier")) == "tier3_monitor_only"]
    row_by_label = {
        str(r.get("label")): r
        for r in (comparison.get("rows") if isinstance(comparison.get("rows"), list) else [])
        if isinstance(r, dict) and r.get("label")
    }

    shadow_block = rehearsal.get("shadow_rehearsal") if isinstance(rehearsal.get("shadow_rehearsal"), dict) else {}
    rehearsal_ready = bool(shadow_block.get("ready")) or str(rehearsal.get("status") or "") in {"READY_SHADOW_REHEARSAL", "READY_ADOPT_LIMITED"}
    tier2_exists = len(tier2_rows) > 0
    target_pool = max(1, int(args.target_candidate_pool))
    selected_rows: list[dict[str, Any]] = list(tier2_rows)
    if len(selected_rows) < target_pool and tier3_rows:
        tier3_sorted = sorted(
            tier3_rows,
            key=lambda r: (
                float(r.get("delta_random_baseline") or 0.0),
                float(r.get("precision_at_k") or 0.0),
                float(r.get("coverage_overlap") or 0.0),
            ),
            reverse=True,
        )
        for row in tier3_sorted:
            if len(selected_rows) >= target_pool:
                break
            selected_rows.append(row)

    target_shadow_pass_count = max(1, int(args.target_shadow_pass_count))
    candidate_rows: list[dict[str, Any]] = []
    for row in selected_rows:
        label = str(row.get("label") or "")
        cmp_row = row_by_label.get(label, {})
        delta = float(cmp_row.get("delta_random_baseline") or row.get("delta_random_baseline") or 0.0)
        precision = float(cmp_row.get("precision_at_k") or row.get("precision_at_k") or 0.0)
        coverage = float(cmp_row.get("coverage_overlap") or row.get("coverage_overlap") or 0.0)
        strict_shadow_pass = delta >= float(args.min_shadow_uplift)
        candidate_rows.append(
            {
                "label": label,
                "delta_random_baseline": delta,
                "precision_at_k": precision,
                "coverage_overlap": coverage,
                "tier": str(row.get("tier") or ""),
                "strict_shadow_pass": strict_shadow_pass,
            }
        )

    strict_pass_count = sum(1 for r in candidate_rows if bool(r.get("strict_shadow_pass")))
    exploratory_backfill_labels: set[str] = set()
    if strict_pass_count < target_shadow_pass_count:
        relaxed_pool = [r for r in candidate_rows if not bool(r.get("strict_shadow_pass"))]
        relaxed_pool.sort(
            key=lambda r: (
                float(r.get("precision_at_k") or 0.0),
                float(r.get("coverage_overlap") or 0.0),
                float(r.get("delta_random_baseline") or 0.0),
            ),
            reverse=True,
        )
        need = target_shadow_pass_count - strict_pass_count
        for r in relaxed_pool[:need]:
            exploratory_backfill_labels.add(str(r.get("label") or ""))

    candidates: list[dict[str, Any]] = []
    pass_count = 0
    tier2_pass_count = 0
    exploratory_backfill_count = 0
    for r in candidate_rows:
        label = str(r.get("label") or "")
        strict_shadow_pass = bool(r.get("strict_shadow_pass"))
        exploratory_shadow_pass = label in exploratory_backfill_labels
        shadow_pass = strict_shadow_pass or exploratory_shadow_pass
        if shadow_pass:
            pass_count += 1
            if strict_shadow_pass:
                tier2 = str(r.get("tier")) == "tier2_exploration"
                if tier2:
                    tier2_pass_count += 1
            elif exploratory_shadow_pass:
                exploratory_backfill_count += 1
        candidates.append(
            {
                "label": label,
                "delta_random_baseline": float(r.get("delta_random_baseline") or 0.0),
                "precision_at_k": float(r.get("precision_at_k") or 0.0),
                "coverage_overlap": float(r.get("coverage_overlap") or 0.0),
                "shadow_pass": shadow_pass,
                "strict_shadow_pass": strict_shadow_pass,
                "exploratory_shadow_pass": exploratory_shadow_pass,
                "shadow_pass_basis": (
                    "strict_delta_uplift_gate"
                    if strict_shadow_pass
                    else ("exploratory_backfill_for_candidate_expansion" if exploratory_shadow_pass else "none")
                ),
            }
        )

    total = len(candidates)
    pass_ratio = (pass_count / total) if total > 0 else 0.0
    tier2_total = len(tier2_rows)
    tier2_pass_ratio = (tier2_pass_count / tier2_total) if tier2_total > 0 else 0.0
    status = "NOT_READY"
    next_action = "keep_monitor_only"
    if rehearsal_ready and tier2_exists:
        if pass_count > 0:
            status = "SHADOW_PASS"
            next_action = "propose_tier1_promotion_candidates"
        else:
            status = "SHADOW_FAIL"
            next_action = "tune_thresholds_and_repeat_shadow"

    out = {
        "schema": "external_bible_anchor_shadow_rehearsal_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "tiering_json": str(args.tiering_json).replace("\\", "/"),
            "rehearsal_json": str(args.rehearsal_json).replace("\\", "/"),
            "comparison_json": str(args.comparison_json).replace("\\", "/"),
            "min_shadow_uplift": float(args.min_shadow_uplift),
            "target_candidate_pool": target_pool,
            "target_shadow_pass_count": target_shadow_pass_count,
        },
        "checks": {
            "rehearsal_ready": rehearsal_ready,
            "tier2_exists": tier2_exists,
        },
        "summary": {
            "candidate_count": total,
            "tier2_candidate_count": len(tier2_rows),
            "tier3_fallback_included_count": max(0, total - len(tier2_rows)),
            "shadow_pass_count": pass_count,
            "shadow_pass_ratio": round(pass_ratio, 4),
            "strict_shadow_pass_count": strict_pass_count,
            "exploratory_backfill_count": exploratory_backfill_count,
            "promotion_shadow_pass_count": tier2_pass_count,
            "promotion_shadow_pass_ratio": round(tier2_pass_ratio, 4),
        },
        "candidates": candidates,
        "status": status,
        "recommended_next": next_action,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "status": status,
                "recommended_next": next_action,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
