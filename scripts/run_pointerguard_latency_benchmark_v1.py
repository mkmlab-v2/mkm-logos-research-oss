#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_latency_benchmark_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    idx = max(0, min(len(values) - 1, int(round((p / 100.0) * (len(values) - 1)))))
    return sorted(values)[idx]


def _run_once(cmd: list[str]) -> tuple[int, float]:
    t0 = time.perf_counter()
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    return cp.returncode, dt_ms


def _bench_case(name: str, cmd: list[str], iterations: int) -> dict[str, Any]:
    latencies: list[float] = []
    ok = 0
    fail = 0
    t0 = time.perf_counter()
    for _ in range(iterations):
        rc, dt = _run_once(cmd)
        latencies.append(dt)
        if rc == 0:
            ok += 1
        else:
            fail += 1
    elapsed = max(1e-9, time.perf_counter() - t0)
    return {
        "name": name,
        "iterations": iterations,
        "ok_count": ok,
        "fail_count": fail,
        "fail_rate": float(fail) / float(iterations),
        "throughput_rps": float(ok) / elapsed,
        "latency_ms": {
            "min": min(latencies) if latencies else 0.0,
            "p50": _pct(latencies, 50),
            "p95": _pct(latencies, 95),
            "p99": _pct(latencies, 99),
            "max": max(latencies) if latencies else 0.0,
            "mean": statistics.fmean(latencies) if latencies else 0.0,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iterations", type=int, default=20)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    py = sys.executable
    router = "scripts/pointer_hash_snapping_router_v1.py"

    cases = [
        (
            "reports_apply_shadow",
            [py, router, "--enable-snap", "--target-path", "reports/demo_run.json"],
        ),
        (
            "memory_v2_apply_shadow_with_passthrough",
            [py, router, "--enable-snap", "--target-path", "projects/bitcoin-trading/memory/v2/demo.json"],
        ),
        (
            "memory_v2_apply_shadow_without_passthrough",
            [
                py,
                router,
                "--enable-snap",
                "--disable-memory-v2-oov-passthrough",
                "--target-path",
                "projects/bitcoin-trading/memory/v2/demo.json",
            ],
        ),
    ]

    results = [_bench_case(name, cmd, max(1, int(args.iterations))) for name, cmd in cases]
    out_doc = {
        "schema": "pointerguard_latency_benchmark_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {"iterations": int(args.iterations)},
        "cases": results,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "case_count": len(results)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
