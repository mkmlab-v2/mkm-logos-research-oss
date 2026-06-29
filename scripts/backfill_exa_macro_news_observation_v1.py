#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[HYPO] Weekly Exa news backfill → news_observation_v1 staging (B-track only).

Uses startPublishedDate/endPublishedDate windows. Dedupes by text_sha256.
Not Track A / live trading ingest.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_exa_macro_news_observation_v1 import (  # noqa: E402
    DEFAULT_OUT,
    DEFAULT_QUERY,
    _rows_from_fixture,
    _utc_now,
    exa_search,
)

DEFAULT_META = ROOT / "reports/exa_macro_news_backfill_v1_latest.json"
ART_META = ROOT / "docs/final/artifacts/exa_macro_news_backfill_v1_latest.json"


def iter_date_windows(date_from: str, date_to: str, *, step_days: int) -> Iterator[tuple[str, str]]:
    start = date.fromisoformat(date_from[:10])
    end = date.fromisoformat(date_to[:10])
    step = max(1, int(step_days))
    cur = start
    while cur <= end:
        win_end = min(cur + timedelta(days=step - 1), end)
        yield cur.isoformat(), win_end.isoformat()
        cur = win_end + timedelta(days=1)


def _load_existing_hashes(path: Path) -> set[str]:
    hashes: set[str] = set()
    if not path.is_file():
        return hashes
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        h = str(row.get("text_sha256") or "").strip()
        if h:
            hashes.add(h)
    return hashes


def _published_days(rows: list[dict[str, Any]]) -> set[str]:
    days: set[str] = set()
    for row in rows:
        for key in ("published_utc", "as_of_utc"):
            ts = str(row.get(key) or "")
            if len(ts) >= 10:
                days.add(ts[:10])
                break
    return days


def run_backfill(
    *,
    date_from: str,
    date_to: str,
    step_days: int,
    num_results: int,
    query: str,
    output: Path,
    sleep_s: float,
    max_windows: int | None,
    dry_run: bool,
    fixture_json: Path | None,
    api_key: str | None,
) -> dict[str, Any]:
    ingested_at = _utc_now()
    existing_hashes = _load_existing_hashes(output)
    windows = list(iter_date_windows(date_from, date_to, step_days=step_days))
    if max_windows is not None:
        windows = windows[: max(0, int(max_windows))]

    written = 0
    skipped_dup = 0
    window_log: list[dict[str, Any]] = []
    all_new_days: set[str] = set()

    for i, (w_from, w_to) in enumerate(windows):
        win_query = f"{query} macro markets week {w_from} to {w_to}"
        if dry_run:
            window_log.append({"window": [w_from, w_to], "status": "dry_run"})
            continue

        if fixture_json:
            doc = json.loads(fixture_json.read_text(encoding="utf-8"))
            rows = _rows_from_fixture(doc, ingested_at=ingested_at)
            source = "fixture"
        else:
            key = (api_key or "").strip()
            if not key:
                raise RuntimeError("EXA_API_KEY not set; use --fixture-json for offline PoC.")
            start_iso = f"{w_from}T00:00:00Z"
            end_iso = f"{w_to}T23:59:59Z"
            try:
                doc = exa_search(
                    win_query,
                    num_results=num_results,
                    api_key=key,
                    start_published_date=start_iso,
                    end_published_date=end_iso,
                    category="news",
                )
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:400]
                window_log.append(
                    {
                        "window": [w_from, w_to],
                        "status": "http_error",
                        "code": exc.code,
                        "body": body,
                    }
                )
                if sleep_s > 0:
                    time.sleep(sleep_s)
                continue
            except urllib.error.URLError as exc:
                window_log.append(
                    {"window": [w_from, w_to], "status": "network_error", "reason": str(exc.reason)}
                )
                if sleep_s > 0:
                    time.sleep(sleep_s)
                continue
            rows = _rows_from_fixture(doc, ingested_at=ingested_at)
            source = "exa_api"

        new_rows: list[dict[str, Any]] = []
        for row in rows:
            h = str(row.get("text_sha256") or "")
            if h and h in existing_hashes:
                skipped_dup += 1
                continue
            if h:
                existing_hashes.add(h)
            new_rows.append(row)

        if new_rows:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("a", encoding="utf-8") as f:
                for row in new_rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += len(new_rows)
            all_new_days |= _published_days(new_rows)

        window_log.append(
            {
                "window": [w_from, w_to],
                "status": "ok",
                "source": source,
                "fetched": len(rows),
                "appended": len(new_rows),
                "published_days": sorted(_published_days(rows)),
            }
        )
        if sleep_s > 0 and i + 1 < len(windows):
            time.sleep(sleep_s)

    total_rows = sum(1 for ln in output.read_text(encoding="utf-8").splitlines() if ln.strip()) if output.is_file() else 0
    return {
        "schema": "exa_macro_news_backfill_v1",
        "generated_at_utc": ingested_at,
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "boundary_ack": "B-track calibration ingest only; not A-track or live trigger.",
        "preset": None,
        "window": {"from": date_from, "to": date_to, "step_days": step_days},
        "n_windows_planned": len(windows),
        "rows_appended": written,
        "rows_skipped_duplicate_sha256": skipped_dup,
        "staging_total_rows": total_rows,
        "new_published_days": sorted(all_new_days),
        "output_jsonl": str(output.relative_to(ROOT)).replace("\\", "/")
        if output.is_relative_to(ROOT)
        else str(output),
        "windows": window_log,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default=None)
    ap.add_argument("--date-to", required=True)
    ap.add_argument("--step-days", type=int, default=7)
    ap.add_argument("--num-results", type=int, default=6)
    ap.add_argument("--query", default=DEFAULT_QUERY)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--meta-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--artifact-meta", type=Path, default=ART_META)
    ap.add_argument("--sleep-s", type=float, default=0.35)
    ap.add_argument("--max-windows", type=int, default=None, help="Cap API windows (cost guard)")
    ap.add_argument(
        "--preset",
        choices=("none", "monthly_2020"),
        default="none",
        help="monthly_2020 = 2020-01-01..date-to, step 30d",
    )
    ap.add_argument("--fixture-json", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args(argv)

    date_from = args.date_from
    date_to = args.date_to
    step_days = args.step_days
    max_windows = args.max_windows
    if args.preset == "monthly_2020":
        date_from = "2020-01-01"
        step_days = 30
        if max_windows is None:
            max_windows = 72
    if not date_from:
        print("ERROR: --date-from required unless --preset monthly_2020", file=sys.stderr)
        return 2

    api_key = os.environ.get("EXA_API_KEY", "").strip() or None
    if not args.dry_run and not args.fixture_json and not api_key:
        print("ERROR: EXA_API_KEY not set; use --fixture-json or --dry-run.", file=sys.stderr)
        return 2

    doc = run_backfill(
        date_from=date_from,
        date_to=date_to,
        step_days=step_days,
        num_results=args.num_results,
        query=args.query,
        output=args.output,
        sleep_s=max(0.0, float(args.sleep_s)),
        max_windows=max_windows,
        dry_run=bool(args.dry_run),
        fixture_json=args.fixture_json,
        api_key=api_key,
    )
    if args.preset != "none":
        doc["preset"] = args.preset
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.meta_json.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_meta.parent.mkdir(parents=True, exist_ok=True)
    args.meta_json.write_text(payload, encoding="utf-8")
    args.artifact_meta.write_text(payload, encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} appended={doc['rows_appended']} "
        f"staging_total={doc['staging_total_rows']} windows={doc['n_windows_planned']}"
    )
    print(f"META: {args.meta_json.resolve()}")

    if args.validate and args.output.is_file():
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/validate_news_observation_jsonl_v1.py"), "--news-jsonl", str(args.output)],
            cwd=str(ROOT),
        )
        return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
