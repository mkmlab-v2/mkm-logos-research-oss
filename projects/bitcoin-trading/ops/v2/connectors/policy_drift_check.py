from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def check_policy_drift(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    policy_path = project_root / "ops" / "v2" / "policies" / "risk_policy.yaml"
    rules_path = project_root.parent.parent / ".cursorrules"

    drift: list[str] = []
    policy = {}
    if policy_path.exists():
        try:
            policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            drift.append(f"risk_policy parse error: {e}")
    else:
        drift.append("risk_policy.yaml missing")

    rp = policy.get("risk_policy", {}) if isinstance(policy, dict) else {}
    max_dd = rp.get("max_drawdown_limit")
    state_max_dd = ((state.get("risk") or {}).get("max_drawdown_limit"))
    if max_dd is not None and state_max_dd is not None and float(max_dd) != float(state_max_dd):
        drift.append(f"max_drawdown_limit mismatch policy={max_dd} state={state_max_dd}")

    if not rules_path.exists():
        drift.append("workspace .cursorrules missing")

    return {
        "policy_path": str(policy_path),
        "rules_path": str(rules_path),
        "drift_count": len(drift),
        "drift_items": drift,
        "is_aligned": len(drift) == 0,
    }
