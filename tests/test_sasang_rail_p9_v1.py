from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
P9_GATE = _ROOT / "docs/final/artifacts/sasang_rail_p9_gate_v1_latest.json"
LIT_GATE = _ROOT / "docs/final/artifacts/sasang_literature_supervised_gate_v1_latest.json"
COMP = _ROOT / "reports/sasang_joint_benchmark_composition_v1_latest.json"


def test_p9_gate() -> None:
    if not P9_GATE.is_file():
        pytest.skip("p9 gate missing")
    gate = json.loads(P9_GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sasang_rail_p9_status") == "literature_data_ok"
    assert gate.get("send_gate") == "HOLD"


def test_literature_supervised_gate() -> None:
    if not LIT_GATE.is_file():
        pytest.skip("literature gate missing")
    doc = json.loads(LIT_GATE.read_text(encoding="utf-8-sig"))
    assert doc.get("gate_ok") is True
    assert int(doc.get("rows") or 0) >= 15


def test_benchmark_has_non_dummy() -> None:
    if not COMP.is_file():
        pytest.skip("composition report missing")
    doc = json.loads(COMP.read_text(encoding="utf-8-sig"))
    assert doc.get("composition_ok") is True
    assert int(doc.get("rows_non_dummy") or 0) >= 1
