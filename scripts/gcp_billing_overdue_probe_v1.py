#!/usr/bin/env python3
"""GCP billing overdue probe via CDP Chrome (human login if needed)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/gcp_billing_overdue_probe_latest.json"
SHOT = ROOT / "reports/gcp_billing_overdue_probe_latest.png"

BILLING_ID = "019340-DD2318-993817"
PAGES = [
    ("overview", f"https://console.cloud.google.com/billing/{BILLING_ID}"),
    ("payment", f"https://console.cloud.google.com/billing/{BILLING_ID}/payment"),
    (
        "transactions",
        f"https://console.cloud.google.com/billing/{BILLING_ID}/transactions",
    ),
    ("credits", f"https://console.cloud.google.com/billing/{BILLING_ID}/credits"),
]


def _hints(text: str) -> dict:
    low = text.lower()
    return {
        "login_required": any(
            x in low
            for x in (
                "sign in",
                "로그인",
                "choose an account",
                "계정 선택",
                "accounts.google.com/signin",
            )
        ),
        "overdue_or_payment_issue": any(
            x in text or x in low
            for x in (
                "연체",
                "past due",
                "overdue",
                "payment failed",
                "결제 실패",
                "결제 정보",
                "payment method",
                "fix your payment",
                "update your payment",
                "unable to charge",
                "account suspended",
                "일시 중지",
                "invalid payment",
                "expired",
                "만료",
            )
        ),
        "account_closed_or_disabled": any(
            x in low for x in ("closed", "disabled", "비활성", "폐쇄")
        ),
        "billing_active_ok": any(
            x in text or x in low
            for x in (
                "billing account is active",
                "결제 계정이 활성",
                "no outstanding balance",
                "미결제 잔액 없",
            )
        ),
        "has_balance_due": any(
            x in text or x in low
            for x in ("balance due", "amount due", "미결제", "청구 금액", "잔액")
        ),
    }


def main() -> int:
    run: dict = {
        "schema": "gcp_billing_overdue_probe_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "billing_account_id": BILLING_ID,
        "pages": [],
        "login_required": None,
        "overdue_or_payment_issue": False,
        "verdict": None,
        "error": None,
        "screenshot": str(SHOT),
    }
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0]
            page = ctx.new_page()
            for label, url in PAGES:
                page.goto(url, wait_until="domcontentloaded", timeout=120_000)
                page.wait_for_timeout(7000)
                body = page.inner_text("body", timeout=20_000) or ""
                hints = _hints(body)
                amounts = re.findall(
                    r"(\$[\d,]+\.\d{2}|₩[\d,]+|[\d,]+\.\d{2}\s*USD|[\d,]+\s*KRW)",
                    body,
                )
                run["pages"].append(
                    {
                        "label": label,
                        "url": page.url,
                        "title": page.title(),
                        "hints": hints,
                        "amounts_seen": list(dict.fromkeys(amounts))[:20],
                        "body_snippet": re.sub(r"\s+", " ", body[:4000]),
                    }
                )
                if hints["overdue_or_payment_issue"]:
                    run["overdue_or_payment_issue"] = True
                if label == "overview":
                    run["login_required"] = hints["login_required"]
            page.screenshot(path=str(SHOT), full_page=False)
            page.close()
    except Exception as exc:
        run["error"] = str(exc)

    if run.get("error"):
        run["verdict"] = "probe_error"
    elif run.get("login_required"):
        run["verdict"] = "login_required"
    elif run["overdue_or_payment_issue"]:
        run["verdict"] = "payment_issue_detected"
    else:
        active_ok = any(p["hints"].get("billing_active_ok") for p in run.get("pages", []))
        run["verdict"] = "no_overdue_banner_detected" if active_ok else "inconclusive"

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"verdict={run.get('verdict')} login_required={run.get('login_required')}")
    print(f"overdue_or_payment_issue={run.get('overdue_or_payment_issue')}")
    for pg in run.get("pages", []):
        print(f"  {pg['label']}: overdue={pg['hints'].get('overdue_or_payment_issue')}")
    if run.get("login_required") or run.get("error"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
