#!/usr/bin/env python3
"""Surgical normalize hardcoded C:\\workspace in OSS public surface — Launch Gate #1.

  py scripts/normalize_workspace_paths_v1.py --dry-run
  py scripts/normalize_workspace_paths_v1.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/normalize_workspace_paths_v1_latest.json"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from check_hardcoded_workspace_paths_v1 import _oss_files, _rel, _scan_file  # noqa: E402

README_CD_RE = re.compile(r"^\s*cd\s+C:[/\\]workspace\s*$", re.IGNORECASE | re.MULTILINE)
README_CD_REPL = "# from repo root (after git clone)"

PY_NORMALIZE_SKIP = frozenset(
    {
        "scripts/check_hardcoded_workspace_paths_v1.py",
        "scripts/normalize_workspace_paths_v1.py",
    }
)


def _normalize_readme(text: str) -> tuple[str, int]:
    new_text, n = README_CD_RE.subn(README_CD_REPL, text)
    return new_text, n


def _normalize_py_root_literal(text: str) -> tuple[str, int]:
    """Replace Path('<workspace-root>') assignments only — not regex pattern strings."""
    pat = re.compile(r'''Path\(\s*["']C:[/\\]workspace["']\s*\)''', re.I)
    out, n = pat.subn("Path(__file__).resolve().parents[1]", text)
    return out, n


def normalize_file(path: Path, *, apply: bool) -> dict[str, Any]:
    rel = _rel(path)
    original = path.read_text(encoding="utf-8")
    updated = original
    changes = 0

    if rel in ("README.md", "SECURITY.md"):
        updated, n = _normalize_readme(original)
        changes += n
    elif path.suffix == ".py" and rel.replace("\\", "/") not in PY_NORMALIZE_SKIP:
        updated, n = _normalize_py_root_literal(original)
        changes += n

    changed = updated != original
    if changed and apply:
        path.write_text(updated, encoding="utf-8")

    return {
        "file": rel,
        "changes": changes,
        "changed": changed,
        "applied": bool(changed and apply),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="Report only (default when --apply omitted)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    apply = bool(args.apply)

    targets = [p for p in _oss_files() if _scan_file(p)]
    rows = [normalize_file(p, apply=apply) for p in targets]
    changed_rows = [r for r in rows if r["changed"]]

    doc = {
        "schema": "normalize_workspace_paths_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "mode": "apply" if apply else "dry_run",
        "targets_with_hits": len(targets),
        "files_changed": len(changed_rows),
        "ok": True,
        "rows": rows,
        "reproduce_apply": "py scripts/normalize_workspace_paths_v1.py --apply",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "mode": doc["mode"],
                "targets_with_hits": doc["targets_with_hits"],
                "files_changed": doc["files_changed"],
                "out": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
