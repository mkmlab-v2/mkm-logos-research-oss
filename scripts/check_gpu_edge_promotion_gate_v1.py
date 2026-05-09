#!/usr/bin/env python3
"""Decide GPU->Edge promotion candidate status from sweep and safety artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", default="C:/workspace")
    ap.add_argument("--min-objective", type=float, default=0.95)
    ap.add_argument("--max-p99-ms", type=float, default=40.0)
    ap.add_argument("--min-quality", type=float, default=0.90)
    ap.add_argument("--max-hold-ratio", type=float, default=0.20)
    ap.add_argument("--prefer-compressed", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    root = Path(args.workspace_root)
    artifacts = root / "docs" / "final" / "artifacts"
    sweep_path = artifacts / "gpu_sim_to_edge_sweep_v1_latest.json"
    safety_path = artifacts / "athena_safety_judge_v1_latest.json"
    out_path = artifacts / "gpu_edge_promotion_gate_v1_latest.json"

    sweep = _read_json(sweep_path)
    safety = _read_json(safety_path)

    all_candidates = sweep.get("all_candidates") or []
    selected = sweep.get("selected_candidates") or []
    top = selected[0] if selected else {}
    if args.prefer_compressed and all_candidates:
        compressed = [
            c
            for c in all_candidates
            if c.get("precision") in {"fp8", "int8", "int4"}
            and c.get("method") in {"qat", "awq", "ptq"}
            and float((c.get("metrics") or {}).get("quality_score_0_1", 0.0) or 0.0) >= float(args.min_quality)
        ]
        if compressed:
            compressed.sort(key=lambda c: float(c.get("objective_score_0_1", 0.0) or 0.0), reverse=True)
            top = compressed[0]
    top_metrics = top.get("metrics") or {}
    summary = safety.get("summary") or {}

    objective = float(top.get("objective_score_0_1", 0.0) or 0.0)
    p99_ms = float(top_metrics.get("p99_ms", 9999.0) or 9999.0)
    quality = float(top_metrics.get("quality_score_0_1", 0.0) or 0.0)
    hold_ratio = float(summary.get("hold_ratio", 1.0) or 1.0)

    checks = {
        "objective_gte_min": objective >= float(args.min_objective),
        "p99_lte_max": p99_ms <= float(args.max_p99_ms),
        "quality_gte_min": quality >= float(args.min_quality),
        "hold_ratio_lte_max": hold_ratio <= float(args.max_hold_ratio),
        "sweep_has_candidate": bool(selected),
    }
    pass_all = all(checks.values())
    decision = "GO_CANDIDATE_GPU_EDGE_V1" if pass_all else "HOLD_GPU_EDGE_V1"

    doc = {
        "schema": "gpu_edge_promotion_gate_v1",
        "generated_at_utc": _now_iso(),
        "inputs": {
            "sweep_path": str(sweep_path),
            "safety_path": str(safety_path),
            "min_objective": float(args.min_objective),
            "max_p99_ms": float(args.max_p99_ms),
            "min_quality": float(args.min_quality),
            "max_hold_ratio": float(args.max_hold_ratio),
            "prefer_compressed": bool(args.prefer_compressed),
        },
        "metrics": {
            "top_objective_score_0_1": objective,
            "top_p99_ms": p99_ms,
            "top_quality_score_0_1": quality,
            "safety_hold_ratio": hold_ratio,
            "top_candidate": {
                "method": top.get("method"),
                "precision": top.get("precision"),
                "distill_mode": top.get("distill_mode"),
                "model_size_m": top.get("model_size_m"),
                "batch_size": top.get("batch_size"),
            },
        },
        "checks": checks,
        "decision": decision,
        "promotion_ready": pass_all,
        "constraints": {
            "research_only": True,
            "target_board_measurement_required_for_final_promotion": True,
            "no_auto_live_binding": True,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "output_json": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
