# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.9, K:0.4, M:0.7}
# Balance: 91
# Purpose: Produce PASS/HOLD readiness gate for high-reliability answer mode.
# Keywords: reliability, gate, pass, hold, entry16, btrack
#!/usr/bin/env python3
"""Evaluate high-reliability readiness from locked artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUALITY = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_quality_anchor_verified_only_latest.json"
DEFAULT_GATE = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_promotion_gate_anchor_verified_only_latest.json"
DEFAULT_ENTRY16_GATE = ROOT / "docs" / "final" / "artifacts" / "entry16_promotion_gate.json"
DEFAULT_ENTRY16_LOCK = ROOT / "docs" / "final" / "artifacts" / "entry16_manual_promotion_decision_lock_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "high_reliability_mode_gate_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate high-reliability operation gate")
    ap.add_argument("--quality", default=str(DEFAULT_QUALITY))
    ap.add_argument("--btrack-gate", default=str(DEFAULT_GATE))
    ap.add_argument("--entry16-gate", default=str(DEFAULT_ENTRY16_GATE))
    ap.add_argument("--entry16-lock", default=str(DEFAULT_ENTRY16_LOCK))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--repro-min", type=float, default=0.9)
    args = ap.parse_args()

    quality_path = _abs(args.quality)
    btrack_gate_path = _abs(args.btrack_gate)
    entry16_gate_path = _abs(args.entry16_gate)
    entry16_lock_path = _abs(args.entry16_lock)
    out_path = _abs(args.out)

    for p in (quality_path, btrack_gate_path, entry16_gate_path, entry16_lock_path):
        if not p.is_file():
            print(f"ERROR: missing required file: {p}")
            return 2

    quality = _jread(quality_path)
    btrack_gate = _jread(btrack_gate_path)
    entry16_gate = _jread(entry16_gate_path)
    entry16_lock = _jread(entry16_lock_path)

    q_metrics = quality.get("metrics", {})
    reproducibility = _f(q_metrics.get("reproducibility_match_rate"))
    resolution = _f(q_metrics.get("resolution_confidence_delta_b_minus_a"))
    contamination = _f(q_metrics.get("contamination_snr_delta_b_minus_a"))

    checks = {
        "btrack_gate_pass": str(btrack_gate.get("decision", "")).lower() == "pass",
        "reproducibility_gte_threshold": reproducibility is not None and reproducibility >= args.repro_min,
        "resolution_non_negative": resolution is not None and resolution >= 0.0,
        "contamination_non_negative": contamination is not None and contamination >= 0.0,
        "entry16_candidate_ready": str(entry16_gate.get("decision", "")) == "promote_candidate"
        and str(entry16_gate.get("status", "")) == "candidate_ready_for_manual_review",
        "entry16_lock_approved": str(entry16_lock.get("final_decision", "")) == "approved",
        "entry16_dss_fact_lock_kept": bool(entry16_lock.get("constraints", {}).get("dss_missing_anchor_fact_lock", False)),
    }

    decision = "PASS" if all(checks.values()) else "HOLD"
    report = {
        "schema": "high_reliability_mode_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "quality_report": str(quality_path),
            "btrack_gate_report": str(btrack_gate_path),
            "entry16_gate_report": str(entry16_gate_path),
            "entry16_decision_lock": str(entry16_lock_path),
        },
        "thresholds": {
            "reproducibility_min": args.repro_min,
            "resolution_min": 0.0,
            "contamination_min": 0.0,
        },
        "metrics_snapshot": {
            "reproducibility_match_rate": reproducibility,
            "resolution_confidence_delta_b_minus_a": resolution,
            "contamination_snr_delta_b_minus_a": contamination,
        },
        "checks": checks,
        "decision": decision,
        "operational_mode": (
            "high_reliability_enabled_with_fact_lock"
            if decision == "PASS"
            else "high_reliability_hold"
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: high reliability mode gate generated")
    print(f"out={out_path}")
    print(f"decision={decision}")
    return 0 if decision == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
