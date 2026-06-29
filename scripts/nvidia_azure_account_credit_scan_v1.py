#!/usr/bin/env python3
"""Scan Azure tenants/billing for existing credits + attempt Inception top-up (CDP)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_account_credit_scan_latest.json"

AZURE_HOME = "https://portal.azure.com/#home"
BILLING_SCOPES = "https://portal.azure.com/#view/Microsoft_Azure_GTM/ModernBillingMenuBlade/~/BillingScopes"
SUBSCRIPTIONS = "https://portal.azure.com/#view/HubsExtension/BrowseResource/subscriptions"
STARTUPS_HUB = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    "AzureForStartups.ReactView/skipWizardRedirect~/true"
)
FOUNDERS_PORTAL = "https://portal.startups.microsoft.com/"
NVIDIA_AZURE = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)


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
            if len(t) > 80:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def _amounts(text: str) -> list[str]:
    return list(
        dict.fromkeys(
            re.findall(r"(?:\$|USD\s*|₩)\s*[\d,]+(?:\.\d{2})?|[\d,]+\s*(?:USD|원)", text)
        )
    )[:20]


def _probe(page, url: str, label: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(8000)
    text = _all_text(page)
    out: dict[str, Any] = {
        "label": label,
        "url": page.url[:320],
        "logged_in": "moksorinw@gmail.com" in text or "onmicrosoft.com" in text.lower(),
        "tenant_hint": None,
        "amounts": _amounts(text),
        "has_active_credits": bool(
            re.search(r"remaining|잔액|active credit|사용 가능|balance", text, re.I)
        ),
        "ineligible": any(k in text for k in ("받을 수 없음", "not eligible", "ineligible")),
        "linkedin_gate": "LinkedIn" in text,
        "nvidia_inception": bool(re.search(r"nvidia|inception", text, re.I)),
        "snippet": text[:2000].replace("\n", " | "),
    }
    m = re.search(r"기본 디렉터리\(([^)]+)\)|default directory\s*\(([^)]+)\)", text, re.I)
    if m:
        out["tenant_hint"] = (m.group(1) or m.group(2) or "").strip()
    shot = ROOT / f"reports/nvidia_azure_scan_{label}_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=35_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def _click_billing_credits(page, run: dict[str, Any]) -> None:
    step: dict[str, Any] = {"label": "billing_account_credits_drill", "clicks": []}
    try:
        page.goto(BILLING_SCOPES, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(6000)
        for name in ("lee ryun", "lee", "mkmlab", "no1kmedi"):
            try:
                row = page.get_by_text(name, exact=False).first
                if row.count() and row.is_visible(timeout=2000):
                    row.click(timeout=8000)
                    page.wait_for_timeout(4000)
                    step["clicks"].append(f"scope:{name}")
                    break
            except Exception:
                continue
        for link in ("크레딧", "Credits", "청구 크레딧"):
            try:
                lnk = page.get_by_role("link", name=link, exact=False).first
                if not lnk.count():
                    lnk = page.get_by_text(link, exact=False).first
                if lnk.count() and lnk.is_visible(timeout=2000):
                    lnk.click(timeout=8000)
                    page.wait_for_timeout(5000)
                    step["clicks"].append(link)
                    break
            except Exception:
                continue
        text = _all_text(page)
        step["url"] = page.url[:320]
        step["amounts"] = _amounts(text)
        step["credit_rows"] = []
        for line in text.splitlines():
            if any(k in line.lower() for k in ("credit", "크레딧", "promo", "startup", "nvidia")):
                step["credit_rows"].append(line.strip()[:200])
        step["snippet"] = text[:1500].replace("\n", " | ")
        shot = ROOT / "reports/nvidia_azure_scan_billing_credits_drill_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=35_000)
        step["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    except Exception as exc:
        step["error"] = str(exc)[:200]
    run["billing_drill"] = step


def _try_directory_list(page, run: dict[str, Any]) -> None:
    step: dict[str, Any] = {"label": "directory_switcher", "directories": []}
    try:
        page.goto(AZURE_HOME, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(4000)
        for sel in (
            "button[aria-label*='디렉터리']",
            "button[aria-label*='directory']",
            "#navbar-subtitle",
        ):
            try:
                btn = page.locator(sel).first
                if btn.count() and btn.is_visible(timeout=2000):
                    btn.click(timeout=5000)
                    page.wait_for_timeout(2000)
                    break
            except Exception:
                continue
        text = _all_text(page)
        for m in re.finditer(r"([A-Za-z0-9._-]+onmicrosoft\.com)", text, re.I):
            step["directories"].append(m.group(1))
        step["directories"] = list(dict.fromkeys(step["directories"]))
        step["snippet"] = text[:800].replace("\n", " | ")
    except Exception as exc:
        step["error"] = str(exc)[:200]
    run["directories"] = step


def _attempt_nvidia_benefit(page, run: dict[str, Any]) -> None:
    step: dict[str, Any] = {"label": "nvidia_azure_benefit_apply"}
    try:
        page.goto(NVIDIA_AZURE, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(5000)
        for btn in ("Get started", "Apply now", "Sign up", "Activate", "Claim", "Continue"):
            try:
                b = page.get_by_role("link", name=btn, exact=False).first
                if b.count() and b.is_visible(timeout=2000):
                    b.click(timeout=8000)
                    page.wait_for_timeout(4000)
                    step["clicked"] = btn
                    break
            except Exception:
                continue
        text = _all_text(page)
        step["url"] = page.url[:320]
        step["amounts"] = _amounts(text)
        step["snippet"] = text[:1200].replace("\n", " | ")
        shot = ROOT / "reports/nvidia_azure_scan_nvidia_benefit_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=35_000)
        step["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    except Exception as exc:
        step["error"] = str(exc)[:200]
    run["nvidia_benefit"] = step


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_account_credit_scan_v1",
        "generated_at_utc": _utc(),
        "pages": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "portal.azure.com" in (pg.url or "")), None)
        if page is None:
            page = ctx.new_page()
        page.bring_to_front()
        for url, label in (
            (AZURE_HOME, "home"),
            (BILLING_SCOPES, "billing_scopes"),
            (SUBSCRIPTIONS, "subscriptions"),
            (STARTUPS_HUB, "startups_hub"),
            (FOUNDERS_PORTAL, "founders_portal"),
        ):
            try:
                run["pages"].append(_probe(page, url, label))
            except Exception as exc:
                run["pages"].append({"label": label, "error": str(exc)[:200]})
        _try_directory_list(page, run)
        _click_billing_credits(page, run)
        _attempt_nvidia_benefit(page, run)
        page.close()

    accounts: list[dict[str, Any]] = []
    for p in run["pages"]:
        accounts.append(
            {
                "surface": p.get("label"),
                "tenant": p.get("tenant_hint"),
                "amounts": p.get("amounts"),
                "has_active_credits": p.get("has_active_credits"),
                "ineligible": p.get("ineligible"),
            }
        )
    drill = run.get("billing_drill") or {}
    best_credit_account = None
    if drill.get("amounts") and drill.get("credit_rows"):
        best_credit_account = {
            "billing_scope": "lee ryun",
            "amounts": drill.get("amounts"),
            "rows": drill.get("credit_rows")[:10],
        }
    run["summary"] = {
        "logged_in": any(p.get("logged_in") for p in run["pages"]),
        "tenants_seen": run.get("directories", {}).get("directories", []),
        "accounts_with_credit_hints": [a for a in accounts if a.get("amounts") or a.get("has_active_credits")],
        "best_billing_credit_drill": best_credit_account,
        "startups_ineligible": any(p.get("ineligible") for p in run["pages"] if p.get("label") == "startups_hub"),
        "verdict": (
            "credits_found_on_billing_drill"
            if best_credit_account
            else (
                "no_credits_only_ineligible_startups"
                if any(p.get("ineligible") for p in run["pages"])
                else "no_credits_detected"
            )
        ),
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
