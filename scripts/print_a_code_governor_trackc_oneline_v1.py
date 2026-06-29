#!/usr/bin/env python3
"""Print one-line A-code governor summary from Track C dashboard ([HYPO·non-gating])."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASH = ROOT / "docs/final/artifacts/mkm_trackc_ops_dashboard_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Print A-code Track C dashboard one-liner")
    parser.add_argument("--dashboard", type=Path, default=DEFAULT_DASH)
    args = parser.parse_args()
    if not args.dashboard.is_file():
        print("[HYPO·non-gating] A-code governor: NODATA (dashboard missing)", file=sys.stderr)
        return 0
    doc = json.loads(args.dashboard.read_text(encoding="utf-8-sig"))
    ac = (doc.get("trackc") or {}).get("a_code_governor") or {}
    if ac.get("state") != "OK":
        print(f"[HYPO·non-gating] A-code governor: {ac.get('state', 'NODATA')}")
        return 0
    line = ac.get("evening_append_line")
    if line:
        print(line)
        return 0
    gate = ac.get("gate_decision")
    ready = ac.get("checklist_mechanical_ready")
    hint = ac.get("operator_hint") or "WATCH only"
    print(
        f"▸ A-code S2 [HYPO·non-gating]: gate={gate} mechanical_ready={ready} · {hint}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
