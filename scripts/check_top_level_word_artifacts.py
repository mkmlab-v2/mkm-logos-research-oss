#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _git_status_porcelain(repo_root: Path) -> list[str]:
    out = subprocess.check_output(
        ["git", "status", "--porcelain"],
        cwd=str(repo_root),
        text=True,
    )
    return out.splitlines()


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Detect suspicious top-level untracked word-like artifacts "
            "(e.g. 'Do', 'Stop', 'attempt')."
        )
    )
    ap.add_argument("--root", default=".", help="Repository root")
    ap.add_argument(
        "--allow",
        action="append",
        default=[],
        help="Top-level names to allow explicitly (repeatable)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    allow = set(args.allow)
    suspicious: list[str] = []

    for line in _git_status_porcelain(root):
        if not line.startswith("?? "):
            continue
        path = line[3:]
        if "/" in path or "\\" in path:
            continue
        if path in allow:
            continue
        # Flag bare word-like top-level files only.
        candidate = root / path
        if candidate.is_file():
            suspicious.append(path)

    if suspicious:
        print("[top-level-word-artifacts] BLOCK: suspicious untracked top-level files detected:")
        for name in suspicious:
            print(f"- {name}")
        print(
            "\nThese are commonly produced by malformed shell quoting/tokenization. "
            "Remove them or allowlist explicitly."
        )
        return 1

    print("[top-level-word-artifacts] PASS: no suspicious top-level word artifacts detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
