#!/usr/bin/env python3
"""Fact-Lock TKM encounter_sequence pytest smoke (P18–P26 gates) [HYPO]."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/tkm_encounter_sequence_fact_lock_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    tests = [
        "tests/test_tkm_clinic_encounter_match_rate_v1.py",
        "tests/test_tkm_match_rate_delta_report_v1.py",
        "tests/test_encounter_sequence_weekly_report_v1.py",
        "tests/test_tkm_myeongni_sasang_lens_separation_v1.py",
        "tests/test_encounter_sequence_p28_v1.py",
        "tests/test_encounter_sequence_p29_v1.py",
        "tests/test_encounter_sequence_p30_v1.py",
        "tests/test_encounter_sequence_p31_v1.py",
        "tests/test_encounter_sequence_p32_v1.py",
        "tests/test_encounter_sequence_p33_v1.py",
        "tests/test_encounter_sequence_p34_v1.py",
        "tests/test_encounter_sequence_p35_v1.py",
        "tests/test_encounter_sequence_p36_v1.py",
        "tests/test_tkm_physician_gold_myeongni_engine_v1.py",
        "tests/test_tkm_l0_sasang_lens_separation_v1.py",
    ]
    proc = subprocess.run([PY, "-m", "pytest", *tests, "-q"], cwd=ROOT, capture_output=True, text=True)
    doc = {
        "schema": "tkm_encounter_sequence_fact_lock_smoke_v1",
        "generated_at_utc": _utc(),
        "ok": proc.returncode == 0,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-400:],
        "tests": tests,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(__import__("json").dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(__import__("json").dumps({"ok": doc["ok"]}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
