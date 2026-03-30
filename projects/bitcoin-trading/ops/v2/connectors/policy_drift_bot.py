from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ops.v2.connectors.policy_drift_check import check_policy_drift


def _task_exists(task_name: str) -> bool:
    cmd = ["schtasks", "/Query", "/TN", task_name]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _build_recommended_actions(project_root: Path, drift_items: list[str], missing_tasks: list[str], strategy_changed: bool) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for item in drift_items:
        if "risk_policy parse error" in item:
            actions.append(
                {
                    "priority": "P0",
                    "title": "Fix risk policy YAML parse error",
                    "command_template": "python -c \"import yaml, pathlib; p=pathlib.Path('ops/v2/policies/risk_policy.yaml'); yaml.safe_load(p.read_text(encoding='utf-8')); print('ok')\"",
                }
            )
        elif "max_drawdown_limit mismatch" in item:
            actions.append(
                {
                    "priority": "P0",
                    "title": "Align risk max_drawdown_limit",
                    "command_template": "Compare state.risk.max_drawdown_limit vs ops/v2/policies/risk_policy.yaml and update one source of truth.",
                }
            )
        elif "workspace .cursorrules missing" in item:
            actions.append(
                {
                    "priority": "P1",
                    "title": "Restore workspace .cursorrules",
                    "command_template": "Ensure C:/workspace/.cursorrules exists and is readable.",
                }
            )

    if missing_tasks:
        actions.append(
            {
                "priority": "P0",
                "title": "Re-register missing scheduler tasks",
                "command_template": "powershell -ExecutionPolicy Bypass -File .\\ops\\windows-rehearsal\\register_direct_watchdog_task.ps1; powershell -ExecutionPolicy Bypass -File .\\ops\\windows-rehearsal\\register_kpi_snapshot_task.ps1; powershell -ExecutionPolicy Bypass -File .\\ops\\windows-rehearsal\\register_brain_sync_task.ps1; powershell -ExecutionPolicy Bypass -File .\\ops\\v2\\tasks\\register_cycle_task.ps1; powershell -ExecutionPolicy Bypass -File .\\ops\\v2\\tasks\\register_shadow_cycle_task.ps1; powershell -ExecutionPolicy Bypass -File .\\ops\\v2\\reports\\register_morning_brief_task.ps1",
            }
        )

    if strategy_changed:
        actions.append(
            {
                "priority": "P1",
                "title": "Run shadow validation after strategy change",
                "command_template": "python ops/v2/graph/runner.py --mode shadow",
            }
        )

    if not actions:
        actions.append(
            {
                "priority": "P3",
                "title": "No action needed",
                "command_template": "System aligned. Keep monitoring.",
            }
        )
    return actions


def evaluate_policy_drift_bot(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    base = check_policy_drift(project_root, state)
    drift_items = list(base.get("drift_items") or [])

    required_tasks = [
        "Bitcoin-Direct-Watchdog-5min",
        "Bitcoin-KPI-Snapshot-30min",
        "Bitcoin-BrainSync-Daily-0805",
        "Bitcoin-V2-Orchestrator-15min",
        "Bitcoin-V2-Shadow-15min",
        "Bitcoin-V2-Execute-Guarded-15min",
        "Bitcoin-V2-MorningBrief-0800",
    ]
    missing_tasks = [t for t in required_tasks if not _task_exists(t)]
    if missing_tasks:
        drift_items.append(f"missing tasks: {', '.join(missing_tasks)}")

    strategy = state.get("strategy") or {}
    strategy_hash = strategy.get("strategy_hash")
    state_dir = project_root / "memory" / "v2" / "policy"
    state_dir.mkdir(parents=True, exist_ok=True)
    prev_hash_path = state_dir / "last_strategy_hash.txt"
    prev_hash = _read_text(prev_hash_path).strip()

    strategy_changed = bool(strategy_hash and prev_hash and strategy_hash != prev_hash)
    if strategy_changed:
        drift_items.append("strategy hash changed since previous run")
    if strategy_hash:
        prev_hash_path.write_text(strategy_hash, encoding="utf-8")

    recommended_actions = _build_recommended_actions(
        project_root=project_root,
        drift_items=drift_items,
        missing_tasks=missing_tasks,
        strategy_changed=strategy_changed,
    )

    return {
        "base": base,
        "drift_count": len(drift_items),
        "drift_items": drift_items,
        "is_aligned": len(drift_items) == 0,
        "required_tasks": required_tasks,
        "missing_tasks": missing_tasks,
        "strategy_changed": strategy_changed,
        "recommended_actions": recommended_actions,
        "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
