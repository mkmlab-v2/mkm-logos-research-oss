#!/usr/bin/env python3
"""NVIDIA Inception Azure $5K: Sign in on microsoft.com/startups + claim (CDP)."""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_inception_benefit_apply_latest.json"
NVIDIA = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)
SIGNUP = "https://portal.startups.microsoft.com/signup"
PORTAL_STARTUPS = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)

_spec = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benefits)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    try:
        return page.inner_text("body", timeout=12_000) or ""
    except Exception:
        return ""


def _click(page, *labels: str) -> str | None:
    for label in labels:
        for role in ("link", "button"):
            try:
                loc = page.get_by_role(role, name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=2000):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(4000)
                    return f"{role}:{label}"
            except Exception:
                pass
    return None


def _ms_login_pick(page, email: str, run: dict[str, Any]) -> None:
    body = _text(page)
    if email.split("@")[0] in body or email in body:
        hit = _click(page, email, email.split("@")[0], "기륜", "giryun288@gmail.com")
        if hit:
            run["ms_picked"] = hit
            page.wait_for_timeout(5000)
            return
    try:
        inp = page.locator("input[type='email'], input[name='loginfmt']").first
        if inp.count() and inp.is_visible(timeout=2000):
            inp.fill(email, timeout=5000)
            page.locator("input[type='submit'], button[type='submit']").first.click(timeout=5000)
            page.wait_for_timeout(3000)
            run["ms_email_filled"] = email
    except Exception as exc:
        run["ms_prefill_error"] = str(exc)[:120]
    if page.locator("input[type='password']").count():
        run["human_gate"] = "microsoft_password_on_benefit_signin"


def main() -> int:
    from playwright.sync_api import sync_playwright

    cfg = benefits._load_form_answers().get("azure") or {}
    email = str(cfg.get("microsoft_account_email") or "giryun288@gmail.com")
    run: dict[str, Any] = {
        "schema": "nvidia_azure_inception_benefit_apply_v1",
        "generated_at_utc": _utc(),
        "email": email,
        "submit_ok": False,
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].new_page()
        page.goto(NVIDIA, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(4000)
        run["landing_url"] = page.url[:320]

        sign = _click(page, "Sign in", "로그인")
        if sign:
            run["sign_in_clicked"] = sign
            page.wait_for_timeout(5000)
            run["after_signin_url"] = page.url[:320]
            if any(x in (page.url or "") for x in ("login.live.com", "login.microsoftonline.com")):
                _ms_login_pick(page, email, run)
                if "계정 선택" in _text(page) or "Pick an account" in _text(page):
                    hit = _click(page, "giryun288@gmail.com", "giryun lee")
                    if hit:
                        run["azure_account_picked"] = hit
                        page.wait_for_timeout(8000)

        if not run.get("human_gate"):
            for btn in ("Get started now", "Get started", "Apply now", "Claim", "Activate"):
                hit = _click(page, btn)
                if hit:
                    run["benefit_cta"] = hit
                    page.wait_for_timeout(5000)
                    break

        if "portal.startups.microsoft.com" in (page.url or "") or "signup" in (page.url or ""):
            run["on_signup"] = True
            pointer = benefits._load_pointer()
            inc = pointer.get("inception", {}).get("company_form", {})
            company = str(cfg.get("company_name") or inc.get("display_name") or "mkmlab")
            website = str(cfg.get("website") or "https://jema-ai.com")
            contact = str(cfg.get("contact_email") or benefits._pointer_email())
            fills: list[str] = []
            for label, value in (
                ("Company name", company),
                ("Website", website),
                ("Email", contact),
                ("Work email", contact),
            ):
                if benefits._fill_labeled_input(page, label, value):
                    fills.append(label)
            run["fills"] = fills
            run["validation_errors"] = benefits._validation_error_count(page)
            if run["validation_errors"] == 0:
                sub = _click(page, "Submit", "Apply", "Continue", "Next")
                if sub:
                    run["submitted"] = sub
                    run["submit_ok"] = benefits._validation_error_count(page) == 0

        # Azure portal startups blade (alternate path)
        if not run.get("submit_ok"):
            if "login.microsoftonline.com" in (page.url or ""):
                hit = _click(page, "giryun288@gmail.com", "giryun lee")
                if hit:
                    run["portal_account_picked"] = hit
                    page.wait_for_timeout(8000)
            page.goto(PORTAL_STARTUPS, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(8000)
            run["portal_startups_url"] = page.url[:320]
            t = _text(page)
            run["portal_startups_snippet"] = t[:800].replace("\n", " | ")
            if "LinkedIn" in t:
                run["human_gate"] = "linkedin_verify_on_azure_startups"
            if "크레딧" in t or "credit" in t.lower():
                run["credits_visible_on_portal"] = True

        run["final_url"] = page.url[:320]
        run["final_snippet"] = _text(page)[:900].replace("\n", " | ")
        shot = ROOT / "reports/nvidia_azure_inception_benefit_apply_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=35_000)
        run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        page.close()

    run["verdict"] = (
        "submit_ok"
        if run.get("submit_ok")
        else (run.get("human_gate") or "benefit_flow_partial")
    )
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submit_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
