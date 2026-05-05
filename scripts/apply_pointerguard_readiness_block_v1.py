#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
READINESS_DEFAULT = ART / "pointerguard_ops_readiness_latest.json"
GUARDED_DEFAULT = ART / "genesis_pointer_routing_decision_guarded_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--readiness-json", type=Path, default=READINESS_DEFAULT)
    ap.add_argument("--guarded-decision-json", type=Path, default=GUARDED_DEFAULT)
    ap.add_argument("--out", type=Path, default=GUARDED_DEFAULT)
    args = ap.parse_args()

    readiness_path = args.readiness_json if args.readiness_json.is_absolute() else ROOT / args.readiness_json
    guarded_path = args.guarded_decision_json if args.guarded_decision_json.is_absolute() else ROOT / args.guarded_decision_json
    out_path = args.out if args.out.is_absolute() else ROOT / args.out

    readiness = _read_json(readiness_path)
    guarded = _read_json(guarded_path)
    block_applied = not bool(readiness.get("all_ok", False))

    if block_applied:
        guarded["decision"] = "HOLD_POINTER_ROUTE"
        guarded["route_mode"] = "track_a_primary"
        guarded["guard_applied"] = True
        guarded["guard_reason"] = "ops_readiness_block"
    guarded["readiness_block_checked_at_utc"] = _now_utc()
    guarded["readiness_block_inputs"] = {
        "readiness_json": str(readiness_path),
        "guarded_decision_json": str(guarded_path),
    }
    guarded["readiness_block_applied"] = block_applied

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(guarded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_path),
                "readiness_all_ok": bool(readiness.get("all_ok", False)),
                "block_applied": block_applied,
                "decision": guarded.get("decision"),
                "route_mode": guarded.get("route_mode"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
