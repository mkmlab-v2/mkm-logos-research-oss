#!/usr/bin/env python3
"""Gmail inception/partner search for a specific mail/u/N index."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent

QUERIES = [
    ("nvidia_from", "from:inceptionprogram@nvidia.com"),
    ("nvidia_domain", "from:nvidia.com (inception OR credit OR benefit)"),
    ("inception90", "in:anywhere inception (credit OR benefit OR confirmed OR partner OR activate) newer_than:90d"),
    ("lambda", "from:lambda (credit OR inception OR promo OR coupon OR cloud)"),
    ("nebius", "from:nebius (credit OR inception OR promo OR cloud)"),
    ("aws", "from:(aws.amazon.com OR amazon.com) (activate OR credit OR inception OR startup)"),
    ("gcp_startup", 'from:google.com (startup OR "cloud credit" OR inception OR activate OR NVIDIA)'),
    ("azure", "from:microsoft.com (startup OR credit OR azure OR inception OR founders)"),
    ("no1kmedi", "from:no1kmedi.com (inception OR nvidia OR credit)"),
]


def _search(page, mail_index: int, label: str, q: str) -> dict:
    page.goto(
        f"https://mail.google.com/mail/u/{mail_index}/#search/{quote(q)}",
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
            r"([^\n]{0,40}(?:Lambda|Google Cloud|Microsoft|inceptionprogram|NVIDIA|Nebius|AWS|Azure|Startup|credit|Inception)[^\n]{0,120})",
            body,
            re.I,
        ):
            t = re.sub(r"\s+", " ", m.group(1).strip())
            if len(t) > 15 and "Gmail에 이 대화" not in t:
                hits.append(t[:160])
    return {
        "label": label,
        "query": q,
        "mail_index": mail_index,
        "no_results": no_results,
        "hits": list(dict.fromkeys(hits))[:12],
        "body_snippet": re.sub(r"\s+", " ", body[800:4200]),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--mail-index", type=int, default=1)
    ap.add_argument("--out", type=Path, default=ROOT / "reports/gmail_moksorinw_inception_search_latest.json")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    run: dict = {"mail_index": args.mail_index, "gmail_title": None, "queries": []}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].new_page()
        page.goto(
            f"https://mail.google.com/mail/u/{args.mail_index}/#inbox",
            wait_until="domcontentloaded",
            timeout=120_000,
        )
        page.wait_for_timeout(4000)
        run["gmail_title"] = page.title()
        for label, q in QUERIES:
            run["queries"].append(_search(page, args.mail_index, label, q))
            page.wait_for_timeout(1000)
        shot = ROOT / "reports/gmail_moksorinw_inception_search_latest.png"
        page.screenshot(path=str(shot), full_page=False)
        run["screenshot"] = str(shot)
        page.close()

    args.out.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"account: {run['gmail_title']}")
    for q in run["queries"]:
        print(f"  {q['label']}: no_results={q['no_results']} hits={len(q['hits'])}")
        for h in q["hits"][:3]:
            print(f"    - {h[:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
