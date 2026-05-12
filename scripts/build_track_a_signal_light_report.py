#!/usr/bin/env python3
"""Combine Track A metering + cost sim snapshots into a signal-light report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(p: Path) -> dict | None:
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Directory containing track_a_*_latest.json inputs (default: docs/final/artifacts under workspace)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
    )
    args = ap.parse_args()
    root: Path = args.workspace_root.resolve()
    art = (args.artifacts_dir or (root / "docs/final/artifacts")).resolve()
    out = (args.out or art / "track_a_signal_light_report_latest.json").resolve()

    weekly = _read(art / "track_a_metering_weekly_report_latest.json")
    gate = _read(art / "track_a_metering_band_gate_latest.json")
    cost = _read(art / "track_a_conversational_cost_simulation_latest.json")

    color = "green"
    if gate and str(gate.get("decision") or "").lower() == "warning":
        color = "yellow"
    if gate and str(gate.get("decision") or "").lower() == "block":
        color = "red"
    if cost and str(cost.get("gate_decision") or "").upper() != "GO":
        color = "yellow" if color == "green" else color

    payload = {
        "schema": "track_a_signal_light_report_v1",
        "generated_at_utc": _utc(),
        "signal_light": {"status": color.upper()},
        "inputs": {
            "weekly": str(art / "track_a_metering_weekly_report_latest.json").replace("\\", "/"),
            "band_gate": str(art / "track_a_metering_band_gate_latest.json").replace("\\", "/"),
            "cost_sim": str(art / "track_a_conversational_cost_simulation_latest.json").replace("\\", "/"),
        },
        "snapshots_present": {
            "weekly": weekly is not None,
            "band_gate": gate is not None,
            "cost_sim": cost is not None,
        },
        "weekly_target_band_hit_rate": (weekly or {}).get("target_band_hit_rate"),
        "band_gate_decision": (gate or {}).get("decision") or (gate or {}).get("status"),
        "cost_gate_decision": (cost or {}).get("gate_decision"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
