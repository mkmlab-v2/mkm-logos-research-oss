#!/usr/bin/env python3
"""Nebius Inception credits — landing form + auth.nebius.com prefill (Tier-3 password human)."""
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

OUT = ROOT / "reports/nvidia_nebius_finish_latest.json"
LANDING = (
    "https://nebius.com/nebius-nvidia-inception-credit-offering"
    "?utm_campaign=nvidiainception&utm_medium=referral&utm_source=nvidia"
)


def _find_page(browser, *needles: str):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            url = (pg.url or "").lower()
            if any(n.lower() in url for n in needles):
                return pg
    return None


def _fill_nebius_contact_details(page, cfg: dict, run: dict) -> None:
    """auth.tokenfactory.nebius.com/ui/contact-details — post-OAuth onboarding."""
    run["phase"] = "contact_details"
    run["contact_url"] = page.url[:220]
    first = str(cfg.get("first_name") or "Giryun")
    last = str(cfg.get("last_name") or "Lee")
    company = str(
        cfg.get("billing_legal_entity_ko")
        or cfg.get("company_name")
        or benefits._load_form_answers().get("company_name")
        or "주식회사 목소리네트워크"
    )
    fills: list[str] = []

    for label, value in (
        ("First name", first),
        ("Last name", last),
        ("Company", company),
    ):
        filled = False
        try:
            loc = page.get_by_label(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=2500):
                loc.click(timeout=3000)
                loc.fill(value, timeout=5000)
                filled = True
        except Exception:
            pass
        if not filled and benefits._fill_labeled_input(page, label, value):
            filled = True
        if not filled:
            try:
                ph = page.get_by_placeholder(label, exact=False).first
                if ph.count() and ph.is_visible(timeout=1500):
                    ph.fill(value, timeout=5000)
                    filled = True
            except Exception:
                pass
        if filled:
            fills.append(label.lower().replace(" ", "_"))

    run["contact_fills"] = fills

    try:
        body = (page.inner_text("body", timeout=5000) or "").lower()
        run["email_verified"] = "verified" in body and "moksorinw" in body
    except Exception:
        run["email_verified"] = None

    terms_checked = False
    for cb in page.locator("input[type='checkbox']").all():
        try:
            if not cb.is_visible(timeout=800):
                continue
            row = ""
            try:
                row = (cb.locator("xpath=ancestor::label[1]").inner_text(timeout=800) or "").lower()
            except Exception:
                pass
            if not row:
                try:
                    row = (cb.evaluate(
                        "el => (el.closest('div')?.innerText || '').slice(0,200)"
                    ) or "").lower()
                except Exception:
                    row = ""
            if "terms of use" in row or "continue" in row or not terms_checked:
                if not cb.is_checked():
                    cb.check(timeout=5000)
                terms_checked = True
                run["terms_checked"] = True
                break
        except Exception:
            continue

    for btn in ("Continue", "계속"):
        try:
            b = page.get_by_role("button", name=btn, exact=False).first
            if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                b.click(timeout=8000)
                page.wait_for_timeout(4000)
                run["contact_continued"] = btn
                run["after_continue_url"] = page.url[:220]
                break
        except Exception:
            continue

    run["submit_ok"] = bool(run.get("contact_continued")) and len(fills) >= 3


def _fill_nebius_landing(page, cfg: dict, run: dict) -> None:
    email = str(cfg.get("email") or benefits._pointer_email())
    first = str(cfg.get("first_name") or "Giryun")
    last = str(cfg.get("last_name") or "Lee")
    fills: list[str] = []
    page.goto(LANDING, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(2500)
    page.evaluate("document.querySelector('#form')?.scrollIntoView({block:'center'})")
    page.wait_for_timeout(1000)

    mapping = [
        ("First name", first, "input"),
        ("Last name", last, "input"),
        ("Company", str(cfg.get("billing_legal_entity_ko") or "주식회사 목소리네트워크"), "input"),
        ("Email", email, "input"),
        ("Work email", email, "input"),
    ]
    for label, value, _ in mapping:
        if benefits._fill_labeled_input(page, label, value):
            fills.append(label.lower().replace(" ", "_"))
            continue
        try:
            loc = page.get_by_placeholder(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.fill(value, timeout=5000)
                fills.append(f"ph:{label[:12]}")
        except Exception:
            pass

    for cb in page.locator("input[type='checkbox']").all():
        try:
            if cb.is_visible(timeout=500) and not cb.is_checked():
                cb.check(timeout=3000)
                fills.append("checkbox")
        except Exception:
            continue

    run["landing_fills"] = fills
    run["landing_url"] = page.url[:200]

    for btn in ("Subscribe", "Submit", "Sign up", "Apply", "Get started", "Apply now"):
        try:
            b = page.get_by_role("button", name=btn, exact=False).first
            if b.count() and b.is_visible(timeout=2000):
                if not b.is_enabled():
                    page.wait_for_timeout(1500)
                if b.is_enabled():
                    b.click(timeout=8000)
                    page.wait_for_timeout(4000)
                    run["landing_submitted"] = btn
                    body = (page.inner_text("body", timeout=5000) or "").lower()
                    run["landing_thanks"] = any(
                        k in body for k in ("thank", "subscrib", "received", "success", "we'll be in touch")
                    )
                    break
        except Exception:
            continue

    if not run.get("landing_submitted"):
        try:
            form_btn = page.locator("#form button[type='submit'], #form button").first
            if form_btn.count() and form_btn.is_visible(timeout=2000) and form_btn.is_enabled():
                form_btn.click(timeout=8000)
                page.wait_for_timeout(4000)
                run["landing_submitted"] = "form_submit"
                body = (page.inner_text("body", timeout=5000) or "").lower()
                run["landing_thanks"] = any(
                    k in body for k in ("thank", "subscrib", "received", "success")
                )
        except Exception:
            pass

    try:
        link = page.get_by_role("link", name="Log in to AI Cloud", exact=False).first
        if link.count() and link.is_visible(timeout=2000):
            link.click(timeout=8000)
            page.wait_for_timeout(4000)
            run["opened_console_login"] = True
    except Exception:
        pass


def _prefill_nebius_auth(page, cfg: dict, run: dict) -> None:
    run["auth_url"] = page.url[:200]
    for btn_text in ("Allow all", "Required only", "필수만", "모두 허용"):
        try:
            b = page.get_by_role("button", name=btn_text, exact=False).first
            if b.count() and b.is_visible(timeout=1500):
                b.click(timeout=5000)
                page.wait_for_timeout(800)
                run["cookie_dismissed"] = btn_text
                break
        except Exception:
            continue

    provider = str(cfg.get("oauth_provider") or "google").lower()
    oauth_labels = {
        "google": "Get started with Google",
        "microsoft": "Get started with Microsoft",
        "github": "Get started with GitHub",
    }
    label = oauth_labels.get(provider, oauth_labels["google"])
    try:
        b = page.get_by_role("button", name=label, exact=False).first
        if b.count() and b.is_visible(timeout=3000):
            with page.context.expect_page(timeout=15_000) as pinfo:
                b.click(timeout=8000)
            oauth = pinfo.value
            oauth.wait_for_load_state("domcontentloaded", timeout=60_000)
            oauth.wait_for_timeout(2000)
            run["oauth_clicked"] = label
            run["oauth_url"] = oauth.url[:200]
            if "accounts.google.com" in oauth.url:
                run["human_gate"] = "google_account_chooser_or_consent"
            elif "login.microsoftonline.com" in oauth.url:
                run["human_gate"] = "microsoft_password_or_mfa"
            return
    except Exception as exc:
        run["oauth_error"] = str(exc)[:160]
        try:
            b = page.get_by_role("button", name=label, exact=False).first
            if b.count() and b.is_visible(timeout=2000):
                b.click(timeout=8000)
                page.wait_for_timeout(4000)
                run["oauth_clicked"] = label
                run["oauth_url"] = page.url[:200]
                if "accounts.google.com" in page.url:
                    run["human_gate"] = "google_account_chooser_or_consent"
                elif "login.microsoftonline.com" in page.url:
                    run["human_gate"] = "microsoft_password_or_mfa"
        except Exception as exc2:
            run["oauth_same_tab_error"] = str(exc2)[:120]

    run["human_gate"] = run.get("human_gate") or "nebius_oauth_manual"


def main() -> int:
    from playwright.sync_api import sync_playwright

    cfg = benefits._load_form_answers().get("nebius") or {}
    email = str(cfg.get("email") or benefits._pointer_email())
    run: dict = {"submit_ok": False, "email": email}

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        auth = _find_page(
            browser,
            "tokenfactory.nebius.com",
            "auth.nebius.com",
            "console.nebius.com",
        )
        if auth is None:
            ctx = browser.contexts[0]
            page = ctx.new_page()
            _fill_nebius_landing(page, cfg, run)
            auth = (
                _find_page(browser, "tokenfactory.nebius.com", "auth.nebius.com", "console.nebius.com")
                or page
            )
        auth.bring_to_front()
        if "contact-details" in (auth.url or ""):
            _fill_nebius_contact_details(auth, cfg, run)
        elif "accounts.google.com" in (auth.url or ""):
            run["oauth_url"] = auth.url[:200]
            run["human_gate"] = "google_account_chooser_or_consent"
        elif "auth.nebius.com" in (auth.url or ""):
            _prefill_nebius_auth(auth, cfg, run)
        elif "nebius.com/nebius-nvidia" in (auth.url or ""):
            _fill_nebius_landing(auth, cfg, run)
            auth2 = _find_page(browser, "auth.nebius.com", "tokenfactory.nebius.com")
            if auth2:
                auth2.bring_to_front()
                if "contact-details" in (auth2.url or ""):
                    _fill_nebius_contact_details(auth2, cfg, run)
                else:
                    _prefill_nebius_auth(auth2, cfg, run)

        if not run.get("landing_thanks"):
            ctx = browser.contexts[0]
            landing_page = ctx.new_page()
            _fill_nebius_landing(landing_page, cfg, run)
            run["landing_phase"] = "forced_new_tab"

        run["landing_ok"] = bool(run.get("landing_thanks"))
        run["submit_ok"] = run["landing_ok"] or bool(run.get("contact_continued"))
        if run.get("human_gate"):
            run["submit_ok"] = False
        shot = ROOT / "reports/nvidia_nebius_finish_latest.png"
        try:
            tab = (
                _find_page(browser, "tokenfactory.nebius.com")
                or _find_page(browser, "auth.nebius.com")
                or _find_page(browser, "nebius.com")
                or auth
            )
            tab.screenshot(path=str(shot), full_page=True, timeout=20_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    OUT.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("submit_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
