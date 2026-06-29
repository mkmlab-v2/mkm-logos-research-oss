#!/usr/bin/env python3
"""Offline gate: Logos Cosmic Anchor pilot v1 manifest + 3 anchor rows."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/logos_cosmic_anchor_pilot_v1_manifest_latest.json"
OUT_DIR = ROOT / "docs/final/artifacts/logos_cosmic_anchor_pilot_v1"
MKMLIFE_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data"
MKMLIFE_STEMS = ("seed", "light", "way")
BUILD = ROOT / "scripts/build_logos_cosmic_anchor_pilot_v1.py"
SCHEMA = ROOT / "docs/final/schemas/logos_cosmic_anchor_formalization_v1.schema.json"
PYTEST = ROOT / "tests/test_logos_cosmic_anchor_formalization_v1.py"


def main() -> int:
    missing = [p for p in (MANIFEST, SCHEMA, BUILD, PYTEST) if not p.is_file()]
    for stem in ("seed", "light", "way"):
        if not (OUT_DIR / f"{stem}.json").is_file():
            missing.append(OUT_DIR / f"{stem}.json")
    if missing:
        for p in missing:
            print(f"MISSING: {p}", file=sys.stderr)
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("anchor_count") != 3:
        print("anchor_count must be 3", file=sys.stderr)
        return 1
    if not manifest.get("forbidden_synthesis"):
        print("manifest forbidden_synthesis must be true", file=sys.stderr)
        return 1

    for stem in ("seed", "light", "way"):
        doc = json.loads((OUT_DIR / f"{stem}.json").read_text(encoding="utf-8"))
        if doc["fact_lock"].get("forbidden_synthesis") is not True:
            print(f"{stem}: forbidden_synthesis false", file=sys.stderr)
            return 1
        if doc["track_wall"].get("a_track_auto_promotion") is not False:
            print(f"{stem}: a_track_auto_promotion not false", file=sys.stderr)
            return 1

    for stem in MKMLIFE_STEMS:
        pub = MKMLIFE_PUBLIC / "logos_cosmic_anchor_pilot_v1" / f"{stem}.json"
        if not pub.is_file():
            print(f"MISSING mkmlife public: {pub}", file=sys.stderr)
            return 1

    print(
        json.dumps(
            {
                "overall_ok": True,
                "cosmic_anchor_pilot_ok": True,
                "anchor_count": manifest["anchor_count"],
                "mkmlife_public_ok": True,
                "manifest": str(MANIFEST.relative_to(ROOT)),
                "reproducible_command": manifest.get("reproducible_command"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
