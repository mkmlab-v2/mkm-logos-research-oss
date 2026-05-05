#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.8, K:0.4, M:0.7}
# Balance: 88
# Purpose: Track monitor_only streaks and emit recalibration hint.
# Keywords: threshold, recalibration, streak, monitor_only
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit threshold recalibration hint from monitor_only streak.")
    ap.add_argument("--exploration-brief-json", default="docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json")
    ap.add_argument("--history-json", default="docs/final/artifacts/external_bible_crossref_action_history_latest.json")
    ap.add_argument("--streak-trigger", type=int, default=3)
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_threshold_recalibration_hint_latest.json")
    args = ap.parse_args()

    p_brief = resolve(args.exploration_brief_json)
    p_history = resolve(args.history_json)
    p_out = resolve(args.output_json)
    if not p_brief.is_file():
        raise SystemExit(f"missing brief: {p_brief}")

    brief = json.loads(p_brief.read_text(encoding="utf-8"))
    action = str(brief.get("recommended_next_action", "no_action"))

    history: dict[str, Any] = {"events": []}
    if p_history.is_file():
        raw = json.loads(p_history.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            history = raw
    events = history.get("events", [])
    if not isinstance(events, list):
        events = []
    events.append({"at_utc": now_utc(), "recommended_next_action": action})
    events = events[-20:]
    monitor_streak = 0
    for e in reversed(events):
        if str((e or {}).get("recommended_next_action", "")) == "monitor_only":
            monitor_streak += 1
        else:
            break

    history_out = {
        "schema": "external_bible_crossref_action_history_v1",
        "generated_at_utc": now_utc(),
        "events": events,
        "monitor_only_streak": monitor_streak,
    }
    p_history.parent.mkdir(parents=True, exist_ok=True)
    p_history.write_text(json.dumps(history_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    trigger = int(args.streak_trigger)
    hint = {
        "schema": "external_bible_crossref_threshold_recalibration_hint_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "monitor_only_streak": monitor_streak,
        "streak_trigger": trigger,
        "hint_active": monitor_streak >= trigger,
        "recommended_action": "propose_threshold_recalibration" if monitor_streak >= trigger else "none",
        "history_ref": str(p_history),
    }
    p_out.parent.mkdir(parents=True, exist_ok=True)
    p_out.write_text(json.dumps(hint, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(p_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
