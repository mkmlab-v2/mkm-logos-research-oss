#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare active vs shadow weight candidate on June KOSPI calendar [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import (  # noqa: E402
    build_calendar,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import eval_calendar  # noqa: E402

EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
BACKTEST_DEFAULT = ROOT / "reports/kospi_multilens_blend_backtest_latest.json"
HORIZON_V2_DEFAULT = ROOT / "reports/three_lens_horizon_empirical_eval_v2_latest.json"
WALKFORWARD_DEFAULT = ROOT / "reports/kospi_multilens_walkforward_backtest_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _weights_near_equal(a: dict[str, Any], b: dict[str, Any], *, tol: float = 1e-4) -> bool:
    keys = set(a) | set(b)
    for k in keys:
        if abs(float(a.get(k, 0) or 0) - float(b.get(k, 0) or 0)) > tol:
            return False
    return True


def _resolve_weight_apply_state(
    rules: dict[str, Any],
    *,
    candidate_id: str,
    active_weights: dict[str, Any],
    candidate_weights: dict[str, Any],
) -> dict[str, Any]:
    last_id = rules.get("last_candidate_apply_id")
    last_at = rules.get("last_candidate_apply_at_utc")
    weights_match = _weights_near_equal(active_weights, candidate_weights)
    already = bool(str(last_id) == candidate_id and weights_match)
    return {
        "candidate_already_applied": already,
        "last_candidate_apply_id": last_id,
        "last_candidate_apply_at_utc": last_at,
        "active_matches_candidate_weights": weights_match,
        "apply_state_ko": (
            f"가중치 적용 완료 ({candidate_id}, {last_at}) — June 포워드 누적 모니터링"
            if already
            else None
        ),
    }


def _direction_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        d = str(r.get("predicted_direction") or "neutral")
        c[d] += 1
    return dict(c)


def _row_direction_map(cal: dict[str, Any]) -> dict[str, str]:
    return {
        str(r.get("session_date")): str(r.get("predicted_direction") or "neutral")
        for r in cal.get("rows") or []
        if r.get("session_date")
    }


def _resolve_effective_policy(
    policy: dict[str, Any],
    rules: dict[str, Any],
    *,
    proxy_gate_pass: bool,
) -> dict[str, Any]:
    """Merge strict policy with pragmatic relaxation when proxy forward gate passes."""
    effective = dict(policy)
    relax = rules.get("gate_relaxation_when_proxy_pass")
    if proxy_gate_pass and isinstance(relax, dict) and relax.get("enabled"):
        effective["policy_tier"] = str(relax.get("policy_tier_label") or "recommended_pragmatic_v1")
        effective["min_backtest_soft_delta_vs_active"] = float(
            relax.get("min_backtest_soft_delta_vs_active", policy.get("min_backtest_soft_delta_vs_active", 0.06))
        )
        effective["walkforward_require_top1_min"] = bool(relax.get("walkforward_require_top1_min", False))
        effective["require_walkforward_candidate_in_top2"] = bool(
            relax.get("require_walkforward_candidate_in_top2", policy.get("require_walkforward_candidate_in_top2", True))
        )
        effective["_relaxation_active"] = True
    else:
        effective["_relaxation_active"] = False
    return effective


def _walkforward_prefilter(
    walk_doc: dict[str, Any] | None,
    *,
    candidate_id: str,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not walk_doc or walk_doc.get("schema") != "kospi_multilens_walkforward_backtest_v1":
        return None
    pol = policy if isinstance(policy, dict) else {}
    require_top1 = bool(pol.get("walkforward_require_top1_min", True))
    min_top1 = float(pol.get("min_walkforward_selection_top1_hit_rate", 0.52))
    require_top2 = bool(pol.get("require_walkforward_candidate_in_top2", True))
    min_forward = int(pol.get("june_forward_min_scored_for_promotion", 15))

    summ = walk_doc.get("summary") if isinstance(walk_doc.get("summary"), dict) else {}
    top2 = [str(x) for x in (summ.get("recommended_prefilter_variants_top2") or [])]
    base_cid = candidate_id.split("_4ai_")[0] if "_4ai_" in candidate_id else candidate_id
    aligned = candidate_id in top2 or base_cid in top2 or any(t.startswith(base_cid) for t in top2)
    rank_rows = summ.get("variant_rank_by_test_mean_soft") or []
    rank_hit = next((r for r in rank_rows if str(r.get("variant_id")) == candidate_id), None)
    if rank_hit is None:
        rank_hit = next((r for r in rank_rows if str(r.get("variant_id", "")).startswith(base_cid)), None)
    sel_hit = summ.get("selection_top1_hit_rate")
    top1_pass = True if not require_top1 else (sel_hit is not None and float(sel_hit) >= min_top1)
    top2_pass = aligned if require_top2 else True
    gate_pass = top1_pass and top2_pass
    blockers: list[str] = []
    if require_top1 and not top1_pass:
        blockers.append(f"walkforward_selection_top1<{min_top1}")
    if require_top2 and not aligned:
        blockers.append("walkforward_candidate_not_in_top2")
    return {
        "schema": "kospi_june2026_walkforward_prefilter_v1",
        "evidence_path": str(WALKFORWARD_DEFAULT.relative_to(ROOT)).replace("\\", "/"),
        "n_folds": summ.get("n_folds"),
        "selection_top1_hit_rate": sel_hit,
        "walkforward_require_top1_min": require_top1,
        "min_selection_top1_hit_rate": min_top1 if require_top1 else None,
        "selection_top1_pass": top1_pass,
        "recommended_top2": top2,
        "candidate_id": candidate_id,
        "candidate_in_top2": aligned,
        "require_candidate_in_top2": require_top2,
        "candidate_in_top2_pass": top2_pass,
        "walkforward_gate_pass": gate_pass,
        "walkforward_blockers": blockers,
        "candidate_walkforward_rank": rank_hit,
        "role": "prefilter_and_gate",
        "note_ko": (
            f"30년 WF는 후보 압축+게이트. June forward n≥{min_forward} + human signoff가 최종."
        ),
    }


def _shadow_myeongni_horizon_contract(
    horizon_v2_doc: dict[str, Any] | None,
    *,
    rules: dict[str, Any],
) -> dict[str, Any] | None:
    if not horizon_v2_doc or horizon_v2_doc.get("schema") != "three_lens_horizon_empirical_eval_v2":
        return None
    shadow_rules = rules.get("horizon_contract_candidates")
    if not isinstance(shadow_rules, dict):
        return None
    entry = shadow_rules.get("myeongni_mid_5d")
    if not isinstance(entry, dict):
        return None
    leg = (horizon_v2_doc.get("legs") or {}).get("kospi") if isinstance(horizon_v2_doc.get("legs"), dict) else {}
    grid = leg.get("myeongni_horizon_grid") if isinstance(leg.get("myeongni_horizon_grid"), dict) else {}
    if not grid:
        return None
    contract_h = str(grid.get("contract_horizon") or entry.get("contract_horizon_active") or "mid_10d")
    shadow_h = str(grid.get("best_horizon") or entry.get("shadow_horizon") or "mid_5d")
    delta = grid.get("soft_delta_best_minus_contract")
    return {
        "schema": "kospi_june2026_myeongni_horizon_shadow_v1",
        "shadow_candidate_id": str(entry.get("shadow_candidate_id") or "myeongni_mid_5d"),
        "status": str(entry.get("status") or "research_shadow"),
        "contract_horizon_active": contract_h,
        "shadow_horizon": shadow_h,
        "contract_soft_hit_rate": grid.get("contract_soft_hit_rate"),
        "shadow_soft_hit_rate": grid.get("best_soft_hit_rate"),
        "soft_delta_shadow_minus_contract": delta,
        "contract_is_best": bool(grid.get("contract_is_best")),
        "evidence_path": str(entry.get("evidence_path") or HORIZON_V2_DEFAULT.relative_to(ROOT)).replace("\\", "/"),
        "promotion_ready": False,
        "blockers": ["human_signoff_required", "horizon_contract_not_active", "june_forward_gate_separate"],
        "note_ko": str(
            entry.get("note_ko")
            or "v2 그리드 최적 호라이즌 shadow — 가중치·June apply와 별도 human gate."
        ),
    }


def compare_candidates(
    *,
    rules: dict[str, Any],
    year_month: str = "2026-06",
    candidate_id: str | None = None,
    backtest_doc: dict[str, Any] | None = None,
    horizon_v2_doc: dict[str, Any] | None = None,
    walkforward_doc: dict[str, Any] | None = None,
    eval_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    policy = rules.get("weight_candidate_policy")
    if not isinstance(policy, dict):
        policy = {}
    cid = candidate_id or str(policy.get("active_candidate_id") or "v2_lens3_heavy")
    candidates = rules.get("blend_weights_v2_candidates")
    if not isinstance(candidates, dict) or cid not in candidates:
        raise ValueError(f"Unknown blend_weights_v2_candidates id: {cid}")

    candidate_entry = candidates[cid]
    active_weights = dict(rules.get("blend_weights_v2") or {})
    candidate_weights = dict(candidate_entry.get("weights") or {})
    weight_apply_status = _resolve_weight_apply_state(
        rules,
        candidate_id=cid,
        active_weights=active_weights,
        candidate_weights=candidate_weights,
    )
    already_applied = bool(weight_apply_status.get("candidate_already_applied"))

    active_cal = build_calendar(
        year_month=year_month,
        skip_panel=True,
        profile="v2_multilens",
    )
    candidate_cal = build_calendar(
        year_month=year_month,
        skip_panel=True,
        profile="v2_multilens",
        weights_candidate_id=cid,
    )

    active_map = _row_direction_map(active_cal)
    candidate_map = _row_direction_map(candidate_cal)
    all_dates = sorted(set(active_map) | set(candidate_map))

    diffs: list[dict[str, Any]] = []
    for dk in all_dates:
        a = active_map.get(dk, "neutral")
        c = candidate_map.get(dk, "neutral")
        if a != c:
            diffs.append({"session_date": dk, "active": a, "candidate": c})

    active_eval = eval_calendar(active_cal)
    candidate_eval = eval_calendar(candidate_cal)

    proxy_policy = rules.get("proxy_forward_policy") if isinstance(rules.get("proxy_forward_policy"), dict) else {}
    proxy_forward_eval: dict[str, Any] | None = None
    if proxy_policy.get("enabled"):
        from scripts.run_kospi_june2026_proxy_forward_eval_v1 import run_proxy_forward_eval  # noqa: WPS433

        proxy_forward_eval = run_proxy_forward_eval(
            rules=rules,
            proxy_year_month=str(proxy_policy.get("proxy_year_month") or "2026-05"),
            candidate_id=cid,
        )

    backtest_ref = candidate_entry.get("backtest_ref") if isinstance(candidate_entry.get("backtest_ref"), dict) else {}
    backtest_delta: dict[str, Any] = {}
    if backtest_doc:
        variants = backtest_doc.get("variants") if isinstance(backtest_doc.get("variants"), list) else []
        active_v = next((v for v in variants if v.get("variant_id") == "v2_default"), None)
        cand_v = next((v for v in variants if v.get("variant_id") == cid), None)
        if active_v and cand_v:
            a_soft = active_v.get("metrics", {}).get("soft_hit_rate")
            c_soft = cand_v.get("metrics", {}).get("soft_hit_rate")
            a_dir = active_v.get("metrics", {}).get("directional_hit_rate")
            c_dir = cand_v.get("metrics", {}).get("directional_hit_rate")
            backtest_delta = {
                "active_variant_id": "v2_default",
                "candidate_variant_id": cid,
                "soft_hit_rate_active": a_soft,
                "soft_hit_rate_candidate": c_soft,
                "soft_hit_rate_delta_candidate_minus_active": (
                    round(float(c_soft) - float(a_soft), 4) if a_soft is not None and c_soft is not None else None
                ),
                "directional_hit_rate_active": a_dir,
                "directional_hit_rate_candidate": c_dir,
                "directional_hit_rate_delta_candidate_minus_active": (
                    round(float(c_dir) - float(a_dir), 4) if a_dir is not None and c_dir is not None else None
                ),
            }

    proxy_min = int(proxy_policy.get("min_scored_for_promotion_substitute", 15))
    proxy_substitute = bool(proxy_policy.get("substitute_june_forward_gate", False))
    proxy_n = int((proxy_forward_eval or {}).get("active", {}).get("n_scored") or 0)
    proxy_gate_pass = bool(proxy_forward_eval and proxy_forward_eval.get("gate_pass"))
    effective_policy = _resolve_effective_policy(policy, rules, proxy_gate_pass=proxy_gate_pass)

    min_delta = float(effective_policy.get("min_backtest_soft_delta_vs_active", 0.04))
    min_forward = int(effective_policy.get("june_forward_min_scored_for_promotion", 10))
    bt_delta = backtest_delta.get("soft_hit_rate_delta_candidate_minus_active")
    n_scored = int(active_eval.get("n_scored") or 0)
    promotion_ready = False
    promotion_blockers: list[str] = []

    if already_applied:
        promotion_blockers = []
    else:
        if policy.get("promotion_requires_human_signoff", True):
            promotion_blockers.append("human_signoff_required")
        if bt_delta is None or float(bt_delta) < min_delta:
            promotion_blockers.append(f"backtest_soft_delta<{min_delta}")

    forward_via: str | None = None
    if n_scored >= min_forward:
        forward_via = "june_elapsed"
    elif proxy_substitute and proxy_gate_pass:
        forward_via = f"proxy_{proxy_policy.get('proxy_year_month', '2026-05')}"
    else:
        if not already_applied:
            if n_scored < min_forward:
                promotion_blockers.append(f"june_forward_n_scored<{min_forward}")
            if proxy_substitute and proxy_n < proxy_min:
                promotion_blockers.append(f"proxy_forward_n_scored<{proxy_min}")

    shadow_horizon = _shadow_myeongni_horizon_contract(horizon_v2_doc, rules=rules)
    walk_prefilter = _walkforward_prefilter(walkforward_doc, candidate_id=cid, policy=effective_policy)
    if not already_applied:
        if walk_prefilter:
            promotion_blockers.extend(walk_prefilter.get("walkforward_blockers") or [])
        elif policy.get("min_walkforward_selection_top1_hit_rate") is not None:
            promotion_blockers.append("walkforward_artifact_missing")

    auto_blockers = [b for b in promotion_blockers if b != "human_signoff_required"]
    forward_ok = forward_via is not None
    if not already_applied and not auto_blockers:
        if (
            bt_delta is not None
            and float(bt_delta) >= min_delta
            and forward_ok
            and (walk_prefilter is None or walk_prefilter.get("walkforward_gate_pass"))
        ):
            promotion_ready = True
    forward_readiness = None
    if eval_doc is not None:
        from scripts.build_kospi_june2026_promotion_readiness_v1 import build_readiness  # noqa: WPS433

        forward_readiness = build_readiness(
            year_month=year_month,
            compare_doc={
                "candidate_id": cid,
                "n_trading_days": len(all_dates),
                "june_forward_eval": {
                    "active": {"n_scored": active_eval.get("n_scored"), "metrics": active_eval.get("metrics")},
                },
                "backtest_delta": backtest_delta,
                "walkforward_prefilter": walk_prefilter,
                "proxy_forward_eval": proxy_forward_eval,
                "forward_gate_via": forward_via,
                "promotion_recommendation": {
                    "ready_for_apply_review": promotion_ready,
                    "blockers": promotion_blockers,
                    "apply_command": (
                        "py scripts/run_kospi_june2026_prophecy_evolution_v1.py "
                        f"--apply-approved --apply-candidate-id {cid}"
                    ),
                },
            },
            eval_doc=eval_doc,
            rules=rules,
        )

    return {
        "schema": "kospi_june2026_weight_candidate_compare_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "year_month": year_month,
        "candidate_id": cid,
        "candidate_status": (
            "applied_active" if already_applied else candidate_entry.get("status")
        ),
        "candidate_note_ko": candidate_entry.get("note_ko"),
        "weight_apply_status": weight_apply_status,
        "active_weights": active_weights,
        "candidate_weights": candidate_weights,
        "direction_counts": {
            "active": _direction_counts(active_cal.get("rows") or []),
            "candidate": _direction_counts(candidate_cal.get("rows") or []),
        },
        "n_trading_days": len(all_dates),
        "n_direction_diffs": len(diffs),
        "direction_diffs": diffs,
        "june_forward_eval": {
            "active": {
                "n_scored": active_eval.get("n_scored"),
                "metrics": active_eval.get("metrics"),
            },
            "candidate": {
                "n_scored": candidate_eval.get("n_scored"),
                "metrics": candidate_eval.get("metrics"),
            },
        },
        "backtest_ref": backtest_ref,
        "backtest_delta": backtest_delta,
        "weight_candidate_policy": dict(policy),
        "effective_weight_candidate_policy": effective_policy,
        "promotion_recommendation": {
            "ready_for_apply_review": promotion_ready,
            "blockers": promotion_blockers,
            "candidate_already_applied": already_applied,
            "apply_command": (
                "py scripts/run_kospi_june2026_prophecy_evolution_v1.py "
                f"--apply-approved --apply-candidate-id {cid}"
            ),
            "note": (
                "June lane — 가중치 적용 완료. Track A / live trading blocked."
                if already_applied
                else "June lane only. Does not auto-apply. Track A / live trading blocked."
            ),
        },
        "shadow_horizon_contract": shadow_horizon,
        "walkforward_prefilter": walk_prefilter,
        "proxy_forward_eval": proxy_forward_eval,
        "forward_gate_via": forward_via,
        "forward_readiness": forward_readiness,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", type=str, default="2026-06")
    ap.add_argument("--candidate-id", type=str, default=None)
    ap.add_argument("--backtest-json", type=Path, default=BACKTEST_DEFAULT)
    ap.add_argument("--horizon-v2-json", type=Path, default=HORIZON_V2_DEFAULT)
    ap.add_argument("--walkforward-json", type=Path, default=WALKFORWARD_DEFAULT)
    ap.add_argument("--eval-json", type=Path, default=ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rules = _read_json(EVOLUTION_RULES)
    backtest_doc = _read_json(args.backtest_json) if args.backtest_json.is_file() else None
    horizon_v2_doc = _read_json(args.horizon_v2_json) if args.horizon_v2_json.is_file() else None
    walkforward_doc = _read_json(args.walkforward_json) if args.walkforward_json.is_file() else None
    eval_doc = _read_json(args.eval_json) if args.eval_json.is_file() else None

    doc = compare_candidates(
        rules=rules,
        year_month=args.year_month,
        candidate_id=args.candidate_id,
        backtest_doc=backtest_doc,
        horizon_v2_doc=horizon_v2_doc,
        walkforward_doc=walkforward_doc,
        eval_doc=eval_doc,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} candidate={doc['candidate_id']} "
        f"diffs={doc['n_direction_diffs']} promotion_ready={doc['promotion_recommendation']['ready_for_apply_review']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
