#!/usr/bin/env python3
"""Build integrated go/no-go report from Layer1+Layer5 benchmark artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYER1 = ROOT / "docs" / "final" / "artifacts" / "layer1_router_benchmark_latest.json"
DEFAULT_LAYER5 = ROOT / "docs" / "final" / "artifacts" / "layer5_policy_gate_benchmark_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "layer1_layer5_integrated_gate_report_latest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--layer1-json", type=Path, default=DEFAULT_LAYER1)
    ap.add_argument("--layer5-json", type=Path, default=DEFAULT_LAYER5)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-approved-samples", type=int, default=50)
    args = ap.parse_args()

    l1 = _read_json(args.layer1_json)
    l5 = _read_json(args.layer5_json)

    l1_status = str(l1.get("benchmark_status", "HOLD"))
    l5_status = str(l5.get("benchmark_status", "HOLD"))
    l1_labeled = int((l1.get("metrics") or {}).get("labeled_count") or 0)
    l5_labeled = int((l5.get("metrics") or {}).get("labeled_count") or 0)
    approved_count = min(l1_labeled, l5_labeled)
    data_sufficient = approved_count >= int(args.min_approved_samples)

    reasons: list[str] = []
    if l1_status != "PASS":
        reasons.append("layer1_not_pass")
    if l5_status != "PASS":
        reasons.append("layer5_not_pass")
    if not data_sufficient:
        reasons.append("insufficient_approved_samples")

    if not data_sufficient:
        decision = "HOLD_DATA_INSUFFICIENT"
    elif l1_status == "PASS" and l5_status == "PASS":
        decision = "GO_CONTROLLED"
    else:
        decision = "HOLD_GATE_FAIL"

    out = {
        "schema": "layer1_layer5_integrated_gate_report_v1",
        "generated_at_utc": _iso_now(),
        "inputs": {
            "layer1_json": str(args.layer1_json).replace("\\", "/"),
            "layer5_json": str(args.layer5_json).replace("\\", "/"),
        },
        "thresholds": {
            "min_approved_samples": int(args.min_approved_samples),
        },
        "benchmarks": {
            "layer1_status": l1_status,
            "layer1_labeled_count": l1_labeled,
            "layer5_status": l5_status,
            "layer5_labeled_count": l5_labeled,
        },
        "data_gate": {
            "approved_sample_count_proxy": approved_count,
            "data_sufficient": data_sufficient,
        },
        "decision": decision,
        "reasons": reasons,
        "note": "GO is allowed only when Layer1 and Layer5 pass and approved sample count is sufficient.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "decision": decision}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
