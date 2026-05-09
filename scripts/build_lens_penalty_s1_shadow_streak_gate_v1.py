#!/usr/bin/env python3
"""Build N-day streak gate from S1 shadow gate history."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_HISTORY = REPORTS / "lens_penalty_s1_shadow_gate_history.jsonl"
DEFAULT_OUT = ART / "lens_penalty_s1_shadow_streak_gate_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--required-streak", type=int, default=3)
    args = ap.parse_args()

    rows = _read_jsonl(args.history_jsonl)
    streak = 0
    for r in reversed(rows):
        if str(r.get("decision") or "") == "GO_REVIEW":
            streak += 1
        else:
            break

    ready = streak >= max(1, int(args.required_streak))
    out = {
        "schema": "lens_penalty_s1_shadow_streak_gate_v1",
        "generated_at_utc": _now(),
        "decision": "READY_FOR_COMMANDER_REVIEW" if ready else "HOLD_STREAK",
        "all_green": ready,
        "snapshot": {
            "required_streak": int(args.required_streak),
            "current_go_streak": streak,
            "history_rows": len(rows),
        },
        "inputs": {
            "history_jsonl": str(args.history_jsonl.resolve()).replace("\\", "/"),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"streak={streak}; ready={ready}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
