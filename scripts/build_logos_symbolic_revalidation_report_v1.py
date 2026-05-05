#!/usr/bin/env python3
"""Build rolling-window revalidation report for Logos symbolic backtest."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKTEST = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_event_backtest_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "logos_symbolic_revalidation_report_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _hit_rate(hits: int, n: int) -> float | None:
    return round(hits / n, 6) if n else None


def _asof_key(row: dict[str, Any]) -> str:
    return str(row.get("as_of_utc") or "")


def _window_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    hits = sum(int(r.get("hit") or 0) for r in rows)
    per_source: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "hits": 0})
    for r in rows:
        sid = str(r.get("source_id") or "unknown")
        per_source[sid]["n"] += 1
        per_source[sid]["hits"] += int(r.get("hit") or 0)
    source_summary = {
        sid: {"n_evaluated": s["n"], "hit_rate": _hit_rate(s["hits"], s["n"])}
        for sid, s in sorted(per_source.items())
    }
    return {
        "n_evaluated": n,
        "hits": hits,
        "hit_rate": _hit_rate(hits, n),
        "source_summary": source_summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backtest-json", type=Path, default=DEFAULT_BACKTEST)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--recent-window-sizes", type=str, default="30,60")
    ap.add_argument("--min-window-hit-rate", type=float, default=0.75)
    ap.add_argument("--min-source-hit-rate", type=float, default=0.5)
    args = ap.parse_args()

    backtest = _load_json(Path(args.backtest_json).resolve())
    rows = backtest.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid backtest rows")
    rows = [r for r in rows if isinstance(r, dict)]
    rows_sorted = sorted(rows, key=_asof_key)
    window_sizes = [int(x.strip()) for x in str(args.recent_window_sizes).split(",") if x.strip()]

    windows: dict[str, Any] = {}
    risk_flags: dict[str, bool] = {}
    for w in window_sizes:
        subset = rows_sorted[-w:] if w > 0 else rows_sorted
        metrics = _window_metrics(subset)
        windows[f"recent_{w}"] = metrics
        key = f"recent_{w}_hit_rate_below_min"
        hr = metrics.get("hit_rate")
        risk_flags[key] = bool(isinstance(hr, float) and hr < float(args.min_window_hit_rate))

    overall = _window_metrics(rows_sorted)
    low_sources: list[str] = []
    for sid, s in (overall.get("source_summary") or {}).items():
        hr = s.get("hit_rate")
        if isinstance(hr, float) and hr < float(args.min_source_hit_rate):
            low_sources.append(sid)
    risk_flags["source_hit_rate_below_min"] = bool(low_sources)
    status = "warning" if any(risk_flags.values()) else "ok"

    out = {
        "schema": "logos_symbolic_revalidation_report_v1",
        "generated_at_utc": _now(),
        "input_backtest_json": str(Path(args.backtest_json).resolve()).replace("\\", "/"),
        "thresholds": {
            "min_window_hit_rate": float(args.min_window_hit_rate),
            "min_source_hit_rate": float(args.min_source_hit_rate),
            "recent_window_sizes": window_sizes,
        },
        "overall": overall,
        "windows": windows,
        "low_source_ids": low_sources,
        "risk_flags": risk_flags,
        "status": status,
    }

    out_path = Path(args.output_json).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

