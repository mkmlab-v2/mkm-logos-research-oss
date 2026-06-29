#!/usr/bin/env python3
"""HD P1 chain: register GP domains + daily loop smoke + registry gate [tier_0]."""
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
    ap.add_argument("--skip-register", action="store_true")
    ap.add_argument("--skip-daily-loop", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    for domain_id in ("general_prophecy_macro_ai", "general_prophecy_geopolitics"):
        if not args.skip_register:
            steps.append(
                _run(
                    f"register_{domain_id}",
                    [
                        PY,
                        "scripts/register_general_prophecy_domain_v1.py",
                        "--domain-id",
                        domain_id,
                        "--activate-registry",
                        "--refresh-artifact",
                    ],
                )
            )

    if not args.skip_daily_loop:
        steps.append(
            _run(
                "domain_daily_loop_gp",
                [
                    PY,
                    "scripts/run_domain_prophecy_daily_loop_v1.py",
                    "--phase",
                    "evening",
                    "--domain-id",
                    "general_prophecy_macro_ai",
                    "--domain-id",
                    "general_prophecy_geopolitics",
                ],
            )
        )

    steps.append(_run("registry_gate", [PY, "scripts/check_domain_prophecy_registry_v1.py"]))
    steps.append(_run("pytest_domain_p1", [PY, "-m", "pytest", "tests/test_domain_prophecy_p1_v1.py", "-q"]))

    ok = all(s["exit_code"] == 0 for s in steps)
    loop_path = ROOT / "reports/domain_prophecy_daily_loop_v1_latest.json"
    loop_doc: dict[str, Any] = {}
    if loop_path.is_file():
        loop_doc = json.loads(loop_path.read_text(encoding="utf-8-sig"))

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "mission": "Multi-domain prophecy P1 — register GP packs + daily loop dispatcher",
        "hypothesis_tier": "B",
        "research_only": True,
        "tier": "tier_0",
        "quality_ok": ok,
        "ok": ok,
        "steps": steps,
        "metrics": {
            "domain_loop_quality_ok": loop_doc.get("quality_ok"),
            "domains_dispatched": len(loop_doc.get("domains") or []),
        },
        "artifacts": {
            "merge_manifest": "data/commander/domain_prophecy_merge_manifest_v1.json",
            "macro_ai_pack": "data/commander/domain_packs/general_prophecy_macro_ai_pack_v1.json",
            "geopolitics_pack": "data/commander/domain_packs/general_prophecy_geopolitics_pack_v1.json",
            "daily_loop": "reports/domain_prophecy_daily_loop_v1_latest.json",
        },
        "reproduce": "py scripts/run_domain_prophecy_hd_p1_chain_v1.py",
        "send_gate": "HOLD",
        "production_apply_authorized": False,
    }
    HD_OUT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": completion["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
