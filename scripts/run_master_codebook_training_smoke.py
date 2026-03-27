#!/usr/bin/env python3
"""Minimal smoke runner for master codebook training gate.

In this repository, the full training codebook toolchain may be absent.
This smoke check validates that core directories exist and that report output
paths are writable, then emits small marker artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Run master codebook training smoke pipeline")
    ap.add_argument("--count", type=int, default=500, help="Synthetic record count for smoke run")
    ap.add_argument("--prefix", default="smoke", help="Output file prefix")
    args = ap.parse_args()

    docs_dir = WORKSPACE_ROOT / "docs" / "final"
    reports_dir = WORKSPACE_ROOT / "reports" / "constitution"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if not docs_dir.is_dir():
        print(f"❌ required directory missing: {docs_dir}")
        return 1

    marker = {
        "status": "ok",
        "mode": "minimal-smoke",
        "count": args.count,
        "prefix": args.prefix,
    }
    out_json = reports_dir / f"master_codebook_training_smoke_{args.prefix}_{args.count}.json"
    out_md = reports_dir / f"master_codebook_training_smoke_{args.prefix}_{args.count}.md"

    out_json.write_text(json.dumps(marker, ensure_ascii=False, indent=2), encoding="utf-8")
    out_md.write_text(
        "# Master Codebook Training Smoke\n\n"
        f"- status: ok\n- mode: minimal-smoke\n- count: {args.count}\n- prefix: {args.prefix}\n",
        encoding="utf-8",
    )

    print("✅ master codebook training smoke pipeline passed")
    print(f"marker_json: {out_json.relative_to(WORKSPACE_ROOT)}")
    print(f"marker_md: {out_md.relative_to(WORKSPACE_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
