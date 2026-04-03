#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hoist vector_4d from vectorization.vector_4d to root for FileBasedMemory-compatible .mkm-memory.

Default: dry-run only. Use --apply to write files (creates .bak next to each file first).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def _valid_slkm(v: Any) -> bool:
    if not isinstance(v, dict):
        return False
    for k in ("S", "L", "K", "M"):
        if k not in v:
            return False
        try:
            x = float(v[k])
        except (TypeError, ValueError):
            return False
        if x < 0.0 or x > 1.0:
            return False
    return True


def _extract_nested_4d(data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    vec = data.get("vectorization")
    if not isinstance(vec, dict):
        return None
    inner = vec.get("vector_4d")
    if not isinstance(inner, dict):
        return None
    out = {}
    for k in ("S", "L", "K", "M"):
        if k not in inner:
            return None
        try:
            out[k] = float(inner[k])
        except (TypeError, ValueError):
            return None
    return out


def _needs_hoist(data: Dict[str, Any]) -> Tuple[bool, str]:
    root = data.get("vector_4d")
    if _valid_slkm(root):
        return False, "already_ok"
    nested = _extract_nested_4d(data)
    if nested is not None:
        return True, "from_vectorization"
    return False, "no_fixable_source"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--from-json",
        type=Path,
        default=Path(r"C:\workspace\reports\memory\total_memory_audit_v1_missing_vector_4d.json"),
        help="List of objects with 'path' key (audit export).",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (with .bak backup). Without this, dry-run only.",
    )
    ap.add_argument("--no-backup", action="store_true", help="Skip .bak copy when applying (not recommended).")
    args = ap.parse_args()

    if not args.from_json.is_file():
        print(f"Missing input: {args.from_json}", file=sys.stderr)
        return 1

    raw = args.from_json.read_text(encoding="utf-8")
    rows = json.loads(raw)
    if not isinstance(rows, list):
        print("from-json must be a JSON array", file=sys.stderr)
        return 1

    paths: List[Path] = []
    for row in rows:
        if isinstance(row, dict) and row.get("path"):
            paths.append(Path(row["path"]))

    would_fix: List[str] = []
    skip: List[str] = []
    errors: List[str] = []

    for path in paths:
        if not path.is_file():
            errors.append(f"missing_file:{path}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            errors.append(f"read:{path}|{e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"not_object:{path}")
            continue

        need, reason = _needs_hoist(data)
        if not need:
            skip.append(f"{path}|{reason}")
            continue

        nested = _extract_nested_4d(data)
        assert nested is not None

        would_fix.append(str(path))
        if not args.apply:
            continue

        data["vector_4d"] = {k: nested[k] for k in ("S", "L", "K", "M")}
        meta = data.get("metadata")
        if isinstance(meta, dict):
            meta["vector_4d_hoisted_at"] = datetime.now(timezone.utc).isoformat()
            meta["vector_4d_hoisted_from"] = "vectorization.vector_4d"
        else:
            data["metadata"] = {
                "vector_4d_hoisted_at": datetime.now(timezone.utc).isoformat(),
                "vector_4d_hoisted_from": "vectorization.vector_4d",
            }

        if not args.no_backup:
            bak = path.with_suffix(path.suffix + ".bak")
            try:
                shutil.copy2(path, bak)
            except OSError as e:
                errors.append(f"backup_failed:{path}|{e}")
                continue

        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            errors.append(f"write:{path}|{e}")

    summary = {
        "input_paths": len(paths),
        "would_fix_or_fixed": len(would_fix),
        "skipped": len(skip),
        "errors": len(errors),
        "apply_mode": bool(args.apply),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if would_fix and not args.apply:
        print("--- dry-run: would hoist vector_4d for ---", file=sys.stderr)
        for p in would_fix[:20]:
            print(p, file=sys.stderr)
        if len(would_fix) > 20:
            print(f"... +{len(would_fix) - 20} more", file=sys.stderr)
    if errors:
        print("--- errors ---", file=sys.stderr)
        for e in errors[:30]:
            print(e, file=sys.stderr)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
