#!/usr/bin/env python3
"""Azure MKM-Startups-Prod tenant: scan credits + Startups + NVIDIA $5K apply (CDP)."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "reports/nvidia_azure_giryun288_apply_chain_latest.json"
TENANT = "e984d55e-e522-431a-b5fd-c81bddea216d"
SUB_ID = "d2ccdc4f-531a-42dd-b05e-edea4961acf0"
PORTAL = f"https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/resource/subscriptions/{SUB_ID}/overview"
STARTUPS = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)
BILLING = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_GTM/ModernBillingMenuBlade/~/BillingAccounts"
)
NVIDIA = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)
SIGNUP = "https://portal.startups.microsoft.com/signup"

from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal, refuse_login_navigation

_spec = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benefits)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    parts: list[str] = []
    try:
        parts.append(page.inner_text("body", timeout=12_000) or "")
    except Exception:
        pass
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=2500) or ""
            if len(t) > 80:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def _tenant_ok(text: str) -> bool:
    return any(
        k in text.lower()
        for k in (
            "giryun288gmail",
            "mkm-startups-prod",
            "e984d55e",
        )
    )


def _logged_in(text: str) -> bool:
    if "sign in" in text.lower()[:600] and "portal.azure.com" not in text.lower()[:200]:
        return False
    if "계정 선택" in text and "github" in text.lower():
        return False
    return _tenant_ok(text) or "MKM-Startups" in text


def _probe(page, url: str, label: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(8000)
    text = _text(page)
    out: dict[str, Any] = {
        "label": label,
        "url": page.url[:320],
        "logged_in": _logged_in(text),
        "tenant_ok": _tenant_ok(text),
        "amounts": list(dict.fromkeys(re.findall(r"\$[\d,]+", text)))[:15],
        "has_credits": bool(re.search(r"credit|크레딧|remaining|잔액|balance", text, re.I)),
        "ineligible": any(k in text for k in ("받을 수 없음", "not eligible", "ineligible")),
        "linkedin_gate": "LinkedIn" in text,
        "snippet": text[:1800].replace("\n", " | "),
    }
    shot = ROOT / f"reports/nvidia_azure_giryun288_{label}_apply_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=35_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    if label == "nvidia_benefit":
        for btn in ("Get started now", "Get started", "Apply now", "Sign up", "Claim"):
            try:
                b = page.get_by_role("link", name=btn, exact=False).first
                if b.count() and b.is_visible(timeout=2000):
                    b.click(timeout=8000)
                    page.wait_for_timeout(5000)
                    out["benefit_clicked"] = btn
                    out["after_click_url"] = page.url[:320]
                    out["after_click_snippet"] = _text(page)[:800].replace("\n", " | ")
                    break
            except Exception:
                continue
    if label == "startups_hub" and out.get("linkedin_gate"):
        for fr in page.frames:
            try:
                li = fr.get_by_text("LinkedIn", exact=False).first
                if li.count() and li.is_visible(timeout=1500):
                    out["linkedin_button_visible"] = True
                    break
            except Exception:
                continue
    return out


def _fill_startup_portal(page, run: dict[str, Any]) -> None:
    cfg = benefits._load_form_answers().get("azure") or {}
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
                fills.append(label)
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
    for cb in page.locator("input[type='checkbox']").all()[:8]:
        try:
            if cb.is_visible(timeout=500) and not cb.is_checked():
                cb.check(timeout=3000)
                fills.append("checkbox")
        except Exception:
            continue
    run["portal_fills"] = fills
    run["validation_errors"] = benefits._validation_error_count(page)
    if run["validation_errors"] == 0:
        for btn in ("Submit", "Apply", "Continue", "Next", "Sign up", "Register", "Get started"):
            try:
                b = page.get_by_role("button", name=btn, exact=False).first
                if b.count() and b.is_visible(timeout=2000) and b.is_enabled():
                    b.click(timeout=8000)
                    page.wait_for_timeout(4000)
                    run["submitted"] = btn
                    run["submit_ok"] = benefits._validation_error_count(page) == 0
                    break
            except Exception:
                continue


def _wrong_tenant(text: str) -> bool:
    return "moksorinwgmail" in text.lower() or "moksorinw@gmail.com" in text


def _switch_to_giryun288_tenant(page, run: dict[str, Any]) -> bool:
    text = _text(page)
    if _tenant_ok(text) and not _wrong_tenant(text):
        run["tenant_switch"] = "already_giryun288"
        return True

    # Force tenant via #@domain deep link
    page.goto(PORTAL, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(8000)
    text = _text(page)
    if _tenant_ok(text) and not _wrong_tenant(text):
        run["tenant_switch"] = "deep_link_ok"
        return True

    # Portal directory switcher UI
    for sel in (
        "button[aria-label*='디렉터리']",
        "button[aria-label*='Directory']",
        "#navbar-subtitle",
    ):
        try:
            btn = page.locator(sel).first
            if btn.count() and btn.is_visible(timeout=2000):
                btn.click(timeout=5000)
                page.wait_for_timeout(2000)
                run["tenant_switch_clicked"] = sel
                break
        except Exception:
            continue
    for label in (
        "giryun288gmail.onmicrosoft.com",
        "giryun288@gmail.com",
        "Default Directory",
        "기본 디렉터리",
        "Switch directory",
        "디렉터리 전환",
    ):
        try:
            loc = page.get_by_text(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.click(timeout=8000)
                page.wait_for_timeout(5000)
                run["tenant_switch_picked"] = label
                break
        except Exception:
            continue

    page.goto(PORTAL, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(8000)
    text = _text(page)
    ok = _tenant_ok(text) and not _wrong_tenant(text)
    run["tenant_switch"] = "switch_ui_ok" if ok else "switch_failed_still_wrong_tenant"
    run["tenant_snippet"] = text[:500].replace("\n", " | ")
    return ok


def _find_logged_in_portal(browser):
    """Reuse existing CDP tab if user already logged into Azure portal."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            url = (pg.url or "").lower()
            if "portal.azure.com" not in url:
                continue
            try:
                text = _text(pg)
            except Exception:
                continue
            if _tenant_ok(text) and not _wrong_tenant(text):
                return pg, True
            if "portal.azure.com" in url and not _wrong_tenant(text):
                return pg, _tenant_ok(text)
    return None, False


def _steer_github_login(page, run: dict[str, Any]) -> None:
    """Reuse login picker → GitHub path when MS account cache is wrong."""
    body = _text(page)
    if "github.com/login" in (page.url or "").lower():
        run["human_gate"] = "complete_github_oauth_in_cdp"
        return
    if "계정 선택" in body or "Pick an account" in body:
        for label in ("다른 계정 사용", "Use another account"):
            try:
                loc = page.get_by_role("button", name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(2500)
                    run["login_other_account"] = label
                    break
            except Exception:
                continue
    for label in ("Sign in with GitHub", "GitHub로 로그인", "GitHub"):
        try:
            loc = page.get_by_role("button", name=label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.click(timeout=8000)
                page.wait_for_timeout(4000)
                run["github_login_clicked"] = label
                break
        except Exception:
            continue
    if "github.com" in (page.url or "").lower():
        run["human_gate"] = "complete_github_oauth_in_cdp"


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_giryun288_apply_chain_v1",
        "generated_at_utc": _utc(),
        "tenant_id": TENANT,
        "subscription": "MKM-Startups-Prod",
        "login_method": "reuse_cdp_portal_tab_only",
        "steps": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if page is None:
            refuse_login_navigation(
                run,
                "no_giryun288_portal_tab — new_page/OAuth disabled to prevent login loop",
            )
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run["summary"] if "summary" in run else run, ensure_ascii=False, indent=2))
            return 2

        page.bring_to_front()
        run["reused_portal_tab"] = True
        run["portal_tab_url"] = page.url[:320]

        if not _tenant_ok(_text(page)) or _wrong_tenant(_text(page)):
            run["human_gate"] = "switch_cdp_directory_to_giryun288gmail"
            run["hint"] = (
                "포털 우상단 디렉터리 → giryun288gmail.onmicrosoft.com. "
                "login/github 탭 닫기 — 스크립트는 OAuth 재시도 안 함."
            )
            refuse_login_navigation(run, "wrong_tenant_on_reused_tab")
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            return 2

        for url, label in (
            (PORTAL, "portal_home"),
            (STARTUPS, "startups_hub"),
            (BILLING, "billing"),
            (NVIDIA, "nvidia_benefit"),
        ):
            try:
                run["steps"].append(_probe(page, url, label))
            except Exception as exc:
                run["steps"].append({"label": label, "error": str(exc)[:200]})

        apply: dict[str, Any] = {"label": "startup_signup_apply"}
        try:
            page.goto(SIGNUP, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(5000)
            apply["url"] = page.url[:320]
            apply["snippet"] = _text(page)[:800].replace("\n", " | ")
            if "login.microsoftonline.com" not in page.url:
                _fill_startup_portal(page, apply)
            else:
                apply["human_gate"] = "ms_login_on_signup"
            shot = ROOT / "reports/nvidia_azure_giryun288_signup_apply_latest.png"
            page.screenshot(path=str(shot), full_page=True, timeout=35_000)
            apply["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception as exc:
            apply["error"] = str(exc)[:200]
        run["steps"].append(apply)

    home = next((s for s in run["steps"] if s.get("label") == "portal_home"), {})
    startups = next((s for s in run["steps"] if s.get("label") == "startups_hub"), {})
    signup = next((s for s in run["steps"] if s.get("label") == "startup_signup_apply"), {})
    run["summary"] = {
        "tenant_reached": home.get("tenant_ok") or startups.get("tenant_ok"),
        "logged_in": home.get("logged_in"),
        "credit_amounts": list(
            dict.fromkeys(
                a for s in run["steps"] for a in (s.get("amounts") or [])
            )
        ),
        "startups_ineligible": startups.get("ineligible"),
        "linkedin_gate": startups.get("linkedin_gate"),
        "signup_submit_ok": signup.get("submit_ok"),
        "verdict": (
            "applied_or_on_signup"
            if signup.get("submit_ok")
            else (
                "tenant_ok_probe_done"
                if home.get("tenant_ok")
                else "need_github_login_on_tenant_url"
            )
        ),
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0 if run["summary"].get("tenant_reached") else 2


if __name__ == "__main__":
    raise SystemExit(main())
