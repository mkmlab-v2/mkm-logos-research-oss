#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clinician encounter accumulation chain (tier_0 · B-track · local ledger).

Steps:
  1. no1kmedi offline smokes (extract + envelope)
  2. optional append ledger row from fixture response
  3. optional patient registry rebuild

research_only · human_gold_required · send_gate HOLD
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
OUT = ROOT / "reports/clinician_encounter_accumulation_chain_v1_latest.json"
PY = sys.executable
NO1K = ROOT / "projects/no1kmedi"
FIXTURE_RESPONSE = NO1K / "scripts/fixtures/paste-chart-encounter-ledger-sample-v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str] | str, *, cwd: Path | None = None, shell: bool = False) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=shell,
    )
    return {
        "name": name,
        "cmd": cmd if isinstance(cmd, list) else [cmd],
        "exit_code": proc.returncode,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-offline-smoke", action="store_true")
    ap.add_argument("--skip-ledger-append", action="store_true")
    ap.add_argument("--skip-registry-rebuild", action="store_true")
    ap.add_argument("--fixture-json", type=Path, default=FIXTURE_RESPONSE)
    ap.add_argument("--output", type=Path, default=OUT)
    ns = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not ns.skip_offline_smoke:
        steps.append(
            _run(
                "paste_extract_smoke",
                "npx --yes tsx ./scripts/smoke-clinician-chart-paste-extract-v1.ts",
                cwd=NO1K,
                shell=True,
            )
        )
        steps.append(
            _run(
                "encounter_envelope_smoke",
                "npx --yes tsx ./scripts/smoke-clinician-encounter-envelope-v1.ts",
                cwd=NO1K,
                shell=True,
            )
        )
        steps.append(
            _run(
                "paste_chart_ledger_bridge_smoke",
                "npx --yes tsx ./scripts/smoke-clinician-paste-chart-ledger-bridge-v1.ts",
                cwd=NO1K,
                shell=True,
            )
        )

    if not ns.skip_ledger_append:
        if ns.fixture_json.is_file():
            steps.append(
                _run(
                    "append_paste_chart_ledger",
                    [
                        PY,
                        "scripts/append_clinician_paste_chart_encounter_ledger_v1.py",
                        "--from-json",
                        str(ns.fixture_json),
                        "--source",
                        "accumulation_chain_fixture",
                    ],
                )
            )
        else:
            steps.append(
                {
                    "name": "append_paste_chart_ledger",
                    "exit_code": 0,
                    "optional": True,
                    "skipped": True,
                    "reason": f"missing_fixture:{ns.fixture_json}",
                }
            )

    if not ns.skip_registry_rebuild:
        reg_script = ROOT / "scripts/build_patient_encounter_registry_v1.py"
        if reg_script.is_file():
            steps.append(
                _run(
                    "rebuild_patient_encounter_registry",
                    [PY, str(reg_script)],
                )
            )

    failed = [s for s in steps if s.get("exit_code", 0) != 0 and not s.get("optional")]
    report = {
        "schema": "clinician_encounter_accumulation_chain_v1",
        "generated_at_utc": _utc(),
        "ok": len(failed) == 0,
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "reproduce": "py scripts/run_clinician_encounter_accumulation_chain_v1.py",
    }
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "output": str(ns.output)}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
