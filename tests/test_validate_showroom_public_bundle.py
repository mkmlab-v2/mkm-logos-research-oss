# -*- coding: utf-8 -*-
import json
from pathlib import Path

import pytest

from scripts.validate_showroom_public_bundle import validate_bundle


def test_validate_good_bundle(tmp_path: Path) -> None:
    p = tmp_path / "showroom_public_bundle_v1.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "generated_at_utc": "2026-04-03T12:00:00+00:00",
        "observability": {},
        "public_ui": {
            "schema": "showroom_public_ui_v1",
            "direction_abstract": "flat",
            "direction_source": "c2",
            "c2_lamp": "GREEN",
            "ops_fusion_ok": True,
            "return_pct_vs_baseline": None,
            "has_return_pct": False,
            "unrealized_pnl_pct_of_equity": None,
            "has_unrealized_pct": False,
            "baseline_mode": "none",
            "unified_score_balanced": 0.4,
        },
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "C2=GREEN_HOLD · exploratory monitor · no investment advice.",
            "schema_version": "public-event.v1",
            "event_id": "showroom-test-001",
            "source": "ops_showroom_bundle_v1",
            "system_status": "online",
            "active_strategies_count": 1,
            "delayed_metrics": {"delay_seconds": 180, "as_of_utc": "2026-04-03T11:57:00+00:00"},
            "direction_abstract": "flat",
            "disclaimer_ref": "jemaai_showroom_v1",
            "last_ok_utc": "2026-04-03T12:00:00+00:00",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    assert validate_bundle(p) == []


def test_validate_rejects_balance_leak(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    doc = {
        "schema": "showroom_public_bundle_v1",
        "public_event_v1": {
            "timestamp": "2026-04-03T12:00:00+00:00",
            "active_character_id": "dragon_quant",
            "risk_level": "INFO",
            "public_signal_direction": "HOLD",
            "abstract_reason": "balance_total_usdt leak",
            "schema_version": "public-event.v1",
            "event_id": "x",
            "source": "ops_showroom_bundle_v1",
            "disclaimer_ref": "jemaai_showroom_v1",
        },
    }
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    errs = validate_bundle(p)
    assert any("forbidden token" in e for e in errs)
