#!/usr/bin/env python3
"""Summarize LIVE_DEEP sweep and regime probes for operational routing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKTEST = ROOT / "backtest_results"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btc_ext_live_deep_operational_readiness_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _probe_summary(regime: str) -> dict[str, Any]:
    path = BACKTEST / f"LOGOS_RESONANCE_BTC_EXT_PROBE_REGIME_{regime}_TOP500.json"
    doc = _load(path)
    hits = doc.get("hits") or []
    top1 = hits[0] if hits else {}
    return {
        "path": str(path).replace("\\", "/"),
        "verses_scanned": int(doc.get("verses_scanned", 0)),
        "top_k": int(doc.get("top_k", 0)),
        "hit_count": len(hits),
        "top1_verse_id": top1.get("verse_id"),
        "top1_cosine_to_regime_fingerprint_4d": top1.get("cosine_to_regime_fingerprint_4d"),
    }


def main() -> int:
    bench = _load(BACKTEST / "LOGOS_GPU_BENCH_v2.json")
    sweep = _load(BACKTEST / "LOGOS_RESONANCE_BTC_EXT_LIVE_DEEP_SWEEP_SUMMARY.json")

    regimes = ("bull_pump", "bear_trend", "capitulation", "sideways_accumulation")
    probes = {r: _probe_summary(r) for r in regimes}

    all_four_any = any(bool((row.get("summary") or {}).get("all_four_non_empty", False)) for row in sweep)
    triple_any = any(bool((row.get("summary") or {}).get("any_triple_non_empty", False)) for row in sweep)
    pairwise_any = any(bool((row.get("summary") or {}).get("any_pairwise_non_empty", False)) for row in sweep)

    out = {
        "schema": "btc_ext_live_deep_operational_readiness_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "gpu_bench": "backtest_results/LOGOS_GPU_BENCH_v2.json",
            "live_deep_sweep": "backtest_results/LOGOS_RESONANCE_BTC_EXT_LIVE_DEEP_SWEEP_SUMMARY.json",
            "regime_probe_pattern": "backtest_results/LOGOS_RESONANCE_BTC_EXT_PROBE_REGIME_<regime>_TOP500.json",
        },
        "gpu": {
            "device": bench.get("device"),
            "cuda_available": bool(bench.get("cuda_available", False)),
            "verses_encoded": int(bench.get("verses_encoded", 0)),
            "items_per_second_wall": float(bench.get("items_per_second_wall", 0.0)),
            "peak_cuda_memory_mb": float(bench.get("peak_cuda_memory_mb", 0.0)),
        },
        "live_deep_sweep": {
            "rows": sweep,
            "any_pairwise_non_empty": pairwise_any,
            "any_triple_non_empty": triple_any,
            "any_all_four_non_empty": all_four_any,
            "count_all_four_total": int(sum(int(row.get("count_all_four", 0)) for row in sweep)),
        },
        "regime_probes_top500": probes,
        "operational_recommendation": {
            "primary_mode": "relaxed_2of4_or_3of4",
            "all_four_mode": "research_only",
            "rationale": "all-four remains zero in LIVE_DEEP sweep while pairwise/triple intersections are non-empty.",
        },
        "note": "B-track evidence summary only; no A-track promotion or deterministic claim.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
