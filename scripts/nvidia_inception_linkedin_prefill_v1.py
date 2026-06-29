#!/usr/bin/env python3
"""LinkedIn login prefill for Azure Founders Hub verification (email only — Tier-3 password)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_linkedin_prefill_latest.json"
LINKEDIN_LOGIN = "https://www.linkedin.com/login"
DEFAULT_EMAIL = "giryun288@gmail.com"


def main() -> int:
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    from playwright.sync_api import sync_playwright

    run: dict = {
        "schema": "nvidia_linkedin_prefill_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "email": email,
        "login_url": LINKEDIN_LOGIN,
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "linkedin.com" in (pg.url or "")), None)
        if page is None:
            page = ctx.new_page()
            page.goto(LINKEDIN_LOGIN, wait_until="domcontentloaded", timeout=120_000)
        else:
            if "login" not in page.url.lower():
                page.goto(LINKEDIN_LOGIN, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()
        page.wait_for_timeout(3000)

        def _logout() -> bool:
            try:
                page.goto(
                    "https://www.linkedin.com/m/logout",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                page.wait_for_timeout(3000)
                for label in ("Sign out", "로그아웃", "Sign Out"):
                    btn = page.get_by_role("button", name=label, exact=False)
                    if btn.count():
                        btn.first.click(timeout=5000)
                        page.wait_for_timeout(3000)
                        return True
                if "login" in page.url.lower():
                    return True
            except Exception:
                pass
            return False

        logged_feed = "feed" in page.url.lower() or "mynetwork" in page.url.lower()
        if logged_feed:
            run["was_logged_in"] = True
            run["prior_profile_hint"] = "mkm ai (screenshot prior)"
            if not _logout():
                run["logout_attempted"] = True
            page.goto(LINKEDIN_LOGIN, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(3000)

        if "login" in page.url.lower() or "uas" in page.url.lower():
            clicked = False
            for target in (
                page.locator("button, a, [role='button']").filter(has_text=email),
                page.get_by_text("Jema", exact=False),
                page.locator("button, a").filter(has_text="Jema 계정"),
            ):
                try:
                    el = target.first
                    if el.count() and el.is_visible(timeout=2000):
                        el.click(timeout=8000)
                        page.wait_for_timeout(5000)
                        clicked = True
                        run["clicked_google_account"] = email
                        break
                except Exception:
                    continue
            if not clicked:
                filled = False
                for sel in (
                    page.locator("#username"),
                    page.get_by_label("Email or phone", exact=False),
                    page.locator("input[name='session_key']"),
                    page.locator("input[type='email']"),
                ):
                    try:
                        el = sel.first
                        if el.count() and el.is_visible(timeout=2000):
                            el.fill(email, timeout=5000)
                            filled = True
                            break
                    except Exception:
                        continue
                run["email_prefilled"] = filled
                run["human_gate"] = "linkedin_password_and_2fa_tier3"
                run["hint"] = "비밀번호·2FA는 지휘관이 CDP Chrome 창에서 직접 입력 후 Sign in"
            else:
                run["human_gate"] = "google_oauth_if_prompted"
                run["hint"] = "Google 팝업에서 giryun288@gmail.com 확인·승인 (비밀번호/2FA 필요 시 직접)"
            run["page_url"] = page.url[:200]
            if "feed" in page.url.lower():
                run["login_ok"] = True

        shot = ROOT / "reports/nvidia_linkedin_prefill_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=False, timeout=10_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception as exc:
            run["screenshot_error"] = str(exc)[:200]

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
