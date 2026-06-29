#!/usr/bin/env python3
"""Build storage/meta/mkm_sidecar_constitution_paths_v1.json from CONSTITUTION anchors.

[HYPO] / research_only — path/gate table slices only; full CONSTITUTION body untouched.

  py scripts/build_mkm_sidecar_constitution_paths_v1.py
  py scripts/build_mkm_sidecar_constitution_paths_v1.py --skip-if-unchanged
  py scripts/build_mkm_sidecar_constitution_paths_v1.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mkm_sidecar_constitution_lib_v1 import (
    CONSTITUTION_REL,
    DEFAULT_SIDECAR_PATH,
    build_sidecar_document,
    sha256_file,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--out", type=Path, default=DEFAULT_SIDECAR_PATH)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--skip-if-unchanged",
        action="store_true",
        help="Exit 0 without write when source SHA256 matches existing sidecar.",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    source = root / CONSTITUTION_REL
    if not source.is_file():
        print(f"FAIL: missing {CONSTITUTION_REL}", file=sys.stderr)
        return 1

    source_hash = sha256_file(source)
    out = args.out
    if args.skip_if_unchanged and out.is_file():
        try:
            existing = json.loads(out.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            existing = {}
        if existing.get("source_sha256") == source_hash:
            print(f"SKIP unchanged: {out} (source_sha256 match)")
            return 0

    try:
        doc = build_sidecar_document(root)
    except (FileNotFoundError, ValueError) as exc:
        print(f"FAIL: sidecar build: {exc}", file=sys.stderr)
        return 1

    if doc.get("source_sha256") != source_hash:
        print("FAIL: source_sha256 drift during build", file=sys.stderr)
        return 1

    seg_count = len(doc.get("segments") or {})
    path_count = len(doc.get("path_pin_union") or [])
    print(f"OK: {seg_count} segments, {path_count} unique path pins")

    if args.dry_run:
        print("DRY-RUN: no write")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
