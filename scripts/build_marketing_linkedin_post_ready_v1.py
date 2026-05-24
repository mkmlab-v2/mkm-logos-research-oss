#!/usr/bin/env python3
"""Build copy-paste LinkedIn post bodies for human_approved queue items (no API publish)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

UNIFIED = ROOT / "data/marketing/marketing_content_queue.json"
DEFAULT_MD = ROOT / "reports/marketing/marketing_linkedin_post_ready_latest.md"
DEFAULT_JSON = ROOT / "reports/marketing/marketing_linkedin_post_ready_latest.json"
# Paste/archive: include live-published rows so *_public.txt stays aligned with latest draft.
_PASTE_ELIGIBLE_STATUSES = frozenset({"human_approved", "published", "drafted"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _buffer_configured() -> bool:
    return bool(
        os.environ.get("BUFFER_ACCESS_TOKEN", "").strip()
        and os.environ.get("BUFFER_LINKEDIN_CHANNEL_ID", "").strip()
    )


def _resolve_draft(item: dict[str, Any]) -> Path | None:
    from scripts.build_marketing_publish_handoff_v1 import _resolve_draft_md

    return _resolve_draft_md(item)


def build(*, queue_path: Path = UNIFIED) -> dict[str, Any]:
    from scripts.push_marketing_draft_to_buffer_v1 import _extract_post_body, _guard_pass

    if not queue_path.is_file():
        return {"ok": False, "error": "queue_missing"}

    doc = json.loads(queue_path.read_text(encoding="utf-8-sig"))
    posts: list[dict[str, Any]] = []
    md_blocks: list[str] = [
        "# LinkedIn post ready (copy-paste)",
        "",
        f"- **generated_at_utc:** `{_utc()}`",
        "- **auto_publish_allowed:** `False`",
        f"- **buffer_api_configured:** `{_buffer_configured()}`",
        "",
        "Paste into LinkedIn composer. After live post run `--mark-published`.",
        "",
    ]

    for item in doc.get("items", []):
        if not isinstance(item, dict) or item.get("channel") != "linkedin":
            continue
        if item.get("status") not in _PASTE_ELIGIBLE_STATUSES:
            continue
        iid = str(item.get("id") or "")
        md_path = _resolve_draft(item)
        if md_path is None:
            posts.append({"id": iid, "ok": False, "error": "draft_missing"})
            continue
        ok_guard, detail = _guard_pass(md_path)
        body = _extract_post_body(md_path)
        char_count = len(body)
        posts.append(
            {
                "id": iid,
                "ok": ok_guard and bool(body),
                "locale": item.get("locale"),
                "draft_markdown": md_path.relative_to(ROOT).as_posix(),
                "char_count": char_count,
                "copy_guard": "PASS" if ok_guard else "FAIL",
                "copy_guard_detail": detail[:6],
                "cta_url": item.get("cta_url"),
                "post_body": body,
            }
        )
        md_blocks.extend(
            [
                f"## `{iid}` ({item.get('locale')})",
                "",
                f"- draft: `{md_path.relative_to(ROOT).as_posix()}`",
                f"- chars: **{char_count}** · copy_guard: **{'PASS' if ok_guard else 'FAIL'}**",
                "",
                "### Post body (copy below)",
                "",
                "```text",
                body,
                "```",
                "",
            ]
        )

    return {
        "ok": all(p.get("ok") for p in posts) if posts else False,
        "schema": "marketing_linkedin_post_ready_v1",
        "generated_at_utc": _utc(),
        "auto_publish_allowed": False,
        "buffer_api_configured": _buffer_configured(),
        "posts": posts,
        "markdown_blocks": md_blocks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue", type=Path, default=UNIFIED)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_JSON)
    args = ap.parse_args()

    doc = build(queue_path=args.queue)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps({k: v for k, v in doc.items() if k != "markdown_blocks"}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text("\n".join(doc.get("markdown_blocks") or []) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc.get("ok"), "out_md": str(args.out_md), "out_json": str(args.out_json), "count": len(doc.get("posts") or [])},
            ensure_ascii=False,
        )
    )
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
