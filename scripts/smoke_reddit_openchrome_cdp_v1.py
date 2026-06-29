#!/usr/bin/env python3
"""Reddit openchrome/CDP smoke — attach to local Chrome on :9222, check login + post UI reachability."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "reports" / "reddit_openchrome_smoke_latest.json"
OUT_PNG = ROOT / "reports" / "reddit_openchrome_smoke_latest.png"
CDP_URL = "http://127.0.0.1:9222"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed", file=sys.stderr)
        return 2

    result: dict = {
        "schema": "reddit_openchrome_smoke_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cdp_url": CDP_URL,
        "login_detected": False,
        "settings_reachable": False,
        "submit_ui_reachable": False,
        "blocking": [],
        "final_url": None,
        "page_title": None,
        "screenshot": str(OUT_PNG.relative_to(ROOT)).replace("\\", "/"),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception as exc:
            result["blocking"].append({"type": "cdp_connect_failed", "detail": str(exc)})
            OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False))
            return 3

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        try:
            page.goto("https://www.reddit.com/settings", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            result["final_url"] = page.url
            result["page_title"] = page.title()

            body = page.inner_text("body")[:4000]
            lower_url = (page.url or "").lower()
            title_lower = (page.title() or "").lower()

            if "/login" in lower_url:
                result["blocking"].append({"type": "not_logged_in", "detail": "redirected to login"})
            elif "settings" in lower_url or "settings" in title_lower:
                result["login_detected"] = True
                result["settings_reachable"] = True
            else:
                result["login_detected"] = True
                result["settings_reachable"] = "settings" in lower_url or "설정" in body

            if result["login_detected"]:
                page.goto("https://www.reddit.com/submit", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
                result["final_url"] = page.url
                submit_body = page.inner_text("body")[:2000].lower()
                if "/login" not in page.url.lower() and (
                    "create" in submit_body or "post" in submit_body or "게시" in submit_body or "title" in submit_body
                ):
                    result["submit_ui_reachable"] = True
                else:
                    result["blocking"].append({"type": "submit_blocked", "detail": page.url})

            page.screenshot(path=str(OUT_PNG), full_page=False)
        except Exception as exc:
            result["blocking"].append({"type": "navigation_error", "detail": str(exc)})
        finally:
            try:
                page.close()
            except Exception:
                pass

    ok = result["login_detected"] and result["submit_ui_reachable"]
    result["overall_passed"] = ok
    result["auto_post_ready"] = ok
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
