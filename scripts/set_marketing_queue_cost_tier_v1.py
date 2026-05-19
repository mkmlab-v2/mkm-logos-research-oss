#!/usr/bin/env python3
"""Set active_cost_tier / tier_15 event-week flags on marketing_content_queue.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/marketing_content_queue_v1.schema.json"
DEFAULT_QUEUE = ROOT / "data/marketing/marketing_content_queue.json"
EXAMPLE = ROOT / "data/marketing/marketing_content_queue_v1.example.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any]) -> None:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def apply(
    queue_path: Path,
    *,
    active_tier: str,
    event_week: bool,
    clear_event_week: bool,
    gemini_item_id: str | None,
    reset_gemini_flags: bool,
) -> dict[str, Any]:
    if not queue_path.is_file() and EXAMPLE.is_file():
        queue_path.parent.mkdir(parents=True, exist_ok=True)
        queue_path.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    doc = _load(queue_path)
    doc["active_cost_tier"] = active_tier
    doc["updated_at_utc"] = _utc_now()

    if clear_event_week:
        doc.pop("tier15_event_week", None)
    elif event_week or active_tier == "tier_15":
        doc["tier15_event_week"] = {
            "enabled": bool(event_week or active_tier == "tier_15"),
            "max_gemini_linkedin_posts_this_month": 2,
            "requires_env": "MKM_MARKETING_GEMINI_ALLOWED=1",
            "run_command": (
                "powershell -NoProfile -ExecutionPolicy Bypass -File "
                "scripts\\Run-MarketingWeeklyDraftBundle_v1.ps1 -Gemini"
            ),
            "checklist": [
                "Set MKM_MARKETING_GEMINI_ALLOWED=1 in .env (event week only)",
                "Only items with allow_gemini: true get -Gemini",
                "Human publish after check_linkedin_b2b_draft_copy_v1.py PASS",
                "Revert: set_marketing_queue_cost_tier_v1.py --active-tier tier_0 --clear-event-week",
            ],
        }

    if reset_gemini_flags or gemini_item_id:
        for item in doc.get("items", []):
            if item.get("channel") != "linkedin":
                continue
            if item.get("status") not in ("pending", "drafted"):
                continue
            allow = bool(gemini_item_id and item.get("id") == gemini_item_id)
            item["allow_gemini"] = allow

    _validate(doc)
    queue_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    gemini_ids = [i["id"] for i in doc.get("items", []) if i.get("allow_gemini")]
    return {
        "ok": True,
        "output": queue_path.as_posix(),
        "active_cost_tier": active_tier,
        "tier15_event_week": doc.get("tier15_event_week"),
        "allow_gemini_item_ids": gemini_ids,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--active-tier", choices=["tier_0", "tier_15", "tier_50"], default="tier_0")
    ap.add_argument("--event-week", action="store_true", help="Enable tier_15 event_week block")
    ap.add_argument("--clear-event-week", action="store_true")
    ap.add_argument(
        "--gemini-item",
        default="",
        help="LinkedIn queue item id allowed to use -Gemini (tier_15). Empty = reset all false.",
    )
    ap.add_argument(
        "--reset-gemini-flags",
        action="store_true",
        help="Set allow_gemini false on all linkedin items",
    )
    args = ap.parse_args()

    gemini_id = args.gemini_item.strip() or None
    if args.reset_gemini_flags:
        gemini_id = None

    doc = apply(
        args.queue,
        active_tier=args.active_tier,
        event_week=args.event_week,
        clear_event_week=args.clear_event_week,
        gemini_item_id=gemini_id if not args.reset_gemini_flags else None,
        reset_gemini_flags=args.reset_gemini_flags or bool(gemini_id),
    )
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
