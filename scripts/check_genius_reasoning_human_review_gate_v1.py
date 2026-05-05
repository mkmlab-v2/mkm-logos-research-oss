#!/usr/bin/env python3
"""Check human review debt gate for genius reasoning goldset."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_QUEUE = ART / "genius_reasoning_human_review_queue_latest.json"
DEFAULT_OUT = ART / "genius_reasoning_human_review_gate_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _parse_dt(ts: Any) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-pending-count", type=int, default=2)
    ap.add_argument("--max-pending-ratio", type=float, default=0.15)
    ap.add_argument("--max-pending-age-days", type=float, default=14.0)
    args = ap.parse_args()

    queue = _read_json(args.queue_json)
    counts = queue.get("counts") if isinstance(queue.get("counts"), dict) else {}
    total_rows = int(counts.get("total_rows") or 0)
    pending_rows = int(counts.get("pending_rows") or 0)
    pending_ratio = (float(pending_rows) / float(total_rows)) if total_rows > 0 else 0.0

    now_utc = datetime.now(timezone.utc)
    goldset_dt = _parse_dt(queue.get("goldset_generated_at_utc"))
    pending_age_days = max(0.0, (now_utc - goldset_dt).total_seconds() / 86400.0) if goldset_dt else 0.0

    reasons: list[str] = []
    status = "PASS"
    if pending_rows > int(args.max_pending_count):
        status = "HOLD"
        reasons.append("pending_count_exceeded")
    if pending_ratio > float(args.max_pending_ratio):
        status = "HOLD"
        reasons.append("pending_ratio_exceeded")
    if pending_rows > 0 and pending_age_days > float(args.max_pending_age_days):
        status = "HOLD"
        reasons.append("pending_age_exceeded")

    out = {
        "schema": "genius_reasoning_human_review_gate_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {"queue_json": str(args.queue_json).replace("\\", "/")},
        "thresholds": {
            "max_pending_count": int(args.max_pending_count),
            "max_pending_ratio": float(args.max_pending_ratio),
            "max_pending_age_days": float(args.max_pending_age_days),
        },
        "current": {
            "total_rows": total_rows,
            "pending_rows": pending_rows,
            "pending_ratio": round(pending_ratio, 4),
            "pending_age_days": round(pending_age_days, 4),
        },
        "status": status,
        "reasons": reasons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(args.output_json).replace("\\", "/")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
