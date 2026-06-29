#!/usr/bin/env python3
"""Gate PersonaDiary Figma ↔ Android design tokens sync."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts/sync_personadiary_figma_design_tokens_v1.py"
DEFAULT_OUT = ROOT / "reports/personadiary_figma_design_sync_gate_latest.json"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--fetch-figma", action="store_true")
    args = ap.parse_args()

    cmd = [sys.executable, str(SYNC)]
    if args.fetch_figma:
        cmd.append("--fetch-figma")

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    sync_report_path = ROOT / "reports/personadiary_figma_design_sync_latest.json"
    sync_report = {}
    if sync_report_path.is_file():
        sync_report = json.loads(sync_report_path.read_text(encoding="utf-8-sig"))

    ok = proc.returncode == 0
    report = {
        "schema": "personadiary_figma_design_sync_gate_v1",
        "ok": ok,
        "sync_script": str(SYNC.relative_to(ROOT)),
        "sync_exit_code": proc.returncode,
        "sync_stdout": proc.stdout.strip(),
        "sync_stderr": proc.stderr.strip(),
        "sync_report": sync_report,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
