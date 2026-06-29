"""MKM12 formula slot → A-code 12-pack router (B-track / research_only)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REGISTRY = ROOT / "docs/final/artifacts/acode_12_pack_registry_v1.json"
DEFAULT_FORMULAS = ROOT / "docs/final/artifacts/mkm12_75_formulas_ssot_v1_latest.json"

LIFECYCLES = ("initial", "peak", "exhaustion")

CATEGORY_AXIS_DEFAULT: dict[str, str] = {
    "vector_mapping": "taeeum",
    "information_entropy": "taeeum",
    "hamilton_product": "taeeum",
    "fft_acceleration": "taeeum",
    "geumhwa_exchange": "taeyang",
    "taeyangin_sparsity": "soyang",
    "integrated_performance": "soyang",
    "integrity_verification": "soeum",
    "mathematical_consistency": "soeum",
    "vault_pending": "soeum",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def slot_key(slot_num: int, category: str) -> str:
    return f"F{int(slot_num):02d}_{category}"


def lifecycle_from_slot(slot_num: int) -> str:
    return LIFECYCLES[(int(slot_num) - 1) % 3]


def pack_by_axis_phase(
    packs: list[dict[str, Any]], four_ai_axis: str, lifecycle_phase: str
) -> dict[str, Any] | None:
    for pack in packs:
        if pack.get("four_ai_axis") == four_ai_axis and pack.get("lifecycle_phase") == lifecycle_phase:
            return pack
    return None


def match_category_rule(
    rules: list[dict[str, Any]], category: str, lifecycle_phase: str
) -> dict[str, Any] | None:
    for rule in rules:
        match = rule.get("match") or {}
        cats = match.get("category_in") or []
        phase = match.get("lifecycle_phase")
        if category in cats and phase == lifecycle_phase:
            return rule
    return None


def resolve_pack_id(
    *,
    slot_num: int,
    category: str,
    lifecycle_phase: str | None = None,
    registry: dict[str, Any],
    slot_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    phase = lifecycle_phase or lifecycle_from_slot(slot_num)
    key = slot_key(slot_num, category)
    overrides = slot_overrides
    if overrides is None:
        overrides = (
            registry.get("routing", {})
            .get("formula_slot_to_pack", {})
            .get("slot_overrides", {})
        )

    if key in overrides:
        override = overrides[key]
        pack_id = int(override["pack_id"])
        pack = next(p for p in registry["packs"] if int(p["pack_id"]) == pack_id)
        return {
            "slot_key": key,
            "slot_num": slot_num,
            "category": category,
            "lifecycle_phase": phase,
            "pack_id": pack_id,
            "acode_state_id": pack["acode_state_id"],
            "rule_id": override.get("rule_id", "slot_override"),
            "resolution": "slot_override",
        }

    rules = (
        registry.get("routing", {})
        .get("formula_slot_to_pack", {})
        .get("category_bias_rules", [])
    )
    rule = match_category_rule(rules, category, phase)
    if rule:
        pack_id = int(rule["primary_pack_id"])
        pack = next(p for p in registry["packs"] if int(p["pack_id"]) == pack_id)
        return {
            "slot_key": key,
            "slot_num": slot_num,
            "category": category,
            "lifecycle_phase": phase,
            "pack_id": pack_id,
            "acode_state_id": pack["acode_state_id"],
            "rule_id": rule.get("rule_id"),
            "resolution": "category_bias_rule",
        }

    axis = CATEGORY_AXIS_DEFAULT.get(category, "taeeum")
    pack = pack_by_axis_phase(registry["packs"], axis, phase)
    if pack is None:
        pack = registry["packs"][0]
    return {
        "slot_key": key,
        "slot_num": slot_num,
        "category": category,
        "lifecycle_phase": phase,
        "pack_id": int(pack["pack_id"]),
        "acode_state_id": pack["acode_state_id"],
        "rule_id": "category_axis_default",
        "resolution": "category_axis_default",
    }


def build_slot_overrides_for_all_formulas(
    registry: dict[str, Any], formulas_doc: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in formulas_doc.get("formulas", []):
        slot_num = int(row["slot"])
        category = str(row.get("category", "unknown"))
        resolved = resolve_pack_id(
            slot_num=slot_num,
            category=category,
            registry=registry,
            slot_overrides={},
        )
        out[resolved["slot_key"]] = {
            "pack_id": resolved["pack_id"],
            "acode_state_id": resolved["acode_state_id"],
            "rule_id": resolved["rule_id"],
            "lifecycle_phase": resolved["lifecycle_phase"],
        }
    return out


def route_all_formula_slots(
    registry_path: Path = DEFAULT_REGISTRY,
    formulas_path: Path = DEFAULT_FORMULAS,
) -> list[dict[str, Any]]:
    registry = load_json(registry_path)
    formulas_doc = load_json(formulas_path)
    overrides = registry.get("routing", {}).get("formula_slot_to_pack", {}).get("slot_overrides", {})
    rows: list[dict[str, Any]] = []
    for row in formulas_doc.get("formulas", []):
        slot_num = int(row["slot"])
        category = str(row.get("category", "unknown"))
        resolved = resolve_pack_id(
            slot_num=slot_num,
            category=category,
            registry=registry,
            slot_overrides=overrides if overrides else None,
        )
        rows.append(resolved)
    return rows


def assign_formula_slot_from_golden_row(row: dict[str, Any]) -> int:
    key = str(row.get("sample_id") or row.get("id") or "")
    digits = re.findall(r"\d+", key)
    if digits:
        return (int(digits[-1]) % 75) + 1
    return (hash(key) % 75) + 1


def route_golden_row_to_pack(
    row: dict[str, Any],
    *,
    registry: dict[str, Any],
    formulas_doc: dict[str, Any],
) -> dict[str, Any]:
    slot_num = assign_formula_slot_from_golden_row(row)
    formula_row = next(
        (f for f in formulas_doc.get("formulas", []) if int(f.get("slot", 0)) == slot_num),
        {"slot": slot_num, "category": "vault_pending"},
    )
    category = str(formula_row.get("category", "vault_pending"))
    resolved = resolve_pack_id(slot_num=slot_num, category=category, registry=registry)
    resolved["sample_id"] = row.get("sample_id")
    return resolved


def pack_label_from_registry(registry: dict[str, Any], pack_id: int) -> str:
    pack = next(p for p in registry["packs"] if int(p["pack_id"]) == int(pack_id))
    slug = pack["acode_state_id"].split(".")[-1]
    return slug.replace("_", "-")
