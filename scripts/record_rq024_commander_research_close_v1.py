#!/usr/bin/env python3
"""Record RQ-024 B-track research CLOSED (human gate — not Track A promotion)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

READINESS = ROOT / "docs/final/artifacts/rq024_research_closure_readiness_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/rq024_commander_research_close_v1_latest.json"
SCHEMA = "rq024_commander_research_close_v1"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--acknowledge", action="store_true", help="Required: human approved research close")
    ap.add_argument("--note", type=str, default="")
    args = ap.parse_args(argv)

    if not args.acknowledge:
        raise SystemExit("Refusing without --acknowledge (human research-close gate).")

    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    if not readiness_path.is_file():
        raise SystemExit(f"missing readiness: {readiness_path}")
    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    if not readiness.get("mechanics_bundle_ok"):
        raise SystemExit("mechanics_bundle_ok is false — run post-triangle chain first.")

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "rq_id": "RQ-024",
        "rq_024_research_closed": True,
        "closed_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "success_tier": "T1_research",
        "track_a_status": "blocked",
        "auto_promote_ready": False,
        "closure_basis": {
            "mechanics_bundle_ok": True,
            "triangle_v1_met": True,
            "nf5_replication_met": True,
            "commander_acknowledge": True,
        },
        "readiness_pointer": str(readiness_path.relative_to(ROOT)).replace("\\", "/"),
        "headline_metrics": readiness.get("headline_metrics"),
        "commander_note": args.note.strip() or None,
        "messaging_contract": readiness.get("messaging_contract"),
        "forbidden": [
            "Track A promotion from this close record",
            "live trading auto-trigger",
            "gate 0.55 success claim",
        ],
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
