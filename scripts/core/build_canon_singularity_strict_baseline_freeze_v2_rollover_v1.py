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


def _write_md(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"# {title}", "", *lines]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _diff_obj(prefix: str, a: Any, b: Any, out: list[dict[str, Any]]) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a.keys()) | set(b.keys()))
        for k in keys:
            p = f"{prefix}.{k}" if prefix else k
            _diff_obj(p, a.get(k), b.get(k), out)
        return
    if a != b:
        out.append({"field": prefix, "v1": a, "v2": b})


def main() -> int:
    ap = argparse.ArgumentParser(description="Conditionally roll strict baseline freeze v2 when day7 gate is ready.")
    ap.add_argument(
        "--freeze-v1-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v1.json",
    )
    ap.add_argument(
        "--day7-checkpoint-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_day7_checkpoint_gate_v1.json",
    )
    ap.add_argument(
        "--quality-gate-policy-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_policy_eval_v1.json",
    )
    ap.add_argument(
        "--promotion-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_gate_v1.json",
    )
    ap.add_argument(
        "--explainability-benchmark-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_explainability_benchmark_gate_v1.json",
    )
    ap.add_argument(
        "--delta-governance-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_delta_cutoff_governance_gate_v1.json",
    )
    ap.add_argument("--health-max-fail-count", type=int, default=0)
    ap.add_argument("--health-min-pass-rate", type=float, default=1.0)
    ap.add_argument("--insight-delta-min-score", type=float, default=0.001)
    ap.add_argument("--delta-governance-min-apply-rate", type=float, default=0.0)
    ap.add_argument("--require-explainability-benchmark", action="store_true", default=True)
    ap.add_argument(
        "--output-v2-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2.json",
    )
    ap.add_argument(
        "--output-v2-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2.md",
    )
    ap.add_argument(
        "--output-rollover-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_v1.json",
    )
    ap.add_argument(
        "--output-rollover-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_v1.md",
    )
    ap.add_argument(
        "--output-diff-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_diff_v2_from_v1.json",
    )
    ap.add_argument(
        "--output-diff-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_diff_v2_from_v1.md",
    )
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_history_v1.jsonl",
    )
    args = ap.parse_args()

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    v1 = _read_json(Path(args.freeze_v1_json))
    day7 = _read_json(Path(args.day7_checkpoint_json))
    day7_verdict = str(day7.get("verdict") or "missing")
    should_roll = day7_verdict == "ready"

    rollover = {
        "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_v1",
        "generated_at_utc": now,
        "inputs": {
            "freeze_v1_json": str(args.freeze_v1_json),
            "day7_checkpoint_json": str(args.day7_checkpoint_json),
        },
        "day7_verdict": day7_verdict,
        "rollover_status": "rolled" if should_roll else "noop_hold",
        "outputs": {
            "freeze_v2_json": str(args.output_v2_json),
            "freeze_v2_md": str(args.output_v2_md),
            "diff_json": str(args.output_diff_json),
            "diff_md": str(args.output_diff_md),
        },
    }

    if not should_roll:
        _write_json(Path(args.output_rollover_json), rollover)
        _write_md(
            Path(args.output_rollover_md),
            "Canon Strict Baseline Freeze V2 Rollover v1",
            [
                f"- generated_at_utc: {now}",
                f"- day7_verdict: {day7_verdict}",
                "- rollover_status: noop_hold",
                "- reason: day7 checkpoint is not ready",
            ],
        )
        _append_jsonl(
            Path(args.history_jsonl),
            {
                "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_event_v1",
                "generated_at_utc": now,
                "rollover_status": "noop_hold",
                "day7_verdict": day7_verdict,
                "freeze_decision": "noop_hold",
            },
        )
        print(str(args.output_rollover_json))
        return 0

    health = _read_json(Path(args.quality_gate_policy_json))
    promo = _read_json(Path(args.promotion_gate_json))
    bench = _read_json(Path(args.explainability_benchmark_gate_json))
    delta = _read_json(Path(args.delta_governance_json))

    gate_status = {
        "quality_gate_policy_status": str(health.get("status") or "missing"),
        "promotion_gate_status": str(promo.get("status") or "missing"),
        "explainability_benchmark_status": str(bench.get("status") or "missing"),
        "delta_governance_status": str(delta.get("status") or "missing"),
        "day7_checkpoint_verdict": day7_verdict,
    }
    freeze_ok = (
        gate_status["quality_gate_policy_status"] == "pass"
        and gate_status["promotion_gate_status"] == "pass"
        and gate_status["explainability_benchmark_status"] == "pass"
        and gate_status["delta_governance_status"] == "pass"
    )
    v2 = {
        "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2",
        "generated_at_utc": now,
        "freeze_decision": "frozen" if freeze_ok else "hold",
        "inputs": rollover["inputs"],
        "profile": {
            "health_max_fail_count": int(args.health_max_fail_count),
            "health_min_pass_rate": float(args.health_min_pass_rate),
            "insight_delta_min_score": float(args.insight_delta_min_score),
            "delta_governance_min_apply_rate": float(args.delta_governance_min_apply_rate),
            "require_explainability_benchmark": bool(args.require_explainability_benchmark),
        },
        "gate_status": gate_status,
    }
    _write_json(Path(args.output_v2_json), v2)
    _write_md(
        Path(args.output_v2_md),
        "Canon Strict Baseline Freeze v2",
        [
            f"- generated_at_utc: {now}",
            f"- freeze_decision: {v2['freeze_decision']}",
            f"- day7_checkpoint_verdict: {day7_verdict}",
        ],
    )

    changes: list[dict[str, Any]] = []
    _diff_obj("", v1.get("profile") or {}, v2.get("profile") or {}, changes)
    _diff_obj("", v1.get("gate_status") or {}, v2.get("gate_status") or {}, changes)
    diff = {
        "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_diff_v2_from_v1",
        "generated_at_utc": now,
        "freeze_v1_json": str(args.freeze_v1_json),
        "freeze_v2_json": str(args.output_v2_json),
        "change_count": len(changes),
        "changes": changes,
    }
    _write_json(Path(args.output_diff_json), diff)
    lines = [f"- generated_at_utc: {now}", f"- change_count: {len(changes)}", "", "## Changes"]
    if changes:
        lines.extend([f"- {c['field']}: v1={c['v1']} -> v2={c['v2']}" for c in changes])
    else:
        lines.append("- none")
    _write_md(Path(args.output_diff_md), "Canon Strict Baseline Freeze Diff v2 from v1", lines)

    _write_json(Path(args.output_rollover_json), rollover)
    _write_md(
        Path(args.output_rollover_md),
        "Canon Strict Baseline Freeze V2 Rollover v1",
        [
            f"- generated_at_utc: {now}",
            f"- day7_verdict: {day7_verdict}",
            "- rollover_status: rolled",
            f"- freeze_v2: {args.output_v2_json}",
            f"- diff: {args.output_diff_json}",
        ],
    )
    _append_jsonl(
        Path(args.history_jsonl),
        {
            "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_event_v1",
            "generated_at_utc": now,
            "rollover_status": "rolled",
            "day7_verdict": day7_verdict,
            "freeze_decision": str(v2.get("freeze_decision") or "hold"),
        },
    )
    print(str(args.output_rollover_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

