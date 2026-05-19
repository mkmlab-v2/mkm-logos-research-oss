#!/usr/bin/env python3
"""Set human_approved / published on unified + linkedin queues (Phase 2 — no API publish)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UNIFIED_SCHEMA = ROOT / "docs/final/schemas/marketing_content_queue_v1.schema.json"
LINKEDIN_SCHEMA = ROOT / "docs/final/schemas/linkedin_b2b_queue_v1.schema.json"
DEFAULT_UNIFIED = ROOT / "data/marketing/marketing_content_queue.json"
DEFAULT_LINKEDIN = ROOT / "data/marketing/linkedin_queue.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate(doc: dict[str, Any], schema_path: Path) -> None:
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def _find_item(doc: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    for item in doc.get("items", []):
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    return None


def _apply_status(item: dict[str, Any], *, approve: bool, published: bool) -> None:
    if published:
        if item.get("status") not in ("drafted", "human_approved", "published"):
            raise ValueError(f"cannot publish from status={item.get('status')}")
        item["status"] = "published"
        item["published_at_utc"] = _utc_now()
        return
    if approve:
        if item.get("status") not in ("drafted", "human_approved"):
            raise ValueError(f"cannot approve from status={item.get('status')}")
        item["status"] = "human_approved"
        item["human_approved_at_utc"] = _utc_now()


def _sync_linkedin_from_unified(unified: dict[str, Any], linkedin_path: Path) -> None:
    items = [
        {
            "id": i["id"],
            "status": i["status"],
            "topic": i["topic"],
            "locale": i["locale"],
            **{k: i[k] for k in ("hook", "audience", "source_artifacts", "cta_url", "notes", "draft_paths", "drafted_at_utc", "human_approved_at_utc", "published_at_utc") if k in i},
        }
        for i in unified.get("items", [])
        if isinstance(i, dict) and i.get("channel") == "linkedin"
    ]
    out = {"schema": "linkedin_b2b_queue_v1", "updated_at_utc": _utc_now(), "items": items}
    _validate(out, LINKEDIN_SCHEMA)
    linkedin_path.parent.mkdir(parents=True, exist_ok=True)
    linkedin_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unified-queue", type=Path, default=DEFAULT_UNIFIED)
    ap.add_argument("--linkedin-queue", type=Path, default=DEFAULT_LINKEDIN)
    ap.add_argument("--item-id", required=True)
    ap.add_argument("--approve", action="store_true", help="drafted → human_approved")
    ap.add_argument("--mark-published", action="store_true", help="after live post on LinkedIn")
    ap.add_argument("--list", action="store_true", help="Print linkedin item statuses")
    args = ap.parse_args()

    if not args.unified_queue.is_file():
        print(json.dumps({"ok": False, "error": "unified queue missing"}))
        return 2

    unified = _load(args.unified_queue)
    if args.list:
        rows = [
            {"id": i.get("id"), "status": i.get("status"), "channel": i.get("channel")}
            for i in unified.get("items", [])
            if i.get("channel") == "linkedin"
        ]
        print(json.dumps({"ok": True, "items": rows}, ensure_ascii=False, indent=2))
        return 0

    if not args.approve and not args.mark_published:
        print("Specify --approve or --mark-published", flush=True)
        return 2
    if args.approve and args.mark_published:
        print("Use one of --approve or --mark-published per invocation", flush=True)
        return 2

    item = _find_item(unified, args.item_id)
    if not item:
        print(json.dumps({"ok": False, "error": f"item not found: {args.item_id}"}))
        return 2
    if item.get("channel") != "linkedin":
        print(json.dumps({"ok": False, "error": "Phase 2 v1 supports linkedin channel only"}))
        return 2

    try:
        _apply_status(item, approve=args.approve, published=args.mark_published)
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2

    unified["updated_at_utc"] = _utc_now()
    _validate(unified, UNIFIED_SCHEMA)
    args.unified_queue.write_text(json.dumps(unified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _sync_linkedin_from_unified(unified, args.linkedin_queue)

    print(
        json.dumps(
            {
                "ok": True,
                "item_id": args.item_id,
                "status": item.get("status"),
                "human_approved_at_utc": item.get("human_approved_at_utc"),
                "published_at_utc": item.get("published_at_utc"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
