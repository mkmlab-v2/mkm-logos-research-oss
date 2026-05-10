#!/usr/bin/env python3
"""Build daily trend and top triggers for prompt auto-brake history (M25)."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = ROOT / "reports" / "lens_music_prompt_overlay_history_log.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "lens_music_prompt_brake_trend_latest.json"


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
    if len(ts) >= 10:
        return ts[:10]
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--max-rows", type=int, default=2000)
    ap.add_argument("--top-n", type=int, default=3)
    ap.add_argument("--active-rate-watch-threshold", type=float, default=0.2)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _load_jsonl(args.history_log_jsonl, max_rows=max(1, int(args.max_rows)))
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"rows": 0, "active": 0})
    triggers = Counter()
    active_total = 0

    for r in rows:
        d = _pick_day(r)
        by_day[d]["rows"] += 1
        active = bool(r.get("auto_brake_active"))
        if active:
            by_day[d]["active"] += 1
            active_total += 1
        if bool(r.get("trigger_governance_watch")):
            triggers["governance_watch"] += 1
        if bool(r.get("trigger_smoke_eval_watch")):
            triggers["smoke_eval_watch"] += 1

    daily = []
    for d in sorted(by_day.keys()):
        rows_n = by_day[d]["rows"]
        active_n = by_day[d]["active"]
        daily.append(
            {
                "date": d,
                "rows": rows_n,
                "active_count": active_n,
                "active_rate": round((active_n / rows_n) if rows_n else 0.0, 6),
            }
        )

    rows_total = len(rows)
    active_rate = round((active_total / rows_total) if rows_total else 0.0, 6)
    top = [{"trigger": k, "count": v} for k, v in triggers.most_common(max(1, int(args.top_n)))]

    out = {
        "schema": "lens_music_prompt_brake_trend_v1",
        "generated_at_utc": _utc_now(),
        "rows_scanned": rows_total,
        "auto_brake_active_count": active_total,
        "auto_brake_active_rate": active_rate,
        "watch_threshold": float(args.active_rate_watch_threshold),
        "state": "WATCH" if active_rate > float(args.active_rate_watch_threshold) else "GO",
        "top_triggers": top,
        "daily_series": daily,
        "advisory_only": True,
        "track": "B",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "state": out["state"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
