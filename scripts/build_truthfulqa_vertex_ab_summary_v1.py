#!/usr/bin/env python3
"""Derive truthfulqa_vertex_ab_summary_latest.json from benchmark_latest (no rows)."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build TruthfulQA Vertex A/B summary from benchmark JSON")
    ap.add_argument(
        "--bench-json",
        type=Path,
        default=Path("docs/final/artifacts/truthfulqa_vertex_ab_benchmark_latest.json"),
    )
    ap.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/truthfulqa_vertex_ab_summary_latest.json"),
    )
    args = ap.parse_args()

    bench = _read_json(args.bench_json)
    n = (bench.get("baseline") or {}).get("count")
    out: dict[str, Any] = {
        "schema": "truthfulqa_vertex_ab_summary_v1",
        "generated_at_utc": bench.get("generated_at_utc") or _now_utc_iso(),
        "summary_derived_at_utc": _now_utc_iso(),
        "source_benchmark": str(args.bench_json.resolve()),
        "research_only": bench.get("research_only", True),
        "billing_surface": bench.get("billing_surface"),
        "vertex_project": bench.get("vertex_project"),
        "vertex_location": bench.get("vertex_location"),
        "dataset_jsonl": bench.get("dataset_jsonl"),
        "baseline_model": bench.get("baseline_model"),
        "candidate_model": bench.get("candidate_model"),
        "baseline": bench.get("baseline"),
        "candidate": bench.get("candidate"),
        "comparative": bench.get("comparative"),
        "note": (
            f"Derived from benchmark only (no per-row payload). "
            f"Eval rows per lane={n!r}."
        ),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
