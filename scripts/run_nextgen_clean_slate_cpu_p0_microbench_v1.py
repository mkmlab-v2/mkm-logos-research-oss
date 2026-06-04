#!/usr/bin/env python3
"""P0: single-host CPU multithread lookup micro-bench (research_only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/p0_microbench_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_blocks(block_count: int, block_kb: int) -> list[bytes]:
    seed = b"nextgen_clean_slate_cpu_v1"
    blocks: list[bytes] = []
    for i in range(block_count):
        h = hashlib.sha256(seed + str(i).encode()).digest()
        unit = (h * ((block_kb * 1024 // len(h)) + 1))[: block_kb * 1024]
        blocks.append(unit)
    return blocks


def _lookup_block(block: bytes, keys: list[int]) -> int:
    acc = 0
    for k in keys:
        idx = k % len(block)
        acc ^= block[idx]
    return acc & 0xFFFF


def _worker(block: bytes, key_batch: list[int]) -> dict:
    t0 = time.perf_counter()
    hits = sum(_lookup_block(block, [k]) for k in key_batch)
    elapsed = time.perf_counter() - t0
    return {"hits": hits, "elapsed_s": elapsed, "bytes": len(block)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--block-count", type=int, default=32)
    ap.add_argument("--block-kb", type=int, default=256)
    ap.add_argument("--keys-per-block", type=int, default=500)
    ap.add_argument("--workers", type=int, default=0, help="0 = auto from cpu_count")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    workers = args.workers or max(2, min(8, (os.cpu_count() or 4) - 1))
    blocks = _make_blocks(args.block_count, args.block_kb)
    keys = list(range(args.keys_per_block))

    t0 = time.perf_counter()
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(_worker, b, keys) for b in blocks]
        for fut in as_completed(futs):
            rows.append(fut.result())
    total_s = time.perf_counter() - t0

    total_bytes = sum(r["bytes"] for r in rows)
    total_hits = sum(r["hits"] for r in rows)
    throughput_mb_s = (total_bytes / (1024 * 1024)) / total_s if total_s > 0 else 0.0

    doc = {
        "schema": "nextgen_clean_slate_cpu_p0_microbench_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "config": {
            "block_count": args.block_count,
            "block_kb": args.block_kb,
            "keys_per_block": args.keys_per_block,
            "workers": workers,
            "cpu_logical": os.cpu_count(),
        },
        "results": {
            "elapsed_s": round(total_s, 4),
            "throughput_mb_s": round(throughput_mb_s, 3),
            "lookup_ops": total_hits,
            "lookup_ops_per_s": round(total_hits / total_s, 1) if total_s else 0.0,
        },
        "note": "Synthetic weight-block lookup; not Golden-40 compression",
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "wrote": str(args.out_json),
                "throughput_mb_s": doc["results"]["throughput_mb_s"],
                "workers": workers,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
