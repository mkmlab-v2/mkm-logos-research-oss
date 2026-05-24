#!/usr/bin/env python3
"""Push human_approved LinkedIn draft text to Buffer as draft only (no auto-schedule/fire)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
UNIFIED = ROOT / "data/marketing/marketing_content_queue.json"
DEFAULT_PREVIEW = ROOT / "reports/marketing/buffer_push_preview_latest.json"
BUFFER_GRAPHQL = "https://graph.buffer.com/graphql"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _find_item(doc: dict[str, Any], item_id: str) -> dict[str, Any] | None:
    for item in doc.get("items", []):
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    return None


def _strip_leading_draft_marker(body: str) -> str:
    lines = body.splitlines()
    while lines:
        s = lines[0].strip().strip("*").strip()
        if s in ("[DRAFT]", "DRAFT"):
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip()


def _extract_post_body(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    # Drop markdown metadata block; keep from first ## Hook or **[DRAFT]**
    lines = text.splitlines()
    out: list[str] = []
    started = False
    for line in lines:
        if line.startswith("> ") or line.startswith("- **generated") or line.startswith("- **mode"):
            continue
        if line.startswith("# ") and "[DRAFT]" in line:
            continue
        if line.strip().startswith("## ") or line.strip().startswith("**[DRAFT]**"):
            started = True
            if line.strip().startswith("**[DRAFT]**"):
                continue
        if started:
            if line.startswith("## B-roll") or line.startswith("<!--"):
                break
            out.append(line)
    body = "\n".join(out).strip()
    body = re.sub(r"\*\*([^*]+)\*\*", r"\1", body)
    body = re.sub(r"`([^`]+)`", r"\1", body)
    return _strip_leading_draft_marker(body)[:3000]


def _guard_pass(md_path: Path) -> tuple[bool, list[str]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from check_linkedin_b2b_draft_copy_v1 import check_file

    forbidden, missing = check_file(md_path)
    detail = [*(f"forbidden: {h}" for h in forbidden), *(f"required: {m}" for m in missing)]
    return not (forbidden or missing), detail


def _buffer_create_draft(*, token: str, channel_id: str, text: str) -> dict[str, Any]:
    mutation = """
    mutation CreateDraft($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post { id status }
        }
        ... on MutationError {
          message
        }
      }
    }
    """
    payload = {
        "query": mutation,
        "variables": {
            "input": {
                "channelId": channel_id,
                "text": text,
                "saveToDraft": True,
            }
        },
    }
    req = urllib.request.Request(
        BUFFER_GRAPHQL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--item-id", required=True)
    ap.add_argument("--queue", type=Path, default=UNIFIED)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_PREVIEW)
    ap.add_argument("--push-draft", action="store_true", help="Requires MKM_BUFFER_PUSH_ALLOWED=1")
    args = ap.parse_args()

    if not args.queue.is_file():
        print(json.dumps({"ok": False, "error": "queue missing"}))
        return 2

    item = _find_item(_load(args.queue), args.item_id)
    if not item:
        print(json.dumps({"ok": False, "error": "item not found"}))
        return 2
    if item.get("channel") != "linkedin":
        print(json.dumps({"ok": False, "error": "Buffer v1 supports linkedin channel only"}))
        return 2
    status = str(item.get("status") or "")
    if args.push_draft:
        if status != "human_approved":
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "status must be human_approved before Buffer push",
                        "status": status,
                    }
                )
            )
            return 2
    elif status not in ("drafted", "human_approved"):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "status must be drafted or human_approved for Buffer preview",
                    "status": status,
                }
            )
        )
        return 2

    paths = item.get("draft_paths") or {}
    rel = paths.get("markdown")
    if not rel:
        print(json.dumps({"ok": False, "error": "draft_paths.markdown missing"}))
        return 2
    md_path = ROOT / str(rel).replace("\\", "/")
    ok_guard, detail = _guard_pass(md_path)
    if not ok_guard:
        print(json.dumps({"ok": False, "error": "copy_guard FAIL", "detail": detail}))
        return 2

    text = _extract_post_body(md_path)
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "").strip()
    channel_id = os.environ.get("BUFFER_LINKEDIN_CHANNEL_ID", "").strip()

    preview = {
        "schema": "marketing_buffer_push_preview_v1",
        "generated_at_utc": _utc_now(),
        "item_id": args.item_id,
        "auto_fire": False,
        "save_to_draft": True,
        "text_preview_chars": len(text),
        "text_excerpt": text[:400],
        "buffer_token_set": bool(token),
        "buffer_channel_id_set": bool(channel_id),
        "push_allowed_env": _truthy("MKM_BUFFER_PUSH_ALLOWED"),
        "boundary_ack": "MKM pushes to Buffer draft only; commander schedules in Buffer UI.",
    }

    if not args.push_draft:
        preview["mode"] = "dry_run"
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "dry_run": True, "output": str(args.out_json)}))
        return 0

    if not _truthy("MKM_BUFFER_PUSH_ALLOWED"):
        print(json.dumps({"ok": False, "error": "MKM_BUFFER_PUSH_ALLOWED not set"}))
        return 2
    if not token or not channel_id:
        print(json.dumps({"ok": False, "error": "BUFFER_ACCESS_TOKEN or BUFFER_LINKEDIN_CHANNEL_ID missing"}))
        return 2

    try:
        resp = _buffer_create_draft(token=token, channel_id=channel_id, text=text)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:500]
        print(json.dumps({"ok": False, "error": f"buffer_http_{e.code}", "body": body}))
        return 2
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2

    preview["mode"] = "pushed_draft"
    preview["buffer_response"] = resp
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
