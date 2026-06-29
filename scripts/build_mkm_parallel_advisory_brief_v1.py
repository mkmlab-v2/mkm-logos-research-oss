#!/usr/bin/env python3
"""Build parallel advisory brief — 4 balanced perspectives, no direction merge."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_parallel_advisory_lens_v1 import (  # noqa: E402
    DEFAULT_FUSION,
    DEFAULT_MANIFEST,
    build_parallel_advisory_brief,
    load_manifest,
)

DEFAULT_OUT = ROOT / "reports/mkm_parallel_advisory_brief_v1_latest.json"


def _read(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def ensure_fusion(fusion_path: Path) -> dict:
    fusion = _read(fusion_path)
    if fusion:
        return fusion
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_kospi_four_lens_graphrag_fusion_v1.py")],
        cwd=str(ROOT),
        check=True,
    )
    fusion = _read(fusion_path)
    if not fusion:
        raise RuntimeError(f"fusion still missing after build: {fusion_path}")
    return fusion


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MKM parallel advisory brief v1")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--fusion", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--domain", default="finance")
    ap.add_argument("--session-date", default=None)
    ap.add_argument("--exclude-lens", action="append", default=[], dest="exclude_lenses")
    ap.add_argument("--include-lens", action="append", default=[], dest="include_lenses")
    ap.add_argument("--skip-fusion-build", action="store_true")
    args = ap.parse_args()

    manifest = load_manifest(args.manifest)
    if args.skip_fusion_build:
        fusion = _read(args.fusion)
        if not fusion:
            print(f"fusion missing: {args.fusion}", file=sys.stderr)
            return 1
    else:
        fusion = ensure_fusion(args.fusion)

    brief = build_parallel_advisory_brief(
        manifest=manifest,
        fusion=fusion,
        domain_id=args.domain,
        session_date=args.session_date,
        exclude_lenses=args.exclude_lenses or None,
        include_lenses=args.include_lenses or None,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.as_posix()), "domain": args.domain}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
