#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _bootstrap_ci(values: list[float], n_boot: int = 1000, alpha: float = 0.05) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    means: list[float] = []
    for _ in range(n_boot):
        sample = [random.choice(values) for _ in range(len(values))]
        means.append(sum(sample) / len(sample))
    means.sort()
    lo_i = int((alpha / 2) * len(means))
    hi_i = int((1 - alpha / 2) * len(means)) - 1
    return means[max(0, lo_i)], means[min(len(means) - 1, hi_i)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", type=Path, default=ROOT / "reports" / "e2e_memory_proof_metrics_latest.json")
    ap.add_argument("--live", type=Path, default=ROOT / "reports" / "e2e_memory_proof_live_metrics_latest.json")
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "e2e_memory_proof_stats_latest.json")
    args = ap.parse_args()

    offline = _read(args.offline)
    live = _read(args.live)

    ttft_a = ((offline.get("metrics") or {}).get("m2_ttft") or {}).get("ttft_ms_raw", {}).get("baseline_a", [])
    ttft_b = ((offline.get("metrics") or {}).get("m2_ttft") or {}).get("ttft_ms_raw", {}).get("compressed_b", [])
    live_a = ((((live.get("metrics") or {}).get("m2_ttft") or {}).get("baseline_a") or {}).get("ttft_ms_raw") or [])
    live_b = ((((live.get("metrics") or {}).get("m2_ttft") or {}).get("compressed_b") or {}).get("ttft_ms_raw") or [])

    all_a = [float(x) for x in [*ttft_a, *live_a]]
    all_b = [float(x) for x in [*ttft_b, *live_b]]
    delta = [(a - b) for a, b in zip(all_a[: min(len(all_a), len(all_b))], all_b[: min(len(all_a), len(all_b))])]
    ci_lo, ci_hi = _bootstrap_ci(delta)

    m1 = (offline.get("metrics") or {}).get("m1_token_cost") or {}
    a_cost = float((((m1.get("estimated_cost_usd") or {}).get("baseline_a")) or 0.0))
    b_cost = float((((m1.get("estimated_cost_usd") or {}).get("compressed_b")) or 0.0))

    out: dict[str, Any] = {
        "schema": "e2e_memory_proof_stats_v1",
        "generated_at_utc": utc_now_iso(),
        "research_only": True,
        "boundary_ack": "[HYPO] statistical aggregate for A/B benchmark",
        "inputs": {
            "offline_metrics": str(args.offline).replace("\\", "/"),
            "live_metrics": str(args.live).replace("\\", "/")
        },
        "summary": {
            "m1_cost_delta_usd": round(a_cost - b_cost, 6),
            "m1_cost_reduction_ratio": round(((a_cost - b_cost) / a_cost), 4) if a_cost > 0 else 0.0,
            "m2_ttft_delta_ms_mean": round((sum(delta) / len(delta)), 3) if delta else 0.0,
            "m2_ttft_delta_ms_ci95": [round(ci_lo, 3), round(ci_hi, 3)],
            "n_pairs": len(delta)
        },
        "distribution": {
            "ttft_baseline_ms": all_a,
            "ttft_compressed_ms": all_b,
            "delta_ms_baseline_minus_compressed": delta
        }
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
