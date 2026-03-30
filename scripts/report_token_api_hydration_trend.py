#!/usr/bin/env python3
"""Append hydration mix snapshot to JSONL log and emit trend summary."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MIX = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_latest.json"
LOG = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_log.jsonl"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_trend_latest.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s.lstrip("\ufeff")))
    return rows


def _dt(v: str) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00"))


def main() -> int:
    mix = _load_json(MIX)
    if not mix:
        raise FileNotFoundError(f"missing mix snapshot: {MIX}")
    now = datetime.now(timezone.utc)
    row = {
        "schema": "token_api_hydration_mix_log_v1",
        "ts_utc": now.isoformat(),
        "source_mix_ts_utc": mix.get("ts_utc"),
        "total_examples": int(mix.get("total_examples", 0)),
        "metrics_mode_counts": mix.get("metrics_mode_counts", {}),
        "live_ratio": float(mix.get("live_ratio", 0.0)),
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(
        (LOG.read_text(encoding="utf-8") if LOG.is_file() else "")
        + json.dumps(row, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    rows = _iter_jsonl(LOG)
    cutoff = now - timedelta(days=7)
    recent = [r for r in rows if "ts_utc" in r and _dt(str(r["ts_utc"])) >= cutoff]
    avg_live_ratio = (
        sum(float(r.get("live_ratio", 0.0)) for r in recent) / len(recent) if recent else 0.0
    )
    latest = rows[-1] if rows else row
    summary = {
        "schema": "token_api_hydration_trend_v1",
        "ts_utc": now.isoformat(),
        "window_days": 7,
        "log_path": "reports/constitution/btrack_pilot/token_api_hydration_mix_log.jsonl",
        "row_count_total": len(rows),
        "row_count_window": len(recent),
        "latest_live_ratio": float(latest.get("live_ratio", 0.0)),
        "avg_live_ratio_7d": avg_live_ratio,
        "latest_metrics_mode_counts": latest.get("metrics_mode_counts", {}),
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"APPENDED: {LOG}")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
