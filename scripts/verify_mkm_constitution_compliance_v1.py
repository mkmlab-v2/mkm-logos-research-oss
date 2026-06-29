#!/usr/bin/env python3
"""Thin P0 compliance wrapper — P0 paths + Logos finish + audit smoke attach [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/mkm_constitution_compliance_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_ps1(script: str) -> dict[str, Any]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / "scripts" / script),
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": script,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
    }


def _run_py(script: str, *extra: str) -> dict[str, Any]:
    cmd = [PY, str(ROOT / "scripts" / script), *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": script,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check-all", action="store_true")
    ap.add_argument("--skip-p0-ps1", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if args.check_all and not args.skip_p0_ps1:
        steps.append(_run_ps1("verify_p0_constitution_gate_paths.ps1"))

    steps.append(_run_py("build_logos_commercial_finish_closure_gate_v1.py"))
    steps.append(_run_py("build_logos_commercial_depth_closure_gate_v1.py"))
    steps.append(_run_py("sync_compression_bench_to_audit_smoke_v1.py", "--attach-smoke"))

    smoke_path = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
    smoke_attached = False
    if smoke_path.is_file():
        try:
            pack = json.loads(smoke_path.read_text(encoding="utf-8-sig"))
            smoke_attached = "logos_audit_smoke_appendix" in pack
        except json.JSONDecodeError:
            smoke_attached = False

    all_ok = all(s["ok"] for s in steps) and smoke_attached
    doc = {
        "schema": "mkm_constitution_compliance_v1",
        "generated_at_utc": _utc(),
        "check_all": args.check_all,
        "steps": steps,
        "smoke_attached_to_reproduce_pack": smoke_attached,
        "ok": all_ok,
        "reproduce": "py scripts/verify_mkm_constitution_compliance_v1.py --check-all",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "smoke_attached": smoke_attached}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
