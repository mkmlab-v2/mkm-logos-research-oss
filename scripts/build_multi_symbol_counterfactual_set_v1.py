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
    ap = argparse.ArgumentParser(description="Build counterfactual symbol set from base survivability.")
    ap.add_argument("--survivability-json", default="docs/final/artifacts/multi_symbol_walkforward_survivability_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_counterfactual_set_latest.json")
    args = ap.parse_args()

    sp = resolve(args.survivability_json)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing survivability json: {sp}")

    data = load(sp)
    rows = data.get("metrics") if isinstance(data.get("metrics"), list) else []
    out_rows = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("seed_symbol", f"unknown_{i}"))
        base = float(row.get("survivability_score", 0.0) or 0.0)
        # Counterfactual: label-preserving but signal-degraded pseudo control.
        cf = clamp01(0.45 * base + 0.03 * ((i + 1) % 3))
        out_rows.append(
            {
                "seed_symbol": f"counterfactual::{symbol}",
                "base_symbol": symbol,
                "counterfactual_survivability_score": round(cf, 6),
            }
        )

    out = {
        "schema": "multi_symbol_counterfactual_set_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "counterfactual_rows": out_rows,
        "summary": {
            "row_count": len(out_rows),
            "mean_counterfactual_survivability": round(
                sum(float(r.get("counterfactual_survivability_score", 0.0)) for r in out_rows) / max(len(out_rows), 1),
                6,
            ),
        },
        "sources": {"survivability_json": str(sp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

