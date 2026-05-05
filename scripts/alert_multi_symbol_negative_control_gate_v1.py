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
    ap = argparse.ArgumentParser(description="Evaluate negative-control gate for multi-symbol pipeline.")
    ap.add_argument("--negative-control-json", default="docs/final/artifacts/multi_symbol_negative_control_latest.json")
    ap.add_argument("--min-mean-uplift", type=float, default=0.10)
    ap.add_argument("--output-json", default="docs/final/artifacts/multi_symbol_negative_control_gate_latest.json")
    args = ap.parse_args()

    np = resolve(args.negative_control_json)
    op = resolve(args.output_json)
    if not np.is_file():
        raise SystemExit(f"missing negative control json: {np}")

    data = load(np)
    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    mean_uplift = float(summary.get("mean_uplift_over_control", 0.0) or 0.0)
    pass_gate = mean_uplift >= float(args.min_mean_uplift)

    out = {
        "schema": "multi_symbol_negative_control_gate_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "inputs": {
            "negative_control_json": str(np),
            "min_mean_uplift": float(args.min_mean_uplift),
        },
        "gate_eval": {
            "pass": pass_gate,
            "should_alert": not pass_gate,
            "promotion_hold": not pass_gate,
            "reasons": [] if pass_gate else ["negative_control_uplift_below_threshold"],
        },
        "metrics": {
            "mean_uplift_over_control": round(mean_uplift, 6),
        },
    }
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

