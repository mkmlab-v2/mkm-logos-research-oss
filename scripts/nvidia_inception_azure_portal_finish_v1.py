#!/usr/bin/env python3
"""Azure portal Microsoft for Startups blade after human login (CDP)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benefits)

OUT = ROOT / "reports/nvidia_azure_portal_finish_latest.json"
AZURE_STARTUPS_VIEW = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    "AzureForStartups.ReactView/skipWizardRedirect~/true"
)
NVIDIA_BENEFIT = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)


def _startup_frame(page):
    for fr in page.frames:
        try:
            txt = fr.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if "Microsoft for Startups" in txt or "LinkedIn" in txt or "Azure 크레딧" in txt:
            if len(txt) > 200:
                return fr
    return page.main_frame


def _extract_status(text: str) -> dict:
    out: dict = {}
    m = re.search(r"\$[\d,]+", text)
    if m:
        out["credits_tier_seen"] = m.group(0)
    if "LinkedIn" in text:
        out["linkedin_verification_required"] = True
    if "150,000" in text or "150000" in text:
        out["max_credits_banner"] = "$150,000"
    if "lee" in text.lower() or "mkmlab" in text.lower():
        out["startup_profile_detected"] = True
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {"submit_ok": False, "logged_in": False}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "portal.azure.com" in (pg.url or "")), None)
        if page is None:
            page = ctx.new_page()
            page.goto(AZURE_STARTUPS_VIEW, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()
        page.wait_for_timeout(5000)
        run["portal_url"] = page.url[:250]
        body_top = page.inner_text("body", timeout=8000) or ""
        run["logged_in"] = "moksorinw@gmail.com" in body_top or "onmicrosoft.com" in body_top.lower()
        fr = _startup_frame(page)
        startup_text = fr.inner_text("body", timeout=8000) or ""
        run.update(_extract_status(startup_text))
        run["startup_snippet"] = startup_text[:600].replace("\n", " | ")

        # NVIDIA Inception benefit deep-link (same Microsoft session)
        benefit_page = next((pg for pg in ctx.pages if "benefit-activity-id=aG9Vv" in (pg.url or "")), None)
        if benefit_page is None:
            benefit_page = ctx.new_page()
            benefit_page.goto(NVIDIA_BENEFIT, wait_until="domcontentloaded", timeout=120_000)
            benefit_page.wait_for_timeout(4000)
        run["benefit_landing_url"] = benefit_page.url[:250]

        for btn in ("Get started", "Apply now", "Sign up", "Join", "Activate", "Claim"):
            try:
                b = benefit_page.get_by_role("link", name=btn, exact=False).first
                if b.count() and b.is_visible(timeout=2000):
                    b.click(timeout=8000)
                    benefit_page.wait_for_timeout(4000)
                    run["benefit_clicked"] = btn
                    break
            except Exception:
                continue

        # LinkedIn verify on startups blade (opens human OAuth)
        try:
            li = fr.get_by_role("button", name="LinkedIn", exact=False).first
            if not li.count():
                li = fr.get_by_text("LinkedIn으로 확인", exact=False).first
            if li.count() and li.is_visible(timeout=2000):
                run["linkedin_button_visible"] = True
                run["human_gate"] = "linkedin_verification_for_azure_credits"
                run["hint"] = (
                    "Azure 포털에서 'LinkedIn으로 확인' 클릭 → LinkedIn 로그인 후 "
                    "$1,000+ 크레딧 해제. NVIDIA $5K는 Benefits Requested 반영까지 며칠 걸릴 수 있음."
                )
        except Exception:
            pass

        run["submit_ok"] = bool(run.get("logged_in")) and not run.get("human_gate")

        shot = ROOT / "reports/nvidia_azure_portal_finish_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=25_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("logged_in") else 1


if __name__ == "__main__":
    raise SystemExit(main())
