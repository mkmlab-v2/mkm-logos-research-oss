#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Read-only audit of .mkm-memory under C:\\workspace\\memory and F:\\workspace_archive (configurable).
Outputs total_memory_audit_v1.json (+ optional CSV of duplicate keys).

Optional: --quarantine-corrupted copies (never moves by default) broken JSON to reports dir.
Optional: --emit-missing-list writes paths where vector_4d fails validation (JSON + txt).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Set, Tuple


def _is_valid_vector_4d(v: Any) -> Tuple[bool, str]:
    if not isinstance(v, dict):
        return False, "not_object"
    for k in ("S", "L", "K", "M"):
        if k not in v:
            return False, f"missing_{k}"
        try:
            x = float(v[k])
        except (TypeError, ValueError):
            return False, f"non_numeric_{k}"
        if x < 0.0 or x > 1.0:
            return False, f"out_of_range_{k}"
    return True, "ok"


def _path_excluded(path: Path, prefixes: List[str]) -> bool:
    if not prefixes:
        return False
    s = str(path.resolve()).lower()
    for pre in prefixes:
        p = (pre or "").strip().lower()
        if not p:
            continue
        if s.startswith(p):
            return True
    return False


def _canonical_id(data: Optional[Dict[str, Any]], stem: str) -> str:
    if data:
        for key in ("id", "memory_id"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return stem


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--roots",
        nargs="+",
        default=[
            r"C:\workspace\memory",
            r"F:\workspace_archive\from_C_workspace_memory_20260324",
        ],
    )
    ap.add_argument("--out-dir", default=r"C:\workspace\reports\memory")
    ap.add_argument(
        "--progress-every",
        type=int,
        default=15000,
        help="Print progress to stderr every N files.",
    )
    ap.add_argument(
        "--quarantine-corrupted",
        action="store_true",
        help="Copy JSON parse failures to out-dir/corrupted_quarantine_<stamp>/ (does not delete source).",
    )
    ap.add_argument(
        "--max-error-paths",
        type=int,
        default=400,
        help="Max parse error paths to list in JSON (rest is count only).",
    )
    ap.add_argument(
        "--emit-missing-list",
        action="store_true",
        help="Write total_memory_audit_v1_missing_vector_4d.json and .txt (path + reason per row).",
    )
    ap.add_argument(
        "--exclude-prefix",
        action="append",
        default=[],
        metavar="PATH_PREFIX",
        help="Skip .mkm-memory files whose resolved path starts with this prefix (case-insensitive). Repeatable.",
    )
    ap.add_argument(
        "--local-memory-only",
        action="store_true",
        help="Scan only C:\\\\workspace\\\\memory (overrides --roots). Use for local SSOT counts without Vault mirrors.",
    )
    args = ap.parse_args()

    if args.local_memory_only:
        args.roots = [r"C:\workspace\memory"]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    quarantine_root: Optional[Path] = None
    if args.quarantine_corrupted:
        quarantine_root = out_dir / f"corrupted_quarantine_{stamp}"
        quarantine_root.mkdir(parents=True, exist_ok=True)

    excluded_by_prefix = 0
    all_paths: List[Tuple[str, Path]] = []
    for root in args.roots:
        rp = Path(root)
        label = str(rp)
        if not rp.is_dir():
            continue
        for p in rp.rglob("*.mkm-memory"):
            resolved = p.resolve()
            if _path_excluded(resolved, args.exclude_prefix):
                excluded_by_prefix += 1
                continue
            all_paths.append((label, resolved))

    total_files = len(all_paths)
    parse_ok = 0
    parse_fail = 0
    missing_vec = 0
    invalid_vec = 0
    valid_vec = 0
    total_bytes = 0
    per_root_bytes: DefaultDict[str, int] = defaultdict(int)
    per_root_files: DefaultDict[str, int] = defaultdict(int)

    id_to_paths: DefaultDict[str, List[str]] = defaultdict(list)
    stem_to_paths: DefaultDict[str, List[str]] = defaultdict(list)
    parse_error_samples: List[str] = []
    vector_problem_rows: List[Dict[str, str]] = []

    for idx, (label, path) in enumerate(all_paths, start=1):
        if args.progress_every and idx % args.progress_every == 0:
            print(f"[audit] {idx}/{total_files}", file=sys.stderr, flush=True)
        try:
            sz = path.stat().st_size
        except OSError:
            parse_fail += 1
            continue
        total_bytes += sz
        per_root_bytes[label] += sz
        per_root_files[label] += 1

        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
            parse_fail += 1
            if len(parse_error_samples) < args.max_error_paths:
                parse_error_samples.append(f"{path}|{type(e).__name__}:{e}")
            if quarantine_root:
                rel = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:16]
                dst = quarantine_root / f"{rel}.mkm-memory.txt"
                try:
                    shutil.copy2(path, dst)
                except OSError:
                    pass
            continue

        if not isinstance(data, dict):
            parse_fail += 1
            continue

        parse_ok += 1
        stem = path.stem
        stem_to_paths[stem].append(str(path))

        cid = _canonical_id(data, stem)
        id_to_paths[cid].append(str(path))

        v = data.get("vector_4d")
        ok, reason = _is_valid_vector_4d(v)
        if ok:
            valid_vec += 1
        else:
            if v is None or (isinstance(v, dict) and not all(k in v for k in ("S", "L", "K", "M"))):
                missing_vec += 1
                kind = "missing_or_incomplete"
            else:
                invalid_vec += 1
                kind = "invalid_range_or_type"
            if args.emit_missing_list:
                vector_problem_rows.append(
                    {
                        "path": str(path),
                        "root_label": label,
                        "failure_reason": reason,
                        "kind": kind,
                    }
                )

    duplicate_ids = {k: v for k, v in id_to_paths.items() if len(v) > 1}
    duplicate_stems = {k: v for k, v in stem_to_paths.items() if len(v) > 1}

    dup_id_count = sum(len(v) - 1 for v in duplicate_ids.values())
    unique_ids = len(id_to_paths)

    report: Dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "roots": args.roots,
        "scan_filters": {
            "exclude_prefixes": list(args.exclude_prefix or []),
            "local_memory_only": bool(args.local_memory_only),
            "paths_skipped_by_exclude_prefix": excluded_by_prefix,
        },
        "total_mkm_files": total_files,
        "total_bytes": total_bytes,
        "per_root": {
            label: {"mkm_files": per_root_files.get(label, 0), "bytes": per_root_bytes.get(label, 0)}
            for label in sorted(set(per_root_files.keys()) | set(per_root_bytes.keys()))
        },
        "json_parse_ok": parse_ok,
        "json_parse_fail": parse_fail,
        "vector_4d": {
            "valid_slkm_0_1": valid_vec,
            "missing_or_incomplete": missing_vec,
            "invalid_range_or_type": invalid_vec,
            "missing_rate": round((missing_vec + invalid_vec) / parse_ok, 6) if parse_ok else None,
        },
        "identity": {
            "unique_canonical_ids": unique_ids,
            "duplicate_canonical_id_keys": len(duplicate_ids),
            "files_in_duplicate_id_groups": sum(len(v) for v in duplicate_ids.values()),
            "extra_paths_from_duplicates": dup_id_count,
            "duplicate_filename_stems": len(duplicate_stems),
        },
        "parse_error_sample_paths": parse_error_samples,
        "parse_error_sample_truncated": parse_fail > len(parse_error_samples),
        "quarantine_copied_to": str(quarantine_root) if quarantine_root else None,
        "notes": [
            "canonical_id = JSON id|memory_id else filename stem; duplicate = same canonical_id, >1 path.",
            "vector validity: S,L,K,M present and each in [0,1].",
        ],
    }
    if args.emit_missing_list:
        report["vector_4d_problem_count"] = len(vector_problem_rows)
        report["vector_4d_problem_list_path"] = str(
            out_dir / "total_memory_audit_v1_missing_vector_4d.json"
        )

    out_json = out_dir / "total_memory_audit_v1.json"
    with out_json.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    dup_csv = out_dir / f"total_memory_audit_v1_duplicate_ids_{stamp}.csv"
    with dup_csv.open("w", encoding="utf-8-sig", newline="") as cf:
        w = csv.writer(cf)
        w.writerow(["canonical_id", "path_count", "paths"])
        for k in sorted(duplicate_ids.keys(), key=lambda x: (-len(duplicate_ids[x]), x))[:5000]:
            paths = duplicate_ids[k]
            w.writerow([k, len(paths), " | ".join(paths[:20]) + (" ..." if len(paths) > 20 else "")])

    if args.emit_missing_list:
        miss_json = out_dir / "total_memory_audit_v1_missing_vector_4d.json"
        with miss_json.open("w", encoding="utf-8") as mf:
            json.dump(vector_problem_rows, mf, ensure_ascii=False, indent=2)
        miss_txt = out_dir / "total_memory_audit_v1_missing_vector_4d.txt"
        with miss_txt.open("w", encoding="utf-8") as tf:
            for row in vector_problem_rows:
                tf.write(row["path"] + "\n")
        print(f"Wrote: {miss_json} ({len(vector_problem_rows)} rows)", file=sys.stderr)
        print(f"Wrote: {miss_txt}", file=sys.stderr)

    print(json.dumps({k: v for k, v in report.items() if k != "parse_error_sample_paths"}, ensure_ascii=False, indent=2))
    print(f"Wrote: {out_json}", file=sys.stderr)
    print(f"Wrote: {dup_csv} (first 5000 duplicate keys)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
