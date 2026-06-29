#!/usr/bin/env python3
"""Validate Han Vocology OSCE rubric SSOT (B-track · M20)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "docs/final/artifacts/han_vocology_osce_rubric_v1_latest.json"
OUT = ROOT / "reports/han_vocology_osce_rubric_validation_v1_latest.json"

ALLOWED_POLICIES = {"B1", "A1", "L1", "C1", "MDT"}
EXPECTED_CB = {
    "CB-06-A", "CB-08-A", "CB-10-A", "CB-09-A", "CB-11", "CB-12", "CB-13", "CB-16",
}


def validate(doc: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"name": "schema", "ok": doc.get("schema") == "han_vocology_osce_rubric_v1"})
    checks.append({"name": "track_b", "ok": doc.get("track") == "B"})
    checks.append({"name": "send_gate_hold", "ok": doc.get("send_gate") == "HOLD"})

    stations = doc.get("stations") or []
    checks.append({"name": "station_count_8", "ok": len(stations) == 8})
    checks.append({"name": "station_points_25_each", "ok": all(s.get("points") == 25 for s in stations)})

    cb_seen = {str(s.get("cb_id")) for s in stations}
    checks.append({"name": "cb_ids_expected", "ok": cb_seen == EXPECTED_CB})

    policies = {str(s.get("policy")) for s in stations}
    checks.append({"name": "policies_allowed", "ok": policies.issubset(ALLOWED_POLICIES)})

    dims = doc.get("station_dimensions") or []
    dim_sum = sum(int(d.get("max_points") or 0) for d in dims)
    checks.append({"name": "dimension_sum_100", "ok": dim_sum == 100})

    practice = doc.get("practice_rubric_100") or []
    practice_sum = sum(int(d.get("max_points") or 0) for d in practice)
    checks.append({"name": "practice_rubric_sum_100", "ok": practice_sum == 100})

    grad = doc.get("graduation_rubric_100") or []
    grad_sum = sum(int(d.get("max_points") or 0) for d in grad)
    checks.append({"name": "graduation_rubric_sum_100", "ok": grad_sum == 100})

    rules = doc.get("pass_rules") or {}
    total = sum(int(s.get("points") or 0) for s in stations)
    checks.append(
        {
            "name": "pass_rules_total",
            "ok": rules.get("station_pool_max_points") == total and rules.get("station_pool_min_points") == 160,
        }
    )

    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rubric", type=Path, default=DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.rubric.is_file():
        print(json.dumps({"ok": False, "error": "rubric_missing"}, ensure_ascii=False))
        return 1

    doc = json.loads(args.rubric.read_text(encoding="utf-8"))
    result = validate(doc)
    result["rubric"] = str(args.rubric)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
