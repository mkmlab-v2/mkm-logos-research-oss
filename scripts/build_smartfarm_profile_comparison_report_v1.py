#!/usr/bin/env python3
"""Build and persist standard vs aggressive daily comparison report."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build smartfarm profile comparison report.")
    parser.add_argument(
        "--standard-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_gap_policy_daily_gate_v1_standard.json",
    )
    parser.add_argument(
        "--aggressive-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_gap_policy_daily_gate_v1_aggressive.json",
    )
    parser.add_argument(
        "--history-jsonl",
        default="reports/smartfarm_profile_comparison_history_v1.jsonl",
    )
    parser.add_argument(
        "--output-json",
        default="data/smartfarm_rda_extract_v1/out/smartfarm_profile_comparison_report_latest.json",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=3,
    )
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _score_decision(decision: str) -> int:
    decision_map = {"HOLD": 0, "WATCH": 1, "GO": 2}
    return decision_map.get(str(decision).upper(), -1)


def _date_key(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)
    return dt.date().isoformat()


def main() -> int:
    args = _parse_args()
    std_path = Path(args.standard_json)
    agg_path = Path(args.aggressive_json)
    hist_path = Path(args.history_jsonl)
    out_path = Path(args.output_json)

    if not std_path.exists() or not agg_path.exists():
        raise FileNotFoundError("Missing standard/aggressive gate JSON inputs.")

    std = _load_json(std_path)
    agg = _load_json(agg_path)
    now_utc = datetime.now(UTC)
    now_iso = now_utc.isoformat()

    std_fresh = _safe_float(std.get("freshness", {}).get("freshness_hours"))
    agg_fresh = _safe_float(agg.get("freshness", {}).get("freshness_hours"))
    std_gap = _safe_float(std.get("max_gap_hours_observed"))
    agg_gap = _safe_float(agg.get("max_gap_hours_observed"))

    row = {
        "schema": "smartfarm_profile_comparison_row_v1",
        "generated_at_utc": now_iso,
        "date_utc": now_utc.date().isoformat(),
        "standard": {
            "decision": std.get("decision"),
            "decision_score": _score_decision(std.get("decision", "")),
            "max_gap_hours_observed": std_gap,
            "freshness_hours": std_fresh,
            "profile": std.get("profile"),
        },
        "aggressive": {
            "decision": agg.get("decision"),
            "decision_score": _score_decision(agg.get("decision", "")),
            "max_gap_hours_observed": agg_gap,
            "freshness_hours": agg_fresh,
            "profile": agg.get("profile"),
        },
        "delta": {
            "decision_score": _score_decision(agg.get("decision", "")) - _score_decision(std.get("decision", "")),
            "max_gap_hours_observed": (agg_gap - std_gap) if (agg_gap is not None and std_gap is not None) else None,
            "freshness_hours": (agg_fresh - std_fresh) if (agg_fresh is not None and std_fresh is not None) else None,
        },
    }

    _ensure_parent(hist_path)
    with hist_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Load recent window and keep latest per date.
    rows: list[dict[str, Any]] = []
    with hist_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    rows.sort(key=lambda r: r.get("generated_at_utc", ""))
    by_date: dict[str, dict[str, Any]] = {}
    for r in rows:
        ts = r.get("generated_at_utc")
        if isinstance(ts, str):
            by_date[_date_key(ts)] = r

    recent_dates = sorted(by_date.keys())[-max(args.window_days, 1) :]
    window_rows = [by_date[d] for d in recent_dates]

    decision_diff_days = sum(
        1
        for r in window_rows
        if r.get("standard", {}).get("decision") != r.get("aggressive", {}).get("decision")
    )

    report = {
        "schema": "smartfarm_profile_comparison_report_v1",
        "generated_at_utc": now_iso,
        "window_days": args.window_days,
        "window_available_days": len(window_rows),
        "history_jsonl": str(hist_path),
        "latest": row,
        "window_summary": {
            "decision_diff_days": decision_diff_days,
            "decision_same_days": max(len(window_rows) - decision_diff_days, 0),
            "window_rows": window_rows,
        },
    }

    _ensure_parent(out_path)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] comparison report -> {out_path}")
    print(f"[ok] history -> {hist_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

