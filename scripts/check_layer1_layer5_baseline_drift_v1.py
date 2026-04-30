#!/usr/bin/env python3
"""Check drift against locked Layer1/Layer5 governance baseline."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_baseline_lock_latest.json"
DEFAULT_L1 = ROOT / "docs" / "final" / "artifacts" / "layer1_router_benchmark_latest.json"
DEFAULT_L5 = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_INTEGRATED = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_integrated_gate_report_latest.json"
DEFAULT_READINESS = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_governance_readiness_latest.json"
DEFAULT_GOLDSET_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_summary_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_baseline_drift_check_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline-lock-json", type=Path, default=DEFAULT_LOCK)
    ap.add_argument("--layer1-json", type=Path, default=DEFAULT_L1)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--integrated-json", type=Path, default=DEFAULT_INTEGRATED)
    ap.add_argument("--readiness-json", type=Path, default=DEFAULT_READINESS)
    ap.add_argument("--goldset-summary-json", type=Path, default=DEFAULT_GOLDSET_SUMMARY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    lock = _read_json(args.baseline_lock_json)
    l1 = _read_json(args.layer1_json)
    l5 = _read_json(args.layer5_json)
    integrated = _read_json(args.integrated_json)
    readiness = _read_json(args.readiness_json)
    goldset = _read_json(args.goldset_summary_json)

    baseline = lock.get("baseline") if isinstance(lock.get("baseline"), dict) else {}
    reasons: list[str] = []

    approved_count_min = int(baseline.get("approved_count_min") or 0)
    integrated_required = str(baseline.get("integrated_decision_required") or "GO_CONTROLLED")
    readiness_required = str(baseline.get("readiness_required") or "READY")
    l1_acc_min = _num(baseline.get("layer1_accuracy_min"), 0.0)
    l5_recall_min = _num(baseline.get("layer5_recall_min"), 0.0)
    l5_fpr_max = _num(baseline.get("layer5_fpr_max"), 1.0)

    approved_count_now = int(goldset.get("approved_count") or 0)
    integrated_now = str(integrated.get("decision") or "UNKNOWN")
    readiness_now = str(readiness.get("status") or "UNKNOWN")
    l1_acc_now = _num((l1.get("metrics") or {}).get("accuracy"), 0.0)
    l5_recall_now = _num((l5.get("metrics") or {}).get("recall_block"), 0.0)
    l5_fpr_now = _num((l5.get("metrics") or {}).get("false_positive_rate"), 1.0)

    if approved_count_now < approved_count_min:
        reasons.append("approved_count_below_baseline")
    if integrated_now != integrated_required:
        reasons.append("integrated_decision_drift")
    if readiness_now != readiness_required:
        reasons.append("readiness_status_drift")
    if l1_acc_now < l1_acc_min:
        reasons.append("layer1_accuracy_drift")
    if l5_recall_now < l5_recall_min:
        reasons.append("layer5_recall_drift")
    if l5_fpr_now > l5_fpr_max:
        reasons.append("layer5_fpr_drift")

    status = "PASS" if not reasons else "HOLD_BASELINE_DRIFT"
    out = {
        "schema": "layer1_layer5_baseline_drift_check_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "baseline_lock_json": str(args.baseline_lock_json).replace("\\", "/"),
            "layer1_json": str(args.layer1_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
            "integrated_json": str(args.integrated_json).replace("\\", "/"),
            "readiness_json": str(args.readiness_json).replace("\\", "/"),
            "goldset_summary_json": str(args.goldset_summary_json).replace("\\", "/"),
        },
        "baseline": {
            "approved_count_min": approved_count_min,
            "integrated_decision_required": integrated_required,
            "readiness_required": readiness_required,
            "layer1_accuracy_min": l1_acc_min,
            "layer5_recall_min": l5_recall_min,
            "layer5_fpr_max": l5_fpr_max,
        },
        "current": {
            "approved_count": approved_count_now,
            "integrated_decision": integrated_now,
            "readiness_status": readiness_now,
            "layer1_accuracy": l1_acc_now,
            "layer5_recall": l5_recall_now,
            "layer5_fpr": l5_fpr_now,
        },
        "status": status,
        "reasons": reasons,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "status": status, "output_json": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
