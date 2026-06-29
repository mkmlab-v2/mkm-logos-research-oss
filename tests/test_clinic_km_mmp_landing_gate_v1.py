"""Tests for clinic LOI landing gate and design reference seed."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts" / "check_clinic_km_mmp_landing_gate_v1.py"
SEED_SCHEMA = ROOT / "docs/final/schemas/design_reference_seed_v1.schema.json"
SEED_EXAMPLE = ROOT / "reports/design_reference_seed_clinic_loi_v1.example.json"
TOKENS_V2 = ROOT / "reports/clinic_km_mmp_landing_tokens_v2.dtcg.json"


def test_landing_gate_exit_zero() -> None:
    cp = subprocess.run(
        [sys.executable, str(GATE)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    out = json.loads(cp.stdout.strip().splitlines()[-1])
    assert out["ok"] is True
    assert out["decision"] == "PASS"
    report = json.loads(
        (ROOT / "reports/clinic_km_mmp_landing_gate_v1_latest.json").read_text(encoding="utf-8")
    )
    assert report["schema"] == "clinic_km_mmp_landing_gate_v1"
    assert report["send_gate"] == "HOLD"


def test_tokens_v2_three_layers() -> None:
    doc = json.loads(TOKENS_V2.read_text(encoding="utf-8"))
    layers = doc["clinic-loi-trust-light"]
    assert "primitive" in layers
    assert "semantic" in layers
    assert "component" in layers
    assert doc["css_variables_resolved"]["--clinic-loi-bg"] == "#f9f9fb"


def test_seed_example_required_fields() -> None:
    doc = json.loads(SEED_EXAMPLE.read_text(encoding="utf-8"))
    assert doc["schema"] == "design_reference_seed_v1"
    assert doc["audience_profile"] == "clinic_owner_70s"
    assert SEED_SCHEMA.is_file()
