#!/usr/bin/env python3
"""7-day window stats from Track A metering JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _parse_ts(s: str) -> datetime | None:
    try:
        s = s.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_meter_log(workspace_root: Path, override: Path | None) -> Path:
    if override:
        return override.resolve()
    import os

    raw = os.environ.get("TRACK_A_METERING_LOG_PATH", "").strip()
    if raw:
        return Path(raw)
    return (workspace_root / "reports/constitution/btrack_pilot/track_a_metering_log_v1.jsonl").resolve()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--metering-log", type=Path, default=None)
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output weekly report JSON",
    )
    ap.add_argument("--window-days", type=int, default=7)
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    log_path = _resolve_meter_log(root, args.metering_log)
    out = (args.out or root / "docs/final/artifacts/track_a_metering_weekly_report_latest.json").resolve()

    if not log_path.is_file():
        print(f"error: metering log not found: {log_path}", file=sys.stderr)
        return 2

    events: list[dict] = []
    for ln in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip():
            continue
        try:
            events.append(json.loads(ln))
        except json.JSONDecodeError:
            continue

    times: list[datetime] = []
    for ev in events:
        ts = _parse_ts(str(ev.get("ts_utc") or ""))
        if ts:
            times.append(ts.astimezone(timezone.utc))

    anchor = max(times) if times else datetime.now(timezone.utc)
    start = anchor - timedelta(days=max(1, args.window_days))
    in_win = []
    for ev in events:
        ts = _parse_ts(str(ev.get("ts_utc") or ""))
        if not ts:
            continue
        ts = ts.astimezone(timezone.utc)
        if start <= ts <= anchor:
            in_win.append(ev)

    hits = 0
    for ev in in_win:
        tb = ev.get("tokens_before")
        ta = ev.get("tokens_after")
        if isinstance(tb, int) and isinstance(ta, int) and tb > 0 and ta <= tb:
            hits += 1

    n = len(in_win)
    rate = (hits / n) if n else 0.0

    payload = {
        "schema": "track_a_metering_weekly_report_v1",
        "generated_at_utc": _utc(),
        "anchor_utc": anchor.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "events_in_window": n,
        "target_band_hit_rate": rate,
        "source": str(log_path).replace("\\", "/"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
