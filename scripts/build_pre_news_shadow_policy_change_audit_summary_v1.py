#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build audit summary from policy change log.")
    ap.add_argument(
        "--change-log-jsonl",
        default="reports/pre_news_shadow_stage_threshold_policy_change_log.jsonl",
    )
    ap.add_argument(
        "--state-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_state_latest.json",
    )
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument(
        "--out-json",
        default="docs/final/artifacts/pre_news_shadow_stage_threshold_policy_audit_summary_latest.json",
    )
    args = ap.parse_args()

    log_path = resolve(args.change_log_jsonl)
    state_path = resolve(args.state_json)
    out_path = resolve(args.out_json)
    w = max(1, int(args.window_days))
    cutoff = now() - timedelta(days=w)

    rows: list[dict[str, Any]] = []
    if log_path.is_file():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)

    in_window: list[dict[str, Any]] = []
    for r in rows:
        dt = parse_iso(str(r.get("detected_at_utc", "") or ""))
        if dt is None or dt < cutoff:
            continue
        in_window.append(r)

    latest_change = in_window[-1] if in_window else (rows[-1] if rows else None)
    state: dict[str, Any] = read_json(state_path) if state_path.is_file() else {}

    out = {
        "schema": "pre_news_shadow_stage_threshold_policy_audit_summary_v1",
        "generated_at_utc": to_iso(now()),
        "window_days": w,
        "change_log_jsonl": str(log_path),
        "state_json": str(state_path),
        "metrics": {
            "change_count_window": len(in_window),
            "change_count_total": len(rows),
            "latest_change_detected_at_utc": (latest_change or {}).get("detected_at_utc"),
        },
        "latest_change": latest_change,
        "current_policy_state": {
            "policy_version": state.get("policy_version"),
            "approved_by": state.get("approved_by"),
            "approved_by_1": state.get("approved_by_1"),
            "approved_by_2": state.get("approved_by_2"),
            "effective_from_utc": state.get("effective_from_utc"),
            "policy_fingerprint_sha256": state.get("policy_fingerprint_sha256"),
            "has_two_person_approval": bool(state.get("approved_by_1")) and bool(state.get("approved_by_2")),
        },
        "risk_summary": (
            f"MEDIUM: {len(in_window)} policy change(s) in last {w} days."
            if len(in_window) >= 2
            else (
                f"LOW: {len(in_window)} policy change(s) in last {w} days."
                if len(in_window) == 1
                else f"LOW: no policy changes in last {w} days."
            )
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

