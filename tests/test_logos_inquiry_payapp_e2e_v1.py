"""Tests for logos inquiry PayApp E2E scaffold v1 (P0-2)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from scripts.core.logos_inquiry_payapp_e2e_v1 import (  # noqa: E402
    build_payapp_create_payload,
    load_contract,
    validate_scaffold,
)


def test_contract_loads() -> None:
    doc = load_contract(root=ROOT)
    assert doc["schema"] == "logos_inquiry_payapp_e2e_contract_v1"
    assert doc["send_gate"] == "HOLD"
    assert doc["sku_plans"]["pro"]["plan_code"] == "logos_inquiry_pro_v1"


def test_create_payload_redacts_keys() -> None:
    payload = build_payapp_create_payload()
    assert payload["payapp_key"] == "***REDACTED_G12***"
    assert payload["plan_code"] == "logos_inquiry_pro_v1"
    assert payload["amount"] == 39000


def test_scaffold_validate_ok() -> None:
    report = validate_scaffold(root=ROOT)
    assert report["missing_payapp_routes"] == []
    assert report["missing_inquiry_artifacts"] == []
    assert report["billing_intent_route_exists"] is True
    assert report["ok"] is True
    assert report["mode"] in ("dry_run_scaffold", "live")


def test_chain_script_exit_zero() -> None:
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts/run_logos_inquiry_payapp_e2e_smoke_v1.py"), "--skip-pytest"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    out = json.loads((ROOT / "reports/logos_inquiry_payapp_e2e_smoke_v1_latest.json").read_text(encoding="utf-8"))
    assert out["ok"] is True
