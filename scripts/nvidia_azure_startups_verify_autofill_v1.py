#!/usr/bin/env python3
"""Continue Azure Startups verify wizard on existing giryun288 portal tab (no OAuth loop)."""
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

from nvidia_azure_cdp_session_guard_v1 import find_giryun288_portal, is_giryun288_session, is_login_url

OUT = ROOT / "reports/nvidia_azure_startups_verify_autofill_latest.json"
BLADE = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)
BILLING = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_GTM/ModernBillingMenuBlade/~/BillingAccounts"
)

_spec = importlib.util.spec_from_file_location(
    "benefits", ROOT / "scripts" / "nvidia_inception_benefits_catalog_request_v1.py"
)
benefits = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benefits)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _all_text(page) -> str:
    parts: list[str] = []
    try:
        parts.append(page.inner_text("body", timeout=12_000) or "")
    except Exception:
        pass
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=2500) or ""
            if len(t) > 60:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def _click_any(page, *labels: str) -> str | None:
    for label in labels:
        for role in ("button", "link"):
            try:
                loc = page.get_by_role(role, name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=1500):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(3000)
                    return f"{role}:{label}"
            except Exception:
                pass
        try:
            loc = page.get_by_text(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1200):
                loc.click(timeout=8000)
                page.wait_for_timeout(3000)
                return f"text:{label}"
        except Exception:
            pass
    return None


def _pick_giryun_if_picker(page, run: dict[str, Any]) -> None:
    if not is_login_url(page.url or ""):
        return
    if "계정 선택" not in _all_text(page) and "Pick an account" not in _all_text(page):
        return
    hit = _click_any(page, "giryun288@gmail.com", "giryun lee")
    if hit:
        run["account_picked"] = hit
        page.wait_for_timeout(6000)


def _dismiss_modals(page, cfg: dict, run: dict[str, Any]) -> None:
    email = str(cfg.get("contact_email") or benefits._pointer_email())
    try:
        modal = page.locator(".fxs-modalupdatecontact-container")
        if modal.count() and modal.is_visible(timeout=1500):
            inp = modal.locator("input[type='text'], input[type='email']").first
            if inp.count():
                inp.fill(email, timeout=5000)
                run["contact_email_filled"] = email
            for btn in ("업데이트", "Update"):
                if _click_any(page, btn):
                    run["contact_modal"] = btn
                    break
    except Exception:
        pass
    for fr in page.frames:
        try:
            if "코드 없이" not in (fr.inner_text("body", timeout=1500) or ""):
                continue
            if _click_any(fr, "코드 없이 계속", "Continue without code"):
                run["referral_skipped"] = True
                break
        except Exception:
            continue


def _fill_wizard(page, cfg: dict, run: dict[str, Any]) -> None:
    pointer = benefits._load_pointer()
    inc = pointer.get("inception", {}).get("company_form", {})
    company = str(cfg.get("company_name") or inc.get("display_name") or "mkmlab")
    website = str(cfg.get("website") or inc.get("website") or "https://jema-ai.com")
    contact = str(cfg.get("contact_email") or benefits._pointer_email())
    first = str(cfg.get("first_name") or "Giryun")
    last = str(cfg.get("last_name") or "Lee")
    fills: list[str] = []
    targets = _startup_frames(page)
    mapping = [
        ("Company name", company),
        ("Startup name", company),
        ("Organization", company),
        ("Website", website),
        ("Company website", website),
        ("First name", first),
        ("Last name", last),
        ("Email", contact),
        ("Work email", contact),
    ]
    for target in targets:
        for label, value in mapping:
            if not value:
                continue
            try:
                if benefits._fill_labeled_input(target, label, value):
                    fills.append(label)
                    continue
                loc = target.get_by_label(label, exact=False).first
                if loc.count() and loc.is_visible(timeout=800):
                    loc.fill(value, timeout=4000)
                    fills.append(label)
            except Exception:
                continue
        for txt in (
            "South Korea",
            "Korea",
            "대한민국",
            "Pre-seed",
            "Bootstrapped",
            "Artificial intelligence",
            "AI",
            "B2B",
        ):
            try:
                opt = target.get_by_text(txt, exact=False).first
                if opt.count() and opt.is_visible(timeout=800):
                    opt.click(timeout=4000)
                    fills.append(f"pick:{txt[:12]}")
            except Exception:
                continue
        for cb in target.locator("input[type='checkbox']").all()[:6]:
            try:
                if cb.is_visible(timeout=400) and not cb.is_checked():
                    cb.check(timeout=2000)
                    fills.append("checkbox")
            except Exception:
                continue
    run["fills"] = list(dict.fromkeys(fills))


def _startup_frames(page):
    out = []
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=2000) or ""
        except Exception:
            continue
        if any(k in t for k in ("Microsoft for Startups", "스타트업", "Startup", "LinkedIn", "mkmlab", "Company")):
            if len(t) > 120:
                out.append(fr)
    return out or [page.main_frame]


def _advance_wizard(page, run: dict[str, Any]) -> None:
    clicks: list[str] = []
    for round_i in range(8):
        if "LinkedIn" in _all_text(page):
            run["human_gate"] = "linkedin_oauth_tier3"
            run["hint"] = "LinkedIn 확인은 지휘관 OAuth — 스크립트는 여기서 중단"
            return
        hit = None
        # Round 0: open verify flow
        if round_i == 0:
            for target in _startup_frames(page):
                hit = _click_any(
                    target,
                    "시작 확인",
                    "Verify your startup",
                    "Get verified",
                    "LinkedIn으로 확인",
                )
                if hit:
                    break
        if not hit:
            for target in _startup_frames(page):
                txt = ""
                try:
                    txt = target.inner_text("body", timeout=1500) or ""
                except Exception:
                    pass
                if len(txt) < 80:
                    continue
                hit = _click_any(
                    target,
                    "Continue",
                    "Next",
                    "Submit",
                    "Apply",
                    "Save",
                    "Confirm",
                    "완료",
                    "다음",
                    "제출",
                    "확인",
                )
                if hit:
                    break
        if hit:
            clicks.append(hit)
            page.wait_for_timeout(4000)
            _pick_giryun_if_picker(page, run)
            if is_login_url(page.url or "") and not run.get("account_picked"):
                run["human_gate"] = "unexpected_login_url"
                break
        else:
            break
    run["wizard_clicks"] = clicks


def main() -> int:
    from playwright.sync_api import sync_playwright

    cfg = benefits._load_form_answers().get("azure") or {}
    run: dict[str, Any] = {
        "schema": "nvidia_azure_startups_verify_autofill_v1",
        "generated_at_utc": _utc(),
        "submit_ok": False,
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if page is None:
            run["error"] = "no_giryun288_portal_tab"
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            return 2

        page.bring_to_front()
        if "AzureForStartups" not in (page.url or ""):
            page.goto(BLADE, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(8000)

        run["start_url"] = page.url[:320]
        _dismiss_modals(page, cfg, run)
        _advance_wizard(page, run)
        if not run.get("human_gate"):
            _fill_wizard(page, cfg, run)
            run["validation_errors"] = benefits._validation_error_count(page)
            _advance_wizard(page, run)

        text = _all_text(page)
        run["after_wizard_snippet"] = text[:1500].replace("\n", " | ")
        run["verify_cta_still_visible"] = "시작 확인" in text
        run["linkedin_visible"] = "LinkedIn" in text
        run["amounts"] = list(dict.fromkeys(re.findall(r"\$[\d,]+", text)))[:12]

        if not run.get("human_gate"):
            page.goto(BILLING, wait_until="domcontentloaded", timeout=90_000)
            page.wait_for_timeout(6000)
            bill = _all_text(page)
            run["billing_snippet"] = bill[:800].replace("\n", " | ")
            if _click_any(page, "Giryun Lee", "크레딧", "Credits"):
                page.wait_for_timeout(4000)
                run["billing_credits_snippet"] = _all_text(page)[:800].replace("\n", " | ")

        run["tenant_ok"] = is_giryun288_session(_all_text(page))
        run["submit_ok"] = (
            run.get("tenant_ok")
            and bool(run.get("wizard_clicks"))
            and not run.get("verify_cta_still_visible")
            and not run.get("human_gate")
        )
        if run.get("linkedin_visible") and run.get("verify_cta_still_visible"):
            run["human_gate"] = run.get("human_gate") or "linkedin_verify_needed"

        shot = ROOT / "reports/nvidia_azure_startups_verify_autofill_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=20_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    run["verdict"] = (
        "wizard_advanced"
        if run.get("wizard_clicks")
        else (run.get("human_gate") or "no_clicks")
    )
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("wizard_clicks") or run.get("fills") else 1


if __name__ == "__main__":
    raise SystemExit(main())
