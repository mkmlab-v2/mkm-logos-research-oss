#!/usr/bin/env python3
"""Gmail search on active CDP tab — reports which account title Gmail shows."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/gmail_inception_credit_search_probe_moksorinw_attempt.json"

QUERIES = [
    ("nvidia", "from:inceptionprogram@nvidia.com"),
    (
        "inception90",
        "in:anywhere inception (credit OR benefit OR confirmed OR partner) newer_than:90d",
    ),
    ("lambda", "from:lambda (credit OR inception OR promo OR coupon)"),
    (
        "gcp_startup",
        'from:google.com (startup OR "cloud credit" OR inception OR activate)',
    ),
]


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {"active_gmail_title": None, "queries": []}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = next(
            (pg for pg in browser.contexts[0].pages if "mail.google.com" in (pg.url or "")),
            None,
        )
        if page is None:
            page = browser.contexts[0].new_page()
            page.goto("https://mail.google.com/mail/u/0/#inbox", timeout=120_000)
        page.bring_to_front()
        run["active_gmail_title"] = page.title()
        for label, q in QUERIES:
            page.goto(
                f"https://mail.google.com/mail/u/0/#search/{quote(q)}",
                wait_until="domcontentloaded",
                timeout=120_000,
            )
            page.wait_for_timeout(6000)
            body = page.inner_text("body", timeout=20_000) or ""
            no_results = (
                "검색어와 일치하는 메일이 없습니다" in body
                or "didn't find any messages" in body.lower()
            )
            hits: list[str] = []
            if not no_results:
                for m in re.finditer(
                    r"(Lambda[^\n]{8,100}|Google Cloud[^\n]{8,100}|"
                    r"Microsoft[^\n]{8,100}|inceptionprogram[^\n]{8,100}|"
                    r"NVIDIA[^\n]{8,100}|Nebius[^\n]{8,100}|AWS[^\n]{8,100})",
                    body,
                    re.I,
                ):
                    hits.append(m.group(1).strip()[:120])
            run["queries"].append(
                {
                    "label": label,
                    "query": q,
                    "no_results": no_results,
                    "hits": list(dict.fromkeys(hits))[:8],
                }
            )
        page.screenshot(
            path=str(ROOT / "reports/gmail_inception_credit_search_probe_latest.png")
        )
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
