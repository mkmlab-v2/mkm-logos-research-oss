#!/usr/bin/env python3
"""Lambda Cloud billing/credits probe (CDP, read-only, no GPU spinup)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_lambda_credits_probe_latest.json"

WS = "e8b0295884964f74855d5676d9e9aa45"
INSTANCES = f"https://cloud.lambda.ai/workspace/{WS}/instances"
URLS = [
    ("instances", INSTANCES),
    ("settings_billing", f"https://cloud.lambda.ai/workspace/{WS}/settings/billing"),
    ("billing", f"https://cloud.lambda.ai/workspace/{WS}/billing"),
    ("account_billing", "https://cloud.lambda.ai/settings/billing"),
    ("nvidia_inception", "https://lambda.ai/nvidia-inception"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(page, timeout: int = 15_000) -> str:
    try:
        return page.inner_text("body", timeout=timeout) or ""
    except Exception:
        return ""


def _login_needed(url: str, text: str) -> bool:
    low = (url + " " + text).lower()
    return any(
        k in low
        for k in (
            "auth.lambdalabs.com",
            "log in to lambda",
            "sign in",
            "email address",
            "continue with google",
        )
    ) and "workspace" not in url.lower()


def _probe(page, url: str, label: str) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(6000)
    text = _text(page)
    out: dict[str, Any] = {
        "label": label,
        "url": page.url[:300],
        "logged_in": not _login_needed(page.url, text),
        "amounts": list(dict.fromkeys(re.findall(r"\$[\d,]+(?:\.\d{2})?", text)))[:15],
        "inception_mentioned": bool(re.search(r"inception|nvidia", text, re.I)),
        "has_credit_section": any(
            k in text.lower()
            for k in (
                "credit",
                "promotional",
                "balance",
                "billing",
                "invoice",
            )
        ),
    }
    for pat, key in (
        (r"(?:credit\s*balance|promotional\s*credit|available\s*credit)[^\$]{0,40}(\$[\d,]+(?:\.\d{2})?)", "credit_balance_hint"),
        (r"(?:account\s*balance|balance)[^\$]{0,30}(\$[\d,]+(?:\.\d{2})?)", "account_balance_hint"),
    ):
        m = re.search(pat, text, re.I)
        if m:
            out[key] = m.group(1)
    if out.get("credit_balance_hint") or (
        out["amounts"] and re.search(r"7,?500|7500", text)
    ):
        out["inception_7500_possible"] = True
    out["snippet"] = text[:1200].replace("\n", " | ")
    shot = ROOT / f"reports/nvidia_lambda_{label}_probe_latest.png"
    page.screenshot(path=str(shot), full_page=True, timeout=30_000)
    out["screenshot"] = str(shot.relative_to(ROOT)).replace("\\", "/")
    return out


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict[str, Any] = {
        "schema": "nvidia_lambda_credits_probe_v1",
        "generated_at_utc": _utc(),
        "workspace_id": WS,
        "login_email_expected": "moksorinw@no1kmedi.com",
        "pages": [],
    }
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0]
        page = next(
            (pg for pg in ctx.pages if "cloud.lambda.ai" in (pg.url or "") or "lambda.ai" in (pg.url or "")),
            None,
        )
        if page is None:
            page = ctx.new_page()
        page.bring_to_front()
        for label, url in URLS:
            try:
                run["pages"].append(_probe(page, url, label))
            except Exception as exc:
                run["pages"].append({"label": label, "error": str(exc)[:200]})
        page.close()

    billing_pages = [p for p in run["pages"] if p.get("label") in ("settings_billing", "billing", "account_billing")]
    best = max(billing_pages, key=lambda x: len(x.get("amounts") or []), default={})
    run["summary"] = {
        "logged_in": any(p.get("logged_in") for p in run["pages"] if p.get("label") == "instances"),
        "credit_balance_hint": best.get("credit_balance_hint") or best.get("account_balance_hint"),
        "amounts_seen": best.get("amounts") or [],
        "inception_7500_credited": bool(best.get("inception_7500_possible") and best.get("credit_balance_hint")),
        "inception_form_status": next(
            (p.get("snippet", "")[:200] for p in run["pages"] if p.get("label") == "nvidia_inception"),
            "",
        ),
        "verdict": (
            "credits_active"
            if best.get("credit_balance_hint")
            else (
                "logged_in_no_inception_credits"
                if any(p.get("logged_in") for p in run["pages"])
                else "login_required"
            )
        ),
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")
    print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
