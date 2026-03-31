#!/usr/bin/env python3
"""Compare latest symbol lane gate outputs against locked baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_symbol_lane_baseline_lock_stable_latest.json"
LANE_GATE = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_gate_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _lane_decision(gate: dict[str, Any], lane: str) -> str:
    lanes = gate.get("lanes", {})
    if not isinstance(lanes, dict):
        return ""
    payload = lanes.get(lane, {})
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("decision", ""))


def _lane_metric(gate: dict[str, Any], lane: str, metric: str) -> float | None:
    lanes = gate.get("lanes", {})
    if not isinstance(lanes, dict):
        return None
    payload = lanes.get(lane, {})
    if not isinstance(payload, dict):
        return None
    metrics = payload.get("metrics", {})
    if not isinstance(metrics, dict):
        return None
    return _as_float(metrics.get(metric))


def main() -> int:
    ap = argparse.ArgumentParser(description="Check symbol lane regression against baseline")
    ap.add_argument("--baseline", default=str(BASELINE))
    ap.add_argument("--lane-gate", default=str(LANE_GATE))
    args = ap.parse_args()

    baseline_path = _abs(args.baseline)
    lane_gate_path = _abs(args.lane_gate)
    for p in (baseline_path, lane_gate_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    baseline = _jread(baseline_path)
    gate = _jread(lane_gate_path)
    policy = baseline.get("regression_policy", {})

    failures: list[str] = []
    required_decision = str(policy.get("require_decision", "pass"))
    required_lane_decision = str(policy.get("require_lane_decision", "pass"))

    decision = str(gate.get("decision", ""))
    if decision != required_decision:
        failures.append(f"overall decision mismatch: current={decision} required={required_decision}")

    for lane in ("dss_priority", "mixed", "apocrypha_priority"):
        lane_decision = _lane_decision(gate, lane)
        if lane_decision != required_lane_decision:
            failures.append(f"{lane} decision mismatch: current={lane_decision} required={required_lane_decision}")

    dss_count = _lane_metric(gate, "dss_priority", "count")
    mixed_count = _lane_metric(gate, "mixed", "count")
    apo_count = _lane_metric(gate, "apocrypha_priority", "count")
    dss_ratio = _lane_metric(gate, "dss_priority", "avg_dss_ratio")
    mixed_ratio = _lane_metric(gate, "mixed", "avg_dss_ratio")

    dss_count_min = _as_float(policy.get("dss_priority_count_min"))
    mixed_count_min = _as_float(policy.get("mixed_count_min"))
    apo_count_min = _as_float(policy.get("apocrypha_count_min"))
    dss_ratio_min = _as_float(policy.get("dss_priority_avg_dss_ratio_min"))
    mixed_ratio_min = _as_float(policy.get("mixed_avg_dss_ratio_min"))

    if dss_count_min is not None and (dss_count is None or dss_count < dss_count_min):
        failures.append(f"dss_priority.count below min: current={dss_count} min={dss_count_min}")
    if mixed_count_min is not None and (mixed_count is None or mixed_count < mixed_count_min):
        failures.append(f"mixed.count below min: current={mixed_count} min={mixed_count_min}")
    if apo_count_min is not None and (apo_count is None or apo_count < apo_count_min):
        failures.append(f"apocrypha_priority.count below min: current={apo_count} min={apo_count_min}")
    if dss_ratio_min is not None and (dss_ratio is None or dss_ratio < dss_ratio_min):
        failures.append(f"dss_priority.avg_dss_ratio below min: current={dss_ratio} min={dss_ratio_min}")
    if mixed_ratio_min is not None and (mixed_ratio is None or mixed_ratio < mixed_ratio_min):
        failures.append(f"mixed.avg_dss_ratio below min: current={mixed_ratio} min={mixed_ratio_min}")

    print("B-Track symbol lane regression check")
    print(f"- decision: {decision}")
    print(f"- dss_priority.count: {dss_count} avg_dss_ratio: {dss_ratio}")
    print(f"- mixed.count: {mixed_count} avg_dss_ratio: {mixed_ratio}")
    print(f"- apocrypha_priority.count: {apo_count}")
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
