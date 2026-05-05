#!/usr/bin/env python3
"""Run a non-destructive rollback drill report for Sasang READY state."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "sasang_ready_rollback_drill_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    payload = {
        "schema": "sasang_ready_rollback_drill_v1",
        "drill_at_utc": _now(),
        "mode": "dry_run_non_destructive",
        "rollback_conditions": [
            "strict gate decision degrades from PASS",
            "readiness go flag turns false",
            "production_data_readiness root_cause reappears",
        ],
        "steps": [
            "Re-run status chain",
            "Pinpoint first failing artifact",
            "Switch operation mode to KEEP_OBSERVATION_ONLY",
            "Require renewed human sign-off before re-enable",
        ],
        "result": "DRILL_RECORDED",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
