#!/usr/bin/env python3
"""Aggregate Track A metering JSONL into summary artifact."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
import os
from pathlib import Path


def _resolve_meter_log_path(workspace_root: Path) -> Path:
    raw = os.environ.get("TRACK_A_METERING_LOG_PATH", "").strip()
    if raw:
        return Path(raw)
    return workspace_root / "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--metering-log",
        type=Path,
        default=None,
        help="Override metering JSONL (default: resolve_meter_log_path())",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output summary JSON",
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    log_path = args.metering_log.resolve() if args.metering_log else _resolve_meter_log_path(root)
    out = (args.out or root / "docs/final/artifacts/track_a_metering_summary_latest.json").resolve()

    if not log_path.is_file():
        print(f"error: metering log not found: {log_path}", file=sys.stderr)
        return 2

    ok = 0
    bad = 0
    rows: list[dict] = []
    for ln in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip():
            continue
        try:
            d = json.loads(ln)
            ok += 1
            if len(rows) < 5:
                rows.append(d)
        except json.JSONDecodeError:
            bad += 1

    payload = {
        "schema": "track_a_metering_summary_v1",
        "generated_at_utc": _utc(),
        "line_count": ok + bad,
        "events_total": ok,
        "parse_errors": bad,
        "rows": rows,
        "source": str(log_path).replace("\\", "/"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
