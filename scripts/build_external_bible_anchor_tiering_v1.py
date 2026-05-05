#!/usr/bin/env python3
"""Build anchor tiering/action policy from external baseline comparison index."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_INDEX = ART / "external_bible_crossref_latest_index.json"
DEFAULT_OUT = ART / "external_bible_anchor_tiering_latest.json"


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


def _resolve_path(path_like: Any) -> Path | None:
    if not path_like:
        return None
    p = Path(str(path_like))
    if p.is_absolute():
        return p
    return ROOT / p


def _tier_for_row(
    row: dict[str, Any],
    *,
    min_precision_t1: float,
    min_delta_t1: float,
    min_precision_t2: float,
    min_delta_t2: float,
) -> str:
    p = float(row.get("precision_at_k") or 0.0)
    d = float(row.get("delta_random_baseline") or 0.0)
    if p >= min_precision_t1 and d >= min_delta_t1:
        return "tier1_high_confidence"
    if p >= min_precision_t2 and d >= min_delta_t2:
        return "tier2_exploration"
    return "tier3_monitor_only"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index-json", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--min-precision-tier1", type=float, default=0.07)
    ap.add_argument("--min-delta-tier1", type=float, default=0.005)
    ap.add_argument("--min-precision-tier2", type=float, default=0.02)
    ap.add_argument("--min-delta-tier2", type=float, default=0.001)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    idx = _read_json(args.index_json)
    artifacts = idx.get("artifacts") if isinstance(idx.get("artifacts"), dict) else {}

    comparison_path = _resolve_path(artifacts.get("comparison"))
    queue_path = _resolve_path(artifacts.get("human_review_queue"))
    resolution_path = _resolve_path(artifacts.get("human_review_resolution"))
    apply_gate_path = _resolve_path(artifacts.get("threshold_apply_gate"))
    apply_approval_path = _resolve_path(artifacts.get("threshold_apply_approval"))

    comparison = _read_json(comparison_path) if comparison_path else {}
    queue = _read_json(queue_path) if queue_path else {}
    resolution = _read_json(resolution_path) if resolution_path else {}
    apply_gate = _read_json(apply_gate_path) if apply_gate_path else {}
    apply_approval = _read_json(apply_approval_path) if apply_approval_path else {}

    rows = comparison.get("rows") if isinstance(comparison.get("rows"), list) else []
    tiered: list[dict[str, Any]] = []
    tier_counts = {
        "tier1_high_confidence": 0,
        "tier2_exploration": 0,
        "tier3_monitor_only": 0,
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        tier = _tier_for_row(
            row,
            min_precision_t1=float(args.min_precision_tier1),
            min_delta_t1=float(args.min_delta_tier1),
            min_precision_t2=float(args.min_precision_tier2),
            min_delta_t2=float(args.min_delta_tier2),
        )
        tier_counts[tier] += 1
        tiered.append(
            {
                "label": row.get("label"),
                "precision_at_k": row.get("precision_at_k"),
                "delta_random_baseline": row.get("delta_random_baseline"),
                "coverage_overlap": row.get("coverage_overlap"),
                "threshold_label": row.get("threshold_label"),
                "tier": tier,
            }
        )

    core100_pass = bool(((_read_json(ART / "core100_node_ref_map_quality_gate_latest.json")).get("gate") or {}).get("pass"))
    queue_included = bool(queue.get("included"))
    queue_open = str(queue.get("status") or "").lower() in {"open", "in_review"}
    resolution_completed = str(resolution.get("resolution_state") or "").lower() == "completed"
    apply_gate_ok = str(apply_gate.get("decision") or "").upper() in {"GO_APPLY", "PASS", "APPROVED"}
    apply_approval_ok = str(apply_approval.get("status") or "").upper() in {"APPROVED", "PASS"}

    # Conservative adoption policy:
    # - T1 candidate exists
    # - core100 quality pass
    # - no pending queue
    # - resolution completed
    # - apply gate + approval present
    t1_exists = tier_counts["tier1_high_confidence"] > 0
    adopt_ready = all([t1_exists, core100_pass, (not queue_open), resolution_completed, apply_gate_ok, apply_approval_ok])
    action = "adopt_limited" if adopt_ready else ("monitor_only" if tier_counts["tier2_exploration"] > 0 else "hold")

    out = {
        "schema": "external_bible_anchor_tiering_v1",
        "generated_at_utc": _iso_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "index_json": str(args.index_json).replace("\\", "/"),
            "comparison_json": str(comparison_path).replace("\\", "/") if comparison_path else "",
            "queue_json": str(queue_path).replace("\\", "/") if queue_path else "",
            "resolution_json": str(resolution_path).replace("\\", "/") if resolution_path else "",
            "apply_gate_json": str(apply_gate_path).replace("\\", "/") if apply_gate_path else "",
            "apply_approval_json": str(apply_approval_path).replace("\\", "/") if apply_approval_path else "",
        },
        "tier_counts": tier_counts,
        "tier_rows": tiered,
        "gates": {
            "core100_quality_pass": core100_pass,
            "queue_included": queue_included,
            "queue_open": queue_open,
            "resolution_completed": resolution_completed,
            "apply_gate_ok": apply_gate_ok,
            "apply_approval_ok": apply_approval_ok,
            "tier1_exists": t1_exists,
        },
        "decision": action.upper(),
        "policy_action": action,
        "notes": [
            "Large anchor graph is used as hypothesis pool, not direct production truth.",
            "Adoption requires human-approved and gate-complete evidence chain.",
        ],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json).replace("\\", "/"),
                "policy_action": action,
                "tier_counts": tier_counts,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
