#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_service_load_benchmark_latest.json"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(round((p / 100.0) * (len(s) - 1)))))
    return s[idx]


def _run_once(cmd: list[str]) -> tuple[int, float]:
    t0 = time.perf_counter()
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    dt_ms = (time.perf_counter() - t0) * 1000.0
    return cp.returncode, dt_ms


def _run_level(name: str, cmd: list[str], concurrency: int, requests: int) -> dict[str, Any]:
    latencies: list[float] = []
    ok = 0
    fail = 0
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futures = [ex.submit(_run_once, cmd) for _ in range(max(1, requests))]
        for fut in concurrent.futures.as_completed(futures):
            rc, dt = fut.result()
            latencies.append(dt)
            if rc == 0:
                ok += 1
            else:
                fail += 1
    elapsed = max(1e-9, time.perf_counter() - started)
    return {
        "scenario": name,
        "concurrency": concurrency,
        "request_count": requests,
        "ok_count": ok,
        "fail_count": fail,
        "error_rate": float(fail) / float(max(1, requests)),
        "rps": float(ok) / elapsed,
        "latency_ms": {
            "p50": _pct(latencies, 50),
            "p95": _pct(latencies, 95),
            "p99": _pct(latencies, 99),
            "max": max(latencies) if latencies else 0.0,
            "mean": (sum(latencies) / len(latencies)) if latencies else 0.0,
        },
    }


def _read_host_metrics_windows() -> dict[str, Any]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "(Get-Counter '\\Processor(_Total)\\% Processor Time').CounterSamples[0].CookedValue; "
        "(Get-Counter '\\Memory\\% Committed Bytes In Use').CounterSamples[0].CookedValue",
    ]
    try:
        cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        lines = [x.strip() for x in cp.stdout.splitlines() if x.strip()]
        if len(lines) >= 2:
            return {
                "cpu_utilization": float(lines[0]),
                "memory_utilization": float(lines[1]),
                "note": "Sampled after benchmark via PowerShell Get-Counter.",
            }
    except Exception:
        pass
    return {
        "cpu_utilization": None,
        "memory_utilization": None,
        "note": "Host metrics sampling failed.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--requests-per-level", type=int, default=40)
    ap.add_argument("--concurrency-levels-csv", type=str, default="1,4,8")
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    py = sys.executable
    router = "scripts/pointer_hash_snapping_router_v1.py"
    scenarios = [
        (
            "reports_apply_shadow",
            [py, router, "--enable-snap", "--target-path", "reports/demo_run.json"],
        ),
        (
            "memory_v2_apply_shadow",
            [py, router, "--enable-snap", "--target-path", "projects/bitcoin-trading/memory/v2/demo.json"],
        ),
    ]
    levels = [int(x.strip()) for x in str(args.concurrency_levels_csv).split(",") if x.strip()]
    levels = [x for x in levels if x > 0] or [1]

    runs: list[dict[str, Any]] = []
    for scenario_name, cmd in scenarios:
        for lvl in levels:
            runs.append(_run_level(scenario_name, cmd, lvl, max(1, int(args.requests_per_level))))

    host_metrics = {
        "cpu_utilization": None,
        "memory_utilization": None,
        "note": "Host-level CPU/memory capture not wired in this benchmark harness.",
    }
    if platform.system().lower().startswith("win"):
        host_metrics = _read_host_metrics_windows()

    out_doc = {
        "schema": "pointerguard_service_load_benchmark_v1",
        "generated_at_utc": _now_utc(),
        "research_only": True,
        "source_track": "B",
        "inputs": {
            "requests_per_level": int(args.requests_per_level),
            "concurrency_levels": levels,
        },
        "host_metrics": host_metrics,
        "runs": runs,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "run_count": len(runs)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
