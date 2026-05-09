#!/usr/bin/env python3
"""Dark Flow B-track gate checker (research-only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_eval_template_v1.json"
DEFAULT_POLICY = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_policy_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_gate_latest.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _composite(row: dict[str, Any], weights: dict[str, Any]) -> float:
    evidence = _to_float(row.get("evidence_score"))
    replication = _to_float(row.get("replication_score"))
    consistency = _to_float(row.get("predictive_consistency"))
    risk = _to_float(row.get("systematic_risk"))
    return (
        _to_float(weights.get("evidence_score"), 0.35) * evidence
        + _to_float(weights.get("replication_score"), 0.35) * replication
        + _to_float(weights.get("predictive_consistency"), 0.20) * consistency
        - _to_float(weights.get("systematic_risk_penalty"), 0.30) * risk
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Check Dark Flow B-track gate status.")
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict", action="store_true", help="Exit 1 unless decision is GO_RESEARCH.")
    args = ap.parse_args()

    if not args.eval_json.exists():
        raise FileNotFoundError(f"Missing eval json: {args.eval_json}")
    if not args.policy_json.exists():
        raise FileNotFoundError(f"Missing policy json: {args.policy_json}")

    ev = _load(args.eval_json)
    pol = _load(args.policy_json)
    thresholds = pol.get("thresholds", {})
    outcomes = pol.get("outcomes", {})
    weights = pol.get("weights", {})

    rows = ev.get("hypotheses", [])
    if not isinstance(rows, list):
        rows = []
    datasets = ev.get("datasets", [])
    if not isinstance(datasets, list):
        datasets = []

    composites: list[float] = []
    replication_scores: list[float] = []
    systematic_risks: list[float] = []
    ranked: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        c = _composite(row, weights)
        composites.append(c)
        replication_scores.append(_to_float(row.get("replication_score")))
        systematic_risks.append(_to_float(row.get("systematic_risk")))
        ranked.append(
            {
                "id": str(row.get("id", "")),
                "label": str(row.get("label", "")),
                "composite_score": round(c, 6),
                "evidence_score": _to_float(row.get("evidence_score")),
                "replication_score": _to_float(row.get("replication_score")),
                "systematic_risk": _to_float(row.get("systematic_risk")),
                "predictive_consistency": _to_float(row.get("predictive_consistency")),
            }
        )
    ranked.sort(key=lambda x: x["composite_score"], reverse=True)

    failures: list[str] = []
    if len(rows) < _to_int(thresholds.get("min_hypotheses_count"), 3):
        failures.append("insufficient_hypotheses_count")
    if len(datasets) < _to_int(thresholds.get("min_supported_datasets"), 3):
        failures.append("insufficient_supported_datasets")

    mean_replication = _mean(replication_scores)
    mean_risk = _mean(systematic_risks)
    best_composite = max(composites) if composites else 0.0

    if mean_replication < _to_float(thresholds.get("min_mean_replication_score"), 0.45):
        failures.append("low_mean_replication_score")
    if mean_risk > _to_float(thresholds.get("max_mean_systematic_risk"), 0.55):
        failures.append("high_mean_systematic_risk")

    go_cut = _to_float(thresholds.get("min_best_composite_for_research_go"), 0.52)
    watch_cut = _to_float(thresholds.get("min_best_composite_for_watch"), 0.44)
    if failures:
        decision = str(outcomes.get("hold", "HOLD_INCONCLUSIVE"))
    elif best_composite >= go_cut:
        decision = str(outcomes.get("research_go", "GO_RESEARCH"))
    elif best_composite >= watch_cut:
        decision = str(outcomes.get("watch", "WATCH_NEED_MORE_DATA"))
    else:
        decision = str(outcomes.get("hold", "HOLD_INCONCLUSIVE"))

    out = {
        "schema": "darkflow_btrack_gate_v1",
        "checked_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "observation_mode": "RESEARCH_ONLY",
        "auto_bind_to_atrack_forbidden": True,
        "eval_json": str(args.eval_json),
        "policy_json": str(args.policy_json),
        "hypotheses_count": len(rows),
        "supported_datasets_count": len(datasets),
        "mean_replication_score": round(mean_replication, 6),
        "mean_systematic_risk": round(mean_risk, 6),
        "best_composite_score": round(best_composite, 6),
        "failures": failures,
        "decision": decision,
        "ranked_hypotheses": ranked,
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False))

    if args.strict and decision != str(outcomes.get("research_go", "GO_RESEARCH")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
