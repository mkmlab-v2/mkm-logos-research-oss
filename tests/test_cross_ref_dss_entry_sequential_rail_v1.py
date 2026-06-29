from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = _ROOT / "docs/final/artifacts/cross_ref_dss_entry_rail_registry_v1_latest.json"
GATE = _ROOT / "docs/final/artifacts/cross_ref_dss_entry_sequential_gate_v1_latest.json"
CHAIN = _ROOT / "reports/cross_ref_dss_entry_sequential_chain_v1_latest.json"

ORDER = [
    "ENTRY_01",
    "ENTRY_02",
    "ENTRY_03",
    "ENTRY_04",
    "ENTRY_05",
    "ENTRY_06",
    "ENTRY_07",
    "ENTRY_08",
    "ENTRY_09",
    "ENTRY_10",
    "ENTRY_11",
    "ENTRY_12",
    "ENTRY_13",
    "ENTRY_14",
    "ENTRY_15",
    "ENTRY_16",
]


def test_registry_sequential_order() -> None:
    if not REGISTRY.is_file():
        pytest.skip("registry missing")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    assert reg.get("entry_order") == ORDER
    assert reg.get("summary", {}).get("entries") == 16
    assert reg.get("summary", {}).get("verified_anchor_achieved") == 0


def test_entries_01_05_thematic_in_registry() -> None:
    if not REGISTRY.is_file():
        pytest.skip("registry missing")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    by_id = {p["entry_id"]: p for p in reg.get("packets") or []}
    for eid in ("ENTRY_01", "ENTRY_02", "ENTRY_03", "ENTRY_04", "ENTRY_05"):
        assert by_id[eid]["thematic"] is True
        assert by_id[eid]["verified_anchor_achieved"] is False


def test_entry_12_13_closed_in_registry() -> None:
    if not REGISTRY.is_file():
        pytest.skip("registry missing")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    by_id = {p["entry_id"]: p for p in reg.get("packets") or []}
    assert by_id["ENTRY_12"]["rail_closed"] is True
    assert by_id["ENTRY_13"]["rail_closed"] is True
    assert by_id["ENTRY_16"]["waiting_queue"] is True


def test_sequential_gate() -> None:
    if not GATE.is_file():
        pytest.skip("gate missing")
    gate = json.loads(GATE.read_text(encoding="utf-8-sig"))
    assert gate.get("gate_ok") is True
    assert gate.get("sequential_rail_status") == "closed_sequential_documented"


def test_chain_ok() -> None:
    if not CHAIN.is_file():
        pytest.skip("chain missing")
    chain = json.loads(CHAIN.read_text(encoding="utf-8-sig"))
    assert chain.get("gate_ok") is True
    step_ok = [s for s in chain.get("steps") or [] if not str(s.get("name", "")).startswith("pytest")]
    assert all(s.get("ok") for s in step_ok)
