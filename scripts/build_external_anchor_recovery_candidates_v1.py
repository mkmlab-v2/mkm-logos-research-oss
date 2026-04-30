#!/usr/bin/env python3
"""Build recovery candidate proposal when sustain gate triggers downgrade."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SUSTAIN = ART / "external_bible_anchor_promotion_sustain_gate_latest.json"
DEFAULT_SHADOW = ART / "external_bible_anchor_shadow_rehearsal_latest.json"
DEFAULT_CURRENT = ART / "external_bible_anchor_tier1_promotion_candidates_latest.json"
DEFAULT_OUT = ART / "external_bible_anchor_recovery_candidates_latest.json"


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
    ap.add_argument("--sustain-json", type=Path, default=DEFAULT_SUSTAIN)
    ap.add_argument("--shadow-json", type=Path, default=DEFAULT_SHADOW)
    ap.add_argument("--current-candidates-json", type=Path, default=DEFAULT_CURRENT)
    ap.add_argument("--target-candidates", type=int, default=3)
    ap.add_argument("--max-overlap-with-current", type=int, default=1)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    sustain = _read_json(args.sustain_json)
    shadow = _read_json(args.shadow_json)
    current = _read_json(args.current_candidates_json)

    sustain_status = str(sustain.get("status") or "")
    triggered = sustain_status == "DOWNGRADE_TRIGGER"

    shadow_candidates = shadow.get("candidates") if isinstance(shadow.get("candidates"), list) else []
    current_candidates = current.get("promotion_candidates") if isinstance(current.get("promotion_candidates"), list) else []
    current_labels = {str(r.get("label") or "") for r in current_candidates if isinstance(r, dict)}
    target = max(1, int(args.target_candidates))
    max_overlap = max(0, int(args.max_overlap_with_current))

    proposed: list[dict[str, Any]] = []
    if triggered:
        pool = [r for r in shadow_candidates if isinstance(r, dict)]
        pool.sort(
            key=lambda r: (
                1 if bool(r.get("strict_shadow_pass")) else 0,
                float(r.get("delta_random_baseline") or 0.0),
                float(r.get("precision_at_k") or 0.0),
                float(r.get("coverage_overlap") or 0.0),
            ),
            reverse=True,
        )
        unseen: list[dict[str, Any]] = []
        overlapping: list[dict[str, Any]] = []
        for row in pool:
            label = str(row.get("label") or "")
            if not label:
                continue
            if label in current_labels:
                overlapping.append(row)
            else:
                unseen.append(row)

        selected_rows: list[dict[str, Any]] = []
        for row in unseen:
            if len(selected_rows) >= target:
                break
            selected_rows.append(row)

        overlap_used = 0
        if len(selected_rows) < target and overlapping:
            for row in overlapping:
                if len(selected_rows) >= target:
                    break
                if overlap_used >= max_overlap:
                    break
                selected_rows.append(row)
                overlap_used += 1

        if len(selected_rows) < target and overlapping:
            for row in overlapping:
                if len(selected_rows) >= target:
                    break
                if row in selected_rows:
                    continue
                selected_rows.append(row)

        for row in selected_rows:
            label = str(row.get("label") or "")
            proposed.append(
                {
                    "label": label,
                    "delta_random_baseline": float(row.get("delta_random_baseline") or 0.0),
                    "precision_at_k": float(row.get("precision_at_k") or 0.0),
                    "coverage_overlap": float(row.get("coverage_overlap") or 0.0),
                    "was_in_current_candidates": label in current_labels,
                    "recovery_basis": (
                        "strict_shadow_pass_priority" if bool(row.get("strict_shadow_pass")) else "exploratory_shadow_backfill"
                    ),
                }
            )

    status = "RECOVERY_READY_FOR_REVIEW" if triggered and len(proposed) > 0 else ("NOT_TRIGGERED" if not triggered else "RECOVERY_EMPTY")
    out = {
        "schema": "external_bible_anchor_recovery_candidates_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "sustain_json": str(args.sustain_json).replace("\\", "/"),
            "shadow_json": str(args.shadow_json).replace("\\", "/"),
            "current_candidates_json": str(args.current_candidates_json).replace("\\", "/"),
        },
        "checks": {
            "downgrade_triggered": triggered,
            "candidate_count_gt_zero": len(proposed) > 0,
        },
        "target_candidates": target,
        "max_overlap_with_current": max_overlap,
        "recovery_candidates": proposed,
        "status": status,
        "recommended_next": (
            "request_recovery_manual_signoff" if status == "RECOVERY_READY_FOR_REVIEW" else "keep_current_policy_cycle"
        ),
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "candidate_count": len(proposed), "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
