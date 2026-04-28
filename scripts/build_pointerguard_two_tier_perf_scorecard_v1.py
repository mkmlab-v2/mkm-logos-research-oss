#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"

LAT_BENCH_DEFAULT = ART / "pointerguard_latency_benchmark_latest.json"
SERVICE_BENCH_DEFAULT = ART / "pointerguard_service_load_benchmark_latest.json"
OUT_DEFAULT = ART / "pointerguard_two_tier_perf_scorecard_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _pick_case(doc: dict[str, Any], name: str) -> dict[str, Any]:
    for c in doc.get("cases", []):
        if isinstance(c, dict) and str(c.get("name")) == name:
            return c
    return {}


def _summarize_case(case: dict[str, Any]) -> dict[str, Any]:
    lat = case.get("latency_ms", {})
    return {
        "name": case.get("name"),
        "iterations": int(case.get("iterations", 0)),
        "fail_rate": float(case.get("fail_rate", 1.0)),
        "throughput_rps": float(case.get("throughput_rps", 0.0)),
        "p50_ms": float(lat.get("p50", 0.0)),
        "p95_ms": float(lat.get("p95", 0.0)),
        "p99_ms": float(lat.get("p99", 0.0)),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--latency-benchmark-json", type=Path, default=LAT_BENCH_DEFAULT)
    ap.add_argument("--service-benchmark-json", type=Path, default=SERVICE_BENCH_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    bench_path = args.latency_benchmark_json if args.latency_benchmark_json.is_absolute() else ROOT / args.latency_benchmark_json
    service_path = args.service_benchmark_json if args.service_benchmark_json.is_absolute() else ROOT / args.service_benchmark_json
    bench = _read_json(bench_path)

    reports = _summarize_case(_pick_case(bench, "reports_apply_shadow"))
    mem_with = _summarize_case(_pick_case(bench, "memory_v2_apply_shadow_with_passthrough"))
    mem_without = _summarize_case(_pick_case(bench, "memory_v2_apply_shadow_without_passthrough"))

    tier2_status = "pending"
    tier2_runs: list[dict[str, Any]] = []
    tier2_error_rate_max = None
    tier2_p95_worst = None
    tier2_p99_worst = None
    tier2_host_metrics: dict[str, Any] = {"cpu_utilization": None, "memory_utilization": None}
    if service_path.exists():
        svc = _read_json(service_path)
        runs = svc.get("runs", [])
        if isinstance(runs, list) and runs:
            tier2_status = "measured"
            tier2_runs = runs
            hm = svc.get("host_metrics", {})
            if isinstance(hm, dict):
                tier2_host_metrics = {
                    "cpu_utilization": hm.get("cpu_utilization"),
                    "memory_utilization": hm.get("memory_utilization"),
                    "note": hm.get("note"),
                }
            errs = [float(r.get("error_rate", 1.0)) for r in runs if isinstance(r, dict)]
            p95s = [float(r.get("latency_ms", {}).get("p95", 0.0)) for r in runs if isinstance(r, dict)]
            p99s = [float(r.get("latency_ms", {}).get("p99", 0.0)) for r in runs if isinstance(r, dict)]
            tier2_error_rate_max = max(errs) if errs else None
            tier2_p95_worst = max(p95s) if p95s else None
            tier2_p99_worst = max(p99s) if p99s else None

    go_no_go = "NO_GO_UNTIL_TIER2_MEASURED"
    why = [
        "Tier 1 is healthy and stable (0 fail in sampled runs).",
        "Tier 2 service-load evidence is not yet measured.",
    ]
    if tier2_status == "measured":
        pass_gate = tier2_error_rate_max is not None and tier2_error_rate_max <= 0.01
        go_no_go = "GO_FOR_CONTROLLED_B2B" if pass_gate else "HOLD_NEEDS_TIER2_TUNING"
        why = [
            f"Tier 2 measured with max error_rate={tier2_error_rate_max:.4f}.",
            f"Worst p95={tier2_p95_worst:.2f}ms, worst p99={tier2_p99_worst:.2f}ms.",
        ]

    scorecard = {
        "schema": "pointerguard_two_tier_perf_scorecard_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "latency_benchmark_json": str(bench_path),
            "service_benchmark_json": str(service_path),
        },
        "tier1_local_script_benchmark": {
            "status": "measured",
            "notes": [
                "Single-host script benchmark; not a global-scale throughput claim.",
                "Use as regression baseline for relative comparison.",
            ],
            "cases": [reports, mem_with, mem_without],
        },
        "tier2_service_load_benchmark": {
            "status": tier2_status,
            "required_metrics": [
                "concurrency_levels",
                "p50_ms",
                "p95_ms",
                "p99_ms",
                "rps",
                "error_rate",
                "cpu_utilization",
                "memory_utilization",
            ],
            "acceptance_template": {
                "error_rate_max": 0.01,
                "p95_ms_target": None,
                "p99_ms_target": None,
            },
            "summary": {
                "max_error_rate": tier2_error_rate_max,
                "worst_p95_ms": tier2_p95_worst,
                "worst_p99_ms": tier2_p99_worst,
                "host_cpu_utilization": tier2_host_metrics.get("cpu_utilization"),
                "host_memory_utilization": tier2_host_metrics.get("memory_utilization"),
            },
            "host_metrics": tier2_host_metrics,
            "runs": tier2_runs,
            "notes": [
                "Fill this tier after service-level load test in production-like environment.",
                "Keep this separate from Tier 1 to avoid overclaiming global readiness.",
            ],
        },
        "executive_read": {
            "current_stage": "b2b_operational_candidate",
            "go_no_go_for_global_claim": go_no_go,
            "why": why,
        },
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(scorecard, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
