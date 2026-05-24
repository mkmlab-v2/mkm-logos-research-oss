"""Dual-lane SSOT paths for prophecy hit-rate eval (Phase A).

- Commander headline KPI: only ``promote_op28_headline_kpi_v1`` / explicit human promotion.
- Daily operational: scheduled daily / causal guard chains.
- Strategic observation (O-P29b): separate sync artifact under ``reports/``.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

REL_HEADLINE_KPI = "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
REL_DAILY_OPERATIONAL = "docs/final/artifacts/prophecy_hit_rate_eval_daily_operational_latest.json"
REL_SSOT_POINTER = "docs/final/artifacts/prophecy_hit_rate_ssot_pointer_v1_latest.json"
REL_OP29B_STRATEGIC_SYNC = "reports/op29b_prophecy_gates_headline_sync_v1_latest.json"

HEADLINE_KPI = ART / "prophecy_hit_rate_eval_latest.json"
DAILY_OPERATIONAL = ART / "prophecy_hit_rate_eval_daily_operational_latest.json"
SSOT_POINTER = ART / "prophecy_hit_rate_ssot_pointer_v1_latest.json"
OP29B_STRATEGIC_SYNC = REPORTS / "op29b_prophecy_gates_headline_sync_v1_latest.json"


def is_headline_kpi_path(path: Path) -> bool:
    try:
        return path.resolve() == HEADLINE_KPI.resolve()
    except OSError:
        return path == HEADLINE_KPI or str(path).replace("\\", "/").endswith(REL_HEADLINE_KPI.replace("\\", "/"))
