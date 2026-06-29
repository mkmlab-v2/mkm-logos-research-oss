#!/usr/bin/env python3
"""Find UR GTM Reddit post in r/LocalLLM via openchrome CDP search."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/universal_root_reddit_post_find_v1_latest.json"
CDP = "http://127.0.0.1:9222"
TITLE_NEEDLE = "fixture smoke"
QUERIES = [
    "mkm-universal-root",
    "Research PoC MIT dual-plane",
    "mkmlab fixture smoke",
    "dual-plane metrics 500-pair",
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _score(title: str) -> int:
    t = title.lower()
    score = 0
    for needle in ("fixture", "smoke", "dual-plane", "dual plane", "research poc", "mkm", "universal root", "500-pair"):
        if needle in t:
            score += 2
    if "[research" in t:
        score += 3
    return score


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"ok": False, "error": "playwright_missing"}))
        return 2

    hits: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()
        for q in QUERIES:
            url = f"https://www.reddit.com/r/LocalLLM/search/?q={quote(q)}&restrict_sr=1"
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(4500)
            seen: set[str] = set()
            for a in page.locator('a[href*="/comments/"]').all():
                try:
                    href = a.get_attribute("href") or ""
                    if not href or href in seen:
                        continue
                    title = (a.inner_text() or "").strip().replace("\n", " ")
                    if not title or len(title) < 10:
                        continue
                    seen.add(href)
                    sc = _score(title)
                    if sc <= 0:
                        continue
                    full = href if href.startswith("http") else f"https://www.reddit.com{href}"
                    hits.append({"query": q, "url": full.split("?")[0], "title": title[:200], "score": sc})
                except Exception:
                    continue

    hits.sort(key=lambda x: (-x["score"], x["title"]))
    best = hits[0] if hits else None
    doc = {
        "schema": "universal_root_reddit_post_find_v1",
        "generated_at_utc": _utc(),
        "ok": bool(best),
        "best_match": best,
        "candidates": hits[:10],
        "fallback_search": "https://www.reddit.com/r/LocalLLM/search/?q=Fixture%20smoke%20dual-plane&restrict_sr=1",
        "fallback_submitted": "https://www.reddit.com/user/me/submitted/",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "best": best}, ensure_ascii=False))
    return 0 if best else 1


if __name__ == "__main__":
    raise SystemExit(main())
