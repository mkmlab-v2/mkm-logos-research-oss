#!/usr/bin/env python3
"""Azure credit scan on giryun288 / MKM-Startups-Prod tenant (CDP)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_giryun288_credit_scan_latest.json"

TENANT_ID = "e984d55e-e522-431a-b5fd-c81bddea216d"
SUB_ID = "d2ccdc4f-531a-42dd-b05e-edea4961acf0"
PORTAL = f"https://portal.azure.com/#home?tenant={TENANT_ID}"
STARTUPS = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    f"AzureForStartups.ReactView/skipWizardRedirect~/true&tenant={TENANT_ID}"
)
NVIDIA_BENEFIT = (
    "https://www.microsoft.com/en-us/startups"
    "?benefit-activity-id=aG9Vv000000c5BZKAY"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page) -> str:
    parts = []
    try:
        parts.append(page.inner_text("body", timeout=12_000) or "")
    except Exception:
        pass
    for fr in page.frames:
        try:
            t = fr.inner_text("body", timeout=2000) or ""
            if len(t) > 80:
                parts.append(t)
        except Exception:
            continue
    return "\n".join(parts)


def _cli_snapshot() -> dict[str, Any]:
    out: dict[str, Any] = {"label": "az_cli"}
    try:
        r = subprocess.run(
            ["az", "account", "show", "--output", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            out["account"] = json.loads(r.stdout)
    except Exception as exc:
        out["error"] = str(exc)[:200]
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_giryun288_credit_scan_v1",
        "generated_at_utc": _utc(),
        "target": {
            "email": "giryun288@gmail.com",
            "tenant": "giryun288gmail.onmicrosoft.com",
            "tenant_id": TENANT_ID,
            "subscription": "MKM-Startups-Prod",
            "subscription_id": SUB_ID,
        },
        "cli": _cli_snapshot(),
        "pages": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].new_page()
        for url, label in ((PORTAL, "portal_home"), (STARTUPS, "startups"), (NVIDIA_BENEFIT, "nvidia_benefit")):
            block: dict[str, Any] = {"label": label}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(8000)
                text = _text(page)
                block.update(
                    {
                        "url": page.url[:320],
                        "logged_in_giryun288": "giryun288@gmail.com" in text,
                        "logged_in_moksorinw": "moksorinw@gmail.com" in text,
                        "tenant_hint": (
                            "giryun288gmail.onmicrosoft.com"
                            if "giryun288gmail" in text.lower()
                            else (
                                "MOKSORINWGMAIL.ONMICROSOFT.COM"
                                if "moksorinwgmail" in text.lower()
                                else None
                            )
                        ),
                        "amounts": list(dict.fromkeys(re.findall(r"\$[\d,]+", text)))[:12],
                        "has_credits": bool(re.search(r"credit|크레딧|remaining|잔액", text, re.I)),
                        "ineligible": any(k in text for k in ("받을 수 없음", "not eligible")),
                        "snippet": text[:1500].replace("\n", " | "),
                    }
                )
                if label == "nvidia_benefit":
                    for btn in ("Get started", "Apply now", "Sign up"):
                        try:
                            b = page.get_by_role("link", name=btn, exact=False).first
                            if b.count() and b.is_visible(timeout=2000):
                                b.click(timeout=8000)
                                page.wait_for_timeout(4000)
                                block["clicked"] = btn
                                block["after_click_snippet"] = _text(page)[:800].replace("\n", " | ")
                                break
                        except Exception:
                            continue
                shot = ROOT / f"reports/nvidia_azure_giryun288_{label}_latest.png"
                page.screenshot(path=str(shot), full_page=True, timeout=35_000)
                block["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
            except Exception as exc:
                block["error"] = str(exc)[:200]
            run["pages"].append(block)
        page.close()

    run["summary"] = {
        "correct_tenant_reached": any(
            p.get("tenant_hint") == "giryun288gmail.onmicrosoft.com" for p in run["pages"]
        ),
        "needs_giryun288_login_in_cdp": any(p.get("logged_in_moksorinw") for p in run["pages"]),
        "credit_amounts": list(
            dict.fromkeys(a for p in run["pages"] for a in (p.get("amounts") or []))
        ),
        "verdict": "switch_cdp_to_giryun288_then_retry"
        if not any(p.get("tenant_hint") == "giryun288gmail.onmicrosoft.com" for p in run["pages"])
        else "giryun288_tenant_probed",
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
