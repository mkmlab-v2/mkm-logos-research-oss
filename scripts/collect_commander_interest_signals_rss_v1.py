#!/usr/bin/env python3
"""Optional RSS collector for commander interest topics (B-track observation; stdlib only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from commander_interest_benchmark_v1_lib import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_LOG,
    ensure_signal_log,
    load_config,
    resolve_path,
)

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "commander_interest_rss_collect_latest.json"
USER_AGENT = "MKM-CommanderInterestRSS/1.0 (internal observation only)"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(text or "")).strip()


def _parse_feed(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []

    for item in root.findall(".//item"):
        title = _strip_html(item.findtext("title") or "")
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}updated") or "").strip()
        if title:
            items.append({"title": title, "url": link, "published": pub})

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = _strip_html(entry.findtext("atom:title", default="", namespaces=ns))
        link_el = entry.find("atom:link", ns)
        link = ""
        if link_el is not None:
            link = (link_el.attrib.get("href") or "").strip()
        pub = (entry.findtext("atom:updated", default="", namespaces=ns) or "").strip()
        if title:
            items.append({"title": title, "url": link, "published": pub})

    return items


def _fetch_feed(url: str, *, timeout: int = 20) -> list[dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    return _parse_feed(body.decode("utf-8", errors="replace"))


def collect_rss(
    *,
    config_path: Path,
    log_path: Path,
    max_per_feed: int = 3,
    dry_run: bool = False,
) -> dict[str, Any]:
    config = load_config(config_path)
    feeds = list(config.get("rss_feeds") or [])
    if not feeds:
        return {
            "schema": "commander_interest_rss_collect_v1",
            "generated_at_utc": _utc_now(),
            "feeds_configured": 0,
            "appended_count": 0,
            "skipped_reason": "no_rss_feeds_in_config",
            "track_wall": config.get("track_wall") or {},
        }

    appended = 0
    errors: list[dict[str, str]] = []
    samples: list[dict[str, Any]] = []

    log_file = ensure_signal_log(log_path) if not dry_run else resolve_path(log_path)
    fh = None
    if not dry_run:
        fh = log_file.open("a", encoding="utf-8")

    try:
        for feed in feeds:
            url = str(feed.get("url") or "").strip()
            topic_id = str(feed.get("topic_id") or "").strip()
            platform = str(feed.get("platform") or "rss").strip()
            if not url or not topic_id:
                continue
            try:
                entries = _fetch_feed(url)[: max(1, int(max_per_feed))]
            except Exception as exc:  # pragma: no cover - network
                errors.append({"url": url, "error": str(exc)[:200]})
                continue
            for entry in entries:
                row = {
                    "schema": "commander_interest_signal_v1",
                    "observed_at_utc": _utc_now(),
                    "topic_id": topic_id,
                    "platform": platform,
                    "title": entry.get("title") or "untitled",
                    "url": entry.get("url") or "",
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "shares": 0,
                    "note": f"rss_collect · feed={url}",
                }
                samples.append(row)
                if fh is not None:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    appended += 1
    finally:
        if fh is not None:
            fh.close()

    return {
        "schema": "commander_interest_rss_collect_v1",
        "generated_at_utc": _utc_now(),
        "dry_run": dry_run,
        "feeds_configured": len(feeds),
        "appended_count": appended if not dry_run else len(samples),
        "sample_titles": [s.get("title") for s in samples[:5]],
        "errors": errors,
        "log_path": str(resolve_path(log_path).resolve()),
        "track_wall": config.get("track_wall") or {},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config-json", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--max-per-feed", type=int, default=3)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    payload = collect_rss(
        config_path=args.config_json,
        log_path=args.log_jsonl,
        max_per_feed=args.max_per_feed,
        dry_run=args.dry_run,
    )
    out_json = resolve_path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), **payload}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
