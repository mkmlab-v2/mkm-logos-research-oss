#!/usr/bin/env python3
"""CDP: complete Azure login on giryun288 tenant tab (GitHub or outlook tile)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_tenant_login_finish_latest.json"
TENANT_LOGIN = (
    "https://login.microsoftonline.com/giryun288gmail.onmicrosoft.com/oauth2/v2.0/authorize"
    "?client_id=c44b4083-3bb0-49c1-b47d-974e53cbdf3c"
    "&redirect_uri=https%3A%2F%2Fportal.azure.com%2Fauth%2Flogin%2F"
    "&response_type=code&scope=openid+profile+offline_access"
)
PORTAL = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/resource/subscriptions/"
    "d2ccdc4f-531a-42dd-b05e-edea4961acf0/overview"
)
STARTUPS = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)
NVIDIA = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    try:
        return page.inner_text("body", timeout=12_000) or ""
    except Exception:
        return ""


def _tenant_ok(text: str) -> bool:
    return "giryun288gmail" in text.lower() or "MKM-Startups" in text


def _click_text(page, *labels: str) -> str | None:
    for label in labels:
        for role in ("button", "link"):
            try:
                loc = page.get_by_role(role, name=label, exact=False).first
                if loc.count() and loc.is_visible(timeout=1200):
                    loc.click(timeout=8000)
                    page.wait_for_timeout(4000)
                    return f"{role}:{label}"
            except Exception:
                pass
        try:
            loc = page.get_by_text(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=1200):
                loc.click(timeout=8000)
                page.wait_for_timeout(4000)
                return f"text:{label}"
        except Exception:
            pass
    return None


def _login_flow(page, run: dict[str, Any]) -> None:
    body = _text(page)
    if "계정 선택" in body or "Pick an account" in body:
        run["account_picker"] = True
        # Prefer cached giryun288 tile on tenant-specific login
        for label in ("giryun288@gmail.com", "giryun lee"):
            hit = _click_text(page, label)
            if hit:
                run["picked"] = hit
                page.wait_for_timeout(8000)
                return
        other = _click_text(page, "다른 계정 사용", "Use another account")
        if other:
            run["other_account"] = other
        gh = _click_text(page, "Sign in with GitHub", "GitHub로 로그인", "GitHub")
        if gh:
            run["github"] = gh
            if "github.com" in (page.url or "").lower():
                run["human_gate"] = "github_password_in_cdp"
                return
        for label in ("giryun@outlook.com", "기륜 이"):
            hit = _click_text(page, label)
            if hit:
                run["picked_fallback"] = hit
                page.wait_for_timeout(6000)
                break


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_tenant_login_finish_v1",
        "generated_at_utc": _utc(),
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next(
            (
                pg
                for pg in ctx.pages
                if "giryun288gmail.onmicrosoft.com" in (pg.url or "")
            ),
            None,
        )
        if page is None:
            page = ctx.new_page()
            page.goto(TENANT_LOGIN, wait_until="domcontentloaded", timeout=120_000)
        page.bring_to_front()
        page.wait_for_timeout(2000)
        run["start_url"] = page.url[:320]

        _login_flow(page, run)
        if not run.get("human_gate") and "portal.azure.com" not in (page.url or ""):
            page.wait_for_timeout(5000)
            if "portal.azure.com" not in (page.url or ""):
                page.goto(PORTAL, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(8000)

        text = _text(page)
        run["portal_url"] = page.url[:320]
        run["tenant_ok"] = _tenant_ok(text) and "moksorinwgmail" not in text.lower()
        run["snippet"] = text[:900].replace("\n", " | ")

        steps: list[dict[str, Any]] = []
        if run.get("tenant_ok"):
            for url, label in ((STARTUPS, "startups"), (NVIDIA, "nvidia_benefit")):
                step: dict[str, Any] = {"label": label}
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                    page.wait_for_timeout(8000)
                    t = _text(page)
                    step["url"] = page.url[:320]
                    step["snippet"] = t[:700].replace("\n", " | ")
                    if label == "nvidia_benefit":
                        for btn in ("Get started now", "Get started", "Apply now"):
                            hit = _click_text(page, btn)
                            if hit:
                                step["clicked"] = hit
                                page.wait_for_timeout(5000)
                                step["after_url"] = page.url[:320]
                                step["after_snippet"] = _text(page)[:600].replace("\n", " | ")
                                break
                    shot = ROOT / f"reports/nvidia_azure_tenant_{label}_latest.png"
                    page.screenshot(path=str(shot), full_page=True, timeout=35_000)
                    step["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
                except Exception as exc:
                    step["error"] = str(exc)[:200]
                steps.append(step)
        run["steps"] = steps

        shot = ROOT / "reports/nvidia_azure_tenant_login_finish_latest.png"
        page.screenshot(path=str(shot), full_page=True, timeout=35_000)
        run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")

    run["verdict"] = (
        "tenant_ok_probed"
        if run.get("tenant_ok")
        else (run.get("human_gate") or "login_incomplete_in_cdp")
    )
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("tenant_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
