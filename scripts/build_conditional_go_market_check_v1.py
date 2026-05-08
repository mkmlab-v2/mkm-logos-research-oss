#!/usr/bin/env python3
"""Build Conditional GO market activation check artifact."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "final" / "artifacts" / "conditional_go_market_inputs_latest.json"
DEFAULT_OUTPUT = ROOT / "docs" / "final" / "artifacts" / "conditional_go_market_check_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        low = value.strip().lower()
        if low in {"true", "1", "yes", "y"}:
            return True
        if low in {"false", "0", "no", "n"}:
            return False
    return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--min-confidence", type=float, default=0.62)
    args = ap.parse_args()

    input_path = args.input_json if args.input_json.is_absolute() else ROOT / args.input_json
    output_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    doc = _read_json_optional(input_path)

    checks = doc.get("checks") if isinstance(doc.get("checks"), dict) else {}
    foreign_flow_turn = _as_bool(checks.get("foreign_flow_turn"), False)
    kospi_structure_hold = _as_bool(checks.get("kospi_structure_hold"), False)
    semi_leader_recovery = _as_bool(checks.get("semi_leader_recovery"), False)
    confidence = max(0.0, min(1.0, _as_float(doc.get("confidence_0_1"), 0.0)))
    all_conditions_met = bool(foreign_flow_turn and kospi_structure_hold and semi_leader_recovery)
    armed = bool(all_conditions_met and confidence >= args.min_confidence)

    payload = {
        "schema": "conditional_go_market_check_v1",
        "generated_at_utc": _now(),
        "input_json": str(input_path),
        "activation": {
            "all_conditions_met": all_conditions_met,
            "confidence_0_1": round(confidence, 6),
            "min_confidence_0_1": round(max(0.0, min(1.0, args.min_confidence)), 6),
            "armed": armed,
        },
        "checks": {
            "foreign_flow_turn": foreign_flow_turn,
            "kospi_structure_hold": kospi_structure_hold,
            "semi_leader_recovery": semi_leader_recovery,
        },
        "note": "Defaults to non-armed when input file or checks are missing.",
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(output_path), "armed": armed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
