#!/usr/bin/env python3
"""Gate: MKM_PIXEL_LANGUAGE sprite_deploy_mode matches expected mode."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PIXEL_JSON = ROOT / "projects/mkm/mkm-life/public/data/MKM_PIXEL_LANGUAGE_V1.json"
OUT = ROOT / "reports/mkmlife_pixel_sprite_deploy_mode_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pixel-json", type=Path, default=DEFAULT_PIXEL_JSON)
    ap.add_argument("--expect", choices=("local", "cdn"), default="local")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.pixel_json.is_file():
        print(f"FAIL: missing {args.pixel_json}", file=sys.stderr)
        return 1

    from apply_mkmlife_pixel_language_local_sprite_paths_v1 import (  # noqa: E402
        CDN_PREFIX,
        LOCAL_PREFIX,
        detect_mode,
    )

    doc = json.loads(args.pixel_json.read_text(encoding="utf-8-sig"))
    detected = detect_mode(doc)
    deploy = doc.get("sprite_deploy_mode") or {}
    ok = detected == args.expect
    doc_out = {
        "schema": "mkmlife_pixel_sprite_deploy_mode_gate_v1",
        "generated_at_utc": _utc(),
        "expect": args.expect,
        "detected": detected,
        "sprite_deploy_mode": deploy,
        "ok": ok,
        "local_prefix": LOCAL_PREFIX,
        "cdn_prefix": CDN_PREFIX,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "expect": args.expect, "detected": detected}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
