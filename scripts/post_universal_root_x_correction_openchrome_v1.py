#!/usr/bin/env python3
"""Post UR X correction as reply thread via openchrome CDP (Tier 3 browser, logged-in session)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.post_x_api_v1 import _load_correction_thread  # noqa: E402
from scripts.reddit_agent_governance_lib_v1 import (  # noqa: E402
    RedditGovernanceError,
    enforce_send_gate_for_live,
)

CDP_URL = "http://127.0.0.1:9222"
OUT = ROOT / "reports/universal_root_x_correction_openchrome_v1_latest.json"
PASTE = ROOT / "reports/human_paste/universal_root_x_public_correction_v1.txt"
DEFAULT_REPLY_URL = "https://x.com/moksorinw/status/2068734802661175789"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _acquire_page(context: Any, prefer_url_part: str) -> Any:
    for page in context.pages:
        if prefer_url_part in (page.url or "").lower():
            return page
    page = context.new_page()
    return page


def _reply_box(page: Any) -> Any:
    box = page.locator('[data-testid="tweetTextarea_0"] div[contenteditable="true"]').first
    if box.count() == 0:
        box = page.locator('div[contenteditable="true"][role="textbox"]').first
    box.wait_for(state="visible", timeout=30000)
    return box


def _open_reply_composer(page: Any, tweet_url: str) -> dict[str, Any]:
    page.goto(tweet_url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_timeout(4000)
    step: dict[str, Any] = {"url": page.url}
    if "login" in page.url.lower():
        step["error"] = "redirected_to_login"
        return step
    reply_btn = page.locator('[data-testid="reply"]').first
    reply_btn.wait_for(state="visible", timeout=20000)
    reply_btn.click()
    page.wait_for_timeout(2000)
    step["composer"] = "open"
    return step


def _submit_reply(page: Any, text: str, *, dry_run: bool) -> dict[str, Any]:
    step: dict[str, Any] = {"char_count": len(text), "ok": False}
    box = _reply_box(page)
    box.click()
    box.fill(text)
    shot = ROOT / "reports/universal_root_x_correction_preflight_v1.png"
    page.screenshot(path=str(shot), full_page=False)
    step["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    if dry_run:
        step["ok"] = True
        step["status"] = "dry_run"
        return step
    post_btn = page.locator('[data-testid="tweetButton"], [data-testid="tweetButtonInline"]').first
    post_btn.wait_for(state="visible", timeout=15000)
    if post_btn.is_disabled():
        step["error"] = "post_button_disabled"
        return step
    post_btn.click()
    page.wait_for_timeout(5000)
    result_shot = ROOT / "reports/universal_root_x_correction_post_result_v1.png"
    page.screenshot(path=str(result_shot), full_page=False)
    step["result_screenshot"] = str(result_shot.relative_to(ROOT)).replace("\\", "/")
    step["final_url"] = page.url
    step["ok"] = True
    step["status"] = "posted_heuristic"
    return step


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--acknowledge-send", action="store_true")
    ap.add_argument("--reply-url", default=DEFAULT_REPLY_URL)
    ap.add_argument("--text-file", type=Path, default=PASTE)
    args = ap.parse_args()

    report: dict[str, Any] = {
        "schema": "universal_root_x_correction_openchrome_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "generated_at_utc": _utc(),
        "dry_run": args.dry_run,
        "reply_url": args.reply_url,
        "steps": [],
        "ok": False,
    }

    try:
        enforce_send_gate_for_live(live_post=not args.dry_run, acknowledge_send=args.acknowledge_send)
        chunks = _load_correction_thread(args.text_file)
    except (RedditGovernanceError, FileNotFoundError, ValueError) as exc:
        report["error"] = str(exc)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 5 if isinstance(exc, RedditGovernanceError) else 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        report["error"] = "playwright_missing"
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "error": report["error"]}, ensure_ascii=False))
        return 2

    tweet_url = args.reply_url.strip()
    results: list[dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = _acquire_page(context, "x.com")

        for idx, spec in enumerate(chunks):
            open_step = _open_reply_composer(page, tweet_url)
            open_step["thread_index"] = spec.get("thread_index")
            report["steps"].append({"open": open_step})
            if open_step.get("error"):
                report["error"] = open_step["error"]
                break
            submit = _submit_reply(page, spec["text"], dry_run=args.dry_run)
            submit["thread_index"] = spec.get("thread_index")
            submit["thread_total"] = spec.get("thread_total")
            results.append(submit)
            report["steps"].append({"submit": submit})
            if not submit.get("ok"):
                report["error"] = submit.get("error") or "submit_failed"
                break
            if not args.dry_run and idx + 1 < len(chunks):
                tweet_url = page.url
                page.wait_for_timeout(2500)

    report["results"] = results
    report["ok"] = bool(results) and all(r.get("ok") for r in results)
    report["status"] = "dry_run" if args.dry_run else ("posted" if report["ok"] else "failed")
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "status": report["status"], "results": results}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
