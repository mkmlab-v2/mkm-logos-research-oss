#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_roi_estimate_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--monthly-requests", type=int, required=True)
    ap.add_argument("--avg-input-tokens", type=float, required=True)
    ap.add_argument("--avg-output-tokens", type=float, required=True)
    ap.add_argument("--input-token-price-per-1k-usd", type=float, required=True)
    ap.add_argument("--output-token-price-per-1k-usd", type=float, required=True)
    ap.add_argument("--pointer-input-reduction-ratio", type=float, default=0.90)
    ap.add_argument("--pointer-overhead-usd-per-month", type=float, default=0.0)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    req = max(0, int(args.monthly_requests))
    in_tok = max(0.0, float(args.avg_input_tokens))
    out_tok = max(0.0, float(args.avg_output_tokens))
    in_price = max(0.0, float(args.input_token_price_per_1k_usd))
    out_price = max(0.0, float(args.output_token_price_per_1k_usd))
    reduction = min(0.999, max(0.0, float(args.pointer_input_reduction_ratio)))
    overhead = max(0.0, float(args.pointer_overhead_usd_per_month))

    baseline_input_tokens = req * in_tok
    baseline_output_tokens = req * out_tok
    baseline_input_cost = (baseline_input_tokens / 1000.0) * in_price
    baseline_output_cost = (baseline_output_tokens / 1000.0) * out_price
    baseline_total = baseline_input_cost + baseline_output_cost

    pointer_input_tokens = baseline_input_tokens * (1.0 - reduction)
    pointer_output_tokens = baseline_output_tokens
    pointer_input_cost = (pointer_input_tokens / 1000.0) * in_price
    pointer_output_cost = (pointer_output_tokens / 1000.0) * out_price
    pointer_total = pointer_input_cost + pointer_output_cost + overhead

    monthly_saving_usd = baseline_total - pointer_total
    monthly_saving_rate = (monthly_saving_usd / baseline_total) if baseline_total > 0 else 0.0

    out_doc = {
        "schema": "pointerguard_roi_estimate_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "monthly_requests": req,
            "avg_input_tokens": in_tok,
            "avg_output_tokens": out_tok,
            "input_token_price_per_1k_usd": in_price,
            "output_token_price_per_1k_usd": out_price,
            "pointer_input_reduction_ratio": reduction,
            "pointer_overhead_usd_per_month": overhead,
        },
        "baseline": {
            "input_tokens_monthly": baseline_input_tokens,
            "output_tokens_monthly": baseline_output_tokens,
            "input_cost_usd_monthly": baseline_input_cost,
            "output_cost_usd_monthly": baseline_output_cost,
            "total_cost_usd_monthly": baseline_total,
        },
        "pointerguard": {
            "input_tokens_monthly": pointer_input_tokens,
            "output_tokens_monthly": pointer_output_tokens,
            "input_cost_usd_monthly": pointer_input_cost,
            "output_cost_usd_monthly": pointer_output_cost,
            "overhead_usd_monthly": overhead,
            "total_cost_usd_monthly": pointer_total,
        },
        "roi": {
            "monthly_saving_usd": monthly_saving_usd,
            "monthly_saving_rate": monthly_saving_rate,
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "monthly_saving_usd": monthly_saving_usd}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
