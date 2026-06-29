#!/usr/bin/env python3
"""Weekly passive audit: NL guard (MCP) + phase3 smoke + promotion gate dry-run.

Output: docs/final/artifacts/mkm_theory_mathematization_passive_audit_v1_latest.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/mkm_theory_mathematization_passive_audit_v1_latest.json"
REPORT = ROOT / "reports/mkm_theory_mathematization_passive_audit_v1_latest.json"

STEPS: list[tuple[str, list[str]]] = [
    (
        "nl_guard_smoke",
        [sys.executable, "scripts/run_notebooklm_theory_mathematization_nl_guard_smoke_v1.py", "--ensure-mcp-register"],
    ),
    ("phase3_smoke", [sys.executable, "scripts/run_mkm_theory_mathematization_phase3_smoke_v1.py"]),
    ("promotion_gate_dryrun", [sys.executable, "scripts/run_mkm_theory_formula_promotion_gate_dryrun_v1.py"]),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str], *, skip_mcp: bool) -> dict:
    if skip_mcp and name == "nl_guard_smoke":
        cmd = [
            sys.executable,
            "scripts/run_notebooklm_theory_mathematization_nl_guard_smoke_v1.py",
            "--skip-mcp",
        ]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "step": name,
        "cmd": cmd,
        "exit_code": r.returncode,
        "stdout_tail": (r.stdout or "")[-600:],
        "stderr_tail": (r.stderr or "")[-300:] if r.stderr else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-mcp", action="store_true", help="NL guard static only (pytest/CI)")
    args = ap.parse_args()

    rows = [_run_step(name, cmd, skip_mcp=args.skip_mcp) for name, cmd in STEPS]
    ok = all(r["exit_code"] == 0 for r in rows)
    doc = {
        "schema": "mkm_theory_mathematization_passive_audit_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "skip_mcp": args.skip_mcp,
        "steps": rows,
        "ok": ok,
        "reproduce": "py scripts/run_mkm_theory_mathematization_passive_audit_v1.py",
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    REPORT.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
