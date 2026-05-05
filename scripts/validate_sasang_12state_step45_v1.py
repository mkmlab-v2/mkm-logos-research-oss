#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEP4 = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_baseline_comparison_step4_latest.json"
STEP5 = ROOT / "docs" / "final" / "artifacts" / "sasang_12state_promotion_decision_step5_latest.json"


def _validate_step4(p: Path) -> int:
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_12state_baseline_comparison_step4_v1":
        return 2
    lanes = doc.get("lane_results")
    if not isinstance(lanes, list) or not lanes:
        return 3
    return 0


def _validate_step5(p: Path) -> int:
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != "sasang_12state_promotion_decision_step5_v1":
        return 4
    if "decision" not in doc or "checks" not in doc:
        return 5
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate step4/step5 artifacts.")
    ap.add_argument("--step4-json", type=Path, default=STEP4)
    ap.add_argument("--step5-json", type=Path, default=STEP5)
    args = ap.parse_args()
    if not args.step4_json.is_file() or not args.step5_json.is_file():
        print("missing step4/step5 artifacts")
        return 1
    c4 = _validate_step4(args.step4_json)
    if c4:
        print("invalid step4")
        return c4
    c5 = _validate_step5(args.step5_json)
    if c5:
        print("invalid step5")
        return c5
    print("ok sasang_12state_step45_v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
