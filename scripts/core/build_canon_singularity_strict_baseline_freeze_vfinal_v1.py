#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    g = data.get("gate_status") or {}
    s = data.get("strict_profile") or {}
    b = data.get("balanced_profile") or {}
    lines = [
        "# Canon Strict Baseline Freeze vFinal v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- freeze_decision: {data.get('freeze_decision')}",
        "",
        "## Gate Snapshot",
        f"- promotion_go_no_go_verdict: {g.get('promotion_go_no_go_verdict')}",
        f"- promotion_gate_status: {g.get('promotion_gate_status')}",
        f"- day7_checkpoint_verdict: {g.get('day7_checkpoint_verdict')}",
        f"- freeze_v2_stability_status: {g.get('freeze_v2_stability_status')}",
        f"- delta_governance_status: {g.get('delta_governance_status')}",
        "",
        "## Strict Profile",
        f"- health_max_fail_count: {s.get('health_max_fail_count')}",
        f"- health_min_pass_rate: {s.get('health_min_pass_rate')}",
        f"- insight_delta_min_score: {s.get('insight_delta_min_score')}",
        f"- delta_governance_min_apply_rate: {s.get('delta_governance_min_apply_rate')}",
        f"- delta_governance_max_hold_streak: {s.get('delta_governance_max_hold_streak')}",
        f"- require_explainability_benchmark: {s.get('require_explainability_benchmark')}",
        "",
        "## Balanced Profile",
        f"- health_max_fail_count: {b.get('health_max_fail_count')}",
        f"- health_min_pass_rate: {b.get('health_min_pass_rate')}",
        f"- insight_delta_min_score: {b.get('insight_delta_min_score')}",
        f"- delta_governance_min_apply_rate: {b.get('delta_governance_min_apply_rate')}",
        f"- delta_governance_max_hold_streak: {b.get('delta_governance_max_hold_streak')}",
        f"- require_explainability_benchmark: {b.get('require_explainability_benchmark')}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Freeze vFinal baseline with strict+balanced profiles and promotion/governance gates.")
    ap.add_argument(
        "--promotion-go-no-go-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json",
    )
    ap.add_argument(
        "--promotion-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_gate_v1.json",
    )
    ap.add_argument(
        "--day7-checkpoint-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_day7_checkpoint_gate_v1.json",
    )
    ap.add_argument(
        "--freeze-v2-stability-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--delta-governance-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_delta_cutoff_governance_gate_v1.json",
    )
    ap.add_argument("--strict-health-max-fail-count", type=int, default=0)
    ap.add_argument("--strict-health-min-pass-rate", type=float, default=1.0)
    ap.add_argument("--strict-insight-delta-min-score", type=float, default=0.001)
    ap.add_argument("--strict-delta-governance-min-apply-rate", type=float, default=0.0)
    ap.add_argument("--strict-delta-governance-max-hold-streak", type=int, default=20)
    ap.add_argument("--strict-require-explainability-benchmark", action="store_true", default=True)
    ap.add_argument("--balanced-health-max-fail-count", type=int, default=1)
    ap.add_argument("--balanced-health-min-pass-rate", type=float, default=0.9)
    ap.add_argument("--balanced-insight-delta-min-score", type=float, default=0.0015)
    ap.add_argument("--balanced-delta-governance-min-apply-rate", type=float, default=0.0)
    ap.add_argument("--balanced-delta-governance-max-hold-streak", type=int, default=20)
    ap.add_argument("--balanced-require-explainability-benchmark", action="store_true", default=False)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.md",
    )
    args = ap.parse_args()

    go_no_go = _read_json(Path(args.promotion_go_no_go_json))
    promotion = _read_json(Path(args.promotion_gate_json))
    day7 = _read_json(Path(args.day7_checkpoint_json))
    freeze_v2_stability = _read_json(Path(args.freeze_v2_stability_gate_json))
    delta_governance = _read_json(Path(args.delta_governance_json))

    gate_status = {
        "promotion_go_no_go_verdict": str(go_no_go.get("verdict") or "missing"),
        "promotion_gate_status": str(promotion.get("status") or "missing"),
        "day7_checkpoint_verdict": str(day7.get("verdict") or "missing"),
        "freeze_v2_stability_status": str(freeze_v2_stability.get("status") or "missing"),
        "delta_governance_status": str(delta_governance.get("status") or "missing"),
    }
    freeze_ok = (
        gate_status["promotion_go_no_go_verdict"] == "go"
        and gate_status["promotion_gate_status"] == "pass"
        and gate_status["day7_checkpoint_verdict"] == "ready"
        and gate_status["freeze_v2_stability_status"] == "pass"
        and gate_status["delta_governance_status"] == "pass"
    )

    out = {
        "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "freeze_decision": "frozen" if freeze_ok else "hold",
        "inputs": {
            "promotion_go_no_go_json": str(args.promotion_go_no_go_json),
            "promotion_gate_json": str(args.promotion_gate_json),
            "day7_checkpoint_json": str(args.day7_checkpoint_json),
            "freeze_v2_stability_gate_json": str(args.freeze_v2_stability_gate_json),
            "delta_governance_json": str(args.delta_governance_json),
        },
        "strict_profile": {
            "health_max_fail_count": int(args.strict_health_max_fail_count),
            "health_min_pass_rate": float(args.strict_health_min_pass_rate),
            "insight_delta_min_score": float(args.strict_insight_delta_min_score),
            "delta_governance_min_apply_rate": float(args.strict_delta_governance_min_apply_rate),
            "delta_governance_max_hold_streak": int(args.strict_delta_governance_max_hold_streak),
            "require_explainability_benchmark": bool(args.strict_require_explainability_benchmark),
        },
        "balanced_profile": {
            "health_max_fail_count": int(args.balanced_health_max_fail_count),
            "health_min_pass_rate": float(args.balanced_health_min_pass_rate),
            "insight_delta_min_score": float(args.balanced_insight_delta_min_score),
            "delta_governance_min_apply_rate": float(args.balanced_delta_governance_min_apply_rate),
            "delta_governance_max_hold_streak": int(args.balanced_delta_governance_max_hold_streak),
            "require_explainability_benchmark": bool(args.balanced_require_explainability_benchmark),
        },
        "gate_status": gate_status,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

