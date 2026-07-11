#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claim-A honesty CI/local smoke — closes Claude 'self-report vs repo' residual.

Runs:
  1) pytest tests/test_external_facing_fact_lock_v1.py
  2) check_mkm_middleware_headline_reuse_guard_v1.py

Writes machine-readable log (not chat self-report):
  docs/final/artifacts/mkm_middleware_claim_a_honesty_ci_smoke_v1_latest.json

  py scripts/run_mkm_middleware_claim_a_honesty_ci_smoke_v1.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm_middleware_llm_harness_lib_v1 import utc_now  # noqa: E402

ART = ROOT / "docs/final/artifacts"
OUT = ART / "mkm_middleware_claim_a_honesty_ci_smoke_v1_latest.json"
OUT_MIRROR = ROOT / "reports/mkm_middleware_claim_a_honesty_ci_smoke_v1_latest.json"
CHECKLIST = ART / "mkm_middleware_headline_reuse_checklist_v1_latest.json"


def _run(cmd: list[str]) -> dict:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1000:],
    }


def main() -> int:
    steps = []
    steps.append(
        {
            "id": "pytest_external_facing",
            **_run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/test_external_facing_fact_lock_v1.py",
                    "-q",
                    "--tb=line",
                ]
            ),
        }
    )
    steps.append(
        {
            "id": "headline_reuse_guard",
            **_run(
                [
                    sys.executable,
                    "scripts/check_mkm_middleware_headline_reuse_guard_v1.py",
                ]
            ),
        }
    )

    checklist_ok = None
    generated = None
    if CHECKLIST.is_file():
        try:
            doc = json.loads(CHECKLIST.read_text(encoding="utf-8-sig"))
            checklist_ok = doc.get("ok")
            generated = doc.get("generated_at_utc")
        except json.JSONDecodeError:
            checklist_ok = None

    all_ok = all(s["exit_code"] == 0 for s in steps)
    out = {
        "schema": "mkm_middleware_claim_a_honesty_ci_smoke_v1",
        "version": "1.0.0",
        "generated_at_utc": utc_now(),
        "research_only": True,
        "ok": all_ok,
        "send_gate": "HOLD",
        "note_ko": (
            "Claude residual: '5/5 exit0' must be repo-runnable, not chat oral. "
            "This artifact is the deterministic log. GitHub workflow: "
            "middleware-claim-a-honesty-smoke.yml. ≠ market GO / Track A / product SLA."
        ),
        "wired_gates": [
            "scripts/check_mkm_middleware_headline_reuse_guard_v1.py",
            "scripts/check_external_facing_fact_lock_v1.py (middleware MD)",
            "scripts/apply_mkm_middleware_claim_a_send_open_v1.py",
            "scripts/build_mkm_middleware_claim_a_claude_submit_pack_v1.py",
        ],
        "checklist_ok": checklist_ok,
        "checklist_generated_at_utc": generated,
        "checklist_path": "docs/final/artifacts/mkm_middleware_headline_reuse_checklist_v1_latest.json",
        "steps": [
            {
                "id": s["id"],
                "exit_code": s["exit_code"],
                "cmd": s["cmd"],
                "stdout_tail": s["stdout_tail"],
                "stderr_tail": s["stderr_tail"],
            }
            for s in steps
        ],
        "reproduce": [
            "py scripts/run_mkm_middleware_claim_a_honesty_ci_smoke_v1.py",
            "py -m pytest tests/test_external_facing_fact_lock_v1.py -q",
            "py scripts/check_mkm_middleware_headline_reuse_guard_v1.py",
        ],
        "github_workflow": ".github/workflows/middleware-claim-a-honesty-smoke.yml",
        "not_claimed": [
            "market_GO",
            "track_a",
            "product_SLA",
            "usefulness_proven_for_pointer_arm",
        ],
    }
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    ART.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    OUT_MIRROR.parent.mkdir(parents=True, exist_ok=True)
    OUT_MIRROR.write_text(text, encoding="utf-8")
    print(f"WROTE: {OUT}")
    print(f"ok={all_ok}")
    for s in steps:
        print(f"{s['id']}: exit={s['exit_code']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
