#!/usr/bin/env python3
"""Offline gate: clinical cohort hypo — patient bundle schema smoke [B-track]."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "data/commander/domain_packs/clinical_cohort_hypo_pack_v1.json"
OUT = ROOT / "reports/clinical_cohort_domain_gate_v1_latest.json"
PY = sys.executable


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    errors: list[str] = []
    if not PACK.is_file():
        errors.append("missing clinical pack")
    proc = subprocess.run(
        [PY, "-m", "pytest", "tests/test_patient_care_bundle_v1_schema.py", "-q"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    pytest_ok = proc.returncode == 0
    if not pytest_ok:
        errors.append(f"patient_care_bundle schema pytest exit {proc.returncode}")
    ok = not errors
    report = {
        "schema": "clinical_cohort_domain_gate_v1",
        "generated_at_utc": _utc(),
        "ok": ok,
        "pytest_ok": pytest_ok,
        "errors": errors,
        "reproduce": "py scripts/check_clinical_cohort_domain_gate_v1.py",
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
