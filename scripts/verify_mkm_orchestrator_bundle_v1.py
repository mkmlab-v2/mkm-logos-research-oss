#!/usr/bin/env python3
"""Exit 0 if MKM-Orchestrator Fact-Lock paths exist (no network)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    return Path(__file__).resolve().parents[1]


# Forward slashes: pathlib normalizes on Windows.
REQUIRED_REL = (
    "docs/final/schemas/todo_queue_v1.schema.json",
    "docs/final/artifacts/todo_queue_example_v1.json",
    "docs/final/artifacts/todo_queue_smoke_first_v1.json",
    "docs/final/artifacts/todo_queue_smoke_first_python_v1.json",
    "docs/final/artifacts/mkm_orchestrator_connection_spec_v1.json",
    "scripts/mkm_orchestrator_poll_v1.py",
    "scripts/mkm_orchestrator_poll.ps1",
    "scripts/mkm_orchestrator_telegram_v1.py",
    "scripts/approve_mkm_orchestrator_task_v1.py",
    "scripts/show_mkm_orchestrator_queue_status_v1.py",
    "scripts/mkm_orchestrator_noop_smoke_v1.ps1",
    "scripts/mkm_orchestrator_noop_smoke_v1.py",
    "scripts/bootstrap_mkm_orchestrator_queue_v1.ps1",
    "scripts/run_mkm_orchestrator_smoke_v1.ps1",
    "scripts/Invoke-MkmOrchestratorTelegramIngest.ps1",
    "scripts/Register-MkmOrchestratorPollTask.ps1",
    "scripts/Register-MkmOrchestratorTelegramIngestTask.ps1",
    "scripts/verify_mkm_orchestrator_bundle_v1.py",
    "scripts/apply_trackc_plan_bridge_to_queue_v1.py",
    "scripts/run_trackc_plan_gates_smoke_v1.py",
    "docs/final/artifacts/mkm_trackc_plan_orchestrator_bridge_v1.json",
    "scripts/Invoke-TrackCPlanQueueRefresh.ps1",
    "scripts/Invoke-TrackCPlanOrchestratorCycle.ps1",
    "scripts/Invoke-TrackCPlanGatesSmoke.ps1",
    "scripts/Register-TrackCPlanGatesSmokeTask.ps1",
    "scripts/run_mkm_continuous_daemon.ps1",
    "scripts/Register-MkmOrchestratorDaemonTask.ps1",
    "tests/test_apply_trackc_plan_bridge_v1.py",
    ".github/workflows/mkm-orchestrator-smoke.yml",
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=None)
    args = ap.parse_args()
    root = _root(args.workspace_root)
    missing = [rel for rel in REQUIRED_REL if not (root / rel).exists()]

    if missing:
        print("MKM-Orchestrator bundle verify: FAIL", file=sys.stderr)
        for m in missing:
            print(f"  missing: {m}", file=sys.stderr)
        return 1
    print("MKM-Orchestrator bundle verify: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
