#!/usr/bin/env python3
"""
Read-only scan: large / ignored / untracked areas under workspace root for archive planning.
No file moves or deletes. Paths only; no .env contents.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _dir_size(path: Path, max_files: int = 500_000) -> tuple[int, int, bool]:
    total = 0
    n = 0
    capped = False
    for root, _, files in os.walk(path, topdown=True, followlinks=False):
        for name in files:
            if n >= max_files:
                capped = True
                return total, n, capped
            fp = Path(root) / name
            try:
                total += fp.stat().st_size
            except OSError:
                pass
            n += 1
    return total, n, capped


def _git_check_ignore(repo: Path, rel: str) -> bool | None:
    try:
        r = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if r.returncode == 0:
            return True
        if r.returncode == 1:
            return False
        return None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _git_untracked_files(repo: Path) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "ls-files", "-o", "--exclude-standard"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            return []
        return [line.strip() for line in r.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        return []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("reports/workspace_archive_candidates_scan_v1.json"),
    )
    ap.add_argument("--max-files-per-dir", type=int, default=500_000)
    args = ap.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: root not a directory: {root}", file=sys.stderr)
        return 2

    untracked = _git_untracked_files(root)
    by_top: dict[str, list[str]] = {}
    for rel in untracked:
        top = rel.split("/", 1)[0].replace("\\", "/")
        by_top.setdefault(top, []).append(rel)

    entries: list[dict] = []
    skip_names = {".git"}
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.name in skip_names:
            continue
        rel = child.relative_to(root).as_posix()
        ignored = _git_check_ignore(root, rel)
        size_b, nfiles, capped = _dir_size(child, max_files=args.max_files_per_dir)
        ut = by_top.get(child.name, [])
        entries.append(
            {
                "path": rel,
                "bytes": size_b,
                "files_walked": nfiles,
                "size_capped": capped,
                "git_check_ignore": ignored,
                "untracked_count_under_top": len(ut),
                "untracked_sample": ut[:12],
            }
        )

    entries.sort(key=lambda x: x["bytes"], reverse=True)

    payload = {
        "schema": "workspace_archive_candidates_scan_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "fact_lock_note": "Read-only inventory. Moves/archives are human_gate; do not archive .env or secrets.",
        "untracked_total_paths": len(untracked),
        "top_level_directories": entries,
        "next_steps_ko": [
            "Ring C: 이동 전 F:\\MKM_Archive (또는 팀 경로) 존재·여유 확인",
            "추적 파일·브랜치 작업 트리는 제외; node_modules/.venv는 재설치 계획 후 이동",
            "레포 스크립트 Migrate-FWorkspaceArchiveToE.ps1 등과 경로 중복 여부 확인",
        ],
    }

    out = args.out
    if not out.is_absolute():
        out = (root / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
