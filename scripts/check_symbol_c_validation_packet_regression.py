#!/usr/bin/env python3
"""Regression check between locked baseline and latest symbol C packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASELINE = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_packet_baseline_latest.json"
DEFAULT_PACKET = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_packet_latest.json"
DEFAULT_REGRESSION = (
    ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_packet_regression_template.json"
)


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _resolve_regression_thresholds(
    template_path: Path | None,
    max_stable_task_drop: int,
    max_exploratory_task_drop: int,
    max_overlap_rate_drop: float,
) -> tuple[int, int, float]:
    if template_path is None:
        return max_stable_task_drop, max_exploratory_task_drop, max_overlap_rate_drop
    if not template_path.is_file():
        print(f"ERROR: missing regression template: {template_path}")
        raise SystemExit(2)
    template = _jread(template_path)
    t_stable = template.get("max_stable_task_drop", max_stable_task_drop)
    t_expl = template.get("max_exploratory_task_drop", max_exploratory_task_drop)
    t_overlap = template.get("max_overlap_rate_drop", max_overlap_rate_drop)
    return int(t_stable), int(t_expl), float(t_overlap)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check regression for symbol C validation packet snapshot")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--packet-json", default=str(DEFAULT_PACKET))
    ap.add_argument("--regression-template", default=str(DEFAULT_REGRESSION))
    ap.add_argument("--max-stable-task-drop", type=int, default=5)
    ap.add_argument("--max-exploratory-task-drop", type=int, default=5)
    ap.add_argument("--max-overlap-rate-drop", type=float, default=0.2)
    args = ap.parse_args()

    baseline_path = _abs(args.baseline)
    packet_path = _abs(args.packet_json)
    template_path = _abs(args.regression_template) if args.regression_template else None
    max_stable_drop, max_expl_drop, max_overlap_drop = _resolve_regression_thresholds(
        template_path,
        args.max_stable_task_drop,
        args.max_exploratory_task_drop,
        args.max_overlap_rate_drop,
    )
    if not baseline_path.is_file():
        print(f"ERROR: missing baseline: {baseline_path}")
        return 2
    if not packet_path.is_file():
        print(f"ERROR: missing packet: {packet_path}")
        return 2

    baseline = _jread(baseline_path).get("snapshot", {})
    current = _jread(packet_path).get("snapshot", {})
    if not isinstance(baseline, dict) or not isinstance(current, dict):
        print("ERROR: invalid snapshot format")
        return 2

    b_stable = _as_float(baseline.get("stable_task_count"))
    b_expl = _as_float(baseline.get("exploratory_task_count"))
    b_overlap = _as_float(baseline.get("top_overlap_rate"))

    c_stable = _as_float(current.get("stable_task_count"))
    c_expl = _as_float(current.get("exploratory_task_count"))
    c_overlap = _as_float(current.get("top_overlap_rate"))

    failures: list[str] = []
    if b_stable is None or c_stable is None:
        failures.append("stable_task_count missing in baseline/current")
    elif (b_stable - c_stable) > float(max_stable_drop):
        failures.append(
            f"stable_task_count dropped too much: baseline={b_stable} current={c_stable} "
            f"max_drop={max_stable_drop}"
        )

    if b_expl is None or c_expl is None:
        failures.append("exploratory_task_count missing in baseline/current")
    elif (b_expl - c_expl) > float(max_expl_drop):
        failures.append(
            f"exploratory_task_count dropped too much: baseline={b_expl} current={c_expl} "
            f"max_drop={max_expl_drop}"
        )

    if b_overlap is None or c_overlap is None:
        failures.append("top_overlap_rate missing in baseline/current")
    elif (b_overlap - c_overlap) > float(max_overlap_drop):
        failures.append(
            f"top_overlap_rate dropped too much: baseline={b_overlap} current={c_overlap} "
            f"max_drop={max_overlap_drop}"
        )

    print("Symbol C validation packet regression check")
    print(f"- stable_task_count: baseline={b_stable} current={c_stable}")
    print(f"- exploratory_task_count: baseline={b_expl} current={c_expl}")
    print(f"- top_overlap_rate: baseline={b_overlap} current={c_overlap}")
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
