#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_utc(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check central-memory read acknowledgement freshness.")
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument("--max-age-hours", type=float, default=24.0)
    args = ap.parse_args()

    root = Path(args.workspace_root).resolve()
    ack = root / "reports" / "central_memory_read_ack_latest.json"
    if not ack.exists():
        print(f"CENTRAL MEMORY READ CHECK: FAIL missing ack file: {ack}")
        return 1

    try:
        payload = json.loads(ack.read_text(encoding="utf-8-sig"))
        ts = _parse_utc(str(payload["acknowledged_at_utc"]))
    except Exception as exc:  # noqa: BLE001
        print(f"CENTRAL MEMORY READ CHECK: FAIL parse error: {type(exc).__name__}")
        return 1

    now = datetime.now(timezone.utc)
    age = now - ts
    if age > timedelta(hours=max(args.max_age_hours, 0.0)):
        print(
            f"CENTRAL MEMORY READ CHECK: FAIL stale ack age_hours={age.total_seconds()/3600:.2f} "
            f"max={args.max_age_hours:.2f}"
        )
        return 1

    print(
        f"CENTRAL MEMORY READ CHECK: PASS ack_at={ts.isoformat().replace('+00:00','Z')} "
        f"age_hours={age.total_seconds()/3600:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
