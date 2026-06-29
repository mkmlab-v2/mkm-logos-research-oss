#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backfill ATProto raw JSONL by post ``created_at`` date (B-track tier_a volume).

Paginates Bluesky search, buckets posts into ``YYYYMMDD_atproto_sentiment_raw.jsonl``
per KRX weekday. PIT: only posts with ``created_at <= session_day 09:00 UTC``.

Does not overwrite existing day files unless ``--overwrite``. [HYPO] · no live trading.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = (
    ROOT
    / "projects"
    / "bitcoin-trading"
    / "memory"
    / "v2"
    / "btrack"
    / "raw_feeds"
    / "atproto"
)
REPORT_OUT = ROOT / "reports/btrack_atproto_backfill_v1_latest.json"


def _load_bridge():
    mod_path = ROOT / "scripts/test_atproto_bluesky_bridge.py"
    spec = importlib.util.spec_from_file_location("atproto_bridge_v1", mod_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load test_atproto_bluesky_bridge.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _daterange(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def _skip_day(d: date, mode: str) -> bool:
    if mode == "all":
        return False
    if mode == "krx_weekdays":
        return d.weekday() >= 5
    raise ValueError("calendar_mode must be 'all' or 'krx_weekdays'")


def _parse_created_at(raw: Any) -> datetime | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _pit_cutoff(d: date, hour: int, minute: int) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, 0, tzinfo=timezone.utc)


def _collect_posts(
    bridge: Any,
    *,
    limit: int,
    sort: str,
    since: str | None = None,
    until: str | None = None,
) -> tuple[list[Any], str]:
    client = bridge._load_client()
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw: list[Any] = []
    iter_sig = inspect.signature(bridge._iter_search_batches)
    supports_since = "since" in iter_sig.parameters
    supports_until = "until" in iter_sig.parameters
    supports_tag = "tag" in iter_sig.parameters
    for entry in bridge._default_queries():
        # Bridge query schema can evolve (tuple/list/dict). Normalize to (q, tag, label).
        q = ""
        tag: str | None = None
        if isinstance(entry, dict):
            q = str(entry.get("q", "")).strip()
            tag_val = entry.get("tag")
            tag = str(tag_val).strip() if tag_val is not None else None
            label = str(entry.get("label", q)).strip() or q
        elif isinstance(entry, (tuple, list)):
            q = str(entry[0]).strip() if len(entry) >= 1 and entry[0] is not None else ""
            tag = (
                str(entry[1]).strip()
                if len(entry) >= 2 and entry[1] is not None and str(entry[1]).strip()
                else None
            )
            label = (
                str(entry[2]).strip()
                if len(entry) >= 3 and str(entry[2]).strip()
                else (f"tag={tag}" if tag else q)
            )
        else:
            q = str(entry).strip()
            label = q
        # Some atproto client versions require q and reject tag-only params.
        # Promote tag-only entries to q fallback to preserve coverage.
        if not q and tag:
            q = f"#{tag}"
            label = label or f"q=#{tag}"
        if not q and not tag:
            continue
        if len(bridge._dedupe_posts(raw)) >= limit:
            break
        need = limit - len(bridge._dedupe_posts(raw))
        try:
            iter_kwargs: dict[str, Any] = {
                "q": q or None,
                "per_request": min(100, max(need, 1)),
                "max_posts": need + 10,
                "sort": sort,
            }
            if supports_tag:
                iter_kwargs["tag"] = [tag] if tag else None
            if supports_since and since:
                iter_kwargs["since"] = since
            if supports_until and until:
                iter_kwargs["until"] = until
            for pv in bridge._iter_search_batches(
                client,
                **iter_kwargs,
            ):
                raw.append(pv)
                if len(bridge._dedupe_posts(raw)) >= limit:
                    break
        except Exception as e:
            print(f"query skip {label}: {e}", file=sys.stderr)
            continue
    posts = bridge._dedupe_posts(raw)[:limit]
    return posts, collected_at


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--calendar-mode", choices=("all", "krx_weekdays"), default="krx_weekdays")
    ap.add_argument("--pit-hour", type=int, default=9)
    ap.add_argument("--pit-minute", type=int, default=0)
    ap.add_argument("--min-posts-per-day", type=int, default=3)
    ap.add_argument("--max-posts", type=int, default=2500)
    ap.add_argument("--sort", choices=("latest", "top"), default="latest")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d0 = date.fromisoformat(args.date_from)
    d1 = date.fromisoformat(args.date_to)
    target_days = [d for d in _daterange(d0, d1) if not _skip_day(d, args.calendar_mode)]
    target_set = set(target_days)

    if args.dry_run:
        bridge = _load_bridge()
        ident = bridge._env_identifier()
        pwd = bridge._env_password()
        print(f"dry-run: target_krx_days={len(target_days)} max_posts={args.max_posts}")
        print(f"dry-run: BSKY id set={bool(ident)} password set={bool(pwd)}")
        return 0 if ident and pwd else 2

    bridge = _load_bridge()
    until_exclusive = (d1 + timedelta(days=1)).isoformat()
    since_iso = f"{args.date_from}T00:00:00.000Z"
    until_iso = f"{until_exclusive}T00:00:00.000Z"
    posts, collected_at = _collect_posts(
        bridge,
        limit=max(100, args.max_posts),
        sort=args.sort,
        since=since_iso,
        until=until_iso,
    )
    if not posts:
        posts, collected_at = _collect_posts(
            bridge,
            limit=max(100, args.max_posts),
            sort=args.sort,
        )

    buckets: dict[date, list[dict]] = defaultdict(list)
    pit_rejected = 0
    out_of_range = 0
    for pv in posts:
        row = bridge._post_to_row(pv, collected_at=collected_at, query_label="backfill_created_date_v1")
        created = _parse_created_at(row.get("created_at"))
        if created is None:
            continue
        day = created.date()
        if day not in target_set:
            out_of_range += 1
            continue
        cutoff = _pit_cutoff(day, args.pit_hour, args.pit_minute)
        if created > cutoff:
            pit_rejected += 1
            continue
        buckets[day].append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    written_days: list[str] = []
    skipped_existing: list[str] = []
    skipped_sparse: list[str] = []

    for day in sorted(target_days):
        rows = buckets.get(day, [])
        if len(rows) < args.min_posts_per_day:
            if rows:
                skipped_sparse.append(day.isoformat())
            continue
        ymd = day.strftime("%Y%m%d")
        out_path = args.out_dir / f"{ymd}_atproto_sentiment_raw.jsonl"
        if out_path.is_file() and not args.overwrite:
            skipped_existing.append(day.isoformat())
            continue
        with out_path.open("w", encoding="utf-8") as fp:
            for row in rows:
                fp.write(json.dumps(row, ensure_ascii=False) + "\n")
        written_days.append(day.isoformat())

    covered = sum(
        1
        for day in target_days
        if (args.out_dir / f"{day.strftime('%Y%m%d')}_atproto_sentiment_raw.jsonl").is_file()
    )

    report = {
        "schema": "btrack_atproto_backfill_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "date_from": args.date_from,
        "date_to": args.date_to,
        "calendar_mode": args.calendar_mode,
        "target_krx_weekdays": len(target_days),
        "posts_fetched": len(posts),
        "days_with_pit_rows": len(buckets),
        "days_written": len(written_days),
        "days_covered_on_disk": covered,
        "pit_rejected_after_cutoff": pit_rejected,
        "out_of_target_range": out_of_range,
        "skipped_existing": skipped_existing,
        "skipped_sparse": skipped_sparse,
        "written_days": written_days,
        "out_dir": str(args.out_dir.resolve()).replace("\\", "/"),
        "next": "py scripts/run_btrack_swarm_sasang_stage1_bundle_v1.py",
    }
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    print(str(REPORT_OUT.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
