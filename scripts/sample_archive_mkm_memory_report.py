#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read-only: sample F: archive .mkm-memory (every Nth file), summarize dates/vectors/keywords stub.
Compare date range with C:\\workspace\\memory .mkm-memory (light scan).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _parse_iso_date(s: str) -> Optional[str]:
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def _extract_dates(data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns (primary_date, created, updated) as YYYY-MM-DD or None."""
    created = (
        data.get("created_at")
        or data.get("timestamp")
        or (data.get("metadata") or {}).get("created_at")
    )
    updated = data.get("updated_at")
    if isinstance(created, str):
        cd = _parse_iso_date(created)
    else:
        cd = None
    if isinstance(updated, str):
        ud = _parse_iso_date(updated)
    else:
        ud = None
    primary = cd or ud
    return primary, cd, ud


def _has_4d(data: Dict[str, Any]) -> bool:
    v = data.get("vector_4d")
    if not isinstance(v, dict):
        return False
    return all(k in v for k in ("S", "L", "K", "M"))


def _keyword_stub(content: str, max_words: int = 12) -> str:
    if not content:
        return ""
    words = re.findall(r"[\w가-힣]{2,}", content[:2000])
    return " ".join(words[:max_words])


def _scan_mkm_paths(root: Path) -> List[Path]:
    if not root.is_dir():
        return []
    return sorted(root.rglob("*.mkm-memory"))


def _sample_every_n(paths: List[Path], n: int) -> List[Path]:
    if n <= 1:
        return paths
    return [paths[i] for i in range(0, len(paths), n)]


def _scan_one(path: Path) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "rel_path": str(path),
        "file_size": 0,
        "mtime_iso": "",
        "parse_ok": False,
        "parse_error": "",
        "primary_date": "",
        "created_date": "",
        "updated_date": "",
        "schema_hint": "",
        "has_vector_4d": False,
        "compression_mode": "",
        "content_len": 0,
        "keyword_stub": "",
    }
    try:
        row["file_size"] = path.stat().st_size
        row["mtime_iso"] = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
    except OSError as e:
        row["parse_error"] = f"stat:{e}"
        return row
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        row["parse_error"] = f"read_json:{e}"
        return row
    if not isinstance(data, dict):
        row["parse_error"] = "not_object"
        return row

    row["parse_ok"] = True
    primary, cd, ud = _extract_dates(data)
    row["primary_date"] = primary or ""
    row["created_date"] = cd or ""
    row["updated_date"] = ud or ""
    if data.get("compression_mode"):
        row["compression_mode"] = str(data.get("compression_mode"))
    if "collection" in data:
        row["schema_hint"] = "file_based_memory"
    elif "memory_id" in data and "timestamp" in data:
        row["schema_hint"] = "unified_pipeline"
    else:
        row["schema_hint"] = "other"

    content = data.get("content")
    if isinstance(content, str):
        row["content_len"] = len(content)
        row["keyword_stub"] = _keyword_stub(content)
    else:
        row["content_len"] = 0
        row["keyword_stub"] = ""

    row["has_vector_4d"] = _has_4d(data)
    return row


def _date_range_from_rows(rows: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[str]]:
    dates = [r.get("primary_date") for r in rows if r.get("parse_ok") and r.get("primary_date")]
    if not dates:
        return None, None
    return min(dates), max(dates)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--archive-root",
        default=r"F:\workspace_archive\from_C_workspace_memory_20260324",
    )
    ap.add_argument(
        "--current-root",
        default=os.environ.get("MEMORY_ROOT", r"C:\workspace\memory"),
    )
    ap.add_argument("--every-n", type=int, default=1000, help="Sample 1 file per N files (sorted).")
    ap.add_argument(
        "--current-sample-cap",
        type=int,
        default=500,
        help="Max .mkm-memory files to read in current tree for date range (spread sampling).",
    )
    ap.add_argument(
        "--out-dir",
        default=r"C:\workspace\reports\memory",
    )
    args = ap.parse_args()

    archive_root = Path(args.archive_root)
    current_root = Path(args.current_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"archive_mkm_sample_{stamp}.csv"
    json_path = out_dir / f"archive_mkm_sample_summary_{stamp}.json"

    archive_paths = _scan_mkm_paths(archive_root)
    samples = _sample_every_n(archive_paths, max(1, args.every_n))

    sample_rows: List[Dict[str, Any]] = []
    for p in samples:
        sample_rows.append(_scan_one(p))

    # Current memory: spread-sample for date range
    cur_paths = _scan_mkm_paths(current_root)
    cur_subset: List[Path] = []
    if cur_paths:
        cap = min(args.current_sample_cap, len(cur_paths))
        if len(cur_paths) <= cap:
            cur_subset = cur_paths
        else:
            step = max(1, len(cur_paths) // cap)
            cur_subset = [cur_paths[i] for i in range(0, len(cur_paths), step)][:cap]

    cur_rows = [_scan_one(p) for p in cur_subset]

    arch_min, arch_max = _date_range_from_rows(sample_rows)
    cur_min, cur_max = _date_range_from_rows(cur_rows)

    parse_fail = sum(1 for r in sample_rows if not r.get("parse_ok"))
    vec_yes = sum(1 for r in sample_rows if r.get("has_vector_4d"))
    kw_tokens: Counter[str] = Counter()
    for r in sample_rows:
        for w in (r.get("keyword_stub") or "").split():
            if len(w) >= 2:
                kw_tokens[w.lower()[:40]] += 1

    summary = {
        "archive_root": str(archive_root),
        "archive_total_mkm_files": len(archive_paths),
        "archive_sample_every_n": args.every_n,
        "archive_sample_count": len(samples),
        "archive_sample_parse_failures": parse_fail,
        "archive_sample_has_vector_4d_count": vec_yes,
        "archive_sample_date_range_primary": {"min": arch_min, "max": arch_max},
        "current_memory_root": str(current_root),
        "current_total_mkm_files": len(cur_paths),
        "current_files_read_for_range": len(cur_subset),
        "current_date_range_primary": {"min": cur_min, "max": cur_max},
        "top_keyword_stubs_in_archive_samples": kw_tokens.most_common(30),
        "notes": [
            "Primary date = created_at or timestamp or updated_at (first 10 chars YYYY-MM-DD).",
            "Archive vs current ranges are from sampled JSON fields + spread sample; not exhaustive.",
        ],
    }

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fields = [
            "rel_path",
            "file_size",
            "mtime_iso",
            "parse_ok",
            "parse_error",
            "primary_date",
            "created_date",
            "updated_date",
            "schema_hint",
            "has_vector_4d",
            "compression_mode",
            "content_len",
            "keyword_stub",
        ]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in sample_rows:
            w.writerow({k: r.get(k, "") for k in fields})

    with json_path.open("w", encoding="utf-8") as jf:
        json.dump(summary, jf, ensure_ascii=False, indent=2)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote: {csv_path}")
    print(f"Wrote: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
