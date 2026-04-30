#!/usr/bin/env python3
"""Check weekly streak gate from weekly ops history log."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_LOG = ART / "layer1_layer5_weekly_ops_history_log.jsonl"
DEFAULT_OUT = ART / "layer1_layer5_weekly_streak_gate_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
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


def _consecutive_from_end(rows: list[dict[str, Any]], pred) -> int:
    n = 0
    for r in reversed(rows):
        if pred(r):
            n += 1
        else:
            break
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--required-streak", type=int, default=4)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    pass_streak = _consecutive_from_end(
        rows,
        lambda r: str(r.get("base_weekly_status") or r.get("overall_status") or "") == "PASS",
    )
    preflight_streak = _consecutive_from_end(
        rows, lambda r: str(r.get("emotion_preflight_decision") or "") == "GO_LIVE_CANDIDATE"
    )
    ok = pass_streak >= int(args.required_streak) and preflight_streak >= int(args.required_streak)

    out = {
        "schema": "layer1_layer5_weekly_streak_gate_v1",
        "generated_at_utc": _iso_now(),
        "history_jsonl": str(args.history_jsonl).replace("\\", "/"),
        "required_streak": int(args.required_streak),
        "current": {
            "pass_streak": pass_streak,
            "preflight_go_streak": preflight_streak,
            "history_rows": len(rows),
        },
        "status": "PASS" if ok else "HOLD_STREAK_INSUFFICIENT",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": out["status"], "output_json": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
