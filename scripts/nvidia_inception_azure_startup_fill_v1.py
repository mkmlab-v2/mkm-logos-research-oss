#!/usr/bin/env python3
"""Microsoft for Startups signup after Azure login (Tier-3: MS password human)."""
from __future__ import annotations

import json
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

OUT = ROOT / "reports/nvidia_azure_startup_fill_latest.json"
SIGNUP = "https://portal.startups.microsoft.com/signup"
BENEFIT_LANDING = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)


def _find_page(browser, *needles: str):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            url = (pg.url or "").lower()
            if any(n.lower() in url for n in needles):
                return pg
    return None


def _prefill_ms_login(page, email: str, run: dict) -> None:
    run["ms_login_url"] = page.url[:200]
    try:
        inp = page.locator("input[type='email'], input[name='loginfmt']").first
        if inp.count() and inp.is_visible(timeout=3000):
            inp.click(timeout=3000)
            inp.fill("", timeout=3000)
            inp.fill(email, timeout=5000)
            run["ms_email_filled"] = True
            page.locator("input[type='submit'], button[type='submit']").first.click(timeout=5000)
            page.wait_for_timeout(2500)
            run["ms_next_clicked"] = True
    except Exception as exc:
        run["ms_prefill_error"] = str(exc)[:120]
    if page.locator("input[type='password']").count():
        run["human_gate"] = "microsoft_password_or_mfa"


def _fill_startup_portal(page, cfg: dict, run: dict) -> None:
    pointer = benefits._load_pointer()
    inc = pointer.get("inception", {}).get("company_form", {})
    company = str(cfg.get("company_name") or inc.get("display_name") or "mkmlab")
    website = str(cfg.get("website") or inc.get("website") or "https://jema-ai.com")
    email = str(cfg.get("contact_email") or benefits._pointer_email())
    first = str(cfg.get("first_name") or "Giryun")
    last = str(cfg.get("last_name") or "Lee")
    fills: list[str] = []

    mapping = [
        ("Company name", company),
        ("Startup name", company),
        ("Website", website),
        ("Company website", website),
        ("First name", first),
        ("Last name", last),
        ("Email", email),
        ("Work email", email),
    ]
    for label, value in mapping:
        if not value:
            continue
        if benefits._fill_labeled_input(page, label, value):
            fills.append(label.lower().replace(" ", "_"))
            continue
        try:
            loc = page.get_by_label(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.fill(value, timeout=5000)
                fills.append(label.lower().replace(" ", "_"))
        except Exception:
            pass

    for txt in ("South Korea", "Korea", "Pre-seed", "Bootstrapped", "No funding", "Artificial intelligence", "AI"):
        try:
            opt = page.get_by_text(txt, exact=False).first
            if opt.count() and opt.is_visible(timeout=1000):
                opt.click(timeout=5000)
                fills.append(f"pick:{txt[:16]}")
        except Exception:
            continue

    for cb in page.locator("input[type='checkbox']").all():
        try:
            if cb.is_visible(timeout=500) and not cb.is_checked():
                cb.check(timeout=3000)
                fills.append("checkbox")
        except Exception:
            continue

    run["portal_fills"] = fills
    run["portal_url"] = page.url[:200]
    errs = benefits._validation_error_count(page)
    run["validation_errors"] = errs
    if errs == 0:
        for btn in ("Submit", "Apply", "Continue", "Next", "Sign up", "Register"):
            try:
                b = page.get_by_role("button", name=btn, exact=False).first
                if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                    b.click(timeout=8000)
                    page.wait_for_timeout(3000)
                    run["submitted"] = btn
                    run["submit_ok"] = benefits._validation_error_count(page) == 0
                    break
            except Exception:
                continue


def main() -> int:
    from playwright.sync_api import sync_playwright

    answers = benefits._load_form_answers()
    cfg = answers.get("azure") or {}
    gcp = answers.get("gcp") or {}
    # no1kmedi.com = Google Workspace (NVIDIA/Lambda contact), not Microsoft identity
    email = str(
        cfg.get("microsoft_account_email")
        or gcp.get("google_account_email")
        or benefits._pointer_email()
    )
    run: dict = {"submit_ok": False, "email": email}

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ms = _find_page(browser, "login.microsoftonline.com")
        azure_portal = _find_page(browser, "portal.azure.com")
        portal = _find_page(browser, "portal.startups.microsoft.com")

        if azure_portal and "AzureForStartups" in (azure_portal.url or ""):
            azure_portal.bring_to_front()
            run["azure_portal_url"] = azure_portal.url[:250]
            try:
                modal = azure_portal.locator(".fxs-modalupdatecontact-container")
                if modal.count() and modal.is_visible(timeout=2000):
                    inp = modal.locator("input[type='text'], input[type='email']").first
                    if inp.count():
                        inp.fill(email, timeout=5000)
                        run["contact_email_updated"] = email
                    for btn in ("업데이트", "Update"):
                        b = modal.get_by_role("button", name=btn, exact=False).first
                        if b.count() and b.is_visible(timeout=1500):
                            b.click(timeout=8000)
                            azure_portal.wait_for_timeout(3000)
                            run["contact_modal_dismissed"] = btn
                            break
            except Exception:
                pass
            for fr in azure_portal.frames:
                try:
                    if "코드 없이" not in (fr.inner_text("body", timeout=1500) or ""):
                        continue
                    el = fr.get_by_text("코드 없이 계속", exact=False).first
                    if el.count() and el.is_visible(timeout=2000):
                        el.click(timeout=8000)
                        azure_portal.wait_for_timeout(3000)
                        run["referral_skipped"] = True
                        break
                except Exception:
                    continue
            for fr in azure_portal.frames:
                try:
                    txt = fr.inner_text("body", timeout=2000) or ""
                    if "LinkedIn" in txt:
                        run["human_gate"] = "linkedin_verification_for_azure_credits"
                        run["hint"] = "Azure 포털 Microsoft for Startups에서 'LinkedIn으로 확인' 클릭"
                        break
                except Exception:
                    continue

        if ms and not run.get("azure_portal_url"):
            ms.bring_to_front()
            _prefill_ms_login(ms, email, run)

        portal = _find_page(browser, "portal.startups.microsoft.com")
        if portal is None and not run.get("human_gate"):
            page = browser.contexts[0].new_page()
            page.goto(SIGNUP, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(3000)
            portal = page
        if portal and "portal.startups.microsoft.com" in (portal.url or ""):
            portal.bring_to_front()
            _fill_startup_portal(portal, cfg, run)
        elif _find_page(browser, "microsoft.com/en-us/startups"):
            land = _find_page(browser, "microsoft.com/en-us/startups")
            land.bring_to_front()
            run["landing_url"] = land.url[:200]
            for btn in ("Sign up", "Get started", "Apply now", "Join"):
                try:
                    b = land.get_by_role("link", name=btn, exact=False).first
                    if b.count() and b.is_visible(timeout=2000):
                        b.click(timeout=8000)
                        land.wait_for_timeout(4000)
                        run["landing_clicked"] = btn
                        break
                except Exception:
                    continue
            portal = _find_page(browser, "portal.startups.microsoft.com", "login.microsoftonline.com")
            if portal and "portal.startups.microsoft.com" in (portal.url or ""):
                _fill_startup_portal(portal, cfg, run)
            elif portal and "login.microsoftonline.com" in (portal.url or ""):
                _prefill_ms_login(portal, email, run)

        shot = ROOT / "reports/nvidia_azure_startup_fill_latest.png"
        try:
            tab = (
                _find_page(browser, "portal.startups.microsoft.com")
                or _find_page(browser, "login.microsoftonline.com")
                or _find_page(browser, "microsoft.com/en-us/startups")
            )
            if tab:
                tab.screenshot(path=str(shot), full_page=True, timeout=20_000)
                run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submit_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
