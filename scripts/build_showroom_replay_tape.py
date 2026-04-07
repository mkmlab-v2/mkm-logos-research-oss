#!/usr/bin/env python3
"""Build a compact replay tape from public-event JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

KEEP_KEYS = (
    "timestamp",
    "event_id",
    "risk_level",
    "public_signal_direction",
    "active_character_id",
    "abstract_reason",
    "system_status",
    "c2_signal_lamp",
    "unified_score_balanced",
)


def build_tape(src: Path, out: Path, limit: int = 240) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for line in src.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        slim = {k: obj.get(k) for k in KEEP_KEYS}
        if slim.get("event_id"):
            rows.append(slim)
    rows = rows[-max(1, limit) :]
    payload: Dict[str, Any] = {
        "schema": "showroom_replay_tape_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_jsonl": str(src.as_posix()),
        "count": len(rows),
        "events": rows,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build showroom replay tape JSON.")
    p.add_argument("--src", required=True, help="Input JSONL path")
    p.add_argument("--out", required=True, help="Output replay JSON path")
    p.add_argument("--limit", type=int, default=240, help="Max replay events")
    return p


def main() -> int:
    ns = _parser().parse_args()
    payload = build_tape(Path(ns.src), Path(ns.out), limit=ns.limit)
    print(payload["count"])
    print(payload["schema"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
