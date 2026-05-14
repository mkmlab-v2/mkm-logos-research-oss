#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

HISTORY_ROW_SCHEMA = "aramaic_insight_cap_bucket_threshold_history_row_v1"
RECOMMENDED_KEYS = (
    "mid_vol_threshold",
    "high_vol_threshold",
    "insight_max_delta_low_vol",
    "insight_max_delta_mid_vol",
    "insight_max_delta_high_vol",
)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_under_root(p: Path) -> Path:
    if p.is_absolute():
        return p
    return ROOT / p


def _load_history_rows(hp: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not hp.is_file():
        return rows
    for line in hp.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            o = json.loads(s)
        except Exception:
            continue
        if isinstance(o, dict):
            rows.append(o)
    return rows


def _recommended_snapshots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordered list of `recommended` dicts from valid history rows."""
    out: list[dict[str, Any]] = []
    for r in rows:
        if r.get("schema") != HISTORY_ROW_SCHEMA:
            continue
        rec = r.get("recommended")
        if isinstance(rec, dict) and rec:
            out.append(rec)
    return out


def _compare_last_two(
    prev: dict[str, Any], curr: dict[str, Any], drift_threshold: float
) -> tuple[bool, float, list[str], dict[str, float]]:
    drifted: list[str] = []
    deltas: dict[str, float] = {}
    max_abs = 0.0
    keys = [k for k in RECOMMENDED_KEYS if k in prev and k in curr]
    if not keys:
        keys = [k for k in set(prev) & set(curr) if isinstance(prev.get(k), (int, float)) and isinstance(curr.get(k), (int, float))]
    for k in keys:
        try:
            a = float(prev[k])
            b = float(curr[k])
        except (TypeError, ValueError):
            continue
        d = abs(b - a)
        deltas[k] = d
        max_abs = max(max_abs, d)
        if d > drift_threshold:
            drifted.append(k)
    return (len(drifted) > 0, max_abs, drifted, deltas)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Compare last two insight-cap threshold snapshots in history JSONL and emit drift alert JSON."
    )
    ap.add_argument(
        "--history-jsonl",
        default="reports/ops/aramaic_insight_cap_bucket_threshold_history.jsonl",
        help="Append-only history (default: under repo root).",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/aramaic_insight_cap_bucket_threshold_drift_alert_latest.json",
        help="Drift alert artifact path (default: under repo root).",
    )
    ap.add_argument(
        "--drift-threshold",
        type=float,
        default=1e-4,
        help="Absolute delta above which a numeric recommended field counts as drift (default: 1e-4).",
    )
    a = ap.parse_args()
    hp = resolve_under_root(Path(a.history_jsonl))
    op = resolve_under_root(Path(a.output_json))
    drift_threshold = float(a.drift_threshold)
    if drift_threshold < 0:
        drift_threshold = 0.0

    rows = _load_history_rows(hp)
    recs = _recommended_snapshots(rows)

    base = {
        "schema": "aramaic_insight_cap_threshold_drift_alert_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "history_rows": len(rows),
        "history_recommended_snapshots": len(recs),
        "drift_threshold": drift_threshold,
        "should_alert": False,
        "reason": "insufficient_history",
        "max_abs_delta": 0.0,
        "drifted_keys": [],
        "deltas": {},
    }

    if len(recs) < 2:
        base["reason"] = "insufficient_history"
    else:
        prev, curr = recs[-2], recs[-1]
        should, max_abs, drifted, deltas = _compare_last_two(prev, curr, drift_threshold)
        base["max_abs_delta"] = round(max_abs, 8)
        base["deltas"] = {k: round(v, 8) for k, v in sorted(deltas.items())}
        base["drifted_keys"] = drifted
        if should:
            base["should_alert"] = True
            base["reason"] = "threshold_drift"
        else:
            base["should_alert"] = False
            base["reason"] = "stable_below_threshold"

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
