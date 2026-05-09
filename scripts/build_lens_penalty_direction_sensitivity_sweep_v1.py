#!/usr/bin/env python3
"""Build direction sensitivity sweep report from falsification events."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_EVENTS = REPORTS / "daily_execution_insight_falsification_log.jsonl"
DEFAULT_OUT = ART / "lens_penalty_direction_sensitivity_sweep_latest.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _parse_ts(s: Any) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    x = s.strip()
    if x.endswith("Z"):
        x = x[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(x)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _flip(label: str) -> str:
    if label == "UP":
        return "DOWN"
    if label == "DOWN":
        return "UP"
    return label


def _fail_rate(rows: list[dict[str, str]], flip: bool) -> tuple[int, int, float]:
    events = 0
    fails = 0
    for r in rows:
        pred = str(r.get("prediction_label") or "").upper()
        actual = str(r.get("actual_label") or "").upper()
        if pred not in {"UP", "DOWN", "NEUTRAL"}:
            continue
        if actual not in {"UP", "DOWN", "NEUTRAL"}:
            continue
        events += 1
        used_pred = _flip(pred) if flip else pred
        if used_pred != actual:
            fails += 1
    rate = (fails / events) if events > 0 else 0.0
    return events, fails, round(rate, 6)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--events-jsonl", type=Path, default=DEFAULT_EVENTS)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--min-events", type=int, default=6)
    ap.add_argument("--min-improvement", type=float, default=0.15)
    args = ap.parse_args()

    now = _now()
    window_start = now - timedelta(days=max(args.window_days, 1))
    all_rows = _read_jsonl(args.events_jsonl)
    rows: list[dict[str, Any]] = []
    for r in all_rows:
        ts = _parse_ts(r.get("timestamp_utc"))
        if ts is None:
            continue
        if ts >= window_start:
            rows.append(r)

    by_lens: dict[str, list[dict[str, str]]] = {}
    for r in rows:
        lens_id = str(r.get("lens_id") or "").strip()
        if not lens_id:
            continue
        by_lens.setdefault(lens_id, []).append(
            {
                "prediction_label": str(r.get("prediction_label") or "").upper(),
                "actual_label": str(r.get("actual_label") or "").upper(),
            }
        )

    per_lens: list[dict[str, Any]] = []
    flip_candidates = 0
    for lens_id in sorted(by_lens.keys()):
        lens_rows = by_lens[lens_id]
        base_events, base_fail, base_rate = _fail_rate(lens_rows, flip=False)
        flip_events, flip_fail, flip_rate = _fail_rate(lens_rows, flip=True)
        improvement = round(base_rate - flip_rate, 6)
        recommend_flip = bool(base_events >= int(args.min_events) and improvement >= float(args.min_improvement))
        if recommend_flip:
            flip_candidates += 1
        per_lens.append(
            {
                "lens_id": lens_id,
                "baseline": {"events": base_events, "fail_count": base_fail, "fail_rate": base_rate},
                "flip_simulation": {"events": flip_events, "fail_count": flip_fail, "fail_rate": flip_rate},
                "improvement_if_flip": improvement,
                "recommend_flip_shadow_candidate": recommend_flip,
            }
        )

    out = {
        "schema": "lens_penalty_direction_sensitivity_sweep_v1",
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {
            "days": int(args.window_days),
            "start_utc": window_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "end_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "params": {
            "min_events": int(args.min_events),
            "min_improvement": float(args.min_improvement),
        },
        "summary": {
            "lenses": len(per_lens),
            "flip_candidates": flip_candidates,
        },
        "per_lens": per_lens,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"lenses={len(per_lens)}; flip_candidates={flip_candidates}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
