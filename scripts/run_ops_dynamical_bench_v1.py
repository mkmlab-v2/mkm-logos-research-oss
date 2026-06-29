#!/usr/bin/env python3
"""Ops dynamical bench L0 — calm/watch/stress/crisis from disk SSOT proxies [HYPO · B-track]."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops_dynamical_bench_v1_lib import (  # noqa: E402
    DEFAULT_JSONL,
    DEFAULT_OUT,
    append_jsonl_row,
    build_report,
    timeseries_row_from_bench,
)

OUT = DEFAULT_OUT


def main() -> int:
    parser = argparse.ArgumentParser(description="Build ops dynamical bench L0 artifact")
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--prior-stress", type=float, default=None)
    parser.add_argument("--append-jsonl", dest="append_jsonl", action="store_true", default=True)
    parser.add_argument("--no-append-jsonl", dest="append_jsonl", action="store_false")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    args = parser.parse_args()

    doc = build_report(prior_stress=args.prior_stress)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.append_jsonl:
        append_jsonl_row(args.jsonl, timeseries_row_from_bench(doc))

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "stage": doc["state_machine"]["stage"],
                "jsonl_appended": bool(args.append_jsonl),
                "jsonl": str(args.jsonl) if args.append_jsonl else None,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
