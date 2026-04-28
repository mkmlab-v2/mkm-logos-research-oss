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


def symbol_axis_overrides(symbol: str) -> dict[str, float]:
    table = {
        "tree_of_knowledge_good_evil": {"S": 0.84, "L": 0.86, "K": 0.77, "M": 0.81},
        "babel_tower": {"S": 0.79, "L": 0.73, "K": 0.75, "M": 0.70},
        "exodus_return": {"S": 0.68, "L": 0.74, "K": 0.66, "M": 0.58},
    }
    return table.get(symbol, {"S": 0.70, "L": 0.70, "K": 0.70, "M": 0.70})


def main() -> int:
    ap = argparse.ArgumentParser(description="Build multi-symbol resonance + 4D coupling report.")
    ap.add_argument("--registry-json", default="docs/final/artifacts/atom_anchor_registry_v1.json")
    ap.add_argument("--survivor-json", default="docs/final/artifacts/insight_survivor_candidates_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_resonance_4d_latest.json")
    args = ap.parse_args()

    rp = resolve(args.registry_json)
    sp = resolve(args.survivor_json)
    op = resolve(args.output_json)
    if not rp.is_file():
        raise SystemExit(f"missing registry json: {rp}")
    if not sp.is_file():
        raise SystemExit(f"missing survivor json: {sp}")

    reg = load(rp)
    sv = load(sp)
    seq_map = reg.get("seed_symbol_sequences") if isinstance(reg.get("seed_symbol_sequences"), dict) else {}
    survivors = sv.get("survivors") if isinstance(sv.get("survivors"), list) else []
    top = survivors[0] if survivors else {}
    ci_low = float(top.get("ci_low_defense_contrib", 0.0) or 0.0)
    fusion = float(top.get("fusion_candidate_score", 0.0) or 0.0)

    rows: list[dict[str, Any]] = []
    for symbol, sequence in seq_map.items():
        if not isinstance(sequence, list):
            continue
        seq_len = len(sequence)
        resonance = clamp01(0.4 * (seq_len / 6.0) + 0.3 * ci_low + 0.3 * fusion)
        axes = symbol_axis_overrides(str(symbol))
        s_val = clamp01((axes["S"] * 0.65) + (resonance * 0.35))
        l_val = clamp01((axes["L"] * 0.65) + (resonance * 0.35))
        k_val = clamp01((axes["K"] * 0.65) + (resonance * 0.35))
        m_val = clamp01((axes["M"] * 0.65) + (resonance * 0.35))
        coupling = clamp01((s_val + l_val + k_val + m_val) / 4.0)
        rows.append(
            {
                "seed_symbol": str(symbol),
                "sequence_length": seq_len,
                "sequence": [str(x) for x in sequence],
                "resonance_score": round(resonance, 6),
                "vector_4d": {"S": round(s_val, 6), "L": round(l_val, 6), "K": round(k_val, 6), "M": round(m_val, 6)},
                "coupling_strength": round(coupling, 6),
                "policy": {"research_only": True, "allow_execution_trigger": False},
            }
        )

    ranked = sorted(rows, key=lambda x: float(x.get("coupling_strength", 0.0)), reverse=True)
    out = {
        "schema": "multi_symbol_resonance_4d_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "survivor_snapshot": {
            "candidate_id": top.get("candidate_id"),
            "source_node_id": top.get("source_node_id"),
            "ci_low_defense_contrib": round(ci_low, 6),
            "fusion_candidate_score": round(fusion, 6),
        },
        "symbols": ranked,
        "summary": {
            "symbol_count": len(ranked),
            "top_symbol_by_coupling": (ranked[0].get("seed_symbol") if ranked else None),
            "mean_coupling_strength": round(
                clamp01(sum(float(r.get("coupling_strength", 0.0)) for r in ranked) / max(len(ranked), 1)),
                6,
            ),
        },
        "sources": {"registry_json": str(rp), "survivor_json": str(sp)},
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

