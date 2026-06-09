#!/usr/bin/env python3
"""Fusion bench: ops memory token pattern + fills multi-res index ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS_BENCH = ROOT / "reports/mkm_ops_memory_index_token_bench_v1_latest.json"
FILLS_BENCH = ROOT / "reports/multi_res_fills_token_bench_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/multi_res_fusion_bench_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    ops = _read(OPS_BENCH)
    fills = _read(FILLS_BENCH)
    ops_off = (ops.get("resume_pack_inject_off") or {}).get("tokens")
    ops_full = (ops.get("full_anchor_slices") or {}).get("tokens")
    fills_low = (fills.get("low_res_inject") or {}).get("tokens")
    fills_full = (fills.get("full_high_res_summaries") or {}).get("tokens")

    combined_low = (ops_off or 0) + (fills_low or 0)
    combined_full = (ops_full or 0) + (fills_full or 0)
    saved = combined_full - combined_low
    ratio = round(saved / combined_full, 4) if combined_full else 0.0

    doc = {
        "schema": "multi_res_fusion_bench_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] fused token bench — operational inject scope only",
        "sources": {
            "ops_memory_bench": str(OPS_BENCH.relative_to(ROOT)).replace("\\", "/"),
            "fills_bench": str(FILLS_BENCH.relative_to(ROOT)).replace("\\", "/"),
        },
        "ops_memory": {
            "inject_off_tokens": ops_off,
            "full_slices_tokens": ops_full,
            "reduction_percent": (ops.get("delta_vs_full_slices") or {}).get("reduction_percent"),
        },
        "fills": {
            "low_res_tokens": fills_low,
            "full_high_res_tokens": fills_full,
            "reduction_percent": (fills.get("delta") or {}).get("reduction_percent"),
        },
        "fused": {
            "combined_low_res_tokens": combined_low,
            "combined_full_tokens": combined_full,
            "tokens_saved": saved,
            "reduction_ratio": ratio,
            "reduction_percent": round(ratio * 100, 2),
        },
        "quality_disclaimer": "Token reduction does not imply semantic equivalence or hallucination elimination.",
    }
    args.out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc["fused"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
