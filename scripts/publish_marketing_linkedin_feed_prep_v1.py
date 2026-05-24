#!/usr/bin/env python3
"""PC prep for LinkedIn publish: post_ready exports, clipboard, open feed in default browser."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/marketing/marketing_linkedin_feed_prep_latest.json"
PASTE_DIR = ROOT / "reports/marketing/linkedin_paste_ready"
PRIMARY_TXT = ROOT / "reports/marketing/linkedin_paste_primary_latest.txt"
FEED_URL = "https://www.linkedin.com/feed/"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "ok": proc.returncode == 0,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-400:],
    }


def _load_public_body(item_id: str) -> str | None:
    public = PASTE_DIR / f"{item_id}_public.txt"
    if public.is_file():
        return public.read_text(encoding="utf-8").strip()
    if item_id and PRIMARY_TXT.is_file():
        env_primary = os.environ.get("MKM_LINKEDIN_PASTE_PRIMARY_ID", "")
        if env_primary == item_id or not env_primary:
            return PRIMARY_TXT.read_text(encoding="utf-8").strip()
    return None


def _set_clipboard_win(text: str) -> dict[str, Any]:
    try:
        tmp = ROOT / "reports/marketing/.linkedin_clipboard_tmp.txt"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(text, encoding="utf-8")
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-Content -LiteralPath '{tmp}' -Raw -Encoding UTF8 | Set-Clipboard",
            ],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return {"ok": True, "platform": "windows"}
    except (subprocess.CalledProcessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _open_feed() -> dict[str, Any]:
    try:
        if sys.platform == "win32":
            os.startfile(FEED_URL)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", FEED_URL], start_new_session=True)
        return {"ok": True, "url": FEED_URL}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--item-id", help="Queue item id for clipboard (default: primary from env)")
    ap.add_argument("--primary-id", default=os.environ.get("MKM_LINKEDIN_PASTE_PRIMARY_ID", "showroom_topology_observability_ko"))
    ap.add_argument("--skip-rebuild", action="store_true", help="Do not rebuild post_ready / paste exports")
    ap.add_argument("--no-clipboard", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--emit-agent-request", action="store_true", help="Write openchrome handoff JSON for Cursor agent")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []
    if not args.skip_rebuild:
        steps.append(_run([py, "scripts/build_marketing_linkedin_post_ready_v1.py"]))
        steps.append(_run([py, "scripts/build_marketing_linkedin_paste_exports_v1.py", "--primary-id", args.primary_id]))
        steps.append(_run([py, "scripts/build_marketing_publish_handoff_v1.py"]))

    item_id = args.item_id or args.primary_id
    body = _load_public_body(item_id)
    clipboard: dict[str, Any] = {"skipped": True}
    if body and not args.no_clipboard:
        clipboard = _set_clipboard_win(body)
        clipboard["item_id"] = item_id
        clipboard["char_count"] = len(body)

    browser: dict[str, Any] = {"skipped": True}
    if not args.no_browser:
        browser = _open_feed()

    queue_path = ROOT / "data/marketing/marketing_content_queue.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8")) if queue_path.is_file() else {"items": []}
    pending: list[dict[str, Any]] = []
    for row in queue.get("items") or []:
        if not isinstance(row, dict) or row.get("channel") != "linkedin":
            continue
        iid = str(row.get("id") or "")
        st = str(row.get("status") or "")
        if st in ("human_approved", "drafted") and iid:
            pub = PASTE_DIR / f"{iid}_public.txt"
            pending.append(
                {
                    "id": iid,
                    "queue_status": st,
                    "public_paste": pub.relative_to(ROOT).as_posix() if pub.is_file() else None,
                }
            )

    agent_request_path = ROOT / "reports/marketing/linkedin_openchrome_publish_request_latest.json"
    if args.emit_agent_request:
        agent_request_path.parent.mkdir(parents=True, exist_ok=True)
        agent_request_path.write_text(
            json.dumps(
                {
                    "schema": "linkedin_openchrome_publish_request_v1",
                    "generated_at_utc": _utc(),
                    "publish_via": "openchrome_headed",
                    "cursor_embedded_browser_note": (
                        "Cursor IDE browser tab often has no LinkedIn session. "
                        "Use OpenChrome MCP navigate(..., headed=true) on logged-in Chrome."
                    ),
                    "steps_per_item": [
                        "navigate https://www.linkedin.com/feed/ headed=true",
                        "click 글 올리기",
                        "fill 콘텐츠 제작용 텍스트 에디터 from public paste file",
                        "click 업데이트",
                        "py scripts/set_marketing_queue_publish_status_v1.py --item-id <id> --mark-published",
                    ],
                    "items": pending,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    doc = {
        "schema": "marketing_linkedin_feed_prep_v1",
        "generated_at_utc": _utc(),
        "clipboard_item_id": item_id,
        "clipboard": clipboard,
        "browser": browser,
        "primary_txt": PRIMARY_TXT.relative_to(ROOT).as_posix() if PRIMARY_TXT.is_file() else None,
        "pending_linkedin_items": pending,
        "agent_request_path": (
            agent_request_path.relative_to(ROOT).as_posix() if args.emit_agent_request and agent_request_path.is_file() else None
        ),
        "recommended_publish_path": "linkedin_openchrome_headed",
        "fallback_publish_path": "linkedin_manual_paste",
        "steps": steps,
        "all_ok": all(s.get("ok", True) for s in steps) and clipboard.get("ok", True) and browser.get("ok", True),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "output": str(args.out_json), "clipboard_item_id": item_id}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
