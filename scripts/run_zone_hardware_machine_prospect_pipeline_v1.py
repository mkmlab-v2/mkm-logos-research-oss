#!/usr/bin/env python3
"""B-track pipeline: zone_hardware_machine prospect -> coverage -> twin gate."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/zone_hardware_machine_prospect_pipeline_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(label: str, cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    merged = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    print(f"[{label}] exit={proc.returncode}")
    return proc.returncode, merged.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-prospect-build", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, object]] = []
    chain_ok = True

    if not args.skip_prospect_build:
        code, log = _run(
            "prospect",
            [PY, str(ROOT / "scripts/build_zone_hardware_machine_prospect_v1.py")],
        )
        steps.append({"step": "prospect", "exit_code": code})
        chain_ok = chain_ok and code == 0
        if code != 0:
            steps[-1]["log_tail"] = log[-400:]

    code, log = _run(
        "coverage",
        [PY, str(ROOT / "scripts/run_zone_hardware_machine_template_catalog_coverage_v1.py")],
    )
    steps.append({"step": "coverage", "exit_code": code})
    chain_ok = chain_ok and code == 0

    code, log = _run("twin_gate", [PY, str(ROOT / "scripts/build_zone_hardware_machine_twin_gate_v1.py")])
    steps.append({"step": "twin_gate", "exit_code": code, "gate_pass": code == 0})
    chain_ok = chain_ok and code == 0

    report = {
        "schema": "zone_hardware_machine_prospect_pipeline_v1",
        "generated_at_utc": _utc(),
        "lane": "b_track_hypo",
        "disclaimer": "research_only",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "status": "ok" if chain_ok else "fail",
        "steps": steps,
        "artifacts": {
            "prospect": "reports/zone_hardware_machine_prospect_v1_latest.json",
            "coverage": "reports/zone_hardware_machine_template_catalog_coverage_v1_latest.json",
            "twin_gate": "reports/zone_hardware_machine_twin_gate_v1_latest.json",
        },
        "reproduce": "py scripts/run_zone_hardware_machine_prospect_pipeline_v1.py",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
