#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read-only audit: compare disk *.mkm-memory paths vs indexed file_path entries
(.mkm-index.json + per-collection .mkm-index-shard-*.json).

Orphans = on disk but not in any index path set.
Ghosts = in index but file missing on disk.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_relative(memory_root: Path, raw: Optional[str]) -> Optional[str]:
    """
    Map a file_path string to memory_root-relative POSIX path, or None if invalid/outside root.
    """
    if raw is None or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None
    mr = memory_root.resolve()
    p = Path(s)
    try:
        if p.is_absolute():
            full = p.resolve()
        else:
            full = (mr / p).resolve()
        rel = full.relative_to(mr)
    except (ValueError, OSError):
        return None
    return rel.as_posix()


def collect_indexed_paths(
    memory_root: Path,
    collection_filter: Optional[str],
) -> Set[str]:
    """Union of file_path from root index and all shard index files."""
    out: Set[str] = set()
    mr = memory_root

    root_index = mr / ".mkm-index.json"
    if root_index.exists():
        try:
            with root_index.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            for coll, memmap in data.items():
                if collection_filter is not None and coll != collection_filter:
                    continue
                if not isinstance(memmap, dict):
                    continue
                for _mid, row in memmap.items():
                    if not isinstance(row, dict):
                        continue
                    n = normalize_relative(mr, row.get("file_path"))
                    if n:
                        out.add(n)

    search_root = mr / collection_filter if collection_filter else mr
    if not search_root.is_dir():
        return out

    for shard_path in search_root.rglob(".mkm-index-shard-*.json"):
        try:
            with shard_path.open("r", encoding="utf-8") as f:
                shard_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(shard_data, dict):
            continue
        for _mid, row in shard_data.items():
            if not isinstance(row, dict):
                continue
            n = normalize_relative(mr, row.get("file_path"))
            if n:
                out.add(n)

    return out


def collect_disk_paths(
    memory_root: Path,
    collection_filter: Optional[str],
    max_files: int,
) -> Set[str]:
    """All *.mkm-memory paths relative to memory_root (POSIX)."""
    out: Set[str] = set()
    mr = memory_root.resolve()
    search_root = mr / collection_filter if collection_filter else mr
    if not search_root.is_dir():
        return out

    n = 0
    for p in search_root.rglob("*.mkm-memory"):
        try:
            rel = p.resolve().relative_to(mr)
        except ValueError:
            continue
        out.add(rel.as_posix())
        n += 1
        if max_files > 0 and n >= max_files:
            break
    return out


def _write_list(path: Path, lines: List[str], max_rows: int) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    to_write = lines if max_rows <= 0 else lines[:max_rows]
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for line in to_write:
            f.write(line + "\n")
    return len(to_write)


def main() -> int:
    wr = _workspace_root()
    ap = argparse.ArgumentParser(
        description="Audit MKM memory: disk vs index file_path (read-only)."
    )
    ap.add_argument(
        "--memory-root",
        type=Path,
        default=Path(os.environ.get("MEMORY_ROOT", str(wr / "memory"))),
        help="Memory root. Default: MEMORY_ROOT or <workspace>/memory.",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path(
            os.environ.get("MKM_MEMORY_REPORT_DIR", str(wr / "reports" / "memory"))
        ),
        help="Output directory for JSON/list files. Default: reports/memory.",
    )
    ap.add_argument(
        "--collection",
        type=str,
        default="",
        help="If set, only this collection subdirectory is scanned.",
    )
    ap.add_argument(
        "--max-samples",
        type=int,
        default=200,
        help="Max orphan/ghost paths to include in JSON samples (each). Default: 200.",
    )
    ap.add_argument(
        "--write-lists",
        action="store_true",
        help="Write orphan/ghost full lists to text files (use with care for large trees).",
    )
    ap.add_argument(
        "--max-list-rows",
        type=int,
        default=0,
        help="Cap lines written per list when --write-lists (0 = no cap).",
    )
    ap.add_argument(
        "--max-disk-files",
        type=int,
        default=0,
        help="If >0, stop after N disk files (smoke test; skips latest symlink update).",
    )
    args = ap.parse_args()

    memory_root = Path(args.memory_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    collection_filter = args.collection.strip() or None

    if not memory_root.is_dir():
        print(
            json.dumps(
                {"error": "memory_root_not_found", "path": str(memory_root)},
                ensure_ascii=False,
            ),
            flush=True,
        )
        return 2

    t0 = time.perf_counter()
    print(
        f"[audit] memory_root={memory_root} collection={collection_filter or '*'}",
        flush=True,
    )

    indexed = collect_indexed_paths(memory_root, collection_filter)
    disk = collect_disk_paths(memory_root, collection_filter, args.max_disk_files)

    orphans = sorted(disk - indexed)
    ghosts = sorted(indexed - disk)

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    max_s = max(0, int(args.max_samples))
    partial = args.max_disk_files > 0

    summary: Dict[str, object] = {
        "timestamp_utc": stamp,
        "memory_root": str(memory_root.resolve()),
        "collection_filter": collection_filter,
        "indexed_path_count": len(indexed),
        "disk_file_count": len(disk),
        "orphan_count": len(orphans),
        "ghost_count": len(ghosts),
        "orphan_sample": orphans[:max_s],
        "ghost_sample": ghosts[:max_s],
        "duration_ms": elapsed_ms,
        "max_disk_files_cap": int(args.max_disk_files),
        "partial_disk_scan": partial,
    }
    if partial:
        summary["audit_note"] = (
            "partial_disk_scan: ghost_count and orphan_count are not comparable to a full run; "
            "ghosts are inflated when disk set is capped."
        )

    out_json = out_dir / f"mkm_index_drift_audit_{stamp}.json"
    with out_json.open("w", encoding="utf-8") as jf:
        json.dump(summary, jf, ensure_ascii=False, indent=2)

    if args.write_lists:
        op = out_dir / f"mkm_index_drift_orphans_{stamp}.txt"
        gp = out_dir / f"mkm_index_drift_ghosts_{stamp}.txt"
        w1 = _write_list(op, orphans, int(args.max_list_rows))
        w2 = _write_list(gp, ghosts, int(args.max_list_rows))
        summary["orphan_list_path"] = str(op.resolve())
        summary["ghost_list_path"] = str(gp.resolve())
        summary["orphan_list_lines_written"] = w1
        summary["ghost_list_lines_written"] = w2
        # refresh summary file with paths
        with out_json.open("w", encoding="utf-8") as jf:
            json.dump(summary, jf, ensure_ascii=False, indent=2)

    if partial:
        print(
            "[audit] WARNING: partial disk scan — interpret ghost/orphan counts only as pipeline smoke, "
            "not production drift metrics.",
            flush=True,
        )
    if args.max_disk_files <= 0 and collection_filter is None:
        latest = out_dir / "mkm_index_drift_audit_latest.json"
        with latest.open("w", encoding="utf-8") as jf:
            json.dump(summary, jf, ensure_ascii=False, indent=2)
        print(f"Wrote: {latest}", flush=True)
    else:
        print(
            "[audit] did not update mkm_index_drift_audit_latest.json "
            "(requires full scan with no --collection filter and --max-disk-files 0).",
            flush=True,
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote: {out_json}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
