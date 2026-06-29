"""LTM lane resume pack purity rules ([HYPO] / B-track)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = SCRIPT_ROOT / "docs" / "final" / "artifacts" / "mkm_ltm_inject_contract_v1.json"

DEFAULT_MS_FORBIDDEN = ("47.5%", "jaccard", "MULTILENS_ULTRA", "four_ai_lens", "NON_GATING")
DEFAULT_ORACLE_FORBIDDEN = ("47.5%", "jaccard", "MULTILENS_ULTRA")


def load_inject_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if doc.get("schema") != "mkm_ltm_inject_contract_v1":
        raise ValueError(f"unexpected contract schema: {doc.get('schema')!r}")
    return doc


def purity_needles(contract: dict[str, Any] | None = None) -> tuple[tuple[str, ...], tuple[str, ...]]:
    purity = (contract or {}).get("purity") or {}
    ms = tuple(purity.get("ms_forbidden_needles") or DEFAULT_MS_FORBIDDEN)
    oracle = tuple(purity.get("oracle_forbidden_needles") or DEFAULT_ORACLE_FORBIDDEN)
    return ms, oracle


def lane_purity_violations(
    lane: str,
    inject_text: str,
    *,
    contract: dict[str, Any] | None = None,
) -> list[str]:
    lane_key = lane.strip().lower()
    lower = inject_text.lower()
    ms_forbidden, oracle_forbidden = purity_needles(contract)
    flags: list[str] = []
    if lane_key == "ms":
        for needle in ms_forbidden:
            if needle.lower() in lower:
                flags.append(f"ms_pack_contains:{needle}")
    if lane_key == "oracle":
        for needle in oracle_forbidden:
            if needle in inject_text:
                flags.append(f"oracle_pack_contains:{needle}")
    if lane_key == "infra":
        if "47.5%" in inject_text and "MS" not in inject_text:
            flags.append("infra_pack_contains:47.5%_without_ms_lane_context")
    return flags


def check_all_lanes_purity(
    lane_texts: dict[str, str],
    *,
    contract: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    for lane, text in lane_texts.items():
        for flag in lane_purity_violations(lane, text, contract=contract):
            errors.append(f"{lane}:{flag}")
    return errors
