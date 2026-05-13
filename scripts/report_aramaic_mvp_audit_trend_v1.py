#!/usr/bin/env python3
"""Summarize recent rows from aramaic_mvp_run_audit_log.jsonl into a trend artifact."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_audit_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _float_stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    if len(values) == 1:
        v = values[0]
        return {"mean": v, "min": v, "max": v}
    return {
        "mean": float(statistics.mean(values)),
        "min": float(min(values)),
        "max": float(max(values)),
    }


def _collect_numeric(rows: list[dict[str, Any]], key: str) -> list[float]:
    out: list[float] = []
    for r in rows:
        if key not in r:
            continue
        try:
            out.append(float(r[key]))
        except (TypeError, ValueError):
            continue
    return out


def _histogram_str(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    hist: dict[str, int] = {}
    for r in rows:
        raw = r.get(key)
        if raw is None:
            continue
        label = str(raw).strip() or "(empty)"
        hist[label] = hist.get(label, 0) + 1
    return dict(sorted(hist.items(), key=lambda kv: (-kv[1], kv[0])))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--audit-jsonl",
        default="reports/ops/aramaic_mvp_run_audit_log.jsonl",
        help="Append-only audit log from run_aramaic_mvp_now_with_audit.ps1",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/aramaic_mvp_audit_trend_latest.json",
        help="Trend summary JSON (default under docs/final/artifacts)",
    )
    ap.add_argument(
        "--window",
        type=int,
        default=100,
        help="Use at most this many most recent valid rows (default 100)",
    )
    a = ap.parse_args()

    audit_path = Path(a.audit_jsonl)
    if not audit_path.is_absolute():
        audit_path = ROOT / audit_path
    out_path = Path(a.output_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path

    all_rows = _load_audit_rows(audit_path)
    window_n = max(1, int(a.window))
    window_rows = all_rows[-window_n:] if all_rows else []

    oldest = None
    newest = None
    for r in window_rows:
        ts = r.get("run_at_utc")
        if not isinstance(ts, str) or not ts.strip():
            continue
        t = ts.strip()
        if oldest is None:
            oldest = t
        newest = t

    metrics_keys = (
        "shift_score",
        "delta_shift_score",
        "oos_shift_score",
        "oos_delta_shift_score",
        "conflict_ratio",
    )
    metrics: dict[str, dict[str, float] | None] = {}
    for k in metrics_keys:
        metrics[k] = _float_stats(_collect_numeric(window_rows, k))

    doc: dict[str, Any] = {
        "schema": "aramaic_mvp_audit_trend_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "source": {"audit_jsonl": str(audit_path)},
        "window": {
            "n_requested": window_n,
            "n_used": len(window_rows),
            "total_valid_rows_in_file": len(all_rows),
            "oldest_run_at_utc": oldest,
            "newest_run_at_utc": newest,
        },
        "metrics": metrics,
        "insight_cap_bucket_histogram": _histogram_str(window_rows, "insight_cap_bucket"),
        "oos_scenario_counts": _histogram_str(window_rows, "oos_scenario"),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
