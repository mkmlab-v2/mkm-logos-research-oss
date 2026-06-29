#!/usr/bin/env python3
"""Ordered completion: pilot ROI chain → legal signoff → evidence refresh → closure."""

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
OUT = ROOT / "reports/compression_proof_completion_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-1500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", default="prospect-rehearsal-01")
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument("--skip-evidence", action="store_true")
    ap.add_argument(
        "--sandbox-mode",
        action="store_true",
        help="Pass --sandbox-mode to pilot ROI chain (aux / virtual tenant stub).",
    )
    ap.add_argument(
        "--relax-pass-gate",
        action="store_true",
        help="Pass --relax-pass-gate to pilot ROI chain (thin aux host).",
    )
    ap.add_argument(
        "--input-jsonl",
        type=Path,
        default=None,
        help="Explicit source JSONL for pilot ROI (aux bundle path).",
    )
    ap.add_argument(
        "--skip-metering",
        action="store_true",
        help="Pass --skip-metering to pilot ROI chain (aux thin host).",
    )
    args = ap.parse_args()

    pilot_cmd = [
        PY,
        "scripts/run_compression_pilot_roi_chain_v1.py",
        "--tenant-id",
        args.tenant_id,
        "--max-cases",
        str(args.max_cases),
    ]
    if args.sandbox_mode:
        pilot_cmd.append("--sandbox-mode")
    if args.relax_pass_gate:
        pilot_cmd.append("--relax-pass-gate")
    if args.input_jsonl:
        jsonl_path = (
            args.input_jsonl.resolve()
            if not args.input_jsonl.is_absolute()
            else args.input_jsonl.resolve()
        )
        pilot_cmd.extend(["--input-jsonl", jsonl_path.relative_to(ROOT).as_posix()])
    if args.skip_metering:
        pilot_cmd.append("--skip-metering")

    steps = [
        _run("pilot_roi_chain", pilot_cmd),
        _run(
            "legal_send_signoff_commander",
            [
                PY,
                "scripts/apply_compression_b2b_legal_send_signoff_v1.py",
                "--commander-acknowledge",
                "--note",
                "commander ordered sequential completion 2026-06-10",
            ],
        ),
    ]
    if not args.skip_evidence:
        steps.append(_run("evidence_lv3_chain", [PY, "scripts/run_compression_evidence_lv1_chain_v1.py"]))
        steps.append(
            _run("media_fact_sheets_sync", [PY, "scripts/build_compression_media_fact_sheets_sync_v1.py"])
        )
        steps.append(
            _run("readiness_gate", [PY, "scripts/check_compression_enterprise_summary_readiness_v1.py"])
        )
        steps.append(
            _run("recommended_workflow", [PY, "scripts/build_compression_b2b_recommended_workflow_v1.py"])
        )

    failed = [s for s in steps if s["exit_code"] != 0]
    doc = {
        "schema": "compression_proof_completion_chain_v1",
        "generated_at_utc": _utc(),
        "chain_ok": len(failed) == 0,
        "steps": steps,
        "failed_steps": [s["id"] for s in failed],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": doc["chain_ok"], "failed_steps": doc["failed_steps"]}, ensure_ascii=False))
    return 0 if doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
