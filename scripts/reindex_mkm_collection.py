#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rebuild index entries for an existing *.mkm-memory collection.

Default is dry-run; use --apply to write:
- memory/.mkm-index.json (collection section only)
- memory/<collection>/.mkm-index-shard-*.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_name(value: str) -> str:
    return value.replace("\\", "_").replace("/", "_").strip("_") or "collection"


def _safe_json_load(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _entry_from_file(memory_root: Path, file_path: Path) -> Tuple[str, Dict[str, Any]]:
    raw = _safe_json_load(file_path)
    memory_id = str(raw.get("id") or file_path.stem)
    vector_4d = raw.get("vector_4d") or {}
    if not isinstance(vector_4d, dict):
        vector_4d = {}
    entry = {
        "vector_4d": vector_4d,
        "category": str(raw.get("category") or "general"),
        "tags": raw.get("tags") if isinstance(raw.get("tags"), list) else [],
        "file_path": str(file_path.relative_to(memory_root)).replace("\\", "/"),
        "created_at": str(raw.get("created_at") or ""),
    }
    return memory_id, entry


def _shard_id(collection: str, memory_id: str, shard_count: int) -> int:
    hv = int(hashlib.md5(f"{collection}_{memory_id}".encode()).hexdigest(), 16)
    return hv % max(1, shard_count)


def main() -> int:
    wr = _workspace_root()
    ap = argparse.ArgumentParser(description="Reindex one mkm-memory collection.")
    ap.add_argument("--collection", required=True, help="Collection directory name under memory/.")
    ap.add_argument(
        "--memory-root",
        type=Path,
        default=Path(os.environ.get("MEMORY_ROOT", str(wr / "memory"))),
        help="Memory root (default: MEMORY_ROOT or <workspace>/memory).",
    )
    ap.add_argument(
        "--out-dir",
        type=Path,
        default=Path(os.environ.get("MKM_MEMORY_REPORT_DIR", str(wr / "reports" / "memory"))),
        help="Output dir for audit summary.",
    )
    ap.add_argument("--shard-size", type=int, default=1000, help="Shard size target (default: 1000).")
    ap.add_argument("--max-files", type=int, default=0, help="If >0, cap files for smoke test.")
    ap.add_argument("--apply", action="store_true", help="Write index files. Default: dry-run.")
    args = ap.parse_args()

    memory_root = Path(args.memory_root)
    collection = args.collection.strip()
    if not collection:
        print(json.dumps({"error": "empty_collection"}, ensure_ascii=False))
        return 2
    coll_dir = memory_root / collection
    if not coll_dir.is_dir():
        print(json.dumps({"error": "collection_not_found", "path": str(coll_dir)}, ensure_ascii=False))
        return 2

    files = sorted(coll_dir.glob("*.mkm-memory"))
    if args.max_files > 0:
        files = files[: args.max_files]

    rebuilt: Dict[str, Dict[str, Any]] = {}
    duplicates = 0
    for fp in files:
        memory_id, entry = _entry_from_file(memory_root, fp)
        if memory_id in rebuilt:
            duplicates += 1
            # Keep latest by lexical file path for deterministic behavior.
            if entry["file_path"] > rebuilt[memory_id]["file_path"]:
                rebuilt[memory_id] = entry
        else:
            rebuilt[memory_id] = entry

    count = len(rebuilt)
    shard_count = max(1, (count // max(1, int(args.shard_size))) + 1)
    shards: List[Dict[str, Dict[str, Any]]] = [dict() for _ in range(shard_count)]
    for memory_id, entry in rebuilt.items():
        sid = _shard_id(collection, memory_id, shard_count)
        shards[sid][memory_id] = entry

    write_changed = False
    if args.apply:
        root_index_path = memory_root / ".mkm-index.json"
        root_index = _safe_json_load(root_index_path)
        root_index[collection] = rebuilt
        root_index_path.write_text(json.dumps(root_index, ensure_ascii=False, indent=2), encoding="utf-8")
        write_changed = True

        for sid in range(shard_count):
            shard_path = coll_dir / f".mkm-index-shard-{sid}.json"
            shard_path.write_text(json.dumps(shards[sid], ensure_ascii=False, indent=2), encoding="utf-8")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()
    summary = {
        "timestamp_utc": stamp,
        "collection": collection,
        "memory_root": str(memory_root.resolve()),
        "files_seen": len(files),
        "entries_rebuilt": count,
        "duplicate_ids_collapsed": duplicates,
        "shard_size": int(args.shard_size),
        "shard_count": shard_count,
        "applied": bool(args.apply),
        "max_files_cap": int(args.max_files),
        "root_index_written": bool(write_changed),
    }
    out_path = out_dir / f"mkm_collection_reindex_{_safe_name(collection)}_{stamp}.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
