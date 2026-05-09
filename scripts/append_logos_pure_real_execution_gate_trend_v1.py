#!/usr/bin/env python3
"""Append execution gate status into trend log jsonl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

DEFAULT_GATE = ART / "logos_pure_real_execution_gate_status_latest.json"
DEFAULT_LOG = REPORTS / "logos_pure_real_execution_gate_trend_log.jsonl"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Append pure-real execution gate trend log.")
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    gate = _load_json(args.gate_json)
    inputs = gate.get("inputs") or {}
    rec = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "schema": "logos_pure_real_execution_gate_trend_record_v1",
        "gate_status": gate.get("gate_status"),
        "blockers": gate.get("blockers") or [],
        "execution_status": inputs.get("execution_status"),
        "backfill_dependence_status": inputs.get("backfill_dependence_status"),
        "delta_mixed_minus_pure": float(inputs.get("delta_mixed_minus_pure") or 0.0),
    }

    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with args.log_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(
        json.dumps(
            {
                "ok": True,
                "log_jsonl": str(args.log_jsonl),
                "gate_status": rec["gate_status"],
                "blocker_count": len(rec["blockers"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

