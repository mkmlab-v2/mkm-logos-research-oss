#!/usr/bin/env python3
"""Token bench: multi-res fills low-res inject vs full high-res summaries."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "reports/multi_res_fills_index_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/multi_res_fills_token_bench_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_tokens(text: str) -> tuple[int, str]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text)), "tiktoken:cl100k_base"
    except Exception:
        return max(1, len(text) // 4), "chars_div4_fallback"


def _low_res_inject_text(doc: dict[str, Any]) -> str:
    meta = doc.get("meta") or {}
    daily = (doc.get("low_res") or {}).get("daily_by_utc_date") or {}
    lines = [
        f"n_fill_rows: {meta.get('n_fill_rows')}",
        f"n_daily_buckets: {meta.get('n_daily_buckets')}",
        f"trades_source: {meta.get('trades_source')}",
        "research_only: true",
    ]
    for d, bucket in sorted(daily.items())[:7]:
        lines.append(f"{d}: fill_count={bucket.get('fill_count')}")
    return "\n".join(lines)


def _full_high_res_text(doc: dict[str, Any]) -> str:
    return json.dumps(doc.get("high_res") or {}, ensure_ascii=False)


def build_bench(doc: dict[str, Any]) -> dict[str, Any]:
    low_text = _low_res_inject_text(doc)
    full_text = _full_high_res_text(doc)
    low_tok, method = _count_tokens(low_text)
    full_tok, _ = _count_tokens(full_text)
    saved = full_tok - low_tok
    ratio = round(saved / full_tok, 4) if full_tok else 0.0
    return {
        "schema": "multi_res_fills_token_bench_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] token reduction ≠ answer quality equivalence",
        "n_fill_rows": (doc.get("meta") or {}).get("n_fill_rows"),
        "low_res_inject": {"char_count": len(low_text), "tokens": low_tok, "method": method},
        "full_high_res_summaries": {"char_count": len(full_text), "tokens": full_tok, "method": method},
        "delta": {
            "tokens_saved": saved,
            "reduction_ratio": ratio,
            "reduction_percent": round(ratio * 100, 2),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    if not args.index.is_file():
        print(f"FAIL: missing index {args.index}", flush=True)
        return 1
    doc = json.loads(args.index.read_text(encoding="utf-8-sig"))
    bench = build_bench(doc)
    args.out.write_text(json.dumps(bench, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(bench.get("delta"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
