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
    ap = argparse.ArgumentParser(description="Build scholarly symbol bridge from atom mapping and resonance.")
    ap.add_argument("--mapping-json", default="docs/final/artifacts/symbol_atom_mapping_latest.json")
    ap.add_argument("--resonance-json", default="docs/final/artifacts/atom_resonance_report_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/scholarly_symbol_bridge_latest.json")
    args = ap.parse_args()

    mp = resolve(args.mapping_json)
    rp = resolve(args.resonance_json)
    op = resolve(args.output_json)
    if not mp.is_file():
        raise SystemExit(f"missing mapping json: {mp}")
    if not rp.is_file():
        raise SystemExit(f"missing resonance json: {rp}")

    m = load(mp)
    r = load(rp)
    seed_symbol = str(m.get("seed_symbol", "unknown"))
    resonance = float(r.get("resonance_score", 0.0) or 0.0)
    mapping = m.get("mapping") if isinstance(m.get("mapping"), list) else []

    # NOTE: labels are motif-level anchors for explainability; not execution triggers.
    atom_motif_map = {
        "BOUNDARY_COMMAND": "covenantal_boundary",
        "DESIRE_TRIGGER": "mimetic_desire",
        "TRANSGRESSION_ACT": "boundary_transgression",
        "SHAME_AWARENESS": "identity_fragmentation",
        "EXILE_PATTERN": "sacred_space_loss",
        "RESTORATION_ARC": "covenantal_restoration",
    }

    bridge_rows: list[dict[str, Any]] = []
    for row in mapping:
        if not isinstance(row, dict):
            continue
        atom_id = str(row.get("atom_id", ""))
        bridge_rows.append(
            {
                "position": int(row.get("position", 0) or 0),
                "atom_id": atom_id,
                "motif_label": atom_motif_map.get(atom_id, "unmapped_motif"),
                "source_confidence": round(resonance, 6),
                "research_only": True,
            }
        )

    out = {
        "schema": "scholarly_symbol_bridge_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "seed_symbol": seed_symbol,
        "bridge_rows": bridge_rows,
        "bridge_summary": {
            "row_count": len(bridge_rows),
            "mean_source_confidence": round(resonance, 6),
            "execution_policy": "report_only_non_trigger",
        },
        "sources": {"mapping_json": str(mp), "resonance_json": str(rp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

