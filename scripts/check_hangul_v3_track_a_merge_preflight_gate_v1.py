#!/usr/bin/env python3
"""Gate Track A v3 merge preflight — ko preserve + Golden-40 non-regression (no prod swap)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT = ROOT / "docs/final/artifacts/HANGUL_V3_TRACK_A_MERGE_PREFLIGHT_CONTRACT_V1.json"
DEFAULT_PACKET = ROOT / "reports/hangul_v3_track_a_merge_preflight_packet_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/hangul_v3_track_a_merge_preflight_gate_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--enforce", action="store_true", help="Exit 1 when preflight_ready=false")
    args = ap.parse_args()

    packet_path = args.packet if args.packet.is_absolute() else (ROOT / args.packet)
    if not packet_path.is_file():
        print("ABORT: preflight packet missing")
        return 1

    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    gates = packet.get("preflight_gates") or {}
    ready = bool(packet.get("preflight_ready"))
    failed = [k for k, v in gates.items() if v is False]

    decision = "ADVANCE_TRACK_A_MERGE_CANDIDATE" if ready else "HOLD"
    out_doc = {
        "schema": "hangul_v3_track_a_merge_preflight_gate_v1",
        "generated_at_utc": _utc(),
        "decision": decision,
        "preflight_ready": ready,
        "failed_gates": failed,
        "preflight_gates": gates,
        "packet_path": _rel(packet_path),
        "contract": _rel(CONTRACT) if CONTRACT.is_file() else None,
        "production_pointer_swap": False,
        "send_gate": "HOLD",
        "note_ko": "ADVANCE_* = merge candidate preflight only; production pointer unchanged until commander Track A signoff.",
        "reproduce": "py scripts/check_hangul_v3_track_a_merge_preflight_gate_v1.py --enforce",
    }

    out_path = args.out if args.out.is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"decision": decision, "preflight_ready": ready, "failed": failed}, ensure_ascii=False))
    if args.enforce and not ready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
