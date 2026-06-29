#!/usr/bin/env python3
"""Chain: embedding sidecar smoke + Capacitor shell hypo verify."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_studio_mobile_and_cache_chain_v1_latest.json"


def main() -> int:
    steps = [
        ("mobile_shell_artifact", [PY, "scripts/build_logos_research_mobile_shell_hypo_v1.py"]),
        ("capacitor_shell_verify", [PY, "scripts/check_logos_research_capacitor_shell_hypo_v1.py"]),
        ("sidecar_smoke", [PY, "scripts/check_logos_studio_embedding_sidecar_smoke_v1.py", "--manage-process"]),
    ]
    results: list[dict] = []
    for label, cmd in steps:
        proc = subprocess.run(cmd, cwd=ROOT)
        results.append({"step": label, "exit_code": proc.returncode})
        if proc.returncode != 0:
            out = {
                "ok": False,
                "schema": "logos_studio_mobile_and_cache_chain_v1",
                "steps": results,
                "reproduce": "py scripts/run_logos_studio_mobile_and_cache_chain_v1.py",
            }
            DEFAULT_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 1

    out = {
        "ok": True,
        "schema": "logos_studio_mobile_and_cache_chain_v1",
        "steps": results,
        "reproduce": "py scripts/run_logos_studio_mobile_and_cache_chain_v1.py",
    }
    DEFAULT_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(DEFAULT_OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
