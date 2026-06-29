#!/usr/bin/env python3
"""HD P2 chain: 4 archetype waves — BTC·weather·news·logos [tier_0]."""
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
P2_DOMAINS = (
    "btc_direction",
    "weather_triplet",
    "news_observation",
    "logos_verse_resolution",
    "logos_graphrag_insight",
)


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
    ap.add_argument("--skip-btrack-smoke", action="store_true")
    ap.add_argument("--skip-kospi-aug-dryrun", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    steps.append(
        _run(
            "register_logos_verse",
            [
                PY,
                "scripts/register_general_prophecy_domain_v1.py",
                "--domain-id",
                "logos_verse_resolution",
                "--activate-registry",
                "--refresh-artifact",
            ],
        )
    )

    loop_cmd = [PY, "scripts/run_domain_prophecy_daily_loop_v1.py", "--phase", "evening"]
    for did in P2_DOMAINS:
        loop_cmd.extend(["--domain-id", did])
    steps.append(_run("domain_daily_loop_p2", loop_cmd))

    if not args.skip_btrack_smoke:
        steps.append(
            _run(
                "btrack_domain_feedback_smoke_full",
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Run-BTrackDomainFeedbackSmoke.ps1",
                ],
            )
        )

    if not args.skip_kospi_aug_dryrun:
        steps.append(
            _run(
                "kospi_aug_scheduler_dryrun",
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    "scripts/Register-KospiDailyProphecyEvolutionTask_v1.ps1",
                    "-YearMonth",
                    "2026-08",
                    "-DryRun",
                ],
                timeout=60,
            )
        )

    steps.append(_run("registry_gate", [PY, "scripts/check_domain_prophecy_registry_v1.py"]))
    steps.append(_run("pytest_p2", [PY, "-m", "pytest", "tests/test_domain_prophecy_p2_v1.py", "-q"]))

    ok = all(s["exit_code"] == 0 for s in steps)
    loop_path = ROOT / "reports/domain_prophecy_daily_loop_v1_latest.json"
    loop_doc: dict[str, Any] = {}
    if loop_path.is_file():
        loop_doc = json.loads(loop_path.read_text(encoding="utf-8-sig"))
    btc_path = ROOT / "reports/btc_direction_shadow_eval_v1_latest.json"
    btc_doc: dict[str, Any] = {}
    if btc_path.is_file():
        btc_doc = json.loads(btc_path.read_text(encoding="utf-8-sig"))

    completion = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "mission": "Multi-domain prophecy P2 — BTC·weather·news·logos 4-wave archetype",
        "hypothesis_tier": "B",
        "research_only": True,
        "tier": "tier_0",
        "quality_ok": ok,
        "ok": ok,
        "steps": steps,
        "metrics": {
            "p2_domains_dispatched": len(loop_doc.get("domains") or []),
            "domain_loop_quality_ok": loop_doc.get("quality_ok"),
            "btc_shadow_quality_ok": btc_doc.get("quality_ok"),
        },
        "artifacts": {
            "registry": "data/commander/domain_prophecy_registry_v1.json",
            "btc_shadow_eval": "reports/btc_direction_shadow_eval_v1_latest.json",
            "daily_loop": "reports/domain_prophecy_daily_loop_v1_latest.json",
        },
        "reproduce": "py scripts/run_domain_prophecy_hd_p2_chain_v1.py",
        "send_gate": "HOLD",
        "production_apply_authorized": False,
    }
    HD_OUT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "metrics": completion["metrics"]}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
