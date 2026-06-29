#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry B han clinic owner onboarding chain — infra gate preflight + card rebuild.

research_only · send_gate: HOLD · Track B local harness.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/han_clinic_owner_entry_b_onboarding_chain_v1_latest.json"
BRIEF = ROOT / "docs/final/artifacts/han_clinic_owner_onboarding_brief_v1_latest.md"
SAFE_FIXTURE = ROOT / "tests/fixtures/infra_compliance_gate_v1_safe.env"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = (proc.stdout or proc.stderr or "")[-500:]
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "tail": tail,
    }


def verify_brief_harness() -> dict[str, Any]:
    ok = BRIEF.is_file()
    reasons: list[str] = []
    if not ok:
        reasons.append(f"missing_brief:{BRIEF}")
    else:
        text = BRIEF.read_text(encoding="utf-8", errors="replace")
        for needle in ("cloud-ide.harness", "클라우드 IDE", "infra_compliance_gate_v1"):
            if needle not in text:
                ok = False
                reasons.append(f"missing_needle:{needle}")
    return {"name": "brief_harness", "exit_code": 0 if ok else 1, "reasons": reasons}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--scan-env",
        type=Path,
        help="Optional .env path to scan (never scans workspace .env by default)",
    )
    ap.add_argument("--skip-pytest", action="store_true")
    ap.add_argument("--skip-card", action="store_true")
    args = ap.parse_args()

    rows: list[dict[str, Any]] = []

    if not args.skip_pytest:
        rows.append(
            run_step(
                "pytest_infra_compliance",
                [sys.executable, "-m", "pytest", "tests/test_infra_compliance_gate_v1.py", "-q"],
            )
        )

    rows.append(
        run_step(
            "gate_safe_fixture",
            [sys.executable, "scripts/infra_compliance_gate_v1.py", str(SAFE_FIXTURE)],
        )
    )

    if args.scan_env:
        rows.append(
            run_step(
                "gate_scan_env",
                [sys.executable, "scripts/infra_compliance_gate_v1.py", str(args.scan_env)],
            )
        )

    brief_row = verify_brief_harness()
    rows.append(brief_row)

    if not args.skip_card:
        rows.append(
            run_step(
                "build_onboarding_card",
                [sys.executable, "scripts/build_han_clinic_owner_onboarding_card_v1.py"],
            )
        )

    ok = all(r.get("exit_code", 1) == 0 for r in rows if not r.get("skipped"))

    doc = {
        "schema": "han_clinic_owner_entry_b_onboarding_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "ok": ok,
        "steps": rows,
        "reproduce": "py scripts/run_han_clinic_owner_entry_b_onboarding_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "steps": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
