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
    lines = [
        "# Canon Strict Freeze Drift Gate v1",
        "",
        f"- generated_at_utc: {data['generated_at_utc']}",
        f"- status: {data['status']}",
        f"- drift_count: {data['metrics']['drift_count']}",
        "",
        "## Drift Items",
    ]
    drifts = list(data.get("drifts") or [])
    if not drifts:
        lines.append("- none")
    else:
        for d in drifts:
            lines.append(f"- {d['field']}: baseline={d['baseline']} current={d['current']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare strict baseline freeze against latest gate snapshot for drift.")
    ap.add_argument(
        "--freeze-json",
        default="",
    )
    ap.add_argument(
        "--freeze-vfinal-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_vfinal_v1.json",
    )
    ap.add_argument(
        "--freeze-v2-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2.json",
    )
    ap.add_argument(
        "--freeze-v1-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v1.json",
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
    ap.add_argument(
        "--day7-checkpoint-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_day7_checkpoint_gate_v1.json",
    )
    ap.add_argument(
        "--freeze-v2-stability-gate-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--promotion-go-no-go-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_promotion_go_no_go_v1.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1.md",
    )
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_freeze_drift_gate_history_v1.jsonl",
    )
    ap.add_argument("--append-history", action="store_true")
    args = ap.parse_args()

    freeze_path = None
    if str(args.freeze_json or "").strip():
        p = Path(args.freeze_json)
        if p.exists():
            freeze_path = p
    if freeze_path is None:
        for cand in (Path(args.freeze_vfinal_json), Path(args.freeze_v2_json), Path(args.freeze_v1_json)):
            if cand.exists():
                freeze_path = cand
                break
    freeze = _read_json(freeze_path) if freeze_path is not None else {}
    baseline = dict((freeze.get("gate_status") or {}))
    current = {
        "quality_gate_policy_status": str((_read_json(Path(args.quality_gate_policy_json)).get("status") or "missing")),
        "promotion_gate_status": str((_read_json(Path(args.promotion_gate_json)).get("status") or "missing")),
        "explainability_benchmark_status": str((_read_json(Path(args.explainability_benchmark_gate_json)).get("status") or "missing")),
        "delta_governance_status": str((_read_json(Path(args.delta_governance_json)).get("status") or "missing")),
        "day7_checkpoint_verdict": str((_read_json(Path(args.day7_checkpoint_json)).get("verdict") or "missing")),
        "promotion_go_no_go_verdict": str((_read_json(Path(args.promotion_go_no_go_json)).get("verdict") or "missing")),
        "freeze_v2_stability_status": str((_read_json(Path(args.freeze_v2_stability_gate_json)).get("status") or "missing")),
    }

    drifts: list[dict[str, Any]] = []
    compare_keys = list(baseline.keys()) if baseline else list(current.keys())
    for k in compare_keys:
        curr = current.get(k, "missing")
        base = str(baseline.get(k) or "missing")
        if base != str(curr):
            drifts.append({"field": k, "baseline": base, "current": str(curr)})

    out = {
        "schema": "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "freeze_json": str(freeze_path) if freeze_path is not None else "",
            "quality_gate_policy_json": str(args.quality_gate_policy_json),
            "promotion_gate_json": str(args.promotion_gate_json),
            "explainability_benchmark_gate_json": str(args.explainability_benchmark_gate_json),
            "delta_governance_json": str(args.delta_governance_json),
            "day7_checkpoint_json": str(args.day7_checkpoint_json),
            "freeze_v2_stability_gate_json": str(args.freeze_v2_stability_gate_json),
            "promotion_go_no_go_json": str(args.promotion_go_no_go_json),
        },
        "status": "alert" if drifts else "stable",
        "metrics": {"drift_count": len(drifts)},
        "baseline_gate_status": baseline,
        "current_gate_status": current,
        "drifts": drifts,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    if bool(args.append_history):
        _append_jsonl(
            Path(args.history_jsonl),
            {
                "schema": "original_corpus_regime_singularity_canon_strict_freeze_drift_gate_event_v1",
                "generated_at_utc": out["generated_at_utc"],
                "status": out["status"],
                "metrics": out["metrics"],
                "drifts": out["drifts"],
                "current_gate_status": out["current_gate_status"],
            },
        )
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

