#!/usr/bin/env python3
"""Fetch enabled RSS feeds into external_feed_drop_v1 JSON (B-track research only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mkmlife.rss_minimal import parse_feed_items  # noqa: E402

DEFAULT_SOURCES = ROOT / "data/mkmlife/rss_sources_news_fusion_v1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/external_feed_drop_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "mkm-news-fusion-rss/1.0 (+research-only)"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _checksum(data: list[Any]) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="RSS -> external_feed_drop_v1")
    ap.add_argument("--sources-json", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-per-feed", type=int, default=15)
    ap.add_argument("--timeout-sec", type=float, default=20.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src_path = args.sources_json.resolve()
    if not src_path.is_file():
        print(f"ERROR: missing sources: {src_path}", file=sys.stderr)
        return 1

    cfg = json.loads(src_path.read_text(encoding="utf-8-sig"))
    feeds = cfg.get("feeds") if isinstance(cfg.get("feeds"), list) else []
    now = _utc_now()
    data: list[dict[str, Any]] = []
    errors: list[str] = []
    providers: list[str] = []

    for feed in feeds:
        if not isinstance(feed, dict) or not feed.get("enabled"):
            continue
        fid = str(feed.get("id") or "unknown")
        url = str(feed.get("url") or "").strip()
        if not url:
            errors.append(f"{fid}: missing url")
            continue
        providers.append(fid)
        try:
            raw = _fetch(url, args.timeout_sec)
            items = parse_feed_items(raw)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            errors.append(f"{fid}: fetch failed: {exc}")
            continue
        for it in items[: max(1, args.max_per_feed)]:
            title = str(it.get("title") or "").strip()
            if not title:
                continue
            link = str(it.get("link") or "").strip()
            row: dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "headline": title,
                "title": title,
                "description": str(it.get("description") or "").strip() or title,
                "url": link,
                "source_feed_id": fid,
                "category": feed.get("category"),
            }
            pub = str(it.get("published_utc") or "").strip()
            if pub:
                row["published_utc"] = pub
            data.append(row)

    doc: dict[str, Any] = {
        "schema": "external_feed_drop_v1",
        "schema_version": "v1",
        "generated_at_utc": now,
        "source": {
            "provider": "+".join(providers) if providers else "rss_fetch",
            "dataset": "rss_news_fusion_poc",
            "fetch_mode": "http_rss",
        },
        "collection_window_utc": {"start": now, "end": now},
        "status": "ok" if data else "degraded",
        "items_count": len(data),
        "data": data,
        "checksum_scope": "data_canonical_json_sha256",
        "checksum_sha256": _checksum(data),
        "research_only": True,
        "promotion_required": True,
        "fetch_errors": errors,
    }

    result = {
        "ok": bool(data),
        "output_json": _rel(args.output_json),
        "items_count": len(data),
        "feeds_enabled": len(providers),
        "errors": errors,
    }
    print(json.dumps(result, ensure_ascii=False))

    if args.dry_run:
        return 0 if data or not providers else 1

    out_path = args.output_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if data else 1


if __name__ == "__main__":
    raise SystemExit(main())
