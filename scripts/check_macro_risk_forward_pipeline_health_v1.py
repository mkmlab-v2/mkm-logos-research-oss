#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASHBOARD = ROOT / "docs" / "final" / "artifacts" / "mkm_trackc_ops_dashboard_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "macro_risk_forward_pipeline_health_gate_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return doc


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check forward pipeline health status from Track C ops dashboard.")
    p.add_argument("--dashboard-json", type=Path, default=DEFAULT_DASHBOARD)
    p.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dashboard_path = args.dashboard_json if args.dashboard_json.is_absolute() else (ROOT / args.dashboard_json)
    output_path = args.output_json if args.output_json.is_absolute() else (ROOT / args.output_json)

    dashboard = _read_json(dashboard_path)
    trackc = dashboard.get("trackc") or {}
    health = trackc.get("forward_pipeline_health") or {}

    status = str(health.get("status") or "UNKNOWN").upper()
    passed = bool(health.get("passed") is True and status == "PASS")
    reasons = health.get("reason_codes") or []
    if not isinstance(reasons, list):
        reasons = ["invalid_reason_codes_type"]

    report = {
        "schema": "macro_risk_forward_pipeline_health_gate_v1",
        "passed": passed,
        "status": "PASS" if passed else "FAIL",
        "dashboard_json": str(dashboard_path),
        "forward_pipeline_health": health,
        "reason_codes": reasons if not passed else [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if passed:
        print(f"forward_pipeline_health_gate: PASS -> {output_path}")
        return 0

    print(f"forward_pipeline_health_gate: FAIL -> {output_path}")
    print(f"reason_codes: {reasons}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

