#!/usr/bin/env python3
"""Switch LinkedIn to giryun288@gmail.com via Google/Jema button."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_linkedin_prefill_latest.json"
EMAIL = sys.argv[1] if len(sys.argv) > 1 else "giryun288@gmail.com"


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {
        "schema": "nvidia_linkedin_switch_account_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "email": EMAIL,
        "actions": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "linkedin.com" in (pg.url or "")), None)
        if page is None:
            page = ctx.new_page()
        page.bring_to_front()

        # Sign out via Me menu (mkm ai session)
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(3000)
        for me_label in ("나", "Me", "mkm ai"):
            try:
                me = page.get_by_role("button", name=me_label, exact=False).first
                if not me.count():
                    me = page.locator("button").filter(has_text=me_label).first
                if me.count() and me.is_visible(timeout=2000):
                    me.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    run["actions"].append(f"open_me:{me_label}")
                    break
            except Exception:
                continue
        for label in ("로그아웃", "Sign out", "Sign Out"):
            try:
                loc = page.get_by_role("button", name=label, exact=False)
                if not loc.count():
                    loc = page.get_by_text(label, exact=False)
                if loc.count() and loc.first.is_visible(timeout=2000):
                    loc.first.click(timeout=5000)
                    run["actions"].append(f"logout:{label}")
                    page.wait_for_timeout(4000)
                    break
            except Exception:
                continue
        if "login" not in page.url.lower():
            page.goto("https://www.linkedin.com/m/logout", wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(3000)

        page.goto(
            "https://www.linkedin.com/login?fromSignIn=true",
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        page.wait_for_timeout(3000)

        for label in ("다른 계정으로 로그인", "Sign in using another account", "Use another account"):
            try:
                loc = page.get_by_role("link", name=label)
                if loc.count() and loc.first.is_visible(timeout=1500):
                    loc.first.click(timeout=5000)
                    page.wait_for_timeout(3000)
                    run["actions"].append(f"click:{label}")
                    break
            except Exception:
                continue

        clicked = False
        for loc in (
            page.get_by_text(EMAIL, exact=False),
            page.locator("button, a, [role='button']").filter(has_text="Jema"),
            page.locator(f"text={EMAIL}"),
        ):
            try:
                el = loc.first
                if el.count() and el.is_visible(timeout=2000):
                    el.click(timeout=8000, force=True)
                    page.wait_for_timeout(8000)
                    run["actions"].append(f"click_account:{EMAIL}")
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            for h in page.locator(f"*:has-text('{EMAIL}')").all()[:8]:
                try:
                    if h.is_visible(timeout=500):
                        h.click(timeout=5000, force=True)
                        run["actions"].append("click_has_text")
                        page.wait_for_timeout(8000)
                        clicked = True
                        break
                except Exception:
                    continue

        run["page_url"] = page.url[:250]
        run["on_feed"] = "feed" in page.url.lower()
        body = page.inner_text("body", timeout=8000) or ""
        if EMAIL in body or "Jema" in body:
            run["email_visible_on_page"] = True
        if "mkm ai" in body and EMAIL.lower() not in body.lower():
            run["wrong_account"] = "still_mkm_ai"
            run["human_gate"] = "manual_switch_on_login_page"
            run["hint"] = (
                "CDP Chrome 로그인 화면에서 「다른 계정으로 로그인」 → "
                "「Jema 계정 사용 giryun288@gmail.com」 클릭 → Google 승인"
            )

        if not run["on_feed"]:
            for sel in (page.locator("#username"), page.locator("input[name='session_key']")):
                try:
                    el = sel.first
                    if el.count() and el.is_visible(timeout=1500):
                        el.fill(EMAIL, timeout=5000)
                        run["actions"].append("fill_email")
                        break
                except Exception:
                    continue
            run["human_gate"] = "google_oauth_or_password_tier3"
            run["hint"] = "CDP Chrome: giryun288 선택·Google 승인 또는 비밀번호 입력"

        shot = ROOT / "reports/nvidia_linkedin_prefill_latest.png"
        try:
            page.screenshot(path=str(shot), timeout=10_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception as exc:
            run["screenshot_error"] = str(exc)[:150]

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
