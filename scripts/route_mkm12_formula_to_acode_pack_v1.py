#!/usr/bin/env python3
"""CLI: route MKM12 formula slots to A-code 12-pack IDs (B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.mkm12_acode_pack_router_v1 import (  # noqa: E402
    DEFAULT_FORMULAS,
    DEFAULT_REGISTRY,
    resolve_pack_id,
    route_all_formula_slots,
)

DEFAULT_OUT = ROOT / "reports/lora_tranche2_mkm12_75_to_12_router_smoke_latest.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Route MKM12 75 formula slots → A-code 12 packs.")
    p.add_argument("--registry-json", default=str(DEFAULT_REGISTRY))
    p.add_argument("--formulas-json", default=str(DEFAULT_FORMULAS))
    p.add_argument("--slot-num", type=int, default=0, help="Route one slot only (1-75).")
    p.add_argument("--category", default="", help="Required with --slot-num if not in formulas SSOT.")
    p.add_argument("--lifecycle-phase", default="", choices=["", "initial", "peak", "exhaustion", "unknown"])
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    p.add_argument("--stdout-only", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry_json)
    formulas_path = Path(args.formulas_json)

    if args.slot_num:
        from scripts.mkm12_acode_pack_router_v1 import load_json

        registry = load_json(registry_path)
        category = args.category
        if not category:
            formulas_doc = load_json(formulas_path)
            row = next(
                (f for f in formulas_doc.get("formulas", []) if int(f.get("slot", 0)) == args.slot_num),
                None,
            )
            if row is None:
                print(f"slot {args.slot_num} not found in formulas SSOT", file=sys.stderr)
                return 2
            category = str(row.get("category", "unknown"))
        phase = args.lifecycle_phase or None
        if phase == "unknown":
            phase = None
        result = resolve_pack_id(
            slot_num=int(args.slot_num),
            category=category,
            lifecycle_phase=phase,
            registry=registry,
        )
        payload = {"schema": "mkm12_acode_pack_route_v1", "routes": [result]}
    else:
        routes = route_all_formula_slots(registry_path=registry_path, formulas_path=formulas_path)
        pack_counts: dict[str, int] = {}
        for row in routes:
            pid = str(row["pack_id"])
            pack_counts[pid] = pack_counts.get(pid, 0) + 1
        payload = {
            "schema": "lora_tranche2_mkm12_75_to_12_router_smoke_v1",
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
            "registry_json": str(registry_path),
            "formulas_json": str(formulas_path),
            "slot_count": len(routes),
            "pack_distribution": {k: pack_counts[k] for k in sorted(pack_counts, key=int)},
            "distinct_packs": len(pack_counts),
            "routing_wired_ok": len(routes) == 75 and len(pack_counts) >= 1,
            "routes": routes,
        }

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.stdout_only:
        print(text)
        return 0

    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out_path), "slot_count": payload.get("slot_count", 1)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
