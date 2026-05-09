#!/usr/bin/env python3
"""Build weekly quality report for MKM Three-Lens commercial-safe operations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY = ROOT / "docs" / "final" / "artifacts" / "three_lens_shadow_history_v1.jsonl"
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "three_lens_feature_gate_v2_latest.json"
DEFAULT_PACK = ROOT / "docs" / "final" / "artifacts" / "mkm_commercial_gate_pack_v1_latest.json"
DEFAULT_SCHED = ROOT / "reports" / "scheduler_phase3_slimming_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "mkm_three_lens_weekly_quality_report_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _safe_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return _read_json(path)
    except Exception:
        return {}


def _parse_ts(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _load_history(path: Path, since_utc: datetime) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        ts = _parse_ts(str(row.get("ts_utc", "")))
        if ts is None:
            continue
        if ts >= since_utc:
            rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history-jsonl", type=Path, default=DEFAULT_HISTORY)
    ap.add_argument("--feature-gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--gate-pack-json", type=Path, default=DEFAULT_PACK)
    ap.add_argument("--scheduler-json", type=Path, default=DEFAULT_SCHED)
    ap.add_argument("--window-days", type=int, default=7)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=max(1, args.window_days))
    history = _load_history(args.history_jsonl, since)
    gate = _safe_json(args.feature_gate_json)
    gate_pack = _safe_json(args.gate_pack_json)
    scheduler = _safe_json(args.scheduler_json)

    action_counts = Counter(str(r.get("action", "UNKNOWN")).upper() for r in history)
    total = len(history)
    go_rate = (action_counts.get("GO", 0) / total) if total else 0.0
    watch_rate = (action_counts.get("WATCH", 0) / total) if total else 0.0
    hold_rate = (action_counts.get("HOLD", 0) / total) if total else 0.0

    sched_summary = scheduler.get("summary") if isinstance(scheduler.get("summary"), dict) else {}
    gate_decision = gate.get("decision") if isinstance(gate.get("decision"), dict) else {}
    gate_metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}

    decision = "HOLD_REVIEW"
    if total == 0:
        decision = "NO_DATA"
    elif hold_rate > 0.10:
        decision = "HOLD_HIGH_HOLD_RATE"
    elif watch_rate > 0.85:
        decision = "WATCH_BIAS_RECHECK"
    elif gate_decision.get("action") in {"GO", "WATCH"} and gate_pack.get("commercial_ready_safe_mode") is True:
        decision = "GO_STABLE_SAFE_MODE"

    payload = {
        "schema": "mkm_three_lens_weekly_quality_report_v1",
        "generated_at_utc": _now(),
        "window_days": max(1, args.window_days),
        "sample_count": total,
        "history_action_counts": dict(action_counts),
        "rates": {
            "go_rate": round(go_rate, 6),
            "watch_rate": round(watch_rate, 6),
            "hold_rate": round(hold_rate, 6),
        },
        "gate_latest": {
            "action": gate_decision.get("action"),
            "reason": gate_decision.get("reason"),
            "risk_score_0_1": gate_metrics.get("risk_score_0_1"),
            "opportunity_score_0_1": gate_metrics.get("opportunity_score_0_1"),
            "watch_bias_ratio": gate_metrics.get("watch_bias_ratio"),
        },
        "scheduler_latest": {
            "morning_window_task_count": sched_summary.get("morning_window_task_count"),
            "candidate_reduce_count": sched_summary.get("candidate_reduce_count"),
        },
        "commercial_safe_gate_pack": {
            "commercial_ready_safe_mode": gate_pack.get("commercial_ready_safe_mode"),
            "mode": gate_pack.get("mode"),
        },
        "decision": decision,
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[three-lens-weekly-quality] sample_count={total} decision={decision} out={out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
