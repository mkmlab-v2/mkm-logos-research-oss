#!/usr/bin/env python3
"""Gate-check for symbol C validation packet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PACKET = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_c_validation_packet_latest.json"
DEFAULT_GATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_c_validation_packet_gate_template.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(v: Any) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    return None


def _resolve_gate_thresholds(
    gate_path: Path | None,
    min_stable_tasks: int,
    min_exploratory_tasks: int,
    min_overlap_rate: float,
) -> tuple[int, int, float]:
    if gate_path is None:
        return min_stable_tasks, min_exploratory_tasks, min_overlap_rate
    if not gate_path.is_file():
        print(f"ERROR: missing gate template: {gate_path}")
        raise SystemExit(2)
    gate = _jread(gate_path)
    g_stable = gate.get("min_stable_tasks", min_stable_tasks)
    g_expl = gate.get("min_exploratory_tasks", min_exploratory_tasks)
    g_overlap = gate.get("min_overlap_rate", min_overlap_rate)
    return int(g_stable), int(g_expl), float(g_overlap)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check symbol C validation packet quality gates")
    ap.add_argument("--packet-json", default=str(DEFAULT_PACKET))
    ap.add_argument("--gate-template", default=str(DEFAULT_GATE))
    ap.add_argument("--min-stable-tasks", type=int, default=20)
    ap.add_argument("--min-exploratory-tasks", type=int, default=20)
    ap.add_argument("--min-overlap-rate", type=float, default=0.5)
    args = ap.parse_args()

    packet_path = _abs(args.packet_json)
    gate_path = _abs(args.gate_template) if args.gate_template else None
    min_stable, min_expl, min_overlap = _resolve_gate_thresholds(
        gate_path,
        args.min_stable_tasks,
        args.min_exploratory_tasks,
        args.min_overlap_rate,
    )
    if not packet_path.is_file():
        print(f"ERROR: missing packet: {packet_path}")
        return 2

    packet = _jread(packet_path)
    snap = packet.get("snapshot", {})
    if not isinstance(snap, dict):
        print("ERROR: invalid packet snapshot")
        return 2

    stable_tasks = _as_float(snap.get("stable_task_count"))
    expl_tasks = _as_float(snap.get("exploratory_task_count"))
    overlap_rate = _as_float(snap.get("top_overlap_rate"))

    failures: list[str] = []
    if stable_tasks is None or stable_tasks < float(min_stable):
        failures.append(f"stable_task_count below min: current={stable_tasks} min={min_stable}")
    if expl_tasks is None or expl_tasks < float(min_expl):
        failures.append(f"exploratory_task_count below min: current={expl_tasks} min={min_expl}")
    if overlap_rate is None or overlap_rate < float(min_overlap):
        failures.append(f"top_overlap_rate below min: current={overlap_rate} min={min_overlap}")

    print("Symbol C validation packet check")
    print(f"- stable_task_count: {stable_tasks}")
    print(f"- exploratory_task_count: {expl_tasks}")
    print(f"- top_overlap_rate: {overlap_rate}")
    if failures:
        print("RESULT: FAIL")
        for f in failures:
            print(f"- {f}")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
