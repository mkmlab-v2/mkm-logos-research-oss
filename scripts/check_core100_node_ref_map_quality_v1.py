#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.3, M:0.6}
# Balance: 90
# Purpose: Evaluate core100 node reference map quality and emit gate report.
# Keywords: quality gate, core100, mapping, btrack
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def main() -> int:
    ap = argparse.ArgumentParser(description="Check quality status distribution for core100 node->verse mapping.")
    ap.add_argument("--map-json", default="docs/final/artifacts/core100_node_ref_map_template_v1.json")
    ap.add_argument("--min-verified-ratio", type=float, default=0.6)
    ap.add_argument("--output-json", default="docs/final/artifacts/core100_node_ref_map_quality_gate_latest.json")
    args = ap.parse_args()

    map_path = resolve(args.map_json)
    out_path = resolve(args.output_json)
    if not map_path.is_file():
        raise SystemExit(f"missing map json: {map_path}")

    data = json.loads(map_path.read_text(encoding="utf-8"))
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise SystemExit("invalid map json: rows must be list")

    status_counts: dict[str, int] = {}
    resolved_count = 0
    verified_count = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        if str(row.get("verse_ref", "")).strip():
            resolved_count += 1
        if status == "verified_manual":
            verified_count += 1

    total = len(rows)
    resolved_ratio = (resolved_count / total) if total else 0.0
    verified_ratio = (verified_count / total) if total else 0.0
    pass_gate = verified_ratio >= float(args.min_verified_ratio)

    out: dict[str, Any] = {
        "schema": "core100_node_ref_map_quality_gate_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "inputs": {
            "map_json": str(map_path),
            "min_verified_ratio": float(args.min_verified_ratio),
        },
        "counts": {
            "row_total": total,
            "resolved_count": resolved_count,
            "verified_manual_count": verified_count,
            "status_counts": status_counts,
        },
        "ratios": {
            "resolved_ratio": round(resolved_ratio, 6),
            "verified_manual_ratio": round(verified_ratio, 6),
        },
        "gate": {
            "pass": pass_gate,
            "reason": "verified_manual_ratio_below_threshold" if not pass_gate else "ok",
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
