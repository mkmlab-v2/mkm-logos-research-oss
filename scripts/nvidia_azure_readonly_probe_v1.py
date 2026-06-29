#!/usr/bin/env python3
"""Read-only Azure startups probe — NO login, NO new OAuth tabs."""
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

from nvidia_azure_cdp_session_guard_v1 import (  # noqa: E402
    find_giryun288_portal,
    is_giryun288_session,
    refuse_login_navigation,
)

OUT = ROOT / "reports/nvidia_azure_readonly_probe_latest.json"
BLADE = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)
SUB = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/resource/subscriptions/"
    "d2ccdc4f-531a-42dd-b05e-edea4961acf0/overview"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    parts = []
    try:
        parts.append(page.inner_text("body", timeout=15_000) or "")
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


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_readonly_probe_v1",
        "generated_at_utc": _utc(),
        "steps": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = find_giryun288_portal(browser)
        if page is None:
            refuse_login_navigation(run, "no_giryun288_portal_tab_in_cdp")
            OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(run, ensure_ascii=False, indent=2))
            return 2

        page.bring_to_front()
        run["reused_tab"] = page.url[:320]

        for url, label in ((SUB, "subscription"), (BLADE, "startups_blade")):
            step: dict[str, Any] = {"label": label}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=90_000)
                page.wait_for_timeout(8000)
                text = _text(page)
                step["url"] = page.url[:320]
                step["tenant_ok"] = is_giryun288_session(text)
                step["amounts"] = list(dict.fromkeys(re.findall(r"\$[\d,]+", text)))[:12]
                step["credits_remaining"] = bool(re.search(r"남은|remaining|크레딧", text, re.I))
                step["verify_cta"] = any(k in text for k in ("시작 확인", "Verify your startup"))
                step["snippet"] = text[:1500].replace("\n", " | ")
                shot = ROOT / f"reports/nvidia_azure_readonly_{label}_latest.png"
                page.screenshot(path=str(shot), full_page=True, timeout=15_000)
                step["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
            except Exception as exc:
                step["error"] = str(exc)[:200]
            run["steps"].append(step)

    blade = next((s for s in run["steps"] if s.get("label") == "startups_blade"), {})
    run["summary"] = {
        "tenant_ok": blade.get("tenant_ok"),
        "amounts": blade.get("amounts"),
        "credits_remaining": blade.get("credits_remaining"),
        "verdict": "ok_readonly" if blade.get("tenant_ok") else "tab_not_giryun288",
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0 if blade.get("tenant_ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
