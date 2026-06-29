#!/usr/bin/env python3
"""[HYPO] Sandbox-only PCIe adaptive threshold bench (never Track A preflight bound)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "reports" / "sandbox" / "pcie_adaptive_threshold_bench_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _threshold_for_bandwidth(
    bandwidth_gbps: float,
    *,
    baseline_threshold: int,
    floor_threshold: int,
    ref_gbps: float,
) -> int:
    if bandwidth_gbps <= 0 or ref_gbps <= 0:
        return baseline_threshold
    ratio = max(0.5, min(1.2, bandwidth_gbps / ref_gbps))
    adaptive = int(round(baseline_threshold * ratio))
    return max(floor_threshold, adaptive)


def _simulate(
    *,
    baseline_threshold: int,
    floor_threshold: int,
    ref_gbps: float,
) -> dict[str, Any]:
    synthetic_probe = [
        {"scenario": "idle_high_bandwidth", "pcie_bandwidth_gbps": ref_gbps * 1.08, "latency_p95_ms": 97.0},
        {"scenario": "nominal", "pcie_bandwidth_gbps": ref_gbps, "latency_p95_ms": 112.0},
        {"scenario": "moderate_backpressure", "pcie_bandwidth_gbps": ref_gbps * 0.84, "latency_p95_ms": 154.0},
        {"scenario": "heavy_backpressure", "pcie_bandwidth_gbps": ref_gbps * 0.66, "latency_p95_ms": 210.0},
    ]
    rows: list[dict[str, Any]] = []
    for row in synthetic_probe:
        bw = float(row["pcie_bandwidth_gbps"])
        threshold = _threshold_for_bandwidth(
            bw,
            baseline_threshold=baseline_threshold,
            floor_threshold=floor_threshold,
            ref_gbps=ref_gbps,
        )
        rows.append(
            {
                **row,
                "adaptive_input_tokens_threshold": threshold,
                "determinism_risk": threshold != baseline_threshold,
            }
        )
    return {
        "rows": rows,
        "adaptive_rows": sum(1 for r in rows if r["determinism_risk"]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--baseline-threshold", type=int, default=14000)
    ap.add_argument("--floor-threshold", type=int, default=8000)
    ap.add_argument("--reference-bandwidth-gbps", type=float, default=24.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    out_json = args.out_json.resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)

    sim = _simulate(
        baseline_threshold=max(1, int(args.baseline_threshold)),
        floor_threshold=max(1, int(args.floor_threshold)),
        ref_gbps=max(0.1, float(args.reference_bandwidth_gbps)),
    )

    doc: dict[str, Any] = {
        "schema": "pcie_adaptive_threshold_bench_v1",
        "generated_at_utc": _utc(),
        "lane": "b_track_hypo",
        "disclaimer": "research_only",
        "send_gate": "HOLD",
        "track_a_preflight_binding": False,
        "dry_run": bool(args.dry_run),
        "guardrail": {
            "policy": "forbidden_in_track_a",
            "reason": "runtime adaptive threshold breaks deterministic billing/replay guarantees",
        },
        "params": {
            "baseline_threshold": int(args.baseline_threshold),
            "floor_threshold": int(args.floor_threshold),
            "reference_bandwidth_gbps": float(args.reference_bandwidth_gbps),
        },
        "simulation": sim,
        "recommendation": "sandbox_only_stop_before_preflight",
        "reproduce": [
            "py scripts/sandbox/bench_pcie_adaptive_threshold_v1.py",
            "py scripts/sandbox/bench_pcie_adaptive_threshold_v1.py --dry-run",
        ],
    }
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
