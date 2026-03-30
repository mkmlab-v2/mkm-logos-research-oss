from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        return sum(1 for _ in f)


def _estimate_tokens_from_state(latest_state_path: Path) -> int:
    if not latest_state_path.exists():
        return 0
    try:
        txt = latest_state_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0
    # Rough estimate: 1 token ~= 4 chars.
    return max(1, len(txt) // 4)


def evaluate_cost_governor(project_root: Path) -> dict[str, Any]:
    policy_path = project_root / "ops" / "v2" / "policies" / "cost_policy.yaml"
    policy = (_load_yaml(policy_path).get("cost_policy") or {})

    now = datetime.now(timezone.utc)
    ymd = now.strftime("%Y%m%d")

    daily_state_journal = project_root / "memory" / "v2" / f"state_{ymd}.jsonl"
    latest_state = project_root / "memory" / "v2" / "latest_state.json"

    run_count = _line_count(daily_state_journal)
    est_tokens_per_run = _estimate_tokens_from_state(latest_state)
    est_tokens_total = run_count * est_tokens_per_run

    # Conservative placeholder cost model (can be replaced with real provider pricing)
    est_cost_usd = round((est_tokens_total / 1_000_000.0) * 5.0, 4)

    max_runs = int(policy.get("max_daily_runs", 300))
    max_tokens = int(policy.get("max_daily_estimated_tokens", 250000))
    max_cost = float(policy.get("max_daily_estimated_cost_usd", 25.0))

    breaches: list[str] = []
    if run_count > max_runs:
        breaches.append(f"daily_runs exceeded: {run_count}>{max_runs}")
    if est_tokens_total > max_tokens:
        breaches.append(f"estimated_tokens exceeded: {est_tokens_total}>{max_tokens}")
    if est_cost_usd > max_cost:
        breaches.append(f"estimated_cost exceeded: {est_cost_usd}>{max_cost}")

    budget_ok = len(breaches) == 0
    suggested_mode = "read-only"
    if not budget_ok and bool(policy.get("degrade_to_shadow_on_breach", True)):
        suggested_mode = "shadow"

    return {
        "policy_path": str(policy_path),
        "daily_runs": run_count,
        "estimated_tokens_per_run": est_tokens_per_run,
        "estimated_tokens_total": est_tokens_total,
        "estimated_cost_usd": est_cost_usd,
        "budget_ok": budget_ok,
        "breaches": breaches,
        "suggested_mode": suggested_mode,
        "block_execute_on_breach": bool(policy.get("block_execute_on_breach", True)),
    }
