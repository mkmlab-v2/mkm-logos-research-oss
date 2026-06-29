#!/usr/bin/env python3
"""DISABLED: caused OAuth login loops. Use nvidia_azure_readonly_probe_v1.py instead."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_azure_startups_verify_benefit_latest.json"


def main() -> int:
    run = {
        "schema": "nvidia_azure_startups_verify_benefit_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disabled": True,
        "reason": "This script opened new_page + Sign in + GitHub and caused infinite login loops.",
        "use_instead": "py scripts/nvidia_azure_readonly_probe_v1.py",
        "manual_nvidia_benefit": (
            "Already logged into portal → Microsoft for Startups blade → "
            "시작 확인. NVIDIA $5K: Phoenix Confirmed — credits arrive via partner grant, "
            "not microsoft.com marketing Sign in loop."
        ),
    }
    OUT.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
