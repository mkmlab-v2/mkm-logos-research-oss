"""Track C morning briefing — shadow PnL policy default (OPERATION_MODE_B)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_trackc_macro_risk_morning_briefing_v1.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("morning_briefing", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_default_excludes_shadow_pnl_from_payload() -> None:
    mod = _load_module()
    payload = mod._build_payload(include_shadow_pnl=False)
    assert payload["include_shadow_pnl"] is False
    assert payload["shadow_pnl"]["shadow_pnl_status"] == "EXCLUDED_BY_POLICY"
    assert payload["fact_lock_evidence"].get("shadow_pnl_artifact") is None


def test_include_shadow_pnl_when_flagged() -> None:
    mod = _load_module()
    payload = mod._build_payload(include_shadow_pnl=True)
    assert payload["include_shadow_pnl"] is True
    assert payload["fact_lock_evidence"].get("shadow_pnl_artifact")
