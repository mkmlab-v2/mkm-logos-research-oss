#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Autonomous evolution for June 2026 KOSPI daily prophecy blend weights (dry-run default)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
EVAL_DEFAULT = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
FOUR_AI_DEFAULT = ROOT / "reports/kospi_june2026_4ai_prophecy_report_latest.json"
COMPARE_DEFAULT = ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_prophecy_evolution_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _four_ai_kpi_snapshot(four_ai_doc: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    from scripts.kospi_june_4ai_prophecy_overlay_v1 import compute_four_ai_coordinator_kpi

    rows = four_ai_doc.get("rows") if isinstance(four_ai_doc.get("rows"), list) else []
    coord_pol = rules.get("four_ai_coordinator_policy")
    targets = None
    if isinstance(coord_pol, dict) and isinstance(coord_pol.get("kpi_targets"), dict):
        targets = coord_pol["kpi_targets"]
    embedded = four_ai_doc.get("coordinator_kpi")
    if isinstance(embedded, dict) and embedded.get("n_trading_days"):
        kpi = dict(embedded)
    else:
        kpi = compute_four_ai_coordinator_kpi(rows, targets=targets)
    return kpi


def _apply_candidate_weights(
    rules: dict[str, Any],
    candidate_id: str,
) -> tuple[dict[str, Any], dict[str, float]]:
    candidates = rules.get("blend_weights_v2_candidates")
    if not isinstance(candidates, dict) or candidate_id not in candidates:
        raise ValueError(f"Unknown candidate id: {candidate_id}")
    entry = candidates[candidate_id]
    weights = entry.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise ValueError(f"Candidate {candidate_id} has no weights")
    rules_out = dict(rules)
    rules_out["blend_weights_v2"] = dict(weights)
    rules_out["last_candidate_apply_id"] = candidate_id
    rules_out["last_candidate_apply_at_utc"] = _utc_now()
    return rules_out, dict(weights)


def run_evolution(
    *,
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    four_ai_doc: dict[str, Any] | None = None,
    compare_doc: dict[str, Any] | None = None,
    dry_run: bool = True,
    apply_candidate_id: str | None = None,
) -> dict[str, Any]:
    policy = rules.get("evolution_policy") if isinstance(rules.get("evolution_policy"), dict) else {}
    min_days = int(policy.get("min_scored_days_for_tune", 3))
    boost_ge = float(policy.get("boost_soft_rate_ge", 0.55))
    demote_le = float(policy.get("demote_soft_rate_le", 0.35))
    delta = float(policy.get("weight_delta", 0.05))
    floor_w = float(policy.get("floor_weight", 0.15))
    ceil_w = float(policy.get("ceiling_weight", 0.7))

    metrics = eval_doc.get("metrics") if isinstance(eval_doc.get("metrics"), dict) else {}
    n_scored = int(eval_doc.get("n_scored") or 0)
    soft = metrics.get("soft_hit_rate")
    dir_hr = metrics.get("directional_hit_rate")

    profile = str(rules.get("multilens_profile") or "v2_multilens")
    wkey = "blend_weights_v2" if profile == "v2_multilens" else "blend_weights"
    weights = dict(rules.get(wkey) or rules.get("blend_weights") or {})
    proposals: list[dict[str, Any]] = []
    action = "hold"

    if n_scored >= min_days and soft is not None:
        if soft >= boost_ge:
            action = "boost_session_myeongni"
            old = float(weights.get("session_myeongni", 0.22 if profile == "v2_multilens" else 0.55))
            new = _clamp(old + delta, floor_w, ceil_w)
            weights["session_myeongni"] = round(new, 4)
            mom_key = "momentum_overlay"
            weights[mom_key] = round(
                max(floor_w, float(weights.get(mom_key, 0.12 if profile == "v2_multilens" else 0.25)) - delta / 2),
                4,
            )
            proposals.append(
                {
                    "action": action,
                    "reason": f"soft_hit_rate {soft} >= {boost_ge}",
                    "weight_delta": delta,
                    "before": dict(rules.get(wkey) or rules.get("blend_weights") or {}),
                    "after": dict(weights),
                }
            )
        elif soft <= demote_le:
            action = "demote_session_myeongni"
            old = float(weights.get("session_myeongni", 0.22 if profile == "v2_multilens" else 0.55))
            new = _clamp(old - delta, floor_w, ceil_w)
            weights["session_myeongni"] = round(new, 4)
            mom_key = "momentum_overlay"
            weights[mom_key] = round(
                min(ceil_w, float(weights.get(mom_key, 0.12 if profile == "v2_multilens" else 0.25)) + delta / 2),
                4,
            )
            proposals.append(
                {
                    "action": action,
                    "reason": f"soft_hit_rate {soft} <= {demote_le}",
                    "weight_delta": -delta,
                    "before": dict(rules.get(wkey) or rules.get("blend_weights") or {}),
                    "after": dict(weights),
                }
            )

    norm_keys = (
        list(weights.keys())
        if profile == "v2_multilens"
        else ["session_myeongni", "momentum_overlay", "logos_non_gating"]
    )
    total = sum(float(weights.get(k, 0)) for k in norm_keys)
    if total > 0 and action != "hold":
        for k in norm_keys:
            weights[k] = round(float(weights.get(k, 0)) / total, 4)

    applied = False
    candidate_applied = False
    if proposals and not dry_run:
        rules_out = dict(rules)
        rules_out[wkey] = weights
        rules_out["last_evolution_at_utc"] = _utc_now()
        rules_out["last_evolution_action"] = action
        EVOLUTION_RULES.parent.mkdir(parents=True, exist_ok=True)
        EVOLUTION_RULES.write_text(json.dumps(rules_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        applied = True
        rules = rules_out

    if apply_candidate_id and not dry_run:
        rules_out, cand_weights = _apply_candidate_weights(rules, apply_candidate_id)
        rules_out["last_evolution_at_utc"] = _utc_now()
        rules_out["last_evolution_action"] = f"apply_candidate:{apply_candidate_id}"
        EVOLUTION_RULES.parent.mkdir(parents=True, exist_ok=True)
        EVOLUTION_RULES.write_text(json.dumps(rules_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        applied = True
        candidate_applied = True
        weights = cand_weights
        action = f"apply_candidate:{apply_candidate_id}"

    four_ai_kpi: dict[str, Any] = {}
    if four_ai_doc:
        four_ai_kpi = _four_ai_kpi_snapshot(four_ai_doc, rules)

    return {
        "schema": "kospi_june2026_prophecy_evolution_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "dry_run": dry_run,
        "applied": applied,
        "n_scored": n_scored,
        "soft_hit_rate": soft,
        "directional_hit_rate": dir_hr,
        "evolution_action": action,
        "proposals": proposals,
        "multilens_profile": profile,
        "blend_weights_key": wkey,
        "blend_weights_current": dict(rules.get(wkey) or rules.get("blend_weights") or {}),
        "blend_weights_proposed": weights if proposals else dict(rules.get(wkey) or rules.get("blend_weights") or {}),
        "blend_policy_v2": dict(rules.get("blend_policy_v2") or {}),
        "four_ai_coordinator_kpi": four_ai_kpi,
        "four_ai_coordinator_policy": dict(rules.get("four_ai_coordinator_policy") or {}),
        "weight_candidate_policy": dict(rules.get("weight_candidate_policy") or {}),
        "weight_candidate_compare": compare_doc or {},
        "candidate_applied": candidate_applied,
        "apply_candidate_id": apply_candidate_id,
        "rules_path": str(EVOLUTION_RULES.relative_to(ROOT)).replace("\\", "/"),
        "note": "June lane only. Apply weights with --apply-approved; candidate with --apply-candidate-id.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval-json", type=Path, default=EVAL_DEFAULT)
    ap.add_argument("--four-ai-json", type=Path, default=FOUR_AI_DEFAULT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--apply-approved", action="store_true", help="Write blend_weights to evolution rules file")
    ap.add_argument(
        "--apply-candidate-id",
        type=str,
        default=None,
        help="With --apply-approved, copy blend_weights_v2_candidates.<id> to blend_weights_v2",
    )
    ap.add_argument("--compare-json", type=Path, default=COMPARE_DEFAULT)
    args = ap.parse_args(argv)

    eval_doc = _read_json(args.eval_json)
    rules = _read_json(EVOLUTION_RULES)
    four_ai_doc = _read_json(args.four_ai_json) if args.four_ai_json.is_file() else None
    compare_doc = _read_json(args.compare_json) if args.compare_json.is_file() else None
    dry_run = not args.apply_approved
    if args.apply_candidate_id and not args.apply_approved:
        print("--apply-candidate-id requires --apply-approved", file=sys.stderr)
        return 2

    doc = run_evolution(
        eval_doc=eval_doc,
        rules=rules,
        four_ai_doc=four_ai_doc,
        compare_doc=compare_doc,
        dry_run=dry_run,
        apply_candidate_id=args.apply_candidate_id,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} action={doc['evolution_action']} "
        f"dry_run={doc['dry_run']} proposals={len(doc['proposals'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
