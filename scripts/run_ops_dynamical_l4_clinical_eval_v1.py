#!/usr/bin/env python3
"""Ops dynamical L4 — clinical cohort ε on registered endpoints [HYPO · Track B · HOLD]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    L4_COHORT_GATE_PATH,
    L4_L3_PREREQ_PATH,
    eval_l4_clinical_cohort,
    load_l4_inputs,
)

OUT = ROOT / "reports/ops_dynamical_l4_eval_v1_latest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate ops dynamical L4 clinical cohort epsilon")
    parser.add_argument("--cohort-gate", type=Path, default=L4_COHORT_GATE_PATH)
    parser.add_argument("--l3-prereq", type=Path, default=L4_L3_PREREQ_PATH)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    missing: list[dict] = []
    if not args.cohort_gate.is_file():
        missing.append({"artifact": "cohort_gate", "path": str(args.cohort_gate).replace("\\", "/")})
    if not args.l3_prereq.is_file():
        missing.append({"artifact": "l3_prereq", "path": str(args.l3_prereq).replace("\\", "/")})

    gate_doc, l3_doc, profiles = load_l4_inputs(
        cohort_gate_path=args.cohort_gate,
        l3_prereq_path=args.l3_prereq,
    )
    doc = eval_l4_clinical_cohort(
        gate_doc=gate_doc,
        l3_doc=l3_doc,
        profiles=profiles,
        missing=missing,
    )
    doc["cohort_gate"]["path"] = str(args.cohort_gate).replace("\\", "/")
    doc["l3_prerequisite"]["path"] = str(args.l3_prereq).replace("\\", "/")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["ok"],
                "out": str(args.out),
                "clinical_epsilon_score": doc["metrics"]["clinical_epsilon_score"],
                "checks_pass_count": doc["checks_pass_count"],
            }
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
