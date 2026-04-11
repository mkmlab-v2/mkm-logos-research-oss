#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.7, L:0.5, K:0.8, M:0.2}
# Balance: 88
# Purpose: Aggregate per-case lost tokens from compression_jaccard_loss_patterns into frequency tables.
# Keywords: compression, jaccard, aggregation, codebook
"""Aggregate token loss patterns (global / by shard / by domain)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_IN = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_latest.json"
DEFAULT_OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_aggregated_v1.json"


def _top(counter: Counter[str], n: int) -> list[dict[str, Any]]:
    return [{"token": w, "count": c} for w, c in counter.most_common(n)]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Aggregate Jaccard loss token frequencies.")
    p.add_argument("--input", type=Path, default=DEFAULT_IN, help="Path to compression_jaccard_loss_patterns_*.json")
    p.add_argument("--output", type=Path, default=DEFAULT_OUT, help="Output JSON path")
    p.add_argument("--top", type=int, default=80, help="How many tokens to keep per table")
    return p


def main() -> int:
    args = _parser().parse_args()
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    cases = doc.get("cases") or []

    global_c: Counter[str] = Counter()
    by_shard: dict[str, Counter[str]] = defaultdict(Counter)
    by_domain: dict[str, Counter[str]] = defaultdict(Counter)

    for row in cases:
        lost = row.get("words_lost_sample") or []
        if not isinstance(lost, list):
            continue
        sid = str(row.get("shard_id") or "unknown")
        dom = str(row.get("domain") or "unknown")
        for t in lost:
            if not isinstance(t, str) or not t.strip():
                continue
            w = t.strip()
            global_c[w] += 1
            by_shard[sid][w] += 1
            by_domain[dom][w] += 1

    top_n = max(1, int(args.top))
    out: dict[str, Any] = {
        "schema": "compression_jaccard_loss_patterns_aggregated_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "loss_patterns": str(args.input.resolve()),
            "sla_track": doc.get("sla_track"),
        },
        "summary": {
            "case_count": len(cases),
            "unique_tokens_lost": len(global_c),
            "total_token_occurrences": int(sum(global_c.values())),
        },
        "global_top": _top(global_c, top_n),
        "by_shard_id": {k: _top(v, top_n) for k, v in sorted(by_shard.items())},
        "by_domain": {k: _top(v, top_n) for k, v in sorted(by_domain.items())},
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
