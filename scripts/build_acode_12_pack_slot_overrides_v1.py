#!/usr/bin/env python3
"""Populate acode_12_pack_registry slot_overrides for all 75 MKM12 formula slots."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm12_acode_pack_router_v1 import (  # noqa: E402
    DEFAULT_FORMULAS,
    DEFAULT_REGISTRY,
    build_slot_overrides_for_all_formulas,
    load_json,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build slot_overrides for acode_12_pack_registry_v1.json")
    p.add_argument("--registry-json", default=str(DEFAULT_REGISTRY))
    p.add_argument("--formulas-json", default=str(DEFAULT_FORMULAS))
    p.add_argument("--write", action="store_true", help="Write registry JSON in place.")
    p.add_argument("--stdout-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry_json)
    formulas_path = Path(args.formulas_json)
    registry = load_json(registry_path)
    formulas_doc = load_json(formulas_path)

    overrides = build_slot_overrides_for_all_formulas(registry, formulas_doc)
    registry["generated_at_utc"] = _utc_now()
    routing = registry.setdefault("routing", {})
    routing["status"] = "populated_v1"
    fstp = routing.setdefault("formula_slot_to_pack", {})
    fstp["slot_overrides"] = overrides
    fstp["slot_overrides_status"] = "populated"
    fstp["slot_override_count"] = len(overrides)

    tc = registry.setdefault("training_contract", {})
    tc["status"] = "router_ready_v1"
    tc["implemented"] = True
    gr = tc.setdefault("golden_row_router", {})
    gr["script_status"] = "implemented"
    gr["router_module"] = "scripts/mkm12_acode_pack_router_v1.py"
    gr["supported_shard_modes"] = [
        "acode_state_deterministic_v1",
        "hash_sample_id_mod_12",
    ]

    fls = registry.setdefault("fact_lock_status", {})
    fls["routing_implemented"] = True
    fls["training_shard_implemented"] = True
    fls["evidence_artifacts"] = {
        "router_smoke": "reports/lora_tranche2_mkm12_75_to_12_router_smoke_latest.json",
        "qwen12pack_acode_train_ablation": "reports/lora_tranche2_qwen12pack_acode_train_ablation_latest.json",
        "signoff_pack_pointer": "reports/lora_tranche2_signoff_pack_v1_latest.json",
    }
    fls["next_human_gate"] = (
        "Commander B-track review: acode 12-pack vs bench 4×40 wall; "
        "multi_pack_production_go remains false until separate sign-off."
    )

    summary = {
        "slot_override_count": len(overrides),
        "distinct_pack_ids": len({v["pack_id"] for v in overrides.values()}),
    }

    if args.stdout_only:
        print(json.dumps({"summary": summary, "slot_overrides": overrides}, ensure_ascii=False, indent=2))
        return 0

    if args.write:
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"written": str(registry_path), **summary}))
        return 0

    print(json.dumps({"dry_run": True, **summary}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
