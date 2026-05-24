#!/usr/bin/env python3
"""One-shot: tier_15 + Gemini moat regen (loads .env via Import-WorkspaceDotEnv)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOAT = "compression_governance_moat_w12"
QUEUE = ROOT / "data/marketing/marketing_content_queue.json"


def main() -> int:
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "Import-WorkspaceDotEnv_v1.ps1"),
            "-WorkspaceRoot",
            str(ROOT),
        ],
        cwd=str(ROOT),
        check=False,
    )
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_marketing_linkedin_integrated_v1",
        ROOT / "scripts" / "run_marketing_linkedin_integrated_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    _gemini_api_key_present = mod._gemini_api_key_present
    _queue_reset_for_regen = mod._queue_reset_for_regen
    _set_env_flag = mod._set_env_flag

    if not _gemini_api_key_present():
        print("no gemini api key in env", file=sys.stderr)
        return 2

    _set_env_flag("MKM_MARKETING_GEMINI_ALLOWED", "1")
    subprocess.run(
        [
            sys.executable,
            "scripts/set_marketing_queue_cost_tier_v1.py",
            "--active-tier",
            "tier_15",
            "--event-week",
            "--gemini-item",
            MOAT,
        ],
        cwd=str(ROOT),
        check=True,
    )
    _queue_reset_for_regen(MOAT)
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/generate_linkedin_b2b_copy_v1.py",
            "--gemini",
            "--item-id",
            MOAT,
            "--with-chart",
            "--strict-compliance",
        ],
        cwd=str(ROOT),
    )
    subprocess.run(
        [
            sys.executable,
            "scripts/set_marketing_queue_cost_tier_v1.py",
            "--active-tier",
            "tier_0",
            "--clear-event-week",
            "--reset-gemini-flags",
        ],
        cwd=str(ROOT),
        check=False,
    )
    _set_env_flag("MKM_MARKETING_GEMINI_ALLOWED", "0")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
