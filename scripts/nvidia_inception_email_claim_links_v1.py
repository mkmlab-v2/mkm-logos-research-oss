#!/usr/bin/env python3
"""Open NVIDIA Inception partner request emails and extract claim URLs."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_inception_email_claim_links_latest.json"

TARGETS = [
    ("gcp", "from:inceptionprogram@nvidia.com subject:\"Google Cloud\""),
    ("lambda", "from:inceptionprogram@nvidia.com subject:\"Lambda\""),
    ("nebius", "from:inceptionprogram@nvidia.com subject:\"Nebius\""),
    ("azure", "from:inceptionprogram@nvidia.com subject:\"Azure\""),
    ("aws", "from:inceptionprogram@nvidia.com subject:\"AWS\""),
    ("aws_activate", "from:aws.amazon.com (Activate OR credit) newer_than:60d"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_links(page) -> list[str]:
    links: list[str] = []
    try:
        for a in page.locator("a[href]").all()[:80]:
            href = a.get_attribute("href") or ""
            if href.startswith("http") and "google.com/url" not in href:
                links.append(href)
            elif "google.com/url" in href:
                m = re.search(r"url=([^&]+)", href)
                if m:
                    links.append(m.group(1))
    except Exception:
        pass
    body = page.inner_text("body", timeout=15_000) or ""
    for m in re.finditer(r"https?://[^\s<>\"']+", body):
        u = m.group(0).rstrip(").,]")
        if any(k in u.lower() for k in ("cloud.google", "lambda", "nebius", "azure", "aws", "activate", "startup")):
            links.append(u)
    return list(dict.fromkeys(links))[:20]


def main() -> int:
    from playwright.sync_api import sync_playwright

    run: dict = {"schema": "nvidia_inception_email_claim_links_v1", "generated_at_utc": _utc(), "mail_index": 1, "emails": []}
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = browser.contexts[0].new_page()
        for key, q in TARGETS:
            entry: dict = {"partner_key": key, "query": q, "opened": False, "subject": None, "links": [], "body_snippet": None}
            try:
                page.goto(
                    f"https://mail.google.com/mail/u/1/#search/{quote(q)}",
                    wait_until="domcontentloaded",
                    timeout=120_000,
                )
                page.wait_for_timeout(5000)
                rows = page.locator("tr.zA").all()
                if not rows:
                    entry["error"] = "no_thread"
                    run["emails"].append(entry)
                    continue
                rows[0].click(timeout=8000)
                page.wait_for_timeout(4000)
                entry["opened"] = True
                body = page.inner_text("body", timeout=15_000) or ""
                entry["body_snippet"] = re.sub(r"\s+", " ", body[500:3500])[:1200]
                sm = re.search(r"(Your Request for[^\n]{5,120}|AWS Activate[^\n]{5,120})", body)
                if sm:
                    entry["subject"] = sm.group(1)[:120]
                entry["links"] = _extract_links(page)
                if "unable to process" in body.lower() or "does not meet" in body.lower():
                    entry["aws_rejected"] = True
            except Exception as exc:
                entry["error"] = str(exc)[:200]
            run["emails"].append(entry)
        page.close()

    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")
    for e in run["emails"]:
        print(f"  {e['partner_key']}: links={len(e.get('links', []))} aws_rejected={e.get('aws_rejected')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
