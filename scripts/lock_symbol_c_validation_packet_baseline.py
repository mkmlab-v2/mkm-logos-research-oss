#!/usr/bin/env python3
"""Lock baseline snapshot from symbol C validation packet."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_packet_latest.json"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_packet_baseline_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jwrite(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lock symbol C validation packet baseline")
    ap.add_argument("--packet-json", default=str(DEFAULT_PACKET))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    packet_path = _abs(args.packet_json)
    out_path = _abs(args.out)
    if not packet_path.is_file():
        print(f"ERROR: missing packet: {packet_path}")
        return 2

    packet = _jread(packet_path)
    baseline = {
        "meta": {
            "kind": "symbol_c_validation_packet_baseline",
            "locked_at_utc": datetime.now(timezone.utc).isoformat(),
            "packet_json": str(packet_path),
        },
        "snapshot": packet.get("snapshot", {}),
    }
    _jwrite(out_path, baseline)
    print("OK: symbol C validation packet baseline locked")
    print(f"out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
