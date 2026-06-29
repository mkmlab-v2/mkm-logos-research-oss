#!/usr/bin/env python3
"""Open giryun288 Azure portal in CDP once — pick cached account only, no OAuth loop."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nvidia_azure_cdp_session_guard_v1 import is_giryun288_session, is_login_url

OUT = ROOT / "reports/nvidia_azure_cdp_open_portal_once_latest.json"
PORTAL = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/resource/subscriptions/"
    "d2ccdc4f-531a-42dd-b05e-edea4961acf0/overview"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    try:
        return page.inner_text("body", timeout=12_000) or ""
    except Exception:
        return ""


def _pick_giryun_once(page, run: dict[str, Any]) -> None:
    body = _text(page)
    if "계정 선택" not in body and "Pick an account" not in body:
        return
    run["account_picker_seen"] = True
    for label in ("giryun288@gmail.com", "giryun lee"):
        try:
            loc = page.get_by_text(label, exact=False).first
            if loc.count() and loc.is_visible(timeout=2000):
                loc.click(timeout=8000)
                page.wait_for_timeout(8000)
                run["picked"] = label
                return
        except Exception:
            continue
    run["human_gate"] = "click_giryun288_on_account_picker_in_cdp"


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_cdp_open_portal_once_v1",
        "generated_at_utc": _utc(),
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = ctx.new_page()
        run["opened_azure_tab"] = True

        page.bring_to_front()
        page.goto(PORTAL, wait_until="domcontentloaded", timeout=120_000)
        page.wait_for_timeout(5000)
        _pick_giryun_once(page, run)
        if not run.get("human_gate"):
            page.wait_for_timeout(5000)

        run["final_url"] = page.url[:320]
        text = _text(page)
        run["tenant_ok"] = is_giryun288_session(text) and not is_login_url(page.url or "")
        run["snippet"] = text[:800].replace("\n", " | ")
        shot = ROOT / "reports/nvidia_azure_cdp_open_portal_once_latest.png"
        try:
            page.screenshot(path=str(shot), full_page=True, timeout=20_000)
            run["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
        except Exception:
            pass

    run["verdict"] = "tenant_ok" if run.get("tenant_ok") else (run.get("human_gate") or "await_portal_load")
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0 if run.get("tenant_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
