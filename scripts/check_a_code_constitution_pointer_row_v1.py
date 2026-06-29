#!/usr/bin/env python3
"""Verify CONSTITUTION §1.2.2 A-code operator-assist pointer row is present."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONSTITUTION = ROOT / "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
DEFAULT_OUT = ROOT / "reports/a_code_constitution_pointer_row_check_v1_latest.json"

REQUIRED_MARKERS = [
    "### 1.2.2 A-code 12AI governor operator-assist",
    "Run-ACodeOperatorAssistLaneRoutine_v1.ps1",
    "a_code_operator_assist_lane_v1_latest.json",
    "research_only",
    "Track A/live 승격 **아님**",
]


def evaluate(constitution_text: str) -> dict:
    checks = {marker: marker in constitution_text for marker in REQUIRED_MARKERS}
    pass_count = sum(1 for ok in checks.values() if ok)
    total = len(checks)
    decision = "PASS_POINTER_ROW" if all(checks.values()) else "HOLD_MISSING_ROW"
    return {
        "schema": "a_code_constitution_pointer_row_check_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "constitution_section": "1.2.2",
        "summary": {
            "decision": decision,
            "pass_count": pass_count,
            "total": total,
        },
        "checks": checks,
        "track_wall": {
            "constitution_body_auto_edit": False,
            "track_a_auto_promotion": False,
        },
        "source": str(DEFAULT_CONSTITUTION.relative_to(ROOT)).replace("\\", "/"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--constitution", type=Path, default=DEFAULT_CONSTITUTION)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if not args.constitution.is_file():
        raise SystemExit(f"missing constitution: {args.constitution}")

    report = evaluate(args.constitution.read_text(encoding="utf-8"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"OK: {args.out} decision={report['summary']['decision']} "
        f"{report['summary']['pass_count']}/{report['summary']['total']}"
    )
    if args.strict and report["summary"]["decision"] != "PASS_POINTER_ROW":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
