#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read-only timeline: .mkm-memory count by mtime day (full tree) + optional JSON date sample.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _day_from_mtime(path: Path) -> Optional[str]:
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError:
        return None


def histogram_mtime(root: Path) -> Tuple[int, Counter[str], Optional[str], Optional[str]]:
    if not root.is_dir():
        return 0, Counter(), None, None
    days: Counter[str] = Counter()
    paths = list(root.rglob("*.mkm-memory"))
    n = len(paths)
    min_d: Optional[str] = None
    max_d: Optional[str] = None
    for p in paths:
        d = _day_from_mtime(p)
        if not d:
            continue
        days[d] += 1
        if min_d is None or d < min_d:
            min_d = d
        if max_d is None or d > max_d:
            max_d = d
    return n, days, min_d, max_d


def _json_primary_date(data: Dict[str, Any]) -> Optional[str]:
    for key in ("created_at", "timestamp", "updated_at"):
        v = data.get(key)
        if isinstance(v, str) and len(v) >= 10 and v[4] == "-":
            return v[:10]
    meta = data.get("metadata")
    if isinstance(meta, dict):
        v = meta.get("created_at")
        if isinstance(v, str) and len(v) >= 10:
            return v[:10]
    return None


def sample_json_dates(paths: List[Path], every_n: int) -> Tuple[Counter[str], int, int]:
    """Every nth path, parse JSON for primary date. Returns (day_counter, ok, fail)."""
    if every_n <= 0:
        every_n = 1
    sample = [paths[i] for i in range(0, len(paths), every_n)]
    days: Counter[str] = Counter()
    ok = 0
    fail = 0
    for p in sample:
        try:
            raw = p.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            fail += 1
            continue
        if not isinstance(data, dict):
            fail += 1
            continue
        ok += 1
        pd = _json_primary_date(data)
        if pd:
            days[pd] += 1
        else:
            days["(no_date_in_json)"] += 1
    return days, ok, fail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--archive-root", default=r"F:\workspace_archive\from_C_workspace_memory_20260324")
    ap.add_argument("--current-root", default=os.environ.get("MEMORY_ROOT", r"C:\workspace\memory"))
    ap.add_argument("--out-dir", default=r"C:\workspace\reports\memory")
    ap.add_argument(
        "--json-sample-every",
        type=int,
        default=200,
        help="Parse JSON dates every N files (0=skip).",
    )
    args = ap.parse_args()

    ar = Path(args.archive_root)
    cur = Path(args.current_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    n_ar, days_ar, min_ar, max_ar = histogram_mtime(ar)
    n_cu, days_cu, min_cu, max_cu = histogram_mtime(cur)

    report: Dict[str, Any] = {
        "archive_root": str(ar),
        "archive_mkm_count": n_ar,
        "archive_mtime_day_min": min_ar,
        "archive_mtime_day_max": max_ar,
        "current_memory_root": str(cur),
        "current_mkm_count": n_cu,
        "current_mtime_day_min": min_cu,
        "current_mtime_day_max": max_cu,
        "json_sample_every": args.json_sample_every,
    }

    ar_paths = sorted(ar.rglob("*.mkm-memory")) if ar.is_dir() else []
    cu_paths = sorted(cur.rglob("*.mkm-memory")) if cur.is_dir() else []

    if args.json_sample_every > 0 and ar_paths:
        jd_ar, ok_ar, fail_ar = sample_json_dates(ar_paths, args.json_sample_every)
        report["archive_json_sample"] = {
            "every_n": args.json_sample_every,
            "parsed_ok": ok_ar,
            "parse_fail": fail_ar,
            "json_primary_date_top_days": jd_ar.most_common(40),
        }
    if args.json_sample_every > 0 and cu_paths:
        jd_cu, ok_cu, fail_cu = sample_json_dates(cu_paths, args.json_sample_every)
        report["current_json_sample"] = {
            "every_n": args.json_sample_every,
            "parsed_ok": ok_cu,
            "parse_fail": fail_cu,
            "json_primary_date_top_days": jd_cu.most_common(40),
        }

    # CSV: combined daily comparison for days that appear in either mtime hist
    all_days = sorted(set(days_ar.keys()) | set(days_cu.keys()))
    csv_path = out_dir / f"mkm_memory_timeline_by_day_{stamp}.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["day", "archive_mtime_count", "current_mtime_count"])
        for d in all_days:
            w.writerow([d, days_ar.get(d, 0), days_cu.get(d, 0)])

    json_path = out_dir / f"mkm_memory_timeline_report_{stamp}.json"
    report["mtime_by_day_archive"] = dict(days_ar.most_common())
    report["mtime_by_day_current"] = dict(days_cu.most_common())
    report["csv_path"] = str(csv_path)
    with json_path.open("w", encoding="utf-8") as jf:
        json.dump(report, jf, ensure_ascii=False, indent=2)

    print(json.dumps({k: v for k, v in report.items() if k not in ("mtime_by_day_archive", "mtime_by_day_current")}, ensure_ascii=False, indent=2))
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
