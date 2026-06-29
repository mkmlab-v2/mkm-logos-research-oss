#!/usr/bin/env python3
"""Apply commander signoff for delegation M drafts (no scholarly promotion)."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DRAFT_INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.draft.json"
LIVE_INTAKE = ROOT / "data/logos/manuscripts/evidence_intake/entry_12_13_external_witness_v1.json"
MIN_CMD = ROOT / "reports/compression_open_bench_minimal_command_set_v1_latest.json"
SIGNOFF_OUT = ROOT / "docs/final/artifacts/commander_delegation_m_signoff_v1_latest.json"
CHAIN_OUT = ROOT / "reports/commander_delegation_m_apply_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run(name: str, script: str, *extra: str) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run([PY, str(ROOT / "scripts" / script), *extra], cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "script": script,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviewer", default="commander")
    ap.add_argument("--out", type=Path, default=CHAIN_OUT)
    args = ap.parse_args()

    if not DRAFT_INTAKE.is_file():
        print(json.dumps({"ok": False, "error": "missing draft intake"}, ensure_ascii=False))
        return 1

    intake = _load(DRAFT_INTAKE)
    intake["version"] = "1.1.0-commander-approved"
    intake["draft_status"] = "commander_approved_operational"
    intake["commander_approved_at_utc"] = _utc()
    intake["commander_reviewer"] = args.reviewer
    intake["instructions"] = (
        "Commander approved operational intake path. approve_promotion remains false until "
        "MT Ps.5.2 ↔ 4Q98b verse-line crosswalk is resolved."
    )
    for row in intake.get("witness_promotions") or []:
        row["commander_operational_approved"] = True
        row["approve_promotion"] = False

    LIVE_INTAKE.parent.mkdir(parents=True, exist_ok=True)
    LIVE_INTAKE.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    min_doc: dict[str, Any] = {}
    if MIN_CMD.is_file():
        min_doc = _load(MIN_CMD)
        min_doc["status"] = "commander_approved"
        min_doc["commander_approved_at_utc"] = _utc()
        min_doc["commander_reviewer"] = args.reviewer
        MIN_CMD.write_text(json.dumps(min_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    signoff = {
        "schema": "commander_delegation_m_signoff_v1",
        "generated_at_utc": _utc(),
        "reviewer": args.reviewer,
        "send_gate": "HOLD",
        "promotion_ok": False,
        "approved": {
            "minimal_command_set": True,
            "entry_13_research_draft_operational": True,
            "intake_live_path_written": True,
            "scholarly_promotion": False,
            "mt_ps_5_2_crosswalk_gap_acknowledged": True,
        },
        "artifacts": {
            "intake_live": str(LIVE_INTAKE.relative_to(ROOT)).replace("\\", "/"),
            "minimal_command_set": str(MIN_CMD.relative_to(ROOT)).replace("\\", "/"),
            "research_draft": "reports/entry_13_external_witness_research_draft_v1_latest.json",
        },
        "human_gates_remaining": [
            "Turnstile browser E2E submit",
            "Masked customer JSONL",
            "approve_promotion=true after verse crosswalk resolution",
        ],
        "reproduce": "py scripts/apply_commander_delegation_m_signoff_v1.py",
    }
    SIGNOFF_OUT.parent.mkdir(parents=True, exist_ok=True)
    SIGNOFF_OUT.write_text(json.dumps(signoff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    steps = [
        _run("onboard_smoke", "run_compression_open_bench_onboard_smoke_v1.py"),
        _run("verification_chain", "run_dss_line_witness_verification_chain_v1.py", "--skip-pytest"),
        _run("p6_refresh", "run_p6_post_manuscript_integrity_chain_v1.py"),
        _run("enterprise_smoke", "check_enterprise_apply_live_smoke_v1.py"),
    ]
    all_ok = all(s["ok"] for s in steps)
    doc = {
        "schema": "commander_delegation_m_apply_v1",
        "generated_at_utc": _utc(),
        "signoff": str(SIGNOFF_OUT.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "ok": all_ok,
        "reproduce": "py scripts/apply_commander_delegation_m_signoff_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "promotion_ok": False, "intake": str(LIVE_INTAKE.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
