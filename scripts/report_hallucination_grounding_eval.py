#!/usr/bin/env python3
"""Aggregate hallucination proxy metrics from vLLM benchmark JSON files (glob)."""
from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "hallucination_grounding_eval_v1"
MIN_SAMPLE_ZERO = 1000


def _collect_from_file(path: Path, target_lane: str) -> tuple[list[str], list[dict[str, Any]]]:
    source_reports: list[str] = []
    rows: list[dict[str, Any]] = []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return source_reports, rows
    source_reports.append(str(path))
    for r in list(doc.get("rows") or []):
        if str(r.get("lane") or "") == target_lane:
            rows.append(r)
    return source_reports, rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--target-lane", default="candidate")
    ap.add_argument("--input-glob", required=True)
    args = ap.parse_args()

    out = Path(args.output).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    root = Path(".").resolve()

    paths = sorted({Path(p) for p in glob.glob(args.input_glob)})
    bench_auto = root / "reports/constitution/btrack_pilot/vllm_ab_benchmark_auto_latest.json"
    bench_latest = root / "reports/constitution/btrack_pilot/vllm_ab_benchmark_latest.json"
    for extra in (bench_auto, bench_latest):
        if extra.is_file() and extra not in paths:
            paths.insert(0, extra)

    all_sources: list[str] = []
    merged_rows: list[dict[str, Any]] = []
    for p in paths:
        if not p.is_file():
            continue
        srcs, part = _collect_from_file(p, args.target_lane)
        all_sources.extend(srcs)
        merged_rows.extend(part)

    quality_rows = [r for r in merged_rows if r.get("quality_pass") is not None]
    passes = [r for r in quality_rows if r.get("quality_pass")]
    fail_count = len(quality_rows) - len(passes)
    sample_count = len(quality_rows)
    pass_rate = (len(passes) / sample_count) if sample_count else None
    hallucination_proxy_rate = (1.0 - pass_rate) if pass_rate is not None else None

    ts = datetime.now(timezone.utc).isoformat()
    primary = str(bench_auto) if bench_auto.is_file() else (
        str(paths[0]) if paths else str(bench_latest)
    )

    payload = {
        "schema": SCHEMA,
        "ts_utc": ts,
        "source_report": primary,
        "source_reports": all_sources or ([primary] if primary else []),
        "source_report_count": len(all_sources or ([primary] if primary else [])),
        "target_lane": args.target_lane,
        "sample_count": sample_count,
        "quality_pass_count": len(passes),
        "quality_fail_count": fail_count,
        "quality_pass_rate": pass_rate,
        "hallucination_proxy_rate": hallucination_proxy_rate,
        "min_sample_for_zero_claim": MIN_SAMPLE_ZERO,
        "zero_claim_eligible": sample_count >= MIN_SAMPLE_ZERO and sample_count > 0 and fail_count == 0,
        "note": "Proxy metric from expected-substring grounding checks, not a full factuality audit.",
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out} (samples={sample_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
