#!/usr/bin/env python3
"""Linux/Cloud Agent P0 path gate — mirrors scripts/verify_p0_constitution_gate_paths.ps1."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def repo_root() -> Path:
    env = __import__("os").environ.get("MKM_WORKSPACE_ROOT") or __import__("os").environ.get(
        "WORKSPACE_ROOT"
    )
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve().parent.parent
    return here


def parse_required_paths(ps1: Path) -> list[str]:
    text = ps1.read_text(encoding="utf-8", errors="replace")
    start = text.find("$required = @(")
    if start < 0:
        raise RuntimeError("Could not find $required = @( in verify_p0_constitution_gate_paths.ps1")
    block_start = start + len("$required = @(")
    depth = 1
    i = block_start
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    block = text[block_start : i - 1]
    return re.findall(r'"([^"]+)"', block)


def main() -> int:
    root = repo_root()
    ps1 = root / "scripts" / "verify_p0_constitution_gate_paths.ps1"
    if not ps1.is_file():
        print(f"FAIL: missing {ps1}", file=sys.stderr)
        return 1
    try:
        required = parse_required_paths(ps1)
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    missing: list[str] = []
    for rel in required:
        path = root / rel.replace("\\", "/")
        if not path.exists():
            missing.append(rel)
    if missing:
        print("FAIL: missing P0 paths (cloud gate):", file=sys.stderr)
        for rel in missing[:50]:
            print(f"  {rel}", file=sys.stderr)
        if len(missing) > 50:
            print(f"  ... and {len(missing) - 50} more", file=sys.stderr)
        return 1
    print(f"OK: P0/CONSTITUTION gate paths present ({len(required)} checked, cloud).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
