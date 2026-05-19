#!/usr/bin/env python3
"""Sync marketing_content_queue_v1 linkedin items into linkedin_b2b_queue_v1 (local)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/marketing_content_queue_v1.schema.json"
DEFAULT_UNIFIED = ROOT / "data/marketing/marketing_content_queue.json"
UNIFIED_EXAMPLE = ROOT / "data/marketing/marketing_content_queue_v1.example.json"
DEFAULT_LINKEDIN = ROOT / "data/marketing/linkedin_queue.json"
LINKEDIN_EXAMPLE = ROOT / "data/marketing/linkedin_queue_v1.example.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truthy_env(name: str) -> bool:
    v = __import__("os").environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _validate_unified(doc: dict[str, Any]) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise SystemExit("jsonschema required") from exc
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def _to_linkedin_item(item: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": item["id"],
        "status": item["status"],
        "topic": item["topic"],
        "locale": item["locale"],
    }
    for key in (
        "hook",
        "audience",
        "source_artifacts",
        "cta_url",
        "notes",
        "draft_paths",
        "drafted_at_utc",
        "human_approved_at_utc",
        "published_at_utc",
    ):
        if key in item:
            out[key] = item[key]
    return out


def pull_linkedin_status_to_unified(unified_path: Path, linkedin_path: Path, *, dry_run: bool) -> dict[str, Any]:
    """Copy drafted status/paths from linkedin_b2b_queue back into unified queue."""
    if not unified_path.is_file() or not linkedin_path.is_file():
        return {"ok": True, "skipped": True, "reason": "queue_missing"}
    unified = _load_json(unified_path)
    linkedin = _load_json(linkedin_path)
    by_id = {str(i["id"]): i for i in linkedin.get("items", []) if isinstance(i, dict) and i.get("id")}
    updated = 0
    for item in unified.get("items", []):
        if not isinstance(item, dict) or item.get("channel") != "linkedin":
            continue
        li = by_id.get(str(item.get("id")))
        if not li:
            continue
        if li.get("status") == "drafted":
            item["status"] = "drafted"
            for key in ("draft_paths", "drafted_at_utc"):
                if key in li:
                    item[key] = li[key]
            updated += 1
    unified["updated_at_utc"] = _utc_now()
    if dry_run:
        return {"ok": True, "dry_run": True, "items_updated": updated}
    _validate_unified(unified)
    unified_path.write_text(json.dumps(unified, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "items_updated": updated, "output": _rel(unified_path)}


def sync(unified_path: Path, linkedin_path: Path, *, dry_run: bool) -> dict[str, Any]:
    if not unified_path.is_file():
        return {
            "ok": True,
            "skipped": True,
            "reason": "unified_queue_missing",
            "unified_path": _rel(unified_path),
        }

    unified = _load_json(unified_path)
    _validate_unified(unified)
    linkedin_items = [_to_linkedin_item(i) for i in unified.get("items", []) if i.get("channel") == "linkedin"]

    if not linkedin_items and linkedin_path.is_file():
        return {
            "ok": True,
            "skipped": True,
            "reason": "no_linkedin_channel_items",
            "linkedin_queue_unchanged": _rel(linkedin_path),
        }

    out_doc = {
        "schema": "linkedin_b2b_queue_v1",
        "updated_at_utc": _utc_now(),
        "items": linkedin_items,
    }

    gemini_any = any(bool(i.get("allow_gemini")) for i in unified.get("items", []) if i.get("channel") == "linkedin")
    marketing_gemini_ok = _truthy_env("MKM_MARKETING_GEMINI_ALLOWED")

    summary = {
        "ok": True,
        "linkedin_item_count": len(linkedin_items),
        "output": _rel(linkedin_path),
        "allow_gemini_on_items": gemini_any,
        "marketing_gemini_env_allowed": marketing_gemini_ok,
        "suggest_gemini_flag": bool(gemini_any and marketing_gemini_ok),
    }

    if dry_run:
        summary["dry_run"] = True
        return summary

    linkedin_path.parent.mkdir(parents=True, exist_ok=True)
    linkedin_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unified-queue", type=Path, default=DEFAULT_UNIFIED)
    ap.add_argument("--linkedin-queue", type=Path, default=DEFAULT_LINKEDIN)
    ap.add_argument("--init-from-example", action="store_true", help="Copy unified example if queue missing")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--pull-linkedin-status",
        action="store_true",
        help="Merge drafted status from linkedin queue into unified queue (then exit).",
    )
    args = ap.parse_args()

    unified = args.unified_queue
    if args.pull_linkedin_status:
        print(json.dumps(pull_linkedin_status_to_unified(unified, args.linkedin_queue, dry_run=args.dry_run)))
        return 0

    if args.init_from_example and not unified.is_file() and UNIFIED_EXAMPLE.is_file():
        unified.parent.mkdir(parents=True, exist_ok=True)
        unified.write_text(UNIFIED_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    if not args.linkedin_queue.is_file() and LINKEDIN_EXAMPLE.is_file():
        args.linkedin_queue.parent.mkdir(parents=True, exist_ok=True)
        args.linkedin_queue.write_text(LINKEDIN_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    doc = sync(unified, args.linkedin_queue, dry_run=args.dry_run)
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
