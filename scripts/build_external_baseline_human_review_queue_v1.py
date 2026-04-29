#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.6}
# Balance: 90
# Purpose: Build human review queue artifact when exploration action requests review.
# Keywords: human review, queue, exploration, btrack
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def add_hours(ts_utc: str, hours: int) -> str:
    dt = datetime.strptime(ts_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (dt.timestamp() + hours * 3600)


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Build human review queue from exploration brief.")
    ap.add_argument("--exploration-brief-json", default="docs/final/artifacts/external_bible_crossref_exploration_signal_brief_latest.json")
    ap.add_argument("--dual-mode-json", default="docs/final/artifacts/external_bible_crossref_dual_mode_report_latest.json")
    ap.add_argument("--hint-json", default="docs/final/artifacts/external_bible_crossref_threshold_recalibration_hint_latest.json")
    ap.add_argument("--auto-open-monitor-streak", type=int, default=12)
    ap.add_argument("--output-json", default="docs/final/artifacts/external_bible_crossref_human_review_queue_latest.json")
    args = ap.parse_args()

    p_brief = resolve(args.exploration_brief_json)
    p_dual = resolve(args.dual_mode_json)
    out_path = resolve(args.output_json)
    if not p_brief.is_file():
        raise SystemExit(f"missing exploration brief: {p_brief}")

    brief = json.loads(p_brief.read_text(encoding="utf-8"))
    action = str(brief.get("recommended_next_action", "no_action"))
    dual = json.loads(p_dual.read_text(encoding="utf-8")) if p_dual.is_file() else {}
    hint = json.loads(resolve(args.hint_json).read_text(encoding="utf-8")) if resolve(args.hint_json).is_file() else {}
    monitor_streak = int(hint.get("monitor_only_streak", 0) or 0)
    auto_open_threshold = int(args.auto_open_monitor_streak)
    op = ((dual.get("operating_mode") or {}).get("best_row_by_delta_then_precision") or {})
    ex = ((dual.get("exploratory_mode") or {}).get("best_row_by_delta_then_precision") or {})
    include_action = action == "enqueue_human_review_and_run_extended_sweep"
    include_streak = monitor_streak >= auto_open_threshold
    include = include_action or include_streak
    trigger_reason = "exploration_signal" if include_action else ("monitor_only_streak" if include_streak else "none")

    generated = now_utc()
    due_epoch = add_hours(generated, 48)
    due_utc = datetime.fromtimestamp(due_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "schema": "external_bible_crossref_human_review_queue_v1",
        "generated_at_utc": generated,
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "included": include,
        "trigger_action": action,
        "trigger_reason": trigger_reason,
        "monitor_only_streak": monitor_streak,
        "auto_open_monitor_streak": auto_open_threshold,
        "owner": "athena_human_review_pool",
        "due_utc": due_utc,
        "status": "open" if include else "closed",
        "items": [],
        "guardrails": [
            "B-track only; no A-track hard merge.",
            "No trading trigger or deterministic claim.",
        ],
    }
    if include:
        out["items"] = [
            {
                "id": "review_exploration_signal",
                "title": "Validate exploratory uplift signal",
                "evidence": {
                    "operating_snapshot": op,
                    "exploratory_snapshot": ex,
                    "brief_snapshot": brief.get("snapshot", {}),
                },
                "checkpoints": [
                    "Confirm uplift is not caused by unstable range expansion artifacts.",
                    "Verify coverage trade-off against operating baseline.",
                    "Maintain B-track interpretation only.",
                ],
                "status": "open",
            }
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
