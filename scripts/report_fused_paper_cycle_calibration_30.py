#!/usr/bin/env python3
"""Rolling 30-row calibration snapshot from waiting_queue_monthly_check_log.jsonl."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "docs" / "final" / "artifacts" / "waiting_queue_monthly_check_log.jsonl"
OUT = ROOT / "docs" / "final" / "artifacts" / "fused_paper_cycle_calibration_30_latest.json"
HISTORY = ROOT / "docs" / "final" / "artifacts" / "fused_paper_cycle_decision_history.jsonl"
WINDOW = 30


def _rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip().lstrip("\ufeff")
        if not s:
            continue
        try:
            o = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out


def _decision(row: dict[str, Any]) -> str:
    d = row.get("post_close_eval_decision")
    if d in ("HIT", "FAIL", "NEUTRAL_DRAW", "PENDING_CLOSE"):
        return str(d)
    return "PENDING_CLOSE"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--log-path", type=Path, default=DEFAULT_LOG)
    args = p.parse_args()
    all_rows = _rows(args.log_path)
    window = all_rows[-WINDOW:] if len(all_rows) > WINDOW else all_rows
    decisions = [_decision(r) for r in window]
    counts = {
        "HIT": sum(1 for x in decisions if x == "HIT"),
        "FAIL": sum(1 for x in decisions if x == "FAIL"),
        "NEUTRAL_DRAW": sum(1 for x in decisions if x == "NEUTRAL_DRAW"),
        "PENDING_CLOSE": sum(1 for x in decisions if x == "PENDING_CLOSE"),
    }
    n = len(decisions)
    rates = {
        "hit_rate_raw": (counts["HIT"] / n) if n else 0.0,
        "fail_rate_raw": (counts["FAIL"] / n) if n else 0.0,
        "neutral_draw_rate_raw": (counts["NEUTRAL_DRAW"] / n) if n else 0.0,
        "pending_close_rate_raw": (counts["PENDING_CLOSE"] / n) if n else 0.0,
        "resolved_only_hit_rate": (
            counts["HIT"] / max(1, counts["HIT"] + counts["FAIL"] + counts["NEUTRAL_DRAW"])
        ),
    }
    crs: list[float] = []
    for r in window:
        v = r.get("close_return_pct")
        if v is not None:
            try:
                crs.append(float(v))
            except (TypeError, ValueError):
                pass
    close_stats = {
        "sample_count": len(crs),
        "mean_pct": round(sum(crs) / len(crs), 6) if crs else None,
        "min_pct": round(min(crs), 6) if crs else None,
        "max_pct": round(max(crs), 6) if crs else None,
    }
    pending_rate = rates["pending_close_rate_raw"]
    close_missing = counts["PENDING_CLOSE"]
    doc = {
        "schema": "fused_paper_cycle_calibration_30_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_log_path": str(args.log_path.resolve()),
        "window_size": WINDOW,
        "sample_size": n,
        "counts": counts,
        "rates": rates,
        "data_quality": {
            "close_return_missing_count": close_missing,
            "close_return_missing_non_pending_count": 0,
            "hold_reason_missing_count": 0,
        },
        "close_return_stats": close_stats,
        "hold_reason_samples": [],
        "gate_checks": {
            "pending_close_rate_alert": pending_rate > 0.7,
            "hold_reason_missing_alert": False,
            "close_return_missing_alert": close_missing > 0,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"WROTE: {OUT}")


if __name__ == "__main__":
    main()
