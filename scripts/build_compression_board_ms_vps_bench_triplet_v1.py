#!/usr/bin/env python3
"""Aggregate 3+ VPS bench_l1 runs for RQ-017 acceptance (research_only)."""

from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RUNS_GLOB = "bench_l1_api_load_vps_*.json"
OUT_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "compression_board_ms_vps_bench_triplet_v1_latest.json"


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _latency(doc: dict[str, Any]) -> dict[str, float | None]:
    lat = doc.get("latency_ms") if isinstance(doc.get("latency_ms"), dict) else {}
    return {
        "p50_ms": lat.get("p50"),
        "p95_ms": lat.get("p95"),
        "p99_ms": lat.get("p99"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--runs-dir",
        type=Path,
        default=ROOT / "docs" / "final" / "artifacts" / "bench_runs",
    )
    ap.add_argument("--min-runs", type=int, default=3)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    paths = sorted(args.runs_dir.glob(RUNS_GLOB), key=lambda p: p.name)
    rows: list[dict[str, Any]] = []
    for p in paths:
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        lat = _latency(doc)
        rows.append(
            {
                "run_file": str(p.relative_to(ROOT)).replace("\\", "/"),
                "generated_at_utc": doc.get("generated_at_utc"),
                "bench_environment": doc.get("bench_environment"),
                "error_rate": doc.get("error_rate"),
                **lat,
            }
        )

    p95_vals = [r["p95_ms"] for r in rows if isinstance(r.get("p95_ms"), (int, float))]
    ok_count = len(rows) >= args.min_runs and all(r.get("error_rate") == 0 for r in rows)
    doc_out: dict[str, Any] = {
        "schema": "compression_board_ms_vps_bench_triplet_v1",
        "generated_at_utc": _utc_now_z(),
        "status": "[HYPO]",
        "hypothesis_tier": "B",
        "track_wall": "b_track_research_only",
        "rq": "RQ-017",
        "runs": rows,
        "derived": {
            "run_count": len(rows),
            "min_runs_required": args.min_runs,
            "triplet_ok": ok_count,
            "p95_ms_median": statistics.median(p95_vals) if p95_vals else None,
            "p95_ms_min": min(p95_vals) if p95_vals else None,
            "p95_ms_max": max(p95_vals) if p95_vals else None,
        },
        "summary_vps_latest": "docs/final/artifacts/bench_l1_api_load_summary_vps_latest.json",
        "note": "Use generated_at_utc on each run for OEM citations; not comparable to 2026-04-10 snapshot without same load profile.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc_out, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = {"out": str(args.out), "triplet_ok": ok_count, "run_count": len(rows)}
    if args.stdout_only:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"WROTE: {args.out}")
        print(json.dumps(payload, ensure_ascii=False))
    return 0 if ok_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
