#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Write KOSPI prophecy lane routing SSOT manifest [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_prophecy_lane_routing_v1 import (  # noqa: E402
    ROUTING_ART,
    ROUTING_REPORT,
    build_routing_manifest,
)

DEFAULT_CHAIN = ROOT / "reports/kospi_evening_briefing_chain_v1_latest.json"


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--session-date", default=None)
    ap.add_argument("--evening-chain-json", type=Path, default=DEFAULT_CHAIN)
    args = ap.parse_args()

    chain_path = args.evening_chain_json if args.evening_chain_json.is_absolute() else ROOT / args.evening_chain_json
    doc = build_routing_manifest(
        session_date=args.session_date,
        evening_chain_doc=_read_json(chain_path),
    )
    for p in (ROUTING_REPORT, ROUTING_ART):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(ROUTING_ART), "session_date": args.session_date}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
