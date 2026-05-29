"""Constants for prophecy promotion gates dual-lane SSOT pointer."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

REL_DAILY_SHADOW = "docs/final/artifacts/prophecy_promotion_gates_daily_shadow_v1_latest.json"
REL_LEGACY_V1 = "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
REL_RECOMMENDED_CHAIN = "reports/prophecy_promotion_gates_recommended_chain_v1_latest.json"
REL_SSOT_POINTER = "docs/final/artifacts/prophecy_promotion_gates_ssot_pointer_v1_latest.json"
REL_RUNTIME_HEALTH = "docs/final/artifacts/prophecy_runtime_health_guard_latest.json"

DAILY_SHADOW = ART / "prophecy_promotion_gates_daily_shadow_v1_latest.json"
LEGACY_V1 = ART / "prophecy_promotion_gates_v1_latest.json"
RECOMMENDED_CHAIN = ROOT / "reports" / "prophecy_promotion_gates_recommended_chain_v1_latest.json"
SSOT_POINTER = ART / "prophecy_promotion_gates_ssot_pointer_v1_latest.json"
RUNTIME_HEALTH = ART / "prophecy_runtime_health_guard_latest.json"
