#!/usr/bin/env python3
"""Refresh offline_4d strict LoRA micro-batch (top-N queue ranks, no bulk merge). [HYPO] B-track."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_candidate_edge_offline_4d_lora_strict_batch_v1_latest.json"
DEFAULT_FILTERED = ROOT / "docs/final/artifacts/logos_review_queue_offline_4d_strict_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--max-batch-size", type=int, default=5)
    ap.add_argument(
        "--pending-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip rows with review_decision already set (default: true)",
    )
    ap.add_argument("--output-batch-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--output-filtered-json", type=Path, default=DEFAULT_FILTERED)
    args = ap.parse_args()

    queue_path = args.queue_json if args.queue_json.is_absolute() else ROOT / args.queue_json
    doc = _read_json(queue_path)
    offline_all = [
        i
        for i in doc.get("items") or []
        if isinstance(i, dict) and i.get("lane_id") == "offline_4d_knn"
    ]
    if args.pending_only:
        offline_all = [i for i in offline_all if not i.get("review_decision")]
    offline = offline_all[: max(1, int(args.max_batch_size))]

    batch = {
        "schema": "logos_candidate_edge_offline_4d_lora_strict_batch_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "bulk_merge_blocked": True,
        "pending_only": bool(args.pending_only),
        "max_batch_size": int(args.max_batch_size),
        "lora_strict_only": True,
        "items": [
            {
                "queue_rank": i.get("queue_rank"),
                "pair_key": i.get("pair_key"),
                "similarity": i.get("similarity"),
            }
            for i in offline
        ],
        "recommended_next_ko": [
            "LoRA micro-train strict 소배치만 — promote/canonical merge 금지",
            "500 bulk auto-approve 금지 (saturation lane)",
        ],
    }
    filtered = {
        "schema": "logos_review_queue_offline_4d_strict_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "items": offline,
        "stats": {"selected_count": len(offline)},
    }

    out_batch = args.output_batch_json if args.output_batch_json.is_absolute() else ROOT / args.output_batch_json
    out_filt = args.output_filtered_json if args.output_filtered_json.is_absolute() else ROOT / args.output_filtered_json
    out_batch.parent.mkdir(parents=True, exist_ok=True)
    out_filt.parent.mkdir(parents=True, exist_ok=True)
    out_batch.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_filt.write_text(json.dumps(filtered, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "batch": str(out_batch), "filtered": str(out_filt), "items": len(offline)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
