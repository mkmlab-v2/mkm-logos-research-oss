#!/usr/bin/env python3
"""Build weekly trend summary for lens music hormone-like state (M31 extension)."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "lens_music_prompt_overlay_history_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_hormone_trend_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path, max_rows: int) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines()[-max_rows:]:
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


def _pick_day(row: dict[str, Any]) -> str:
    ts = str(row.get("ts_utc") or "").strip()
    return ts[:10] if len(ts) >= 10 else "unknown"


def _max_consecutive(values: list[bool]) -> int:
    best = 0
    cur = 0
    for v in values:
        if v:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--max-rows", type=int, default=2000)
    ap.add_argument("--high-stress-rate-watch-threshold", type=float, default=0.25)
    ap.add_argument("--high-stress-consecutive-watch-threshold", type=int, default=3)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _load_jsonl(args.history_log_jsonl, max_rows=max(1, int(args.max_rows)))
    hormone_rows = [r for r in rows if str(r.get("hormone_state") or "").strip()]
    n = len(hormone_rows)

    state_counts: Counter[str] = Counter()
    daily: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "high_stress": 0})
    high_stress_flags: list[bool] = []
    stress_samples: list[float] = []

    for r in hormone_rows:
        state = str(r.get("hormone_state") or "UNKNOWN").strip().upper()
        state_counts[state] += 1
        is_high_stress = state == "HIGH_STRESS"
        high_stress_flags.append(is_high_stress)

        day = _pick_day(r)
        daily[day]["rows"] += 1
        if is_high_stress:
            daily[day]["high_stress"] += 1

        try:
            stress_samples.append(float(r.get("stress_index_0_1")))
        except (TypeError, ValueError):
            pass

    high_stress_count = int(state_counts.get("HIGH_STRESS", 0))
    high_stress_rate = round((high_stress_count / n) if n else 0.0, 6)
    max_consecutive_high_stress = _max_consecutive(high_stress_flags)
    mean_stress_index = round((sum(stress_samples) / len(stress_samples)) if stress_samples else 0.0, 6)

    daily_series = []
    for d in sorted(daily.keys()):
        rows_n = daily[d]["rows"]
        hs_n = daily[d]["high_stress"]
        daily_series.append(
            {
                "date": d,
                "rows": rows_n,
                "high_stress_count": hs_n,
                "high_stress_rate": round((hs_n / rows_n) if rows_n else 0.0, 6),
            }
        )

    operator_hint = None
    if n == 0:
        state = "NODATA"
        operator_hint = (
            "rows_scanned==0: append history via scripts/build_lens_music_prompt_overlay_v1.py "
            "(default reports/lens_music_prompt_overlay_history_log.jsonl), then re-run this trend builder."
        )
    elif high_stress_rate > float(args.high_stress_rate_watch_threshold) or (
        max_consecutive_high_stress >= int(args.high_stress_consecutive_watch_threshold)
    ):
        state = "WATCH"
    else:
        state = "GO"

    out = {
        "schema": "lens_music_hormone_trend_v1",
        "generated_at_utc": _utc_now(),
        "history_log_path": str(args.history_log_jsonl.resolve()),
        "rows_scanned": n,
        "state": state,
        "state_counts": dict(state_counts),
        "high_stress_count": high_stress_count,
        "high_stress_rate": high_stress_rate,
        "max_consecutive_high_stress": max_consecutive_high_stress,
        "mean_stress_index_0_1": mean_stress_index,
        "watch_thresholds": {
            "high_stress_rate": float(args.high_stress_rate_watch_threshold),
            "high_stress_consecutive": int(args.high_stress_consecutive_watch_threshold),
        },
        "daily_series": daily_series,
        "advisory_only": True,
        "track": "B",
        "non_biological_notice": "metaphor_only_advisory_controller",
    }
    if operator_hint:
        out["operator_hint"] = operator_hint

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": state, "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
