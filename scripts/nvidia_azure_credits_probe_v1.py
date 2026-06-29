#!/usr/bin/env python3
"""Azure portal startups + credits deep probe (CDP, read-only)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_credits_probe_latest.json"

AZURE_HOME = "https://portal.azure.com/#home"
AZURE_STARTUPS = (
    "https://portal.azure.com/#view/Microsoft_Azure_Startups/"
    "AzureForStartups.ReactView/skipWizardRedirect~/true"
)
CREDITS = "https://portal.azure.com/#view/Microsoft_Azure_GTM/ModernBillingMenuBlade/~/Credits"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text_in_frames(page) -> str:
    parts: list[str] = []
    try:
        parts.append(page.inner_text("body", timeout=10_000) or "")
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


def _probe(page, url: str, label: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(8000)
    text = _text_in_frames(page)
    out: dict[str, Any] = {
        "label": label,
        "url": page.url[:300],
        "logged_in": "moksorinw@gmail.com" in text or "onmicrosoft.com" in text.lower(),
        "amounts": list(dict.fromkeys(re.findall(r"\$[\d,]+", text)))[:10],
        "linkedin_gate": "LinkedIn" in text,
        "ineligible_banner": any(
            k in text
            for k in (
                "받을 수 없음",
                "cannot receive",
                "not eligible",
                "자격 요구",
                "ineligible",
            )
        ),
        "nvidia_inception": bool(re.search(r"nvidia|inception", text, re.I)),
        "snippet": text[:1500].replace("\n", " | "),
    }
    if "$5,000" in text or "$5,000" in str(out["amounts"]):
        out["inception_5k_seen"] = True
    shot = ROOT / f"reports/nvidia_azure_{label}_probe_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=30_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_azure_credits_probe_v1",
        "generated_at_utc": _utc(),
        "account_email_expected": "moksorinw@gmail.com",
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
            (AZURE_STARTUPS, "startups"),
            (CREDITS, "billing_credits"),
        ):
            try:
                run["pages"].append(_probe(page, url, label))
            except Exception as exc:
                run["pages"].append({"label": label, "error": str(exc)[:200]})
        page.close()

    startups = next((p for p in run["pages"] if p.get("label") == "startups"), {})
    credits = next((p for p in run["pages"] if p.get("label") == "billing_credits"), {})
    run["summary"] = {
        "logged_in": any(p.get("logged_in") for p in run["pages"]),
        "startups_ineligible_1k": startups.get("ineligible_banner"),
        "linkedin_required": startups.get("linkedin_gate") or credits.get("linkedin_gate"),
        "inception_5k_visible": startups.get("inception_5k_seen") or credits.get("inception_5k_seen"),
        "credit_amounts": list(
            dict.fromkeys((startups.get("amounts") or []) + (credits.get("amounts") or []))
        ),
        "verdict": (
            "linkedin_verification_needed"
            if startups.get("linkedin_gate")
            else (
                "startups_ineligible_check_requirements"
                if startups.get("ineligible_banner")
                else "probe_only_no_inception_5k_yet"
            )
        ),
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
