#!/usr/bin/env python3
"""Holdout-style stability report on SANDBOX stream snapshots (research_only).

Each stream row stores a rolling 30d batch hit_rate snapshot (not single-day oracle).
Holdout = mean hit_rate on the last H calendar snapshot days vs prior days.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STREAM = ROOT / "reports/sandbox_prophecy_stream_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/sandbox_prophecy_holdout_report_v1_latest.json"


def _load_rollup_helpers():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_sandbox_prophecy_stream_rollup_v1",
        ROOT / "scripts/build_sandbox_prophecy_stream_rollup_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def build_holdout_report(
    stream_rows: list[dict[str, Any]],
    *,
    holdout_snapshot_days: int = 7,
    train_min_snapshots: int = 2,
    pass_holdout_mean: float = 0.5,
    pass_train_mean: float = 0.5,
) -> dict[str, Any]:
    mod = _load_rollup_helpers()
    by_target = mod._dedupe_latest_per_day(stream_rows)
    targets_out: list[dict[str, Any]] = []

    for tid in sorted(by_target.keys()):
        if str(tid).endswith("_invert"):
            continue
        days_map = by_target[tid]
        days = sorted(days_map.keys())
        numeric = [(d, mod._hit(days_map[d])) for d in days]
        numeric = [(d, h) for d, h in numeric if h is not None]
        if len(numeric) < train_min_snapshots + 1:
            targets_out.append(
                {
                    "target_id": tid,
                    "ok": False,
                    "reason": "insufficient_snapshot_days",
                    "n_snapshot_days": len(numeric),
                }
            )
            continue

        h = min(holdout_snapshot_days, max(1, len(numeric) // 4))
        train_part = numeric[:-h] if len(numeric) > h else []
        hold_part = numeric[-h:]
        train_mean = sum(x[1] for x in train_part) / len(train_part) if train_part else None
        hold_mean = sum(x[1] for x in hold_part) / len(hold_part) if hold_part else None
        latest = numeric[-1][1]
        passed = (
            train_mean is not None
            and hold_mean is not None
            and train_mean >= pass_train_mean
            and hold_mean >= pass_holdout_mean
        )
        targets_out.append(
            {
                "target_id": tid,
                "asset": days_map[days[-1]].get("asset"),
                "lens_profile": days_map[days[-1]].get("lens_profile"),
                "n_snapshot_days": len(numeric),
                "holdout_snapshot_days": h,
                "train_mean_hit": round(train_mean, 6) if train_mean is not None else None,
                "holdout_mean_hit": round(hold_mean, 6) if hold_mean is not None else None,
                "latest_snapshot_hit": round(latest, 6),
                "holdout_pass": passed,
                "ok": True,
            }
        )

    passed_ids = [t["target_id"] for t in targets_out if t.get("holdout_pass")]
    return {
        "schema": "sandbox_prophecy_holdout_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "SANDBOX",
        "research_only": True,
        "method_note_ko": (
            "스트림 각 행은 당일 30일 배치 적중률 스냅샷. "
            "홀드아웃은 최근 H일 스냅샷 평균 vs 이전 스냅샷 평균(안정성)."
        ),
        "policy": {
            "holdout_snapshot_days": holdout_snapshot_days,
            "pass_holdout_mean": pass_holdout_mean,
            "pass_train_mean": pass_train_mean,
            "exclude_invert_suffix": True,
        },
        "n_targets": len(targets_out),
        "n_holdout_pass": len(passed_ids),
        "holdout_pass_target_ids": passed_ids,
        "targets": targets_out,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stream-jsonl", type=Path, default=DEFAULT_STREAM)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--holdout-snapshot-days", type=int, default=7)
    args = ap.parse_args()
    if not args.stream_jsonl.is_file():
        print(f"Missing stream: {args.stream_jsonl}", file=__import__("sys").stderr)
        return 2
    mod = _load_rollup_helpers()
    doc = build_holdout_report(
        mod._read_jsonl(args.stream_jsonl),
        holdout_snapshot_days=args.holdout_snapshot_days,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    print(f"holdout_pass={doc['n_holdout_pass']}/{doc['n_targets']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
