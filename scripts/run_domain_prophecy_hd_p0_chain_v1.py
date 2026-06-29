#!/usr/bin/env python3
"""HD P0 chain: domain registry gate + B-track domain smoke + completion artifact [tier_0]."""
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
HD_OUT = ROOT / "reports/hd_autonomous_evolution_completion_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 600) -> dict[str, Any]:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "step": name,
        "cmd": cmd,
        "exit_code": cp.returncode,
        "tail": ((cp.stdout or "") + (cp.stderr or "")).strip()[-500:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-btrack-smoke", action="store_true")
    ap.add_argument("--skip-kospi-verify", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run("registry_gate", [PY, "scripts/check_domain_prophecy_registry_v1.py"]))

    if not args.skip_btrack_smoke:
        steps.append(
            _run(
                "btrack_domain_feedback_smoke",
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Run-BTrackDomainFeedbackSmoke.ps1",
                ],
                timeout=900,
            )
        )

    if not args.skip_kospi_verify:
        steps.append(
            _run(
                "kospi_scheduler_verify",
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Verify-KospiDailyProphecyEvolutionTask_v1.ps1",
                    "-YearMonth",
                    "2026-07",
                ],
                timeout=120,
            )
        )

    ok = all(s["exit_code"] == 0 for s in steps)
    gate_path = ROOT / "reports/domain_prophecy_registry_gate_v1_latest.json"
    gate_doc: dict[str, Any] = {}
    if gate_path.is_file():
        gate_doc = json.loads(gate_path.read_text(encoding="utf-8-sig"))

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "mission": "Multi-domain prophecy P0 — domain_prophecy_config schema + registry + gates",
        "hypothesis_tier": "B",
        "research_only": True,
        "tier": "tier_0",
        "quality_ok": ok,
        "ok": ok,
        "steps": steps,
        "metrics": {
            "domain_count": gate_doc.get("domain_count"),
            "config_validated_count": gate_doc.get("config_validated_count"),
            "registry_gate_ok": gate_doc.get("ok"),
        },
        "artifacts": {
            "registry": "data/commander/domain_prophecy_registry_v1.json",
            "config_schema": "docs/final/schemas/domain_prophecy_config_v1.schema.json",
            "registry_schema": "docs/final/schemas/domain_prophecy_registry_v1.schema.json",
            "registry_gate": "reports/domain_prophecy_registry_gate_v1_latest.json",
            "schedule": "docs/final/artifacts/mkm_multi_domain_prophecy_hd_schedule_v1_latest.json",
        },
        "reproduce": "py scripts/run_domain_prophecy_hd_p0_chain_v1.py",
        "send_gate": "HOLD",
        "production_apply_authorized": False,
    }
    HD_OUT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": completion["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
