#!/usr/bin/env python3
"""Gate: public showroom panel must not expose forbidden theological / internal terms."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL = ROOT / "docs/final/artifacts/saving_the_news_matrix_panel_slice_v1_latest.json"

sys.path.insert(0, str(ROOT))
from scripts.saving_the_news_public_copy_facade_v1 import DISPLAY_PUBLIC, scan_public_violations  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-json", type=Path, default=DEFAULT_PANEL)
    args = ap.parse_args()
    if not args.panel_json.is_file():
        print(f"MISSING: {args.panel_json}")
        return 2
    panel = json.loads(args.panel_json.read_text(encoding="utf-8"))
    mode = panel.get("display_mode", "")
    if mode != DISPLAY_PUBLIC:
        print(f"SKIP: display_mode={mode!r} (not {DISPLAY_PUBLIC})")
        return 0
    violations = scan_public_violations(panel)
    if violations:
        for v in violations[:20]:
            print(f"VIOLATION: {v}")
        print(f"FAIL: {len(violations)} forbidden term(s) in public panel")
        return 1
    print(f"OK: public copy gate passed ({args.panel_json.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
