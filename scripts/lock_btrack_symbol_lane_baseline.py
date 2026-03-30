#!/usr/bin/env python3
"""Lock B-Track symbol lane gate outputs as baseline artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LANE_GATE = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_gate_latest.json"
LANE_SUMMARY = ROOT / "reports" / "constitution" / "btrack_pilot" / "symbol_lane_summary_latest.json"
GATE_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_lane_gate_template.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_symbol_lane_baseline_lock_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    v = metrics.get(metric)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Lock B-Track symbol lane baseline")
    ap.add_argument("--lane-gate", default=str(LANE_GATE))
    ap.add_argument("--lane-summary", default=str(LANE_SUMMARY))
    ap.add_argument("--gate-template", default=str(GATE_TEMPLATE))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    lane_gate = _abs(args.lane_gate)
    lane_summary = _abs(args.lane_summary)
    gate_template = _abs(args.gate_template)
    out = _abs(args.out)
    for p in (lane_gate, lane_summary, gate_template):
        if not p.is_file():
            print(f"ERROR: missing required file: {p}")
            return 2

    gate = _jread(lane_gate)
    lock = {
        "schema": "btrack_symbol_lane_baseline_lock_v1",
        "locked_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "lane_gate": str(lane_gate),
            "lane_summary": str(lane_summary),
            "gate_template": str(gate_template),
        },
        "input_hashes": {
            "lane_gate_sha256": _sha256(lane_gate),
            "lane_summary_sha256": _sha256(lane_summary),
            "gate_template_sha256": _sha256(gate_template),
        },
        "baseline_decision": gate.get("decision"),
        "baseline_lane_metrics": {
            "dss_priority": {
                "count": _lane_metric(gate, "dss_priority", "count"),
                "avg_score_tfidf_like": _lane_metric(gate, "dss_priority", "avg_score_tfidf_like"),
                "avg_dss_ratio": _lane_metric(gate, "dss_priority", "avg_dss_ratio"),
            },
            "mixed": {
                "count": _lane_metric(gate, "mixed", "count"),
                "avg_score_tfidf_like": _lane_metric(gate, "mixed", "avg_score_tfidf_like"),
                "avg_dss_ratio": _lane_metric(gate, "mixed", "avg_dss_ratio"),
            },
            "apocrypha_priority": {
                "count": _lane_metric(gate, "apocrypha_priority", "count"),
                "avg_score_tfidf_like": _lane_metric(gate, "apocrypha_priority", "avg_score_tfidf_like"),
                "avg_dss_ratio": _lane_metric(gate, "apocrypha_priority", "avg_dss_ratio"),
            },
        },
        "regression_policy": {
            "require_decision": "pass",
            "require_lane_decision": "pass",
            "dss_priority_count_min": 3,
            "mixed_count_min": 4,
            "apocrypha_count_min": 10,
            "dss_priority_avg_dss_ratio_min": 0.02,
            "mixed_avg_dss_ratio_min": 0.01,
        },
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: symbol lane baseline locked")
    print(f"out={out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
