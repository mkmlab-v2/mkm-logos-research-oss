"""PersonaDiary iOS shell hypo parity (schema + copy contract; no simulator on Windows)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/final/artifacts/fixtures/personadiary_native_shell_hypo_v1.example.json"
COPY_CONTRACT = ROOT / "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json"
SHELL_DIR = ROOT / "projects/no1kmedi/personadiary-native-hypo-v1"


def test_copy_contract_references_non_prediction_boundary() -> None:
    doc = json.loads(COPY_CONTRACT.read_text(encoding="utf-8"))
    assert doc["schema"] == "personadiary_non_prediction_copy_contract_v1"
    assert doc["send_gate_default"] == "HOLD"
    assert "non_prediction" in doc["native_shell_boundary_ack"]


def test_native_shell_fixture_acknowledges_copy_contract() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert "non_prediction_copy_contract_v1" in fixture["boundary_ack"]


def test_capacitor_config_has_ios_block() -> None:
    cfg = json.loads((SHELL_DIR / "capacitor.config.json").read_text(encoding="utf-8"))
    assert "ios" in cfg
    assert cfg["server"]["url"].endswith("/ops")
