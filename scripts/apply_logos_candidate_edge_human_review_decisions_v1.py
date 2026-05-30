#!/usr/bin/env python3
"""Apply human review decisions on Logos candidate-edge queue ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_queue_ranks(raw: str | None) -> set[int] | None:
    if not raw or not str(raw).strip():
        return None
    out: set[int] = set()
    for part in str(raw).split(","):
        part = part.strip()
        if part:
            out.add(int(part))
    return out or None


def _item_matches(
    item: dict[str, Any],
    *,
    queue_ranks: set[int] | None,
    auto_ann_lite: bool,
    auto_offline_4d: bool,
) -> bool:
    if queue_ranks is not None:
        try:
            rank = int(item.get("queue_rank"))
        except (TypeError, ValueError):
            return False
        return rank in queue_ranks
    if auto_ann_lite:
        return item.get("lane_id") == "ann_lite" and item.get("priority") == "primary"
    if auto_offline_4d:
        return item.get("lane_id") == "offline_4d_knn" and item.get("priority") == "secondary_4d_only"
    return False


def apply_decisions(
    doc: dict[str, Any],
    *,
    queue_ranks: set[int] | None,
    auto_ann_lite: bool,
    auto_offline_4d: bool,
    decision: str,
    reviewer: str,
) -> tuple[int, list[dict[str, Any]]]:
    items = list(doc.get("items") or [])
    updated = 0
    touched: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if not _item_matches(
            item,
            queue_ranks=queue_ranks,
            auto_ann_lite=auto_ann_lite,
            auto_offline_4d=auto_offline_4d,
        ):
            continue
        item["review_decision"] = decision
        item["review_status"] = "approved" if decision == "approve" else decision
        item["review_notes_ko"] = f"auto:{reviewer}@{_utc_now()}"
        updated += 1
        touched.append(
            {
                "queue_rank": item.get("queue_rank"),
                "pair_key": item.get("pair_key"),
                "review_decision": decision,
            }
        )

    stats = dict(doc.get("stats") or {})
    approved = sum(1 for i in items if i.get("review_decision") == "approve")
    rejected = sum(1 for i in items if i.get("review_decision") == "reject")
    deferred = sum(1 for i in items if i.get("review_decision") == "defer")
    stats.update(
        {
            "pending_count": sum(1 for i in items if not i.get("review_decision")),
            "approved_count": approved,
            "rejected_count": rejected,
            "deferred_count": deferred,
        }
    )
    doc["stats"] = stats
    doc["last_review_applied_at_utc"] = _utc_now()
    doc["last_reviewer"] = reviewer
    return updated, touched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Write result here; source queue unchanged when set",
    )
    ap.add_argument(
        "--queue-ranks",
        default="",
        help="Comma-separated queue_rank filter (e.g. 1,2,3,4,5)",
    )
    ap.add_argument(
        "--auto-approve-ann-lite-primary",
        action="store_true",
        help="Set review_decision=approve for ann_lite + priority=primary rows",
    )
    ap.add_argument(
        "--auto-approve-offline-4d-only",
        action="store_true",
        help="Set review_decision=approve for offline_4d_knn + priority=secondary_4d_only rows",
    )
    ap.add_argument("--decision", choices=("approve", "reject", "defer"), default="approve")
    ap.add_argument("--reviewer", default="commander_auto_staging")
    ap.add_argument("--dry-run", action="store_true", help="Preview only; no file write")
    args = ap.parse_args()

    src = args.queue_json if args.queue_json.is_absolute() else ROOT / args.queue_json
    if not src.is_file():
        print(f"Missing queue: {src}", file=sys.stderr)
        return 2

    queue_ranks = _parse_queue_ranks(args.queue_ranks)
    if queue_ranks is None and not args.auto_approve_ann_lite_primary and not args.auto_approve_offline_4d_only:
        print("Specify --queue-ranks and/or --auto-approve-* filter", file=sys.stderr)
        return 2

    doc = json.loads(src.read_text(encoding="utf-8-sig"))
    if not doc.get("items"):
        print("empty queue", file=sys.stderr)
        return 2

    updated, touched = apply_decisions(
        doc,
        queue_ranks=queue_ranks,
        auto_ann_lite=args.auto_approve_ann_lite_primary,
        auto_offline_4d=args.auto_approve_offline_4d_only,
        decision=args.decision,
        reviewer=args.reviewer,
    )

    out_path = src
    if args.out_json:
        out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    if doc.get("items") and args.out_json:
        doc.setdefault("staging_meta", {})
        if isinstance(doc["staging_meta"], dict):
            doc["staging_meta"].update(
                {
                    "source_queue": str(src.relative_to(ROOT)).replace("\\", "/"),
                    "staging_copy": True,
                    "dry_run": bool(args.dry_run),
                }
            )

    payload = {
        "ok": updated > 0,
        "dry_run": args.dry_run,
        "updated": updated,
        "approved_count": doc.get("stats", {}).get("approved_count"),
        "touched": touched,
        "source": str(src),
        "path": str(out_path),
    }
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False))
        return 0 if updated else 1

    if updated:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if updated else 1


if __name__ == "__main__":
    raise SystemExit(main())
