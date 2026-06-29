#!/usr/bin/env python3
"""Record one Gate B timing trial (commander stopwatch values).

Example:
  py scripts/record_kospi_dart_mda_poc_human_timing_v1.py --trial-id 1 --manual-sec 120 --poc-sec 85
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SHEET = ROOT / "reports/kospi_dart_mda_poc_human_timing_v1_latest.json"
CHECK = ROOT / "scripts/check_kospi_dart_mda_poc_human_timing_v1.py"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trial-id", type=int, required=True)
    ap.add_argument("--manual-sec", type=float, required=True)
    ap.add_argument("--poc-sec", type=float, required=True)
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    if not SHEET.is_file():
        subprocess.run([sys.executable, "scripts/build_kospi_dart_mda_poc_human_timing_v1.py"], cwd=ROOT, check=True)

    doc: dict[str, Any] = json.loads(SHEET.read_text(encoding="utf-8-sig"))
    updated = False
    for trial in doc.get("trials") or []:
        if int(trial.get("trial_id") or 0) == args.trial_id:
            trial["manual_sec"] = args.manual_sec
            trial["poc_click_verify_sec"] = args.poc_sec
            if args.notes:
                trial["notes"] = args.notes
            updated = True
            break
    if not updated:
        print(json.dumps({"ok": False, "error": "trial_id_not_found"}, ensure_ascii=False))
        return 1

    SHEET.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror = ROOT / "reports/kospi_dart_mda_poc_human_timing_v1.json"
    mirror.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    proc = subprocess.run([sys.executable, str(CHECK)], cwd=ROOT)
    print(json.dumps({"ok": True, "trial_id": args.trial_id}, ensure_ascii=False))
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
