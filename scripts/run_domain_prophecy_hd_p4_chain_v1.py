#!/usr/bin/env python3
"""HD P4 chain: router map + smoke coverage + weekly digest + Fact-Lock wiring [tier_0]."""
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


def _run(name: str, cmd: list[str], *, timeout: int = 900) -> dict[str, Any]:
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
    ap.add_argument("--skip-multi-smoke", action="store_true")
    ap.add_argument("--skip-btrack-extend", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    steps.append(_run("shallow_router_self_test", [PY, "scripts/route_domain_prophecy_from_shallow_v1.py", "--self-test"]))
    steps.append(_run("smoke_coverage_gate", [PY, "scripts/check_domain_prophecy_smoke_coverage_v1.py"]))
    steps.append(_run("weekly_digest", [PY, "scripts/build_domain_prophecy_weekly_digest_v1.py"]))

    if not args.skip_multi_smoke:
        steps.append(
            _run(
                "multi_domain_prophecy_smoke",
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Run-MultiDomainProphecySmoke_v1.ps1",
                ],
            )
        )

    if not args.skip_btrack_extend:
        steps.append(
            _run(
                "btrack_smoke_with_domain_prophecy",
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Run-BTrackDomainFeedbackSmoke.ps1",
                    "-IncludeDomainProphecy",
                    "-SkipNews",
                ],
            )
        )

    steps.append(_run("registry_gate", [PY, "scripts/check_domain_prophecy_registry_v1.py"]))
    steps.append(_run("pytest_p4", [PY, "-m", "pytest", "tests/test_domain_prophecy_p4_v1.py", "-q"]))

    ok = all(s["exit_code"] == 0 for s in steps)
    digest_path = ROOT / "reports/domain_prophecy_weekly_digest_v1_latest.json"
    smoke_path = ROOT / "reports/domain_prophecy_smoke_coverage_v1_latest.json"
    digest_doc: dict[str, Any] = {}
    smoke_doc: dict[str, Any] = {}
    if digest_path.is_file():
        digest_doc = json.loads(digest_path.read_text(encoding="utf-8-sig"))
    if smoke_path.is_file():
        smoke_doc = json.loads(smoke_path.read_text(encoding="utf-8-sig"))

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "mission": "Multi-domain prophecy P4 — router map + smoke coverage + weekly digest + Fact-Lock hook",
        "hypothesis_tier": "B",
        "research_only": True,
        "tier": "tier_0",
        "quality_ok": ok,
        "ok": ok,
        "steps": steps,
        "metrics": {
            "smoke_coverage_ok": smoke_doc.get("ok"),
            "smoke_mapped_count": smoke_doc.get("smoke_mapped_count"),
            "portfolio_active_count": (digest_doc.get("portfolio") or {}).get("active_count"),
        },
        "artifacts": {
            "router_map": "data/commander/domain_prophecy_shallow_router_map_v1.json",
            "smoke_coverage": "reports/domain_prophecy_smoke_coverage_v1_latest.json",
            "weekly_digest": "reports/domain_prophecy_weekly_digest_v1_latest.json",
            "digest_log": "reports/domain_prophecy_weekly_digest_v1.jsonl",
        },
        "reproduce": "py scripts/run_domain_prophecy_hd_p4_chain_v1.py",
        "send_gate": "HOLD",
        "production_apply_authorized": False,
    }
    HD_OUT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": completion["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
