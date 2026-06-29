#!/usr/bin/env python3
"""OI 20460237 — fill 붙임1 사업계획서 (delegates to submission_complete chain)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META_OUT = ROOT / "reports/kstartup_open_innovation_20460237_submission_complete_latest.json"


def _run(cmd: list[str]) -> None:
    print(">>", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template-hwpx", type=Path, default=None)
    ap.add_argument("--demand-pdf", type=Path, default=None)
    ap.add_argument("--skip-hancom", action="store_true")
    args = ap.parse_args()

    cmd = [sys.executable, "scripts/run_kstartup_open_innovation_20460237_submission_complete_v1.py"]
    if args.template_hwpx:
        cmd += ["--template-hwpx", str(args.template_hwpx)]
    if args.demand_pdf:
        cmd += ["--demand-pdf", str(args.demand_pdf)]
    if args.skip_hancom:
        cmd += ["--skip-hancom"]
    _run(cmd)

    meta = json.loads(META_OUT.read_text(encoding="utf-8")) if META_OUT.is_file() else {"ok": False}
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0 if meta.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
