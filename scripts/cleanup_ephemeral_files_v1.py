#!/usr/bin/env python3
"""Cleanup ephemeral files/directories in workspace with retention policy.

Default mode is dry-run. Use --apply to perform deletions.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List


DEFAULT_RETENTION_DAYS = 3
DEFAULT_SUMMARY_OUT = "docs/final/artifacts/ephemeral_cleanup_summary_latest.json"
DEFAULT_LOG_PATH = "reports/ephemeral_cleanup_log.jsonl"
DEFAULT_WHITELIST_JSON = "scripts/ephemeral_cleanup_whitelist_v1.json"


@dataclass
class Candidate:
    path: Path
    kind: str
    age_days: float
    size_bytes: int
    rule: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def safe_relpath(root: Path, p: Path) -> str:
    return p.resolve().relative_to(root.resolve()).as_posix()


def path_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total


def collect_by_glob(root: Path, pattern: str) -> List[Path]:
    return [p for p in root.glob(pattern) if p.exists()]


def collect_candidates(root: Path, now: datetime, retention_days: int) -> List[Candidate]:
    candidates: List[Candidate] = []

    dir_rules = [
        ("tmp", "tmp_tree"),
        ("staging", "staging_tree"),
        ("out", "out_tree"),
        ("logs", "logs_tree"),
    ]
    root_dir_globs = [
        ("logos_reval_*", "logos_reval_root"),
    ]
    file_rules = [
        ("tmp_*.html", "tmp_html"),
        ("tmp_*.css", "tmp_css"),
        ("*.tmp", "tmp_ext"),
        ("*.temp", "temp_ext"),
    ]

    def append_candidate(path: Path, rule: str) -> None:
        if path.resolve() == root.resolve():
            return
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            return
        age_days = (now - mtime).total_seconds() / 86400.0
        if age_days < retention_days:
            return
        kind = "dir" if path.is_dir() else "file"
        candidates.append(
            Candidate(
                path=path,
                kind=kind,
                age_days=age_days,
                size_bytes=path_size_bytes(path),
                rule=rule,
            )
        )

    for relative_dir, rule in dir_rules:
        p = root / relative_dir
        if p.exists():
            append_candidate(p, rule)

    for pattern, rule in root_dir_globs:
        for p in collect_by_glob(root, pattern):
            if p.is_dir():
                append_candidate(p, rule)

    for pattern, rule in file_rules:
        for p in collect_by_glob(root, pattern):
            append_candidate(p, rule)

    unique = {}
    for c in candidates:
        unique[str(c.path.resolve())] = c
    return sorted(unique.values(), key=lambda x: str(x.path))


def filter_by_allowed_roots(candidates: List[Candidate], allowed_roots: List[str]) -> List[Candidate]:
    if not allowed_roots:
        return candidates
    normalized = [x.strip().strip("/\\").lower() for x in allowed_roots if x.strip()]
    allowed = set(normalized)
    out: List[Candidate] = []
    for c in candidates:
        root_name = c.path.parts[0].lower() if c.path.parts else ""
        if root_name in allowed or c.rule == "logos_reval_root":
            out.append(c)
    return out


def load_whitelist_prefixes(root: Path, whitelist_json: str) -> List[str]:
    p = root / whitelist_json
    if not p.exists():
        return []
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    raw = payload.get("exclude_path_prefixes", [])
    if not isinstance(raw, list):
        return []
    out = []
    for x in raw:
        s = str(x).strip().replace("\\", "/").strip("/")
        if s:
            out.append(s.lower())
    return sorted(set(out))


def filter_by_whitelist_prefixes(root: Path, candidates: List[Candidate], prefixes: List[str]) -> List[Candidate]:
    if not prefixes:
        return candidates
    out: List[Candidate] = []
    for c in candidates:
        rel = safe_relpath(root, c.path).lower()
        if any(rel == p or rel.startswith(p + "/") for p in prefixes):
            continue
        out.append(c)
    return out


def delete_candidate(c: Candidate) -> None:
    if c.kind == "dir":
        shutil.rmtree(c.path, ignore_errors=True)
    else:
        c.path.unlink(missing_ok=True)


def write_log(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup ephemeral files/directories.")
    parser.add_argument("--retention-days", type=int, default=DEFAULT_RETENTION_DAYS)
    parser.add_argument(
        "--allowed-roots",
        nargs="+",
        default=["out", "logs", "staging"],
        help="Only delete candidates under these top-level roots",
    )
    parser.add_argument(
        "--whitelist-json",
        default=DEFAULT_WHITELIST_JSON,
        help="JSON file with exclude_path_prefixes list",
    )
    parser.add_argument("--summary-out", default=DEFAULT_SUMMARY_OUT)
    parser.add_argument("--log-path", default=DEFAULT_LOG_PATH)
    parser.add_argument("--apply", action="store_true", help="Perform deletion")
    parser.add_argument(
        "--max-delete-count",
        type=int,
        default=0,
        help="0 means unlimited",
    )
    args = parser.parse_args()

    if args.retention_days < 1:
        raise ValueError("--retention-days must be >= 1")

    root = Path(".").resolve()
    now = utc_now()
    candidates = collect_candidates(root=root, now=now, retention_days=args.retention_days)
    candidates = filter_by_allowed_roots(candidates, args.allowed_roots)
    whitelist_prefixes = load_whitelist_prefixes(root, args.whitelist_json)
    candidates = filter_by_whitelist_prefixes(root, candidates, whitelist_prefixes)
    selected = candidates[: args.max_delete_count] if args.max_delete_count > 0 else candidates

    deleted_count = 0
    deleted_bytes = 0
    errors = 0

    for c in selected:
        rel = safe_relpath(root, c.path)
        row = {
            "timestamp_utc": now.isoformat(),
            "action": "delete_ephemeral_candidate" if args.apply else "preview_ephemeral_candidate",
            "path": rel,
            "kind": c.kind,
            "age_days": round(c.age_days, 2),
            "size_bytes": c.size_bytes,
            "rule": c.rule,
        }
        if args.apply:
            try:
                delete_candidate(c)
                deleted_count += 1
                deleted_bytes += c.size_bytes
            except Exception as exc:  # noqa: BLE001
                row["error"] = str(exc)
                errors += 1
        write_log(root / args.log_path, row)

    preview_rows = [
        {
            "path": safe_relpath(root, c.path),
            "kind": c.kind,
            "age_days": round(c.age_days, 2),
            "size_bytes": c.size_bytes,
            "rule": c.rule,
        }
        for c in selected[:100]
    ]
    summary = {
        "schema": "ephemeral_cleanup_summary_v1",
        "generated_at_utc": now.isoformat(),
        "retention_days": args.retention_days,
        "apply": bool(args.apply),
        "allowed_roots": args.allowed_roots,
        "whitelist_json": args.whitelist_json,
        "whitelist_prefix_count": len(whitelist_prefixes),
        "candidate_count": len(candidates),
        "selected_count": len(selected),
        "deleted_count": deleted_count,
        "deleted_bytes": deleted_bytes,
        "error_count": errors,
        "log_path": args.log_path,
        "preview": preview_rows,
    }
    summary_path = root / args.summary_out
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] summary: {args.summary_out}")
    print(f"[ok] selected_count: {summary['selected_count']}")
    print(f"[ok] deleted_count: {summary['deleted_count']}")
    print(f"[ok] error_count: {summary['error_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
