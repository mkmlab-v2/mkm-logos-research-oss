"""L0 vs sasang constitution separation guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports/tkm_l0_sasang_lens_separation_v1_latest.json"
FIXTURE = ROOT / "tests/fixtures/encounter_sequence_v1.example.json"


def test_separation_report_ok() -> None:
    if not REPORT.is_file():
        pytest.skip("separation report missing")
    doc = json.loads(REPORT.read_text(encoding="utf-8-sig"))
    assert doc.get("separation_ok") is True
    assert int(doc.get("checked") or 0) >= 1


def test_fixture_l0_non_gating() -> None:
    if not FIXTURE.is_file():
        pytest.skip("fixture missing")
    seq = json.loads(FIXTURE.read_text(encoding="utf-8-sig"))
    import importlib.util

    path = ROOT / "scripts/tkm_encounter_sequence_l0_router_v1.py"
    spec = importlib.util.spec_from_file_location("l0", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert not mod.validate_l0_sasang_separation(seq)
    summary = seq.get("sequence_summary") or {}
    assert summary.get("final_ai_constitution") not in ("l0_escalation", "red_flag")
