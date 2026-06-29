"""Route MKM12 75 formula slots → A-code 12-pack router tests (B-track)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_registry() -> dict:
    path = ROOT / "docs/final/artifacts/acode_12_pack_registry_v1.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_formulas() -> dict:
    path = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_route_all_75_slots() -> None:
    from scripts.mkm12_acode_pack_router_v1 import route_all_formula_slots

    routes = route_all_formula_slots()
    assert len(routes) == 75
    pack_ids = {r["pack_id"] for r in routes}
    assert 1 <= min(pack_ids) and max(pack_ids) <= 12
    assert len(pack_ids) >= 4


def test_slot_override_populated_count() -> None:
    doc = _load_registry()
    overrides = doc.get("routing", {}).get("formula_slot_to_pack", {}).get("slot_overrides", {})
    assert len(overrides) == 75
    assert doc.get("fact_lock_status", {}).get("routing_implemented") is True


def test_golden_row_routing_deterministic() -> None:
    from scripts.mkm12_acode_pack_router_v1 import route_golden_row_to_pack

    registry = _load_registry()
    formulas = _load_formulas()
    row = {"sample_id": "golden_row_042"}
    a = route_golden_row_to_pack(row, registry=registry, formulas_doc=formulas)
    b = route_golden_row_to_pack(row, registry=registry, formulas_doc=formulas)
    assert a["pack_id"] == b["pack_id"]
    assert a["acode_state_id"] == b["acode_state_id"]


def test_resolve_single_slot_f01() -> None:
    from scripts.mkm12_acode_pack_router_v1 import resolve_pack_id

    registry = _load_registry()
    formulas = _load_formulas()
    row = next(f for f in formulas["formulas"] if int(f["slot"]) == 1)
    resolved = resolve_pack_id(
        slot_num=1,
        category=str(row["category"]),
        registry=registry,
    )
    assert resolved["pack_id"] >= 1
    assert resolved["acode_state_id"].startswith("acode.")
