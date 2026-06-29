#!/usr/bin/env python3
"""Intake fusion + encounter_sequence + L0 render smoke [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/intake_fusion_encounter_sequence_smoke_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/patient_intake_encounter_sequence_v1.example.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--intake-json", type=Path, default=FIXTURE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    tmp = ROOT / "reports" / "_tmp_intake_fusion_encounter_smoke"
    tmp.mkdir(parents=True, exist_ok=True)
    bundle = tmp / "bundle.json"
    mye = tmp / "mye.json"
    rat = tmp / "rationale.json"
    seq = tmp / "encounter_sequence.json"
    md = tmp / "bundle.md"

    cmd = [
        PY,
        str(ROOT / "scripts/build_patient_intake_fusion_draft_v1.py"),
        "--intake-json",
        str(args.intake_json),
        "--bundle-out",
        str(bundle),
        "--myeongni-out",
        str(mye),
        "--rationale-out",
        str(rat),
        "--with-encounter-sequence",
        "--encounter-sequence-out",
        str(seq),
        "--render-md-out",
        str(md),
        "--skip-intake-json-schema",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    smoke_ok = proc.returncode == 0
    md_text = md.read_text(encoding="utf-8") if md.is_file() else ""
    l0_ok = "L0 안전 알림" in md_text
    doc = {
        "schema": "intake_fusion_encounter_sequence_smoke_v1",
        "smoke_ok": smoke_ok and l0_ok,
        "fusion_exit_code": proc.returncode,
        "l0_in_markdown": l0_ok,
        "bundle_path": str(bundle).replace("\\", "/"),
        "sequence_path": str(seq).replace("\\", "/"),
        "markdown_path": str(md).replace("\\", "/"),
    }
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["smoke_ok"], "l0_in_markdown": l0_ok}))
    return 0 if doc["smoke_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
