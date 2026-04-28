#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build symbol->atom mapping from registry and symbolic insight.")
    ap.add_argument("--registry-json", default="docs/final/artifacts/atom_anchor_registry_v1.json")
    ap.add_argument("--symbolic-json", default="docs/final/artifacts/symbolic_topology_insight_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/symbol_atom_mapping_latest.json")
    args = ap.parse_args()

    rp = resolve(args.registry_json)
    sp = resolve(args.symbolic_json)
    op = resolve(args.output_json)
    if not rp.is_file():
        raise SystemExit(f"missing registry json: {rp}")
    if not sp.is_file():
        raise SystemExit(f"missing symbolic json: {sp}")

    reg = load(rp)
    sym = load(sp)
    seed_symbol = str(sym.get("seed_symbol", "tree_of_knowledge_good_evil"))
    seq_map = reg.get("seed_symbol_sequences") if isinstance(reg.get("seed_symbol_sequences"), dict) else {}
    sequence = list(seq_map.get(seed_symbol) or [])
    atoms = reg.get("atoms") if isinstance(reg.get("atoms"), list) else []
    atom_desc = {str(a.get("atom_id")): str(a.get("description")) for a in atoms if isinstance(a, dict)}

    mapping = []
    for i, aid in enumerate(sequence):
        mapping.append(
            {
                "position": i + 1,
                "atom_id": aid,
                "atom_description": atom_desc.get(aid, ""),
                "seed_symbol": seed_symbol,
            }
        )

    out = {
        "schema": "symbol_atom_mapping_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "seed_symbol": seed_symbol,
        "mapping": mapping,
        "sources": {"registry_json": str(rp), "symbolic_json": str(sp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

