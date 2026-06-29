#!/usr/bin/env python3
"""Commander delegation M auto batch: research draft + API smoke + onboarding draft [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/commander_delegation_m_auto_v1_latest.json"

STEPS = [
    ("entry13_research_draft", "build_entry_13_external_witness_research_draft_v1.py"),
    ("enterprise_apply_smoke", "check_enterprise_apply_live_smoke_v1.py"),
    ("minimal_command_set", "build_compression_open_bench_minimal_command_set_v1.py"),
    ("p4_verification_dry", "run_dss_line_witness_verification_chain_v1.py", "--skip-pytest"),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    for row in STEPS:
        if len(row) == 2:
            steps.append(_run(row[0], row[1]))
        else:
            steps.append(_run(row[0], row[1], *row[2:]))

    smoke = {}
    smoke_path = ROOT / "reports/enterprise_apply_live_smoke_v1_latest.json"
    if smoke_path.is_file():
        smoke = json.loads(smoke_path.read_text(encoding="utf-8-sig"))
    research = {}
    research_path = ROOT / "reports/entry_13_external_witness_research_draft_v1_latest.json"
    if research_path.is_file():
        research = json.loads(research_path.read_text(encoding="utf-8-sig"))

    all_ok = all(s["ok"] for s in steps)
    doc = {
        "schema": "commander_delegation_m_auto_v1",
        "generated_at_utc": _utc(),
        "delegation_scale": "M",
        "send_gate": "HOLD",
        "promotion_applied": False,
        "steps": steps,
        "summary": {
            "enterprise_apply_smoke_ok": smoke.get("all_ok"),
            "entry13_draft_ready": research.get("schema") == "entry_13_external_witness_research_draft_v1",
            "mt_ps_5_2_crosswalk_gap": (research.get("scholarly_gap") or {}).get("entry_canon_target") == "Ps.5.2",
            "minimal_command_set": "reports/compression_open_bench_minimal_command_set_v1_latest.md",
        },
        "human_gates_remaining": [
            "Turnstile browser E2E submit (Tier 3)",
            "Masked customer JSONL upload",
            "Commander approve minimal command set + intake draft",
        ],
        "ok": all_ok,
        "reproduce": "py scripts/run_commander_delegation_m_auto_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": all_ok, "summary": doc["summary"]}, ensure_ascii=False))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
