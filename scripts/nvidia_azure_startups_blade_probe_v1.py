#!/usr/bin/env python3
"""Probe existing CDP Azure startups blade + founders portal (no new login)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_startups_blade_probe_latest.json"
BLADE = (
    "https://portal.azure.com/#@giryun288gmail.onmicrosoft.com/"
    "view/Microsoft_Azure_Startups/AzureForStartups.ReactView/skipWizardRedirect~/true"
)
FOUNDERS = "https://portal.startups.microsoft.com/"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _all_text(page) -> str:
    parts = []
    try:
        parts.append(page.inner_text("body", timeout=15_000) or "")
    except Exception:
        pass
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=3000) or ""
            if len(t) > 100:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {"schema": "nvidia_azure_startups_blade_probe_v1", "generated_at_utc": _utc(), "pages": []}

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next(
            (pg for pg in ctx.pages if "AzureForStartups" in (pg.url or "")),
            None,
        )
        if page is None:
            page = ctx.new_page()
        page.bring_to_front()

        for url, label in ((BLADE, "startups_blade"), (FOUNDERS, "founders_portal")):
            block: dict[str, Any] = {"label": label}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(10000)
                text = _all_text(page)
                block["url"] = page.url[:320]
                block["tenant"] = (
                    "giryun288"
                    if "giryun288" in text.lower()
                    else ("moksorinw" if "moksorinw" in text.lower() else None)
                )
                block["amounts"] = list(dict.fromkeys(re.findall(r"\$[\d,]+", text)))[:12]
                block["linkedin"] = "LinkedIn" in text
                block["nvidia"] = bool(re.search(r"nvidia|inception", text, re.I))
                block["verify_startup"] = any(k in text for k in ("Verify your startup", "스타트업 확인", "LinkedIn"))
                block["snippet"] = text[:2000].replace("\n", " | ")
                for btn in ("LinkedIn", "LinkedIn으로 확인", "Verify", "Get started", "Apply"):
                    try:
                        b = page.get_by_role("button", name=btn, exact=False).first
                        if not b.count():
                            b = page.get_by_text(btn, exact=False).first
                        if b.count() and b.is_visible(timeout=1500):
                            block[f"button_visible_{btn}"] = True
                    except Exception:
                        pass
                shot = ROOT / f"reports/nvidia_azure_startups_blade_{label}_latest.png"
                page.screenshot(path=str(shot), full_page=True, timeout=20_000)
                block["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
            except Exception as exc:
                block["error"] = str(exc)[:200]
            run["pages"].append(block)

    blade = next((p for p in run["pages"] if p.get("label") == "startups_blade"), {})
    run["summary"] = {
        "tenant": blade.get("tenant"),
        "amounts": blade.get("amounts"),
        "linkedin_gate": blade.get("linkedin"),
        "verdict": "giryun288_startups_blade_ok" if blade.get("tenant") == "giryun288" else "wrong_tenant_or_loading",
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0 if blade.get("tenant") == "giryun288" else 2


if __name__ == "__main__":
    raise SystemExit(main())
