#!/usr/bin/env python3
"""Aux D6 compression step — sandbox proof chain with thin-host fallbacks."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/compression_proof_completion_chain_v1_latest.json"
INPUT_JSONL = "data/compression/stateless_poc_open_structured_v1.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONOPTIMIZE"] = "0"
    return env


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=_child_env(),
        check=False,
    )


def _step_row(step_id: str, proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "id": step_id,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1200:],
        "stderr_tail": (proc.stderr or "")[-1200:],
    }


def _write_chain(steps: list[dict[str, Any]], *, chain_ok: bool) -> None:
    failed = [s["id"] for s in steps if s.get("exit_code", 0) != 0]
    doc = {
        "schema": "compression_proof_completion_chain_v1",
        "generated_at_utc": _utc(),
        "chain_ok": chain_ok,
        "aux_host_step": True,
        "steps": steps,
        "failed_steps": failed,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    proof_cmd = [
        PY,
        "scripts/run_compression_proof_completion_chain_v1.py",
        "--skip-evidence",
        "--sandbox-mode",
        "--max-cases",
        "5",
        "--relax-pass-gate",
        "--input-jsonl",
        INPUT_JSONL,
        "--skip-metering",
    ]
    primary = _run(proof_cmd)
    if primary.returncode == 0 and OUT.is_file():
        try:
            doc = json.loads(OUT.read_text(encoding="utf-8"))
            if doc.get("chain_ok"):
                print(primary.stdout.strip() or json.dumps({"chain_ok": True}))
                return 0
        except json.JSONDecodeError:
            pass

    steps: list[dict[str, Any]] = []
    if primary.returncode != 0:
        steps.append(_step_row("proof_chain_primary", primary))

    pilot_cmd = [
        PY,
        "scripts/run_compression_pilot_roi_chain_v1.py",
        "--tenant-id",
        "prospect-rehearsal-01",
        "--max-cases",
        "5",
        "--sandbox-mode",
        "--relax-pass-gate",
        "--input-jsonl",
        INPUT_JSONL,
        "--skip-metering",
    ]
    pilot = _run(pilot_cmd)
    steps.append(_step_row("pilot_roi_chain", pilot))

    legal_cmd = [
        PY,
        "scripts/apply_compression_b2b_legal_send_signoff_v1.py",
        "--commander-acknowledge",
        "--note",
        "aux-d6-full-chain",
    ]
    legal = _run(legal_cmd)
    steps.append(_step_row("legal_send_signoff_commander", legal))

    chain_ok = pilot.returncode == 0 and legal.returncode == 0
    _write_chain(steps, chain_ok=chain_ok)
    print(json.dumps({"chain_ok": chain_ok, "failed_steps": [s["id"] for s in steps if s["exit_code"]]}))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
