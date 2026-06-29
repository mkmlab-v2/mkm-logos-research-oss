#!/usr/bin/env python3
"""Path A commercial defense publish chain — fact sheet · OI paste · GitHub funnel · gates."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/path_a_commercial_defense_publish_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"cmd": cmd, "exit_code": proc.returncode, "ok": proc.returncode == 0, "parsed": parsed}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-defense-chain", action="store_true")
    args = ap.parse_args()

    steps: dict[str, Any] = {}
    ok = True

    if not args.skip_defense_chain:
        steps["defense_chain"] = _run(
            [sys.executable, "scripts/run_path_a_spine_commercial_defense_chain_v1.py"]
        )
        ok = ok and steps["defense_chain"]["ok"]

    steps["github_funnel_appendix"] = _run(
        [sys.executable, "scripts/build_path_a_github_funnel_inbound_appendix_v1.py"]
    )
    ok = ok and steps["github_funnel_appendix"]["ok"]

    steps["oi_paste_build"] = _run(
        [sys.executable, "scripts/build_kstartup_open_innovation_20460237_paste_ready_v1.py"]
    )
    ok = ok and steps["oi_paste_build"]["ok"]

    steps["oi_paste_gate"] = _run(
        [sys.executable, "scripts/check_kstartup_open_innovation_20460237_paste_gate_v1.py"]
    )
    ok = ok and steps["oi_paste_gate"]["ok"]

    doc = {
        "schema": "path_a_commercial_defense_publish_chain_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "chain_ok": ok,
        "steps": steps,
        "artifacts": {
            "fact_sheet": "reports/path_a_spine_commercial_defense_fact_sheet_v1_latest.json",
            "github_funnel_md": "reports/human_paste/path_a_github_funnel_inbound_appendix_v1_latest.md",
            "github_funnel_txt": "reports/human_paste/path_a_github_funnel_inbound_appendix_v1_latest.txt",
            "oi_paste_dir": "reports/kstartup_open_innovation_20460237_paste_ready",
            "oi_gate": "reports/kstartup_open_innovation_20460237_paste_gate_latest.json",
        },
        "reproducible_command": "py scripts/run_path_a_commercial_defense_publish_chain_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
