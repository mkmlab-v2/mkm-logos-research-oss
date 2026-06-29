#!/usr/bin/env python3
"""Validate Han Vocology graduation gate report (B-track · M21)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "reports/han_vocology_graduation_gate_v1_latest.json"
OUT = ROOT / "reports/han_vocology_graduation_gate_validation_v1_latest.json"

EXPECTED_DIMS = {
    "volume_gap_350": 20,
    "osce_55": 30,
    "cb_coverage": 25,
    "policy_spot": 15,
    "ethics_hold": 10,
}


def validate(doc: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"name": "schema", "ok": doc.get("schema") == "han_vocology_graduation_gate_v1"})
    checks.append({"name": "track_b", "ok": doc.get("track") == "B"})
    checks.append({"name": "send_gate_hold", "ok": doc.get("send_gate") == "HOLD"})

    dims = doc.get("dimensions") or []
    dim_ids = {str(d.get("id")) for d in dims}
    checks.append({"name": "dimension_ids", "ok": dim_ids == set(EXPECTED_DIMS)})

    max_sum = sum(int(d.get("max_points") or 0) for d in dims)
    checks.append({"name": "max_sum_100", "ok": max_sum == 100})

    earned = sum(int(d.get("earned") or 0) for d in dims)
    checks.append({"name": "total_earned_match", "ok": earned == int(doc.get("total_earned") or -1)})

    pass_min = int(doc.get("pass_min_points") or 70)
    passed = bool(doc.get("passed"))
    checks.append({"name": "pass_logic", "ok": passed == (earned >= pass_min)})

    for dim in dims:
        dim_id = str(dim.get("id"))
        max_pts = EXPECTED_DIMS.get(dim_id, 0)
        earned_pts = int(dim.get("earned") or 0)
        checks.append(
            {
                "name": f"earned_within_max_{dim_id}",
                "ok": 0 <= earned_pts <= max_pts,
            }
        )

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "total_earned": earned, "passed": passed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gate", type=Path, default=DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.gate.is_file():
        print(json.dumps({"ok": False, "error": "gate_missing"}, ensure_ascii=False))
        return 1

    doc = json.loads(args.gate.read_text(encoding="utf-8"))
    result = validate(doc)
    result["gate"] = str(args.gate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "passed": result.get("passed"), "out": str(args.out)}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
