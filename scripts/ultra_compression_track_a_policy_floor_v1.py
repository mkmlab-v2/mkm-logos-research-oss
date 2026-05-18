"""Track A promoted compression policy floor (RQ-016 bench alignment).

SSOT: bench / decision / canary / active KPI use **0.47** for promoted Track A.
Grid sweeps in ``evaluate_report`` may still reference legacy 0.49 internally.
"""

from __future__ import annotations

from typing import Any

TRACK_A_PROMOTED_POLICY_MIN = 0.47
BENCH_SAVING_FLOOR_REF = 0.47


def apply_promoted_policy_floor_to_quality_gate(
    report: dict[str, Any],
    *,
    policy_min: float = TRACK_A_PROMOTED_POLICY_MIN,
) -> dict[str, Any]:
    """Align ``quality_gate`` with promoted Track A bench floor (in-place)."""
    metrics = report.get("compression_metrics") or {}
    saving = metrics.get("global_token_saving_rate")
    qg = report.setdefault("quality_gate", {})
    if not isinstance(qg, dict):
        return report
    qg["ultra_saving_policy_min"] = policy_min
    if saving is not None:
        qg["ultra_saving_policy_ok"] = float(saving) >= float(policy_min)
    qg["track_a_promoted_policy_floor_aligned"] = True
    qg["legacy_eval_policy_min"] = 0.49
    return report
