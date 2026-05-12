#!/usr/bin/env python3
"""Track A metering band gate (warning vs block) from weekly report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--weekly-json",
        type=Path,
        default=None,
        help="track_a_metering_weekly_report_latest.json",
    )
    ap.add_argument("--mode", choices=("warning", "block"), default="warning")
    ap.add_argument("--min-hit-rate", type=float, default=0.85)
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    weekly = (args.weekly_json or root / "docs/final/artifacts/track_a_metering_weekly_report_latest.json").resolve()
    out = (args.out or root / "docs/final/artifacts/track_a_metering_band_gate_latest.json").resolve()

    if not weekly.is_file():
        print(f"error: weekly report missing: {weekly}", file=sys.stderr)
        return 2

    doc = json.loads(weekly.read_text(encoding="utf-8"))
    rate = float(doc.get("target_band_hit_rate") or 0.0)
    ok = rate >= args.min_hit_rate

    if ok:
        decision = "pass"
        status = "pass"
    elif args.mode == "block":
        decision = "block"
        status = "fail"
    else:
        decision = "warning"
        status = "pass"

    payload = {
        "schema": "track_a_metering_band_gate_v1",
        "generated_at_utc": _utc(),
        "status": status,
        "decision": decision,
        "mode": args.mode,
        "target_band_hit_rate": rate,
        "min_hit_rate": args.min_hit_rate,
        "source_weekly": str(weekly).replace("\\", "/"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0 if status == "pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
