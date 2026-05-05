#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Staleness guard: compare curated joint ingest signal time vs celebrity hit-rate artifact time.

- **curated signal time:** max of per-line ``ingest_at_utc`` (ISO-8601, Z recommended); if none
  present, uses the curated JSONL file mtime (UTC).
- **bench time:** ``generated_at_utc`` from ``myeongni_celebrity_hit_rate_v1.json`` (if present).
- **STALE** when the absolute gap between the two instants exceeds ``--threshold-hours`` (default 24),
  or when the hit-rate file is missing while the curated file has content.

Exit: 0 by default. With ``--strict``, exit 1 if status is STALE or error.

CI / ``run_fact_lock_bundle.ps1``: keep **non-strict** by default so clock skew and missing
hit-rate artifact do not fail PRs; use ``--strict`` in scheduled/nightly governance if you want
hard fail on stale curated vs benchmark artifact.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CURATED = ROOT / "data" / "myeongni" / "curated_saju_joint_v1.jsonl"
DEFAULT_BENCH = ROOT / "docs" / "final" / "artifacts" / "myeongni_celebrity_hit_rate_v1.json"
_DEFAULT_STALE_OUT = ROOT / "reports" / "curated_saju_joint_staleness_v1_latest.json"


def _parse_utc(s: str) -> datetime | None:
    t = (s or "").strip()
    if not t:
        return None
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(t)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _curated_signal_utc(path: Path) -> tuple[datetime | None, str, list[str]]:
    """Return (max instant, method, notes)."""
    notes: list[str] = []
    if not path.is_file():
        return None, "missing_file", ["curated file not found"]
    instants: list[datetime] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            notes.append(f"line {line_no}: skip json {e}")
            continue
        if not isinstance(row, dict):
            continue
        raw = str(row.get("ingest_at_utc") or "").strip()
        if raw:
            dt = _parse_utc(raw)
            if dt:
                instants.append(dt)
            else:
                notes.append(f"line {line_no}: bad ingest_at_utc {raw!r}")
    if instants:
        return max(instants), "max_ingest_at_utc", notes
    mtime = path.stat().st_mtime
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return dt, "curated_file_mtime_utc", notes


def _bench_generated_utc(path: Path) -> tuple[datetime | None, str]:
    if not path.is_file():
        return None, "missing"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "unreadable"
    g = str(doc.get("generated_at_utc") or "").strip()
    if not g:
        return None, "no_field"
    dt = _parse_utc(g)
    if dt is None:
        return None, "bad_timestamp"
    return dt, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--curated-jsonl", type=Path, default=DEFAULT_CURATED)
    ap.add_argument("--hit-rate-json", type=Path, default=DEFAULT_BENCH)
    ap.add_argument("--threshold-hours", type=float, default=24.0)
    ap.add_argument("--strict", action="store_true", help="Exit 1 when STALE or missing bench with curated rows.")
    ap.add_argument("--out-json", type=Path, default=None, help=f"Write summary (default: {_DEFAULT_STALE_OUT})")
    args = ap.parse_args()

    curated_dt, curated_src, c_notes = _curated_signal_utc(args.curated_jsonl)
    bench_dt, bench_src = _bench_generated_utc(args.hit_rate_json)

    status = "UNKNOWN"
    stale_reason = ""
    gap_hours: float | None = None

    has_curated_rows = False
    if args.curated_jsonl.is_file():
        raw = args.curated_jsonl.read_text(encoding="utf-8").strip()
        has_curated_rows = bool(raw)

    if not has_curated_rows:
        status = "OK_EMPTY_CURATED"
        stale_reason = "curated jsonl empty — staleness not applicable"
    elif curated_dt is None:
        status = "ERROR"
        stale_reason = "could not derive curated signal time"
    elif bench_dt is None:
        status = "STALE"
        stale_reason = f"hit-rate artifact missing or unreadable ({bench_src})"
        gap_hours = None
    else:
        gap_seconds = abs((curated_dt - bench_dt).total_seconds())
        gap_hours = gap_seconds / 3600.0
        if gap_hours > float(args.threshold_hours):
            status = "STALE"
            stale_reason = (
                f"|curated_signal - bench_generated| = {gap_hours:.2f}h "
                f"(threshold {args.threshold_hours}h); curated={curated_src}, bench={bench_src}"
            )
        else:
            status = "OK"
            stale_reason = "within threshold"

    summary = {
        "schema": "curated_saju_joint_staleness_v1",
        "status": status,
        "stale_reason": stale_reason,
        "threshold_hours": args.threshold_hours,
        "gap_hours": round(gap_hours, 4) if gap_hours is not None else None,
        "curated_signal_utc": curated_dt.isoformat().replace("+00:00", "Z") if curated_dt else None,
        "curated_signal_source": curated_src,
        "bench_generated_utc": bench_dt.isoformat().replace("+00:00", "Z") if bench_dt else None,
        "bench_source": bench_src,
        "paths": {
            "curated_jsonl": str(args.curated_jsonl),
            "hit_rate_json": str(args.hit_rate_json),
        },
        "notes": c_notes[:20],
    }

    out_path = args.out_json if args.out_json is not None else _DEFAULT_STALE_OUT
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.strict and status in ("STALE", "ERROR"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
