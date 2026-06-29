#!/usr/bin/env python3
"""Enrich PersonaDiary daily package with optional Ollama preset polish [HYPO]."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from polish_personadiary_moment_copy_v1 import enrich_package_with_preset_polish, polish_enabled

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "docs/final/artifacts/personadiary_daily_response_package_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package-json", type=Path, default=DEFAULT_PACKAGE)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--force", action="store_true", help="Run even if env flag off")
    ap.add_argument("--timeout-sec", type=int, default=45)
    ap.add_argument("--dry-run", action="store_true", help="Report enabled state only")
    args = ap.parse_args()

    if args.dry_run:
        print(json.dumps({"polish_enabled": polish_enabled(), "force": args.force}, ensure_ascii=False))
        return 0

    if not args.force and not polish_enabled():
        print("SKIP: MKM_PERSONADIARY_MOMENT_OLLAMA_POLISH not enabled")
        return 0

    package = json.loads(args.package_json.read_text(encoding="utf-8-sig"))
    enrich_package_with_preset_polish(
        package, force=args.force, timeout_sec=args.timeout_sec
    )
    out = args.out_json or args.package_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    applied = sum(
        1
        for p in (package.get("moment_preset_polish_v1") or {}).get("presets", {}).values()
        if (p.get("polish_meta") or {}).get("applied")
    )
    print(f"WROTE: {out} presets_polished={applied}/3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
