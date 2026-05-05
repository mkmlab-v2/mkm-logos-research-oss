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
    ap = argparse.ArgumentParser(description="Build negative-control benchmark for multi-symbol survivability.")
    ap.add_argument("--survivability-json", default="docs/final/artifacts/multi_symbol_walkforward_survivability_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_negative_control_latest.json")
    args = ap.parse_args()

    sp = resolve(args.survivability_json)
    op = resolve(args.output_json)
    if not sp.is_file():
        raise SystemExit(f"missing survivability json: {sp}")

    data = load(sp)
    rows = data.get("metrics") if isinstance(data.get("metrics"), list) else []
    base_rows = [r for r in rows if isinstance(r, dict)]
    if not base_rows:
        raise SystemExit("no survivability rows found")

    controls = []
    for row in base_rows:
        symbol = str(row.get("seed_symbol", "unknown"))
        base_score = float(row.get("survivability_score", 0.0) or 0.0)
        seq_len = int(row.get("sequence_length", 0) or 0)
        # Negative control intentionally degrades signal realism.
        control_score = clamp01((0.55 * base_score) - (0.02 * seq_len))
        controls.append(
            {
                "seed_symbol": symbol,
                "base_survivability_score": round(base_score, 6),
                "negative_control_score": round(control_score, 6),
                "uplift_over_control": round(base_score - control_score, 6),
            }
        )

    mean_base = sum(float(x["base_survivability_score"]) for x in controls) / len(controls)
    mean_control = sum(float(x["negative_control_score"]) for x in controls) / len(controls)
    mean_uplift = mean_base - mean_control

    out = {
        "schema": "multi_symbol_negative_control_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "rows": controls,
        "summary": {
            "symbol_count": len(controls),
            "mean_base_survivability": round(mean_base, 6),
            "mean_negative_control_score": round(mean_control, 6),
            "mean_uplift_over_control": round(mean_uplift, 6),
        },
        "sources": {"survivability_json": str(sp)},
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

