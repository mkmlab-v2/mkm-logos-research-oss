#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI weight-candidate promotion readiness tracker [HYPO][research_only]."""

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
COMPARE_DEFAULT = ROOT / "reports/kospi_june2026_weight_candidate_compare_latest.json"
EVAL_DEFAULT = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_promotion_readiness_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_june2026_promotion_readiness_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _calendar_path(year_month: str) -> Path:
    cal_path = ROOT / f"reports/kospi_{year_month.replace('-', '')}_daily_prophecy_calendar_v1.json"
    if not cal_path.is_file() and year_month == "2026-06":
        cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    return cal_path


def _count_june_trading_days(year_month: str) -> int:
    cal = _read_json(_calendar_path(year_month))
    return len(cal.get("rows") or [])


def _project_forward_gate_eta(
    *,
    year_month: str,
    remaining: int,
    scored_dates: set[str],
    missing_ohlcv: list[str],
    vendor_incomplete: list[str] | None = None,
    min_forward: int,
) -> dict[str, Any]:
    """Estimate which calendar session_date reaches n_scored gate (evening cadence)."""
    if remaining <= 0:
        return {
            "projected_gate_session_date": None,
            "pending_scoreable_dates": [],
            "gate_reachable_in_month": True,
            "eta_note_ko": "이미 포워드 게이트 충족.",
        }
    cal = _read_json(_calendar_path(year_month))
    trading_days = [str(d) for d in (cal.get("trading_days") or []) if d]
    if not trading_days:
        rows = cal.get("rows") or []
        trading_days = sorted(str(r.get("session_date")) for r in rows if r.get("session_date"))
    missing_set = set(missing_ohlcv) | set(vendor_incomplete or [])
    pending = [d for d in trading_days if d not in scored_dates and d not in missing_set]
    gate_date = pending[remaining - 1] if len(pending) >= remaining else None
    reachable = gate_date is not None
    return {
        "projected_gate_session_date": gate_date,
        "pending_scoreable_dates": pending[: min(len(pending), remaining + 3)],
        "gate_reachable_in_month": reachable,
        "eta_note_ko": (
            f"6월 실경과 {len(scored_dates)}일 — OHLCV 있는 날은 evening 1회에 일괄 채점됨. "
            f"June {min_forward}일 게이트는 거래일 {remaining}건 더 경과 시 {gate_date} 예상 "
            f"(6/3 선거 휴장은 krx_non_trading_days_v1로 제외). 전월 프록시 채점은 즉시 가능."
            if reachable
            else f"6월 잔여 채점 가능일({len(pending)}) < 게이트 잔여({remaining}) — 월 내 불가."
        ),
    }


def build_readiness(
    *,
    year_month: str,
    compare_doc: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    policy = rules.get("weight_candidate_policy") if isinstance(rules.get("weight_candidate_policy"), dict) else {}
    cid = str(compare_doc.get("candidate_id") or policy.get("active_candidate_id") or "v2_lens3_heavy")
    eff_policy = compare_doc.get("effective_weight_candidate_policy")
    if not isinstance(eff_policy, dict):
        eff_policy = policy
    policy_tier = str(eff_policy.get("policy_tier") or policy.get("policy_tier") or "default")
    min_forward = int(eff_policy.get("june_forward_min_scored_for_promotion", 15))
    min_bt_delta = float(eff_policy.get("min_backtest_soft_delta_vs_active", 0.06))
    min_wf_top1 = float(policy.get("min_walkforward_selection_top1_hit_rate", 0.52))

    promo = compare_doc.get("promotion_recommendation") if isinstance(compare_doc.get("promotion_recommendation"), dict) else {}
    bt_delta = compare_doc.get("backtest_delta") if isinstance(compare_doc.get("backtest_delta"), dict) else {}
    soft_delta = bt_delta.get("soft_hit_rate_delta_candidate_minus_active")

    n_scored = int((compare_doc.get("june_forward_eval") or {}).get("active", {}).get("n_scored") or eval_doc.get("n_scored") or 0)
    n_trading_days = int(compare_doc.get("n_trading_days") or _count_june_trading_days(year_month))
    remaining = max(0, min_forward - n_scored)
    progress_pct = round(min(1.0, n_scored / min_forward) * 100.0, 1) if min_forward else 0.0
    missing_ohlcv = list(eval_doc.get("missing_ohlcv_trading_days") or [])
    vendor_incomplete = list(eval_doc.get("vendor_incomplete_trading_days") or [])
    scored_dates = {
        str(r.get("session_date"))
        for r in (eval_doc.get("rows") or [])
        if r.get("session_date") and r.get("actual_direction")
    }
    unscored_eligible = max(0, n_trading_days - len(scored_dates) - len(missing_ohlcv) - len(vendor_incomplete))
    projected_days_to_gate = remaining if unscored_eligible >= remaining else None
    gate_eta = _project_forward_gate_eta(
        year_month=year_month,
        remaining=remaining,
        scored_dates=scored_dates,
        missing_ohlcv=missing_ohlcv,
        vendor_incomplete=vendor_incomplete,
        min_forward=min_forward,
    )

    proxy_eval = compare_doc.get("proxy_forward_eval") if isinstance(compare_doc.get("proxy_forward_eval"), dict) else {}
    forward_via = compare_doc.get("forward_gate_via")
    proxy_policy = rules.get("proxy_forward_policy") if isinstance(rules.get("proxy_forward_policy"), dict) else {}

    apply_status = compare_doc.get("weight_apply_status") if isinstance(compare_doc.get("weight_apply_status"), dict) else {}
    if not apply_status.get("candidate_already_applied") and rules.get("last_candidate_apply_id") == cid:
        aw = compare_doc.get("active_weights") if isinstance(compare_doc.get("active_weights"), dict) else rules.get("blend_weights_v2") or {}
        cw = compare_doc.get("candidate_weights") if isinstance(compare_doc.get("candidate_weights"), dict) else {}
        if aw and cw:
            from scripts.run_kospi_june2026_weight_candidate_compare_v1 import _resolve_weight_apply_state  # noqa: WPS433

            apply_status = _resolve_weight_apply_state(
                rules, candidate_id=cid, active_weights=aw, candidate_weights=cw
            )
    already_applied = bool(
        apply_status.get("candidate_already_applied") or promo.get("candidate_already_applied")
    )

    blockers = list(promo.get("blockers") or [])
    walk_pref = compare_doc.get("walkforward_prefilter") if isinstance(compare_doc.get("walkforward_prefilter"), dict) else {}
    wf_top1_actual = walk_pref.get("selection_top1_hit_rate")
    wf_top1_pass = bool(walk_pref["walkforward_gate_pass"]) if walk_pref else None
    gates = {
        "backtest_soft_delta": {
            "required_min": min_bt_delta,
            "actual": soft_delta,
            "pass": (
                True
                if already_applied
                else soft_delta is not None and float(soft_delta) >= min_bt_delta
            ),
            "note": "active=candidate — Δ N/A" if already_applied else None,
        },
        "june_forward_n_scored": {
            "required_min": min_forward,
            "actual": n_scored,
            "pass": n_scored >= min_forward,
        },
        "proxy_forward_substitute": {
            "enabled": bool(proxy_policy.get("enabled")),
            "proxy_year_month": proxy_policy.get("proxy_year_month"),
            "required_min": int(proxy_policy.get("min_scored_for_promotion_substitute", 15)),
            "actual": (proxy_eval.get("active") or {}).get("n_scored"),
            "pass": bool(proxy_eval.get("gate_pass")),
            "forward_gate_via": forward_via,
            "note": "June 실경과 대체 아님 — apply 검토 보조",
        },
        "walkforward_prefilter": {
            "required_min_selection_top1": min_wf_top1,
            "actual_selection_top1": wf_top1_actual,
            "candidate_in_top2": walk_pref.get("candidate_in_top2"),
            "pass": wf_top1_pass if walk_pref else None,
            "note": "artifact 없으면 pass=None",
        },
        "human_signoff": {
            "required": bool(policy.get("promotion_requires_human_signoff", True)),
            "pass": already_applied,
            "signed_at_utc": apply_status.get("last_candidate_apply_at_utc") if already_applied else None,
            "note": (
                f"적용 완료 ({apply_status.get('last_candidate_apply_at_utc')})"
                if already_applied
                else "지휘관 --apply-approved 전제"
            ),
        },
    }
    forward_gate_pass = forward_via is not None
    auto_gates_pass = (
        not already_applied
        and gates["backtest_soft_delta"]["pass"]
        and forward_gate_pass
        and gates["walkforward_prefilter"]["pass"] is True
    )
    if already_applied:
        blockers = []
    human_apply_review = {
        "ready_for_apply_review": False if already_applied else bool(promo.get("ready_for_apply_review")),
        "candidate_already_applied": already_applied,
        "auto_gates_pass_pending_human": auto_gates_pass,
        "apply_command": promo.get("apply_command"),
        "checklist_ko": [
            "Track A·실매매 자동 합선 없음 확인",
            "forward_gate_via·proxy 보조 경로 확인",
            "백테스트·WF·June/프록시 수치 리포트 §6.3 확인",
            "승인 후에만: py scripts/run_kospi_june2026_prophecy_evolution_v1.py --apply-approved --apply-candidate-id v2_lens3_heavy",
        ],
    }

    return {
        "schema": "kospi_june2026_promotion_readiness_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "year_month": year_month,
        "candidate_id": cid,
        "policy_tier": policy_tier,
        "forward_scoring": {
            "n_scored": n_scored,
            "min_required": min_forward,
            "remaining_to_gate": remaining,
            "progress_pct": progress_pct,
            "n_trading_days_in_month": n_trading_days,
            "missing_ohlcv": missing_ohlcv,
            "vendor_incomplete_trading_days": vendor_incomplete,
            "unscored_eligible_trading_days": unscored_eligible,
            "projected_trading_days_to_gate": projected_days_to_gate,
            "projected_gate_session_date": gate_eta.get("projected_gate_session_date"),
            "gate_reachable_in_month": gate_eta.get("gate_reachable_in_month"),
            "pending_scoreable_dates": gate_eta.get("pending_scoreable_dates"),
            "eta_note_ko": gate_eta.get("eta_note_ko"),
        },
        "backtest": {
            "soft_delta_candidate_minus_active": soft_delta,
            "min_required_delta": min_bt_delta,
        },
        "gates": gates,
        "blockers": blockers,
        "ready_for_apply_review": False if already_applied else bool(promo.get("ready_for_apply_review")),
        "candidate_already_applied": already_applied,
        "weight_apply_status": apply_status,
        "auto_gates_pass_pending_human": auto_gates_pass,
        "human_apply_review": human_apply_review,
        "gate_relaxation_active": bool(eff_policy.get("_relaxation_active")),
        "apply_command": promo.get("apply_command"),
        "verdict_ko": (
            str(apply_status.get("apply_state_ko") or "")
            if already_applied
            else (
                f"포워드 {n_scored}/{min_forward}"
                + (f" (보조: {forward_via})" if forward_via and forward_via != "june_elapsed" else "")
                + f" — 승격 검토 {'가능(인간승인 대기)' if auto_gates_pass else '보류'}"
            )
        ),
        "note": (
            "Track A / live trading blocked. 가중치 적용 완료 — June 포워드 모니터링."
            if already_applied
            else "Track A / live trading blocked. apply는 human sign-off 후에만."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", type=str, default="2026-06")
    ap.add_argument("--compare-json", type=Path, default=COMPARE_DEFAULT)
    ap.add_argument("--eval-json", type=Path, default=EVAL_DEFAULT)
    ap.add_argument("--rules-json", type=Path, default=EVOLUTION_RULES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = build_readiness(
        year_month=args.year_month,
        compare_doc=_read_json(args.compare_json),
        eval_doc=_read_json(args.eval_json),
        rules=_read_json(args.rules_json),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.artifact_output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fs = doc["forward_scoring"]
    print(
        f"WROTE: {args.output.resolve()} n_scored={fs['n_scored']}/{fs['min_required']} "
        f"auto_gates={doc['auto_gates_pass_pending_human']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
