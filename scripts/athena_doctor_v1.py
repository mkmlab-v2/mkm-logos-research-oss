#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight execution-governance pre-flight (Fact-Lock).

Prints integrated_governance regime summary and latest ECC status if present.
Does not replace full health bundles (`run_workspace_automation_health.ps1`, etc.).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOV = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "integrated_governance_v1_latest.json"
DEFAULT_ECC = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "ecc_execution_clearance_latest.json"


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Athena doctor v1 — governance + ECC snapshot.")
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOV)
    ap.add_argument("--ecc-json", type=Path, default=DEFAULT_ECC)
    args = ap.parse_args()

    gov = _load(args.governance_json)
    if not gov:
        print(f"athena_doctor_v1: missing or invalid governance: {args.governance_json}", file=sys.stderr)
        return 1
    if str(gov.get("schema") or "") != "integrated_governance_v1":
        print("athena_doctor_v1: governance schema must be integrated_governance_v1", file=sys.stderr)
        return 1

    regime = gov.get("final_regime")
    allowed = gov.get("final_action_allowed")
    veto = gov.get("veto_reason_codes") or []
    print("=== athena_doctor_v1 ===")
    print(f"governance: {args.governance_json}")
    print(f"  final_regime: {regime}")
    print(f"  final_action_allowed: {allowed}")
    print(f"  veto_reason_codes: {veto}")

    ecc = _load(args.ecc_json)
    if ecc:
        print(f"ecc (latest): {args.ecc_json}")
        print(f"  status: {ecc.get('status')}")
        print(f"  reason: {ecc.get('reason')}")
        print(f"  action: {ecc.get('action')}")
        print(f"  generated_at_utc: {ecc.get('generated_at_utc')}")
    else:
        print(f"ecc: (none or unreadable) — {args.ecc_json}")

    print("hint: DENIED explanation uses ECC reason + governance veto_reason_codes; CONSTITUTION §28.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
