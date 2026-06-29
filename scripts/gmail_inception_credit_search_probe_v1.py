#!/usr/bin/env python3
"""Gmail CDP probe — NVIDIA Inception / partner credit emails (human login first)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/gmail_inception_credit_search_probe_latest.json"
SHOT = ROOT / "reports/gmail_inception_credit_search_probe_latest.png"

QUERIES = [
    ("nvidia_from", "from:inceptionprogram@nvidia.com"),
    ("nvidia_domain", "from:nvidia.com inception"),
    ("lambda_credit", "from:lambda (credit OR inception OR promo OR coupon)"),
    ("nebius", "from:nebius (credit OR inception OR promo)"),
    ("gcp_startup", "from:google.com (startup OR credit OR inception OR activate)"),
    ("aws_activate", "from:(aws.amazon.com OR amazon.com) (activate OR credit OR inception)"),
    ("azure_startup", "from:microsoft.com (startup OR credit OR azure OR inception)"),
    ("inception_anywhere", "in:anywhere inception (credit OR benefit OR confirmed) newer_than:90d"),
]


def _login_needed(body: str, page) -> bool:
    low = body.lower()
    if "mail.google.com/mail" not in (page.url or ""):
        return True
    # Inbox loaded markers (KO/EN)
    if any(x in body for x in ("받은편지함", "Inbox", "기본", "Primary")):
        try:
            if page.locator("tr.zA").count() > 0:
                return False
        except Exception:
            pass
    # Login wall only — not "new device login" notification emails
    if "accounts.google.com/signin" in (page.url or ""):
        return True
    return any(
        x in low
        for x in (
            "sign in to continue to gmail",
            "choose an account",
            "계정을 선택",
            "google 계정에 로그인",
        )
    )


def _scrape_search(page, label: str, q: str, mail_index: int = 0) -> dict:
    url = f"https://mail.google.com/mail/u/{mail_index}/#search/{quote(q)}"
    page.goto(url, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(6000)
    body = page.inner_text("body", timeout=15_000) or ""
    no_results = "검색어와 일치하는 메일이 없습니다" in body or "didn't find any messages" in body.lower()
    rows: list[str] = []
    if not no_results:
        for loc in (page.locator("tr.zA"), page.locator('[role="row"]')):
            try:
                n = loc.count()
                if n == 0:
                    continue
                for i in range(min(n, 25)):
                    try:
                        t = re.sub(r"\s+", " ", (loc.nth(i).inner_text(timeout=2000) or "").strip())
                        if len(t) > 8 and "Gmail에 이 대화가" not in t[:30]:
                            rows.append(t[:300])
                    except Exception:
                        pass
                if rows:
                    break
            except Exception:
                pass
    # Fallback: parse visible thread titles from body when row scrape is noisy
    thread_hits: list[str] = []
    for pat in (
        r"(Lambda[^\\n]{10,120})",
        r"(Microsoft Support[^\\n]{10,120})",
        r"(Google Cloud[^\\n]{10,120})",
        r"(inceptionprogram[^\\n]{10,120})",
        r"(NVIDIA[^\\n]{10,120})",
        r"(Nebius[^\\n]{10,120})",
        r"(AWS[^\\n]{10,120})",
    ):
        thread_hits.extend(re.findall(pat, body, flags=re.I))
    return {
        "label": label,
        "query": q,
        "mail_index": mail_index,
        "url": page.url,
        "login_needed": _login_needed(body, page),
        "no_results": no_results,
        "row_count": len(rows),
        "rows_preview": rows[:15],
        "thread_hits": list(dict.fromkeys(thread_hits))[:20],
        "body_snippet": re.sub(r"\s+", " ", body[:3500]),
    }


def main() -> int:
    run: dict = {
        "schema": "gmail_inception_credit_search_probe_v1",
        "queries": [],
        "account_hint": None,
        "login_needed": None,
        "error": None,
        "screenshot": str(SHOT),
    }
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
            ctx = browser.contexts[0]
            page = next(
                (pg for pg in ctx.pages if "mail.google.com" in (pg.url or "")),
                None,
            )
            if page is None:
                page = ctx.new_page()
                page.goto(
                    "https://mail.google.com/mail/u/0/#inbox",
                    wait_until="domcontentloaded",
                    timeout=120_000,
                )
            page.bring_to_front()
            page.wait_for_timeout(3000)
            run["accounts_probed"] = []
            for mail_index in range(3):
                page.goto(
                    f"https://mail.google.com/mail/u/{mail_index}/#inbox",
                    wait_until="domcontentloaded",
                    timeout=120_000,
                )
                page.wait_for_timeout(2500)
                inbox_body = page.inner_text("body", timeout=10_000) or ""
                if _login_needed(inbox_body, page):
                    run["accounts_probed"].append(
                        {"mail_index": mail_index, "status": "not_logged_in"}
                    )
                    continue
                acct = None
                m = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", inbox_body)
                if m:
                    acct = m.group(1)
                run["accounts_probed"].append(
                    {"mail_index": mail_index, "status": "ok", "account_hint": acct}
                )
                if run.get("account_hint") is None and acct:
                    run["account_hint"] = acct
                for label, q in QUERIES:
                    result = _scrape_search(page, label, q, mail_index=mail_index)
                    result["account_hint"] = acct
                    run["queries"].append(result)
                    page.wait_for_timeout(1000)
            run["login_needed"] = not any(
                a.get("status") == "ok" for a in run.get("accounts_probed", [])
            )
            if run["login_needed"]:
                run["error"] = (
                    "Gmail login required in CDP Chrome (NvidiaInceptionAutofillChrome profile)"
                )
            page.screenshot(path=str(SHOT), full_page=False)
    except Exception as exc:
        run["error"] = str(exc)

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"login_needed={run.get('login_needed')} error={run.get('error')}")
    for q in run.get("queries", []):
        acct = q.get("account_hint") or "?"
        nr = q.get("no_results")
        print(f"--- u/{q.get('mail_index')} {acct} {q['label']} no_results={nr} rows={q.get('row_count')}")
        for hit in q.get("thread_hits", [])[:3]:
            print(f"  hit: {hit[:100]}")
    if run.get("login_needed") or run.get("error"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
