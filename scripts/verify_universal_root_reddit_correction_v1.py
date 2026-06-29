#!/usr/bin/env python3
"""Verify UR Reddit correction comment via openchrome CDP (read-only)."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/universal_root_reddit_correction_verify_v1_latest.json"
CDP = "http://127.0.0.1:9222"
NEEDLES = (
    "correction / scope note",
    "mkm-ur-bench-5k",
    "12.21%",
    "plane-separated",
    "do not merge with 500",
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def _full_url(href: str) -> str:
    return href if href.startswith("http") else f"https://www.reddit.com{href}"


def _find_post_urls(page) -> list[dict]:
    urls: list[dict] = []
    seen: set[str] = set()
    for a in page.locator('a[href*="/comments/"]').all():
        try:
            href = a.get_attribute("href") or ""
            if "/comments/" not in href:
                continue
            title = (a.inner_text() or "").strip().replace("\n", " ")
            if not title or len(title) < 8:
                continue
            full = _full_url(href.split("?")[0])
            if full in seen:
                continue
            seen.add(full)
            score = sum(2 for n in ("fixture", "smoke", "dual-plane", "dual plane", "research poc", "mkm", "universal", "500-pair") if n in title.lower())
            if score > 0:
                urls.append({"url": full, "title": title[:200], "score": score})
        except Exception:
            continue
    urls.sort(key=lambda x: (-x["score"], x["title"]))
    return urls


def _page_has_correction(page) -> tuple[bool, str]:
    try:
        text = _norm(page.inner_text("body"))
    except Exception:
        return False, "body_read_failed"
    hits = [n for n in NEEDLES if n in text]
    return len(hits) >= 2, ",".join(hits)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"ok": False, "error": "playwright_missing"}))
        return 2

    report: dict = {
        "schema": "universal_root_reddit_correction_verify_v1",
        "generated_at_utc": _utc(),
        "ok": False,
        "correction_found": False,
        "post_candidates": [],
        "checked_posts": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP)
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        sources = [
            ("submitted", "https://www.reddit.com/user/me/submitted/"),
            ("search", f"https://www.reddit.com/r/LocalLLM/search/?q={quote('Research PoC MIT fixture')}&restrict_sr=1"),
            ("search2", f"https://www.reddit.com/r/LocalLLM/search/?q={quote('mkm-universal-root')}&restrict_sr=1"),
        ]
        candidates: list[dict] = []
        for label, url in sources:
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)
            found = _find_post_urls(page)
            for row in found:
                row["source"] = label
            candidates.extend(found)

        dedup: dict[str, dict] = {}
        for c in candidates:
            u = c["url"]
            if u not in dedup or c["score"] > dedup[u]["score"]:
                dedup[u] = c
        ranked = sorted(dedup.values(), key=lambda x: (-x["score"], x["title"]))[:8]
        report["post_candidates"] = ranked

        for cand in ranked:
            page.goto(cand["url"], wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(5000)
            ok, detail = _page_has_correction(page)
            row = {**cand, "correction_markers": detail, "correction_found": ok}
            report["checked_posts"].append(row)
            if ok:
                report["correction_found"] = True
                report["post_url"] = cand["url"]
                report["post_title"] = cand["title"]
                page.screenshot(path=str(ROOT / "reports/universal_root_reddit_correction_verify_v1.png"), full_page=False)
                report["screenshot"] = "reports/universal_root_reddit_correction_verify_v1.png"
                break

    report["ok"] = report["correction_found"]
    report["status"] = "verified" if report["ok"] else "not_found"
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "status": report["status"], "post_url": report.get("post_url")}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
