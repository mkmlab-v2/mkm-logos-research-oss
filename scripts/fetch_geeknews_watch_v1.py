#!/usr/bin/env python3
"""Weekly GeekNews (news.hada.io) keyword scan — observation only."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "geeknews_watch_latest.json"
FEED_URLS = (
    "https://news.hada.io/rss",
    "https://news.hada.io/feed",
)
WATCH_KEYWORDS = (
    "cursor",
    "origin git",
    "agent",
    "code review",
    "ktx",
    "homelab",
    "gitops",
)


def _fetch(url: str, timeout: float = 25.0) -> tuple[int | None, bytes, str | None]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MKM-GeekNewsWatch/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(800_000), None
    except urllib.error.HTTPError as exc:
        try:
            data = exc.read(100_000)
        except Exception:
            data = b""
        return exc.code, data, str(exc)
    except Exception as exc:  # noqa: BLE001
        return None, b"", str(exc)


def _parse_rss(data: bytes) -> list[dict]:
    root = ET.fromstring(data)
    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title:
            items.append({"title": title, "link": link})
    if items:
        return items
    # atom
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = (entry.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = (link_el.get("href") if link_el is not None else "") or ""
        if title:
            items.append({"title": title, "link": link})
    return items


def _filter_items(items: list[dict]) -> list[dict]:
    matched: list[dict] = []
    for item in items:
        blob = f"{item.get('title', '')} {item.get('link', '')}".lower()
        kws = [kw for kw in WATCH_KEYWORDS if kw in blob]
        if kws:
            matched.append({**item, "keywords": kws})
    return matched


def run_watch(*, dry_run: bool = False) -> dict:
    now = datetime.now(timezone.utc)
    report: dict = {
        "schema": "geeknews_watch_v1",
        "generated_at_utc": now.isoformat(),
        "feed_attempts": [],
        "items_total": 0,
        "items_matched": [],
        "ok": True,
        "operator_note_ko": "GeekNews 주간 스캔 — Cursor Origin·에이전트·ktx·homelab 키워드만 추출",
    }

    if dry_run:
        report["status"] = "dry_run"
        return report

    all_items: list[dict] = []
    for url in FEED_URLS:
        status, data, err = _fetch(url)
        attempt = {"url": url, "http_status": status, "bytes": len(data), "error": err}
        items: list[dict] = []
        if data and (b"<rss" in data[:500] or b"<feed" in data[:500] or b"<item" in data[:2000]):
            try:
                items = _parse_rss(data)
            except ET.ParseError as parse_err:
                attempt["parse_error"] = str(parse_err)
        elif data and b"403" in data[:200]:
            attempt["blocked"] = True
        report["feed_attempts"].append(attempt)
        if items:
            all_items = items
            break

    report["items_total"] = len(all_items)
    report["items_matched"] = _filter_items(all_items)[:20]
    if not all_items:
        report["status"] = "feed_unavailable"
        report["ok"] = True  # non-fatal observation
    else:
        report["status"] = "ok"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="GeekNews weekly keyword watch")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    report = run_watch(dry_run=args.dry_run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    matched = len(report.get("items_matched") or [])
    print(f"GEEKNEWS_WATCH status={report.get('status')} matched={matched} ok={report.get('ok')}")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
