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


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build atom resonance report from symbol-atom mapping.")
    ap.add_argument("--mapping-json", default="docs/final/artifacts/symbol_atom_mapping_latest.json")
    ap.add_argument("--survivor-json", default="docs/final/artifacts/insight_survivor_candidates_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/atom_resonance_report_latest.json")
    args = ap.parse_args()

    mp = resolve(args.mapping_json)
    sp = resolve(args.survivor_json)
    op = resolve(args.output_json)
    if not mp.is_file():
        raise SystemExit(f"missing mapping json: {mp}")
    if not sp.is_file():
        raise SystemExit(f"missing survivor json: {sp}")

    m = load(mp)
    s = load(sp)
    mapping = m.get("mapping") if isinstance(m.get("mapping"), list) else []
    survivors = s.get("survivors") if isinstance(s.get("survivors"), list) else []
    top = survivors[0] if survivors else {}

    sequence_len = len(mapping)
    ci_low = float(top.get("ci_low_defense_contrib", 0.0) or 0.0)
    fusion = float(top.get("fusion_candidate_score", 0.0) or 0.0)
    resonance = clamp01(0.4 * (sequence_len / 6.0) + 0.3 * ci_low + 0.3 * fusion)

    out = {
        "schema": "atom_resonance_report_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "seed_symbol": m.get("seed_symbol"),
        "sequence_length": sequence_len,
        "resonance_score": resonance,
        "supporting_survivor": {
            "candidate_id": top.get("candidate_id"),
            "source_node_id": top.get("source_node_id"),
            "ci_low_defense_contrib": ci_low,
            "fusion_candidate_score": fusion,
        },
        "interpretation": (
            "High resonance implies symbol-level boundary/transgression sequence is structurally coherent with current survivor pattern."
            if resonance >= 0.65
            else "Moderate resonance; keep in research lane and require additional falsification."
        ),
        "sources": {"mapping_json": str(mp), "survivor_json": str(sp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

