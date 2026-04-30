#!/usr/bin/env python3
"""Build baseline lock artifact from latest Layer1/Layer5 governance artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_L1 = ROOT / "docs" / "final" / "artifacts" / "layer1_router_benchmark_latest.json"
DEFAULT_L5 = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_INTEGRATED = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_integrated_gate_report_latest.json"
DEFAULT_READINESS = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_governance_readiness_latest.json"
DEFAULT_GOLDSET_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_summary_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_baseline_lock_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _num(value: Any, default: float) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer1-json", type=Path, default=DEFAULT_L1)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_L5)
    ap.add_argument("--integrated-json", type=Path, default=DEFAULT_INTEGRATED)
    ap.add_argument("--readiness-json", type=Path, default=DEFAULT_READINESS)
    ap.add_argument("--goldset-summary-json", type=Path, default=DEFAULT_GOLDSET_SUMMARY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    l1 = _read_json(args.layer1_json)
    l5 = _read_json(args.layer5_json)
    integrated = _read_json(args.integrated_json)
    readiness = _read_json(args.readiness_json)
    goldset = _read_json(args.goldset_summary_json)

    out = {
        "schema": "layer1_layer5_baseline_lock_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "layer1_json": str(args.layer1_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
            "integrated_json": str(args.integrated_json).replace("\\", "/"),
            "readiness_json": str(args.readiness_json).replace("\\", "/"),
            "goldset_summary_json": str(args.goldset_summary_json).replace("\\", "/"),
        },
        "baseline": {
            "approved_count_min": int(goldset.get("approved_count") or 0),
            "integrated_decision_required": str(integrated.get("decision") or "UNKNOWN"),
            "readiness_required": str(readiness.get("status") or "UNKNOWN"),
            "layer1_accuracy_min": _num((l1.get("metrics") or {}).get("accuracy"), 0.0),
            "layer5_recall_min": _num((l5.get("metrics") or {}).get("recall_block"), 0.0),
            "layer5_fpr_max": _num((l5.get("metrics") or {}).get("false_positive_rate"), 1.0),
        },
        "note": "Use this lock as the current governance baseline. Any drift should trigger hold/alert.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
