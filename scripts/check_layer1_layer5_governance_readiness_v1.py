#!/usr/bin/env python3
"""Check governance readiness from integrated Layer1/Layer5 artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTEGRATED = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_integrated_gate_report_latest.json"
DEFAULT_GOLDSET_SUMMARY = ROOT / "docs" / "final" / "artifacts" / "layer5_incident_goldset_human_summary_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_governance_readiness_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--integrated-json", type=Path, default=DEFAULT_INTEGRATED)
    ap.add_argument("--goldset-summary-json", type=Path, default=DEFAULT_GOLDSET_SUMMARY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--require-decision", type=str, default="GO_CONTROLLED")
    ap.add_argument("--min-approved-count", type=int, default=50)
    args = ap.parse_args()

    integrated = _read_json(args.integrated_json)
    goldset = _read_json(args.goldset_summary_json)

    decision = str(integrated.get("decision") or "UNKNOWN")
    approved_count = int(goldset.get("approved_count") or 0)
    source_mode = str(goldset.get("source_mode") or "unknown")
    reasons: list[str] = []

    if decision != args.require_decision:
        reasons.append("integrated_decision_not_required_state")
    if approved_count < int(args.min_approved_count):
        reasons.append("approved_count_below_threshold")
    if source_mode != "approved_only":
        reasons.append("goldset_not_approved_only")

    status = "READY" if not reasons else "HOLD"
    out = {
        "schema": "layer1_layer5_governance_readiness_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "integrated_json": str(args.integrated_json).replace("\\", "/"),
            "goldset_summary_json": str(args.goldset_summary_json).replace("\\", "/"),
        },
        "checks": {
            "decision": decision,
            "required_decision": args.require_decision,
            "approved_count": approved_count,
            "min_approved_count": int(args.min_approved_count),
            "goldset_source_mode": source_mode,
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
