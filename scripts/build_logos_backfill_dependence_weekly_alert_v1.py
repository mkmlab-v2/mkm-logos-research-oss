#!/usr/bin/env python3
"""Build weekly alert report from backfill dependence trend JSONL."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_LOG = REPORTS / "logos_backfill_dependence_trend_log.jsonl"
DEFAULT_OUT = ART / "logos_backfill_dependence_weekly_alert_latest.json"


def _parse_ts(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly dependence alert report from trend log.")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--delta-alert-threshold", type=float, default=0.3)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=max(1, int(args.window_days)))
    rows = _load_jsonl(args.log_jsonl)

    in_window: list[dict[str, Any]] = []
    deltas: list[float] = []
    fail_count = 0
    for r in rows:
        ts = _parse_ts(str(r.get("timestamp_utc") or ""))
        if ts is None or ts < since:
            continue
        in_window.append(r)
        d = r.get("delta_mixed_minus_pure")
        if isinstance(d, (int, float)):
            deltas.append(float(d))
        if str(r.get("status") or "") == "FAIL_HIGH_BACKFILL_DEPENDENCE":
            fail_count += 1

    avg_delta = round(sum(deltas) / len(deltas), 6) if deltas else None
    max_delta = round(max(deltas), 6) if deltas else None
    latest = in_window[-1] if in_window else None

    alert = False
    if max_delta is not None and max_delta > float(args.delta_alert_threshold):
        alert = True
    if fail_count > 0:
        alert = True

    out = {
        "schema": "logos_backfill_dependence_weekly_alert_v1",
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "inputs": {
            "log_jsonl": str(args.log_jsonl).replace("\\", "/"),
            "window_days": int(args.window_days),
            "delta_alert_threshold": float(args.delta_alert_threshold),
        },
        "window_summary": {
            "record_count": len(in_window),
            "fail_count": fail_count,
            "avg_delta_mixed_minus_pure": avg_delta,
            "max_delta_mixed_minus_pure": max_delta,
            "latest_status": None if latest is None else latest.get("status"),
            "latest_delta_mixed_minus_pure": None if latest is None else latest.get("delta_mixed_minus_pure"),
        },
        "alert": {
            "is_alert": alert,
            "level": "HIGH" if alert else "OK",
            "reason": (
                "FAIL status present or delta threshold exceeded"
                if alert
                else "No FAIL status and delta within threshold"
            ),
        },
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output_json": str(args.output_json),
                "record_count": len(in_window),
                "alert": out["alert"]["is_alert"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

