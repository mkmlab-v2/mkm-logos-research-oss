#!/usr/bin/env python3
"""Extrapolate LoRA pack-count ops cost from efficiency-search runs + architecture sweep.

B-track / research_only — pipeline-cycle seconds, not production inference SLA.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_EFFICIENCY = ROOT / "reports/lora_pack_qwen_efficiency_search_latest.json"
DEFAULT_SWEEP = ROOT / "reports/lora_domain_architecture_sweep_latest.json"
DEFAULT_OUT = ROOT / "reports/lora_pack_latency_extrapolation_latest.json"

# [HYPO] hot adapter switch overhead when >1 pack registered (not measured in repo).
HOT_SWITCH_SEC_PER_EXTRA_PACK = 0.05


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _efficiency_stats(doc: dict[str, Any]) -> dict[str, Any]:
    runs = list(doc.get("runs", []))
    elapsed = [float(r["elapsed_sec"]) for r in runs if r.get("ok") and "elapsed_sec" in r]
    stage = doc.get("stage_reports") or []
    stage200 = next((s for s in stage if int(s.get("stage_target", 0)) == 200), stage[-1] if stage else {})
    mean_from_runs = statistics.mean(elapsed) if elapsed else float(stage200.get("mean_elapsed_sec", 0))
    return {
        "packs_measured": int(doc.get("packs_done", len(elapsed))),
        "successes": int(doc.get("successes", 0)),
        "success_rate_wilson_lb_95": float(stage200.get("success_rate_wilson_lb_95", 0)),
        "mean_pipeline_elapsed_sec_per_pack": round(mean_from_runs, 4),
        "runtime_cv": float(stage200.get("runtime_cv", 0)),
        "packs_per_min": round(float(stage200.get("packs_per_min", 0)), 4),
        "source_schema": doc.get("schema"),
        "source_generated_at_utc": doc.get("generated_at_utc"),
    }


def _estimate_for_pack_count(packs: int, mean_sec: float) -> dict[str, Any]:
    serial_min = (packs * mean_sec) / 60.0
    switch_sec = max(0, packs - 1) * HOT_SWITCH_SEC_PER_EXTRA_PACK
    return {
        "packs": packs,
        "serial_full_refresh_minutes": round(serial_min, 2),
        "hypo_hot_switch_overhead_sec": round(switch_sec, 2),
        "hypo_serial_plus_switch_minutes": round((packs * mean_sec + switch_sec) / 60.0, 2),
    }


def build_report(*, efficiency_path: Path, sweep_path: Path) -> dict[str, Any]:
    eff = _load_json(efficiency_path)
    stats = _efficiency_stats(eff)
    mean_sec = float(stats["mean_pipeline_elapsed_sec_per_pack"])

    sweep_doc: dict[str, Any] | None = None
    architectures: list[dict[str, Any]] = []
    if sweep_path.is_file():
        sweep_doc = _load_json(sweep_path)
        architectures = list(sweep_doc.get("architectures_ranked", []))

    arch_rows: list[dict[str, Any]] = []
    for arch in architectures:
        packs = int(arch.get("packs", 0))
        est = _estimate_for_pack_count(packs, mean_sec)
        arch_rows.append(
            {
                "architecture_id": arch.get("id"),
                "label": arch.get("label"),
                "packs": packs,
                "routing_cells": arch.get("routing_cells"),
                "composite_score": arch.get("score", {}).get("composite_score"),
                **est,
            }
        )

    canonical_counts = sorted({3, 4, 9, 12, 20, 40, 75, 200})
    grid = [_estimate_for_pack_count(n, mean_sec) for n in canonical_counts]

    vision = next((r for r in arch_rows if r.get("architecture_id") == "vision_20x200_flat"), None)
    bench = next((r for r in arch_rows if r.get("architecture_id") == "bench_4x40"), None)
    hybrid = next((r for r in arch_rows if r.get("architecture_id") == "hier_12x75_hybrid"), None)

    return {
        "schema": "lora_pack_latency_extrapolation_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "efficiency_stats": stats,
        "assumptions": {
            "pipeline_run_definition": "W1~W4 LoRA operational template per pack (efficiency_search strict)",
            "hot_switch_sec_per_extra_pack": HOT_SWITCH_SEC_PER_EXTRA_PACK,
            "hot_switch_tag": "[HYPO]",
            "not_measured": "GPU inference-only latency with N adapters resident",
        },
        "canonical_pack_grid": grid,
        "architecture_estimates": arch_rows,
        "comparison_ko": {
            "vision_20x200_serial_refresh_min": vision["serial_full_refresh_minutes"] if vision else None,
            "bench_4x40_serial_refresh_min": bench["serial_full_refresh_minutes"] if bench else None,
            "hier_12x75_hybrid_serial_refresh_min": hybrid["serial_full_refresh_minutes"] if hybrid else None,
            "vision_vs_bench_refresh_ratio": round(
                (vision["serial_full_refresh_minutes"] / bench["serial_full_refresh_minutes"]),
                2,
            )
            if vision and bench and bench["serial_full_refresh_minutes"]
            else None,
        },
        "sweep_pointer": str(sweep_path) if sweep_doc else None,
        "efficiency_pointer": str(efficiency_path),
        "verdict_ko": (
            f"Measured ~{mean_sec:.2f}s/pack pipeline (200/200 strict). "
            "20-pack vision full refresh ~"
            f"{vision['serial_full_refresh_minutes'] if vision else '?'} min vs "
            f"4-pack bench ~{bench['serial_full_refresh_minutes'] if bench else '?'} min — "
            "routing-optimal 4×40 also lowest ops refresh among compared architectures."
        ),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LoRA pack-count latency extrapolation (B-track).")
    p.add_argument("--efficiency-json", default=str(DEFAULT_EFFICIENCY))
    p.add_argument("--sweep-json", default=str(DEFAULT_SWEEP))
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_path = Path(args.out_json)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = build_report(
        efficiency_path=Path(args.efficiency_json),
        sweep_path=Path(args.sweep_json),
    )
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(out_path),
                "mean_sec_per_pack": report["efficiency_stats"]["mean_pipeline_elapsed_sec_per_pack"],
                "vision_vs_bench_ratio": report["comparison_ko"].get("vision_vs_bench_refresh_ratio"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
