#!/usr/bin/env python3
"""Apply commander sign-off for Logos candidate-edge lane ([HYPO] B-track staging).

Writes operational signoff JSON under docs/final/artifacts/ — does not overwrite fixtures.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

LANE_OUT: dict[str, str] = {
    "ann_lite": "docs/final/artifacts/logos_candidate_edge_promotion_signoff_ann_lite_v1_latest.json",
    "offline_4d_knn": "docs/final/artifacts/logos_candidate_edge_promotion_signoff_v1_latest.json",
}

FIXTURE_FALLBACK: dict[str, str] = {
    "ann_lite": "docs/final/fixtures/logos_candidate_edge_promotion_signoff_ann_lite_v1.example.json",
    "offline_4d_knn": "docs/final/fixtures/logos_candidate_edge_promotion_signoff_v1.example.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane-id", choices=sorted(LANE_OUT.keys()), default="ann_lite")
    ap.add_argument("--approver", default="commander_auto_staging")
    ap.add_argument("--approved", action="store_true", default=True)
    ap.add_argument("--no-approved", action="store_false", dest="approved")
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument(
        "--saturation-warning-acknowledged",
        action="store_true",
        help="Required for offline_4d_knn when quality report has saturation_warning",
    )
    args = ap.parse_args()

    lane = str(args.lane_id)
    out_rel = LANE_OUT[lane]
    out_path = args.output_json if args.output_json else ROOT / out_rel
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    base = _read_json(ROOT / FIXTURE_FALLBACK[lane])
    if base.get("schema") != "logos_candidate_edge_promotion_signoff_v1":
        base = {
            "schema": "logos_candidate_edge_promotion_signoff_v1",
            "version": "1.0.0",
            "lane_id": lane,
            "expires_at_utc": "2027-12-31T23:59:59Z",
            "lora_prune_pending_acknowledged": True,
        }

    doc: dict[str, Any] = {
        **base,
        "schema": "logos_candidate_edge_promotion_signoff_v1",
        "version": "1.0.0",
        "lane_id": lane,
        "approved": bool(args.approved),
        "approver": str(args.approver) if args.approved else "",
        "approved_at_utc": _utc_now() if args.approved else None,
        "expires_at_utc": base.get("expires_at_utc") or "2027-12-31T23:59:59Z",
        "lora_prune_pending_acknowledged": True,
        "saturation_warning_acknowledged": bool(
            args.saturation_warning_acknowledged or base.get("saturation_warning_acknowledged")
        ),
        "notes_ko": (
            f"B-track staging auto signoff lane={lane}; pending JSONL only — canonical merge 별도 플래그."
        ),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0 if args.approved else 2


if __name__ == "__main__":
    raise SystemExit(main())
