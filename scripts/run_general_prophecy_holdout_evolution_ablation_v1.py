#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_GATE = ART / "general_prophecy_explainability_holdout_gate_v1_latest.json"
DEFAULT_CANDIDATES = ART / "general_prophecy_holdout_evolution_candidates_latest.json"
DEFAULT_OUT = ART / "general_prophecy_holdout_evolution_ablation_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _set_path(obj: dict[str, Any], dotted: str, value: Any) -> None:
    cur: Any = obj
    parts = dotted.split(".")
    for p in parts[:-1]:
        if not isinstance(cur, dict):
            return
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    if isinstance(cur, dict):
        cur[parts[-1]] = value


def _gate_decision(snapshot: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    n_holdout = int(snapshot.get("holdout_n_questions") or 0)
    direct = _f(snapshot.get("holdout_direct_match_rate"), -1.0)
    repro = _f(snapshot.get("holdout_reproducible_evidence_rate"), -1.0)
    cov = _f(snapshot.get("holdout_avg_biblical_keyword_coverage"), -1.0)
    min_direct = _f(thresholds.get("min_holdout_direct_rate"), 0.7)
    min_repro = _f(thresholds.get("min_holdout_repro_rate"), 0.9)
    min_cov = _f(thresholds.get("min_holdout_coverage"), 0.3)
    checks = {
        "min_holdout_questions_pass": n_holdout >= 1,
        "min_holdout_direct_rate_pass": direct >= min_direct,
        "min_holdout_repro_rate_pass": repro >= min_repro,
        "min_holdout_coverage_pass": cov >= min_cov,
    }
    all_pass = all(checks.values())
    return {
        "checks": checks,
        "all_pass": all_pass,
        "decision": "GO_HOLDOUT_STABLE" if all_pass else "WARN_HOLDOUT_DRIFT_RISK",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Run holdout candidate ablation simulation (proposal only).")
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    gate = _read_json(args.gate_json if args.gate_json.is_absolute() else ROOT / args.gate_json)
    cands = _read_json(args.candidates_json if args.candidates_json.is_absolute() else ROOT / args.candidates_json)
    thresholds_base = gate.get("thresholds") if isinstance(gate.get("thresholds"), dict) else {}
    snapshot = gate.get("metrics_snapshot") if isinstance(gate.get("metrics_snapshot"), dict) else {}
    before = _gate_decision(snapshot, thresholds_base)

    rows: list[dict[str, Any]] = []
    for cand in cands.get("candidates") or []:
        if not isinstance(cand, dict):
            continue
        t2 = dict(thresholds_base)
        target = str(cand.get("target") or "")
        pval = cand.get("proposed_value")
        if target == "holdout_gate.thresholds":
            if isinstance(pval, dict):
                t2.update({k: pval[k] for k in ("min_holdout_direct_rate", "min_holdout_repro_rate", "min_holdout_coverage") if k in pval})
        elif target.startswith("holdout_gate.thresholds."):
            key = target.split(".")[-1]
            if key in {"min_holdout_direct_rate", "min_holdout_repro_rate", "min_holdout_coverage"}:
                t2[key] = pval
        else:
            _set_path(t2, target, pval)
        sim = _gate_decision(snapshot, t2)
        rows.append(
            {
                "id": cand.get("id"),
                "target": target,
                "risk_level": cand.get("risk_level"),
                "decision_before": before["decision"],
                "decision_after": sim["decision"],
                "decision_changed": sim["decision"] != before["decision"],
                "failed_check_keys_after": [k for k, v in sim["checks"].items() if v is False],
                "thresholds_after": t2,
                "reason": cand.get("reason"),
            }
        )

    # Recommendation policy: prefer candidate that reaches GO; then low risk.
    risk_rank = {"low": 0, "medium": 1, "high": 2}
    go_rows = [r for r in rows if r["decision_after"] == "GO_HOLDOUT_STABLE"]
    pool = go_rows if go_rows else rows
    pool_sorted = sorted(pool, key=lambda r: (risk_rank.get(str(r.get("risk_level")), 9), 0 if r.get("decision_changed") else 1, str(r.get("id"))))
    recommended = pool_sorted[0] if pool_sorted else None

    out = {
        "schema": "general_prophecy_holdout_evolution_ablation_v1",
        "generated_at_utc": _now(),
        "mode": "proposal_only_no_auto_apply",
        "before": {
            "decision": before["decision"],
            "failed_check_keys": [k for k, v in before["checks"].items() if v is False],
            "thresholds": thresholds_base,
            "metrics_snapshot": snapshot,
        },
        "candidate_results": rows,
        "recommended_candidate_id": (recommended or {}).get("id"),
        "recommended_note": "human_signoff_required; no auto apply",
        "track_wall": {"source_track": "B", "auto_apply": False, "human_signoff_required": True},
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "rows": len(rows), "recommended_candidate_id": out.get("recommended_candidate_id")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
