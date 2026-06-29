#!/usr/bin/env python3
"""CDP: steer Azure login to giryun288 tenant via GitHub (or tenant account picker)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_github_login_latest.json"
TENANT = "e984d55e-e522-431a-b5fd-c81bddea216d"
PORTAL = f"https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/resource/subscriptions/d2ccdc4f-531a-42dd-b05e-edea4961acf0/overview"
STARTUPS = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    f"AzureForStartups.ReactView/skipWizardRedirect~/true&tenant={TENANT}"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _body(page) -> str:
    try:
        return page.inner_text("body", timeout=10_000) or ""
    except Exception:
        return ""


def _click_first(page, *selectors: str) -> str | None:
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.click(timeout=8000)
                page.wait_for_timeout(3000)
                return sel
        except Exception:
            continue
    return None


def _click_text(page, *labels: str) -> str | None:
    for label in labels:
        try:
            for role in ("button", "link"):
                loc = page.get_by_role(role, name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=1200):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(3000)
                    return f"{role}:{label}"
        except Exception:
            continue
        try:
            loc = page.get_by_text(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1200):
                loc.click(timeout=8000)
                page.wait_for_timeout(3000)
                return f"text:{label}"
        except Exception:
            continue
    return None


def _try_github_login(page, run: dict[str, Any]) -> None:
    url = (page.url or "").lower()
    if "github.com" in url:
        run["on_github_oauth"] = True
        run["human_gate"] = "complete_github_oauth_in_cdp"
        return

    clicked = _click_text(
        page,
        "Sign in with GitHub",
        "GitHub로 로그인",
        "GitHub로 계속",
        "GitHub",
    )
    if clicked:
        run["github_clicked"] = clicked
        page.wait_for_timeout(4000)
        if "github.com" in (page.url or "").lower():
            run["on_github_oauth"] = True
            run["human_gate"] = "complete_github_oauth_in_cdp"
        return

    clicked = _click_text(page, "Sign-in options", "로그인 옵션", "다른 방법으로 로그인")
    if clicked:
        run["sign_in_options"] = clicked
        gh = _click_text(page, "Sign in with GitHub", "GitHub", "GitHub로 로그인")
        if gh:
            run["github_clicked"] = gh
            page.wait_for_timeout(4000)
            if "github.com" in (page.url or "").lower():
                run["human_gate"] = "complete_github_oauth_in_cdp"


def _try_account_picker(page, run: dict[str, Any]) -> None:
    body = _body(page)
    if "계정 선택" not in body and "Pick an account" not in body:
        return
    run["account_picker"] = True
    # Wrong cached accounts — use another account → GitHub path
    other = _click_text(page, "다른 계정 사용", "Use another account")
    if other:
        run["other_account"] = other
        page.wait_for_timeout(2500)
        _try_github_login(page, run)
        return
    # Fallback: giryun outlook tile (may map to same org — probe only)
    for label in ("giryun288@gmail.com", "giryun@outlook.com", "기륜"):
        try:
            loc = page.get_by_text(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1500):
                loc.click(timeout=8000)
                page.wait_for_timeout(5000)
                run["picked_account"] = label
                break
        except Exception:
            continue


def _tenant_ok(text: str) -> bool:
    return "giryun288gmail" in text.lower() or "MKM-Startups-Prod" in text


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_github_login_v1",
        "generated_at_utc": _utc(),
        "target_tenant": TENANT,
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next((pg for pg in ctx.pages if "login.microsoftonline.com" in (pg.url or "")), None)
        if page is None:
            page = ctx.new_page()
            page.goto(PORTAL, wait_until="domcontentloaded", timeout=120_000)
        else:
            page.bring_to_front()
        page.wait_for_timeout(3000)
        run["start_url"] = page.url[:320]

        _try_account_picker(page, run)
        if not run.get("human_gate"):
            _try_github_login(page, run)

        if not _tenant_ok(_body(page)) and "portal.azure.com" not in (page.url or ""):
            page.goto(PORTAL, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(8000)
            _try_account_picker(page, run)
            if not run.get("human_gate"):
                _try_github_login(page, run)

        text = _body(page)
        run["after_login_url"] = page.url[:320]
        run["tenant_ok"] = _tenant_ok(text) or "portal.azure.com" in (page.url or "")
        run["snippet"] = text[:900].replace("\n", " | ")

        if run["tenant_ok"] and "portal.azure.com" in (page.url or ""):
            page.goto(STARTUPS, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_timeout(8000)
            run["startups_url"] = page.url[:320]
            run["startups_snippet"] = _body(page)[:700].replace("\n", " | ")

        shot = ROOT / "reports/nvidia_azure_github_login_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=35_000)
        run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")

    run["verdict"] = (
        "tenant_reached"
        if run.get("tenant_ok")
        else (run.get("human_gate") or "need_manual_github_login")
    )
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("tenant_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
