#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read-only inventory of *.mkm-memory files: schema guess, compression markers, size stats.
Does not modify or delete any file.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _word_count(text: str) -> int:
    if not text:
        return 0
    parts = re.split(r"\s+", text.strip())
    return len([p for p in parts if p])


def classify_record(data: Dict[str, Any]) -> Tuple[str, bool, bool, Optional[str]]:
    """
    Returns: schema_guess, has_ultra_markers, has_coordinate_map, compression_mode
    """
    has_coord = isinstance(data.get("coordinate_map"), dict)
    mode = data.get("compression_mode")
    if isinstance(mode, str):
        mode_s = mode
    else:
        mode_s = None
    has_ultra = bool(mode_s == "ultra" or has_coord)

    if has_ultra:
        schema = "unified_pipeline_ultra"
    elif "collection" in data and ("id" in data or "updated_at" in data):
        schema = "file_based_memory"
    elif "memory_id" in data and "timestamp" in data:
        schema = "unified_pipeline_plain"
    elif "id" in data and "content" in data:
        schema = "file_based_memory_loose"
    else:
        schema = "unknown_schema"

    return schema, has_ultra, has_coord, mode_s


def suggest_tier(
    schema: str,
    content_len: int,
    collection: str,
) -> str:
    col = (collection or "").lower()
    if any(k in col for k in ("logos", "constitution", "canon", "command")):
        return "P0_review_keep_raw"
    if schema in ("unified_pipeline_ultra",):
        return "already_compressed_marker"
    if schema in ("unknown_schema",):
        return "manual_review"
    if content_len >= 50_000:
        return "P1_large_raw_candidate"
    if content_len >= 8_000:
        return "P2_compression_candidate"
    return "small_or_ok"


def blacklist_candidate(
    schema: str,
    content_len: int,
    has_ultra: bool,
    min_raw_chars: int,
) -> str:
    if has_ultra:
        return "no"
    if schema in ("file_based_memory", "file_based_memory_loose", "unified_pipeline_plain"):
        if content_len >= min_raw_chars:
            return "yes"
    return "no"


def scan_one(path: Path, min_raw_chars: int) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "rel_path": "",
        "file_size_bytes": 0,
        "parse_error": "",
        "content_char_len": "",
        "word_count": "",
        "word_density": "",
        "schema_guess": "",
        "has_ultra_markers": "",
        "has_coordinate_map": "",
        "compression_mode": "",
        "original_content_length": "",
        "collection": "",
        "category": "",
        "suggested_tier": "",
        "blacklist_inefficient_raw": "",
    }
    try:
        rel = path.resolve()
    except OSError as e:
        row["parse_error"] = f"path_error:{e}"
        return row

    row["rel_path"] = str(path)
    try:
        row["file_size_bytes"] = path.stat().st_size
    except OSError as e:
        row["parse_error"] = f"stat_error:{e}"
        return row

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        row["parse_error"] = f"read_error:{e}"
        return row

    if not isinstance(data, dict):
        row["parse_error"] = "json_not_object"
        return row

    content = data.get("content")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = json.dumps(content, ensure_ascii=False)

    content_len = len(content)
    wc = _word_count(content)
    density = round(wc / max(content_len, 1), 6)

    schema, has_ultra, has_coord, mode = classify_record(data)
    tier = suggest_tier(schema, content_len, str(data.get("collection") or ""))
    bl = blacklist_candidate(schema, content_len, has_ultra, min_raw_chars)

    row["content_char_len"] = content_len
    row["word_count"] = wc
    row["word_density"] = density
    row["schema_guess"] = schema
    row["has_ultra_markers"] = str(has_ultra).lower()
    row["has_coordinate_map"] = str(has_coord).lower()
    row["compression_mode"] = mode or ""
    ocl = data.get("original_content_length")
    row["original_content_length"] = ocl if ocl is not None else ""
    row["collection"] = str(data.get("collection") or "")
    row["category"] = str(data.get("category") or "")
    row["suggested_tier"] = tier
    row["blacklist_inefficient_raw"] = bl
    return row


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    wr = _workspace_root()
    p = argparse.ArgumentParser(description="Inventory .mkm-memory (read-only).")
    p.add_argument(
        "--memory-root",
        type=Path,
        default=Path(os.environ.get("MEMORY_ROOT", str(wr / "memory"))),
        help="Root directory to scan (recursive). Default: <workspace>/memory or MEMORY_ROOT.",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path(os.environ.get("MKM_MEMORY_REPORT_DIR", str(wr / "reports" / "memory"))),
        help="Directory for CSV/JSON. Default: <workspace>/reports/memory.",
    )
    p.add_argument(
        "--min-chars-flag",
        type=int,
        default=8000,
        help="Threshold for blacklist_inefficient_raw (non-ultra raw content).",
    )
    p.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="If >0, only process first N files after sort (smoke test).",
    )
    args = p.parse_args()
    root = Path(args.memory_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    out_csv = out_dir / f"mkm_memory_inventory_{stamp}.csv"

    files: List[Path] = []
    if root.is_dir():
        files = sorted(root.rglob("*.mkm-memory"))
    if args.max_files > 0:
        files = files[: args.max_files]

    print(f"[inventory] memory_root={root} files_found={len(files)}", flush=True)

    fieldnames = [
        "rel_path",
        "file_size_bytes",
        "parse_error",
        "content_char_len",
        "word_count",
        "word_density",
        "schema_guess",
        "has_ultra_markers",
        "has_coordinate_map",
        "compression_mode",
        "original_content_length",
        "collection",
        "category",
        "suggested_tier",
        "blacklist_inefficient_raw",
    ]

    rows: List[Dict[str, Any]] = []
    for i, fp in enumerate(files, start=1):
        rows.append(scan_one(fp, args.min_chars_flag))
        if i % 500 == 0:
            print(f"[inventory] processed {i}/{len(files)}", flush=True)

    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    # Summary counts
    total = len(rows)
    errors = sum(1 for r in rows if r.get("parse_error"))
    ultra = sum(1 for r in rows if str(r.get("has_ultra_markers")).lower() == "true")
    bl = sum(1 for r in rows if r.get("blacklist_inefficient_raw") == "yes")
    by_schema: Dict[str, int] = {}
    for r in rows:
        if r.get("parse_error"):
            continue
        sg = str(r.get("schema_guess") or "unknown")
        by_schema[sg] = by_schema.get(sg, 0) + 1

    summary = {
        "timestamp_utc": stamp,
        "memory_root": str(root.resolve()) if root.is_dir() else str(root),
        "total_mkm_memory_files": total,
        "parse_errors": errors,
        "has_ultra_markers": ultra,
        "blacklist_inefficient_raw_yes": bl,
        "min_chars_threshold": args.min_chars_flag,
        "by_schema_guess": by_schema,
        "csv_path": str(out_csv.resolve()),
    }
    if args.max_files > 0:
        summary["sample_run"] = True
        summary["max_files_cap"] = int(args.max_files)

    summary_path = out_dir / f"mkm_memory_inventory_summary_{stamp}.json"
    with summary_path.open("w", encoding="utf-8") as jf:
        json.dump(summary, jf, ensure_ascii=False, indent=2)

    # Do not overwrite mkm_memory_inventory_latest.* when capped (e.g. health chain --max-files 8000).
    if args.max_files <= 0:
        latest_json = out_dir / "mkm_memory_inventory_latest.json"
        latest_csv = out_dir / "mkm_memory_inventory_latest.csv"
        with latest_json.open("w", encoding="utf-8") as jf:
            json.dump(summary, jf, ensure_ascii=False, indent=2)
        try:
            shutil.copy2(out_csv, latest_csv)
        except OSError:
            pass
        print(f"Wrote: {latest_json}")
        print(f"Wrote: {latest_csv}")
    else:
        print(
            "[inventory] sample run: did not update mkm_memory_inventory_latest.* (full scan: --max-files 0 or omit)",
            flush=True,
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote: {out_csv}")
    print(f"Wrote: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
