#!/usr/bin/env python3
"""Gate Phase 1A baseline comparison artifact [HYPO · HOLD]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
ART = ROOT / "reports/universal_root_phase1a_baseline_compare_v1_latest.json"
BUILDER = ROOT / "scripts/build_universal_root_phase1a_baseline_compare_v1.py"
OUT = ROOT / "reports/universal_root_phase1a_baseline_compare_gate_v1_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    if args.rebuild or not ART.is_file():
        proc = subprocess.run([PY, str(BUILDER)], cwd=str(ROOT), capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "error": "build_failed"}))
            return 1

    doc = json.loads(ART.read_text(encoding="utf-8-sig"))
    violations: list[str] = []
    if doc.get("schema") != "universal_root_phase1a_baseline_compare_v1":
        violations.append("schema_mismatch")
    if int(doc.get("pair_count") or 0) != 500:
        violations.append("pair_count_not_500")
    methods = {m.get("id"): m for m in doc.get("methods") or []}
    for mid in ("B0", "B1", "B2", "B3", "B4"):
        if mid not in methods:
            violations.append(f"missing_method_{mid}")
    b3 = methods.get("B3") or {}
    b4 = methods.get("B4") or {}
    if b4.get("forbidden_headline") is not True:
        violations.append("b4_forbidden_flag_missing")
    if b3.get("primary_value") is None:
        violations.append("b3_metric_missing")

    gate = {
        "schema": "universal_root_phase1a_baseline_compare_gate_v1",
        "artifact": str(ART.relative_to(ROOT)).replace("\\", "/"),
        "gate_ok": not violations,
        "violations": violations,
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": "py scripts/check_universal_root_phase1a_baseline_compare_v1.py --strict",
    }
    OUT.write_text(json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": gate["gate_ok"], "violations": violations, "out": str(OUT)}))
    if args.strict and violations:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
