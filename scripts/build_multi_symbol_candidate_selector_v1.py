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
    ap = argparse.ArgumentParser(description="Select top multi-symbol insight candidates.")
    ap.add_argument("--multi-symbol-json", default="docs/final/artifacts/multi_symbol_resonance_4d_latest.json")
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--min-coupling", type=float, default=0.65)
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_candidate_selector_latest.json")
    args = ap.parse_args()

    mp = resolve(args.multi_symbol_json)
    op = resolve(args.output_json)
    if not mp.is_file():
        raise SystemExit(f"missing multi symbol json: {mp}")

    data = load(mp)
    rows = data.get("symbols") if isinstance(data.get("symbols"), list) else []
    ranked = [r for r in rows if isinstance(r, dict)]
    ranked = sorted(ranked, key=lambda r: float(r.get("coupling_strength", 0.0) or 0.0), reverse=True)
    selected = []
    for row in ranked:
        c = float(row.get("coupling_strength", 0.0) or 0.0)
        if c < args.min_coupling:
            continue
        selected.append(
            {
                "seed_symbol": row.get("seed_symbol"),
                "coupling_strength": round(c, 6),
                "resonance_score": round(float(row.get("resonance_score", 0.0) or 0.0), 6),
                "sequence_length": int(row.get("sequence_length", 0) or 0),
                "source_artifact": "multi_symbol_resonance_4d_latest.json",
            }
        )
        if len(selected) >= max(args.top_k, 1):
            break

    out = {
        "schema": "multi_symbol_candidate_selector_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "thresholds": {"top_k": max(args.top_k, 1), "min_coupling": float(args.min_coupling)},
        "selected_count": len(selected),
        "selected": selected,
        "sources": {"multi_symbol_json": str(mp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

