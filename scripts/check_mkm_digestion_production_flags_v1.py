#!/usr/bin/env python3
"""Static guard: forbid --no-mark-miss-as-wrong in production automation paths (O-02)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = "no-mark-miss-as-wrong"

# Definition site + docs mentioning the escape hatch are allowed.
ALLOW_SUFFIXES = {".md"}
ALLOW_REL_PATHS = {
    "scripts/check_digested_numeric_fact_v1.py",
    "scripts/check_mkm_digestion_production_flags_v1.py",
}

SCAN_ROOTS = (
    ROOT / "scripts",
    ROOT / ".github" / "workflows",
)


def _posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def scan_violations() -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for base in SCAN_ROOTS:
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            rel = _posix(path)
            if rel in ALLOW_REL_PATHS:
                continue
            if path.suffix in ALLOW_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if FORBIDDEN not in text:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if FORBIDDEN in line:
                    hits.append({"path": rel, "line": str(lineno), "snippet": line.strip()[:160]})
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail if production paths reference escape hatch flag")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    violations = scan_violations()
    doc = {
        "schema": "mkm_digestion_production_flags_check_v1",
        "version": "1.0.0",
        "ok": len(violations) == 0,
        "forbidden_token": FORBIDDEN,
        "violation_count": len(violations),
        "violations": violations,
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": "py scripts/check_mkm_digestion_production_flags_v1.py",
    }
    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    elif violations:
        for v in violations:
            print(f"{v['path']}:{v['line']}: {v['snippet']}", file=sys.stderr)
    else:
        print(json.dumps({"ok": True, "violation_count": 0}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
