#!/usr/bin/env python3
"""Phase 2 publish handoff — guard results + human-fire checklist (no auto-publish)."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/marketing_publish_handoff_v1.schema.json"
UNIFIED = ROOT / "data/marketing/marketing_content_queue.json"
DRAFTS = ROOT / "reports/marketing/linkedin_drafts"
DEFAULT_JSON = ROOT / "reports/marketing/marketing_publish_handoff_latest.json"
DEFAULT_MD = ROOT / "reports/marketing/marketing_publish_checklist_latest.md"

COMMANDER_CHECKLIST = [
    "Open each draft_markdown path; confirm [DRAFT] and disclaimer.",
    "Verify numbers match attached KPI/enterprise SSOT only (no new claims).",
    "Run: py scripts/set_marketing_queue_publish_status_v1.py --item-id <id> --approve",
    "Post on LinkedIn manually OR schedule in Buffer after approve (no API auto-fire from MKM).",
    "After live post: py scripts/set_marketing_queue_publish_status_v1.py --item-id <id> --mark-published",
    "Optional Buffer draft tray: py scripts/push_marketing_draft_to_buffer_v1.py --item-id <id> (dry-run) then --push-draft after MKM_BUFFER_PUSH_ALLOWED=1",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _resolve_draft_md(item: dict[str, Any]) -> Path | None:
    paths = item.get("draft_paths") if isinstance(item.get("draft_paths"), dict) else {}
    rel = paths.get("markdown")
    if rel:
        p = ROOT / str(rel).replace("\\", "/")
        if p.is_file():
            return p
    item_id = str(item.get("id", ""))
    if not item_id:
        return None
    candidates = sorted(
        DRAFTS.glob(f"{item_id}_*_[DRAFT].md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def _guard_status(md_path: Path | None) -> tuple[str, list[str]]:
    if md_path is None or not md_path.is_file():
        return "MISSING_DRAFT", ["draft markdown not found"]
    from check_linkedin_b2b_draft_copy_v1 import check_file

    forbidden, missing = check_file(md_path)
    detail = [*(f"forbidden: {h}" for h in forbidden), *(f"required: {m}" for m in missing)]
    if forbidden or missing:
        return "FAIL", detail
    return "PASS", []


def build(*, unified_path: Path = UNIFIED) -> dict[str, Any]:
    unified = _load(unified_path) if unified_path.is_file() else {"items": []}
    buffer_ok = bool(os.environ.get("BUFFER_ACCESS_TOKEN", "").strip())

    handoff_items: list[dict[str, Any]] = []
    for item in unified.get("items", []):
        if not isinstance(item, dict) or item.get("channel") != "linkedin":
            continue
        status = str(item.get("status", "pending"))
        md_path = _resolve_draft_md(item)
        guard, detail = _guard_status(md_path)
        paths = item.get("draft_paths") if isinstance(item.get("draft_paths"), dict) else {}
        ready_fire = guard == "PASS" and status in ("drafted", "human_approved")
        ready_buffer = ready_fire and status == "human_approved" and buffer_ok

        if status == "published":
            action = "Already marked published in queue."
        elif guard != "PASS":
            action = "Fix draft or regenerate bundle; do not approve until copy_guard PASS."
        elif status == "drafted":
            action = "Review draft → --approve → post or Buffer schedule → --mark-published"
        elif status == "human_approved":
            action = "Approved: post or Buffer schedule now → --mark-published when live."
        else:
            action = "Run weekly bundle to create draft first."

        row: dict[str, Any] = {
            "id": item.get("id"),
            "channel": item.get("channel"),
            "locale": item.get("locale"),
            "queue_status": status,
            "topic": item.get("topic"),
            "copy_guard": guard,
            "copy_guard_detail": detail[:8],
            "ready_for_human_fire": ready_fire,
            "ready_for_buffer_schedule": ready_buffer,
            "next_commander_action": action,
        }
        if md_path:
            row["draft_markdown"] = md_path.relative_to(ROOT).as_posix()
        if paths.get("evidence_json"):
            row["evidence_json"] = paths["evidence_json"]
        if paths.get("chart_png"):
            row["chart_png"] = paths["chart_png"]
        handoff_items.append(row)

    return {
        "schema": "marketing_publish_handoff_v1",
        "generated_at_utc": _utc_now(),
        "boundary_ack": (
            "Phase 2: MKM never auto-publishes. copy_guard PASS is necessary not sufficient. "
            "Human approves (human_approved) then fires LinkedIn or Buffer. "
            "PUBLIC_FACING v1.7; no hallucination-eradication claims."
        ),
        "auto_publish_allowed": False,
        "buffer_api_configured": buffer_ok,
        "commander_checklist": COMMANDER_CHECKLIST,
        "items": handoff_items,
    }


def _render_md(doc: dict[str, Any]) -> str:
    lines = [
        "# Marketing publish checklist (Phase 2)",
        "",
        f"- **generated_at_utc:** `{doc['generated_at_utc']}`",
        f"- **auto_publish_allowed:** `{doc['auto_publish_allowed']}`",
        f"- **buffer_api_configured:** `{doc['buffer_api_configured']}`",
        "",
        "## Commander checklist",
        "",
    ]
    for i, step in enumerate(doc.get("commander_checklist", []), 1):
        lines.append(f"{i}. {step}")
    lines.extend(["", "## Items", ""])
    for it in doc.get("items", []):
        lines.append(f"### {it.get('id')} (`{it.get('queue_status')}`)")
        lines.append(f"- copy_guard: **{it.get('copy_guard')}**")
        lines.append(f"- draft: `{it.get('draft_markdown') or '—'}`")
        lines.append(f"- ready_for_human_fire: `{it.get('ready_for_human_fire')}`")
        lines.append(f"- next: {it.get('next_commander_action')}")
        if it.get("copy_guard_detail"):
            lines.append(f"- detail: {it['copy_guard_detail'][:3]}")
        lines.append("")
    lines.append(doc.get("boundary_ack", ""))
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--unified-queue", type=Path, default=UNIFIED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--skip-md", action="store_true")
    args = ap.parse_args()

    doc = build(unified_path=args.unified_queue)
    try:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft7Validator(schema).validate(doc)
    except ImportError:
        pass

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(_render_md(doc), encoding="utf-8")

    ready = sum(1 for i in doc["items"] if i.get("ready_for_human_fire"))
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.out_json),
                "output_md": None if args.skip_md else str(args.out_md),
                "linkedin_items": len(doc["items"]),
                "ready_for_human_fire": ready,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
