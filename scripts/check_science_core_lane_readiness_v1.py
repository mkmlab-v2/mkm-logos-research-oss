#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core B-track lane readiness gate [HYPO][research_only].

Checks required scripts exist and (optionally) governance bundle contract fields.
Does not re-run empirical eval. Track A / live trading promotion forbidden.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SCRIPTS = (
    "scripts/btrack_science_core_v1.py",
    "scripts/build_btrack_science_core_per_date_v1.py",
    "scripts/run_science_core_horizon_empirical_eval_v1.py",
    "scripts/run_science_core_holdout_combo_v1.py",
    "scripts/run_science_core_walkforward_v1.py",
    "scripts/run_science_core_long_walkforward_v1.py",
    "scripts/run_science_core_governance_bundle_v1.py",
    "scripts/run_science_core_macro_gate_bias_audit_v1.py",
    "scripts/run_science_core_long_history_slice_eval_v1.py",
    "scripts/run_science_core_humanist_source_ab_v1.py",
    "scripts/backfill_exa_macro_news_observation_v1.py",
    "scripts/run_science_core_news_coverage_audit_v1.py",
    "scripts/run_science_core_news_weight_ablation_v1.py",
    "scripts/run_science_core_long_window_lane_compare_v1.py",
    "scripts/run_science_core_triple_blend_weight_sweep_v1.py",
    "scripts/run_science_core_pnl_bootstrap_v1.py",
    "scripts/run_science_core_prophecy_combo_attach_v1.py",
    "scripts/build_science_core_instrument_matrix_v1.py",
    "scripts/run_science_core_conditional_attach_research_v1.py",
    "scripts/run_science_core_prophecy_combo_sensitivity_v1.py",
    "scripts/build_science_core_shock_discordant_day_report_v1.py",
    "scripts/build_btrack_market_sasang_per_date_jsonl_v1.py",
    "scripts/build_btrack_myeongni_per_date_jsonl_v1.py",
    "scripts/build_btrack_logos_per_date_jsonl_v1.py",
    "scripts/Run-ScienceCoreGovernanceBundle_v1.ps1",
    "scripts/Run-ScienceCoreDailyPassive_v1.ps1",
    "scripts/Run-ScienceCoreKospiModeBResearch_v1.ps1",
    "scripts/Register-ScienceCoreKospiModeBWeeklyTask.ps1",
    "scripts/Register-ScienceCoreWeeklyGovernanceTask.ps1",
    "scripts/Verify-ScienceCoreWeeklyGovernanceTask_v1.ps1",
    "scripts/run_science_core_kospi_shock_only_attach_backtest_v1.py",
)

DEFAULT_GOVERNANCE = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/science_core_lane_readiness_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _check_scripts() -> tuple[list[str], list[str]]:
    missing: list[str] = []
    present: list[str] = []
    for rel in REQUIRED_SCRIPTS:
        p = ROOT / rel
        if p.is_file():
            present.append(rel)
        else:
            missing.append(rel)
    return present, missing


def _validate_governance(doc: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    promo = doc.get("promotion_gate") or {}
    if promo.get("track_a_ready") is True:
        issues.append("promotion_gate.track_a_ready must be false")
    if promo.get("live_trading_ready") is True:
        issues.append("promotion_gate.live_trading_ready must be false")
    attach = doc.get("composite_attach") or doc.get("attach_recommendation")
    if not isinstance(attach, dict):
        issues.append("missing composite_attach or attach_recommendation object")
        return issues
    if "composite_attach_recommended" not in attach:
        issues.append("composite_attach.composite_attach_recommended missing")
    if "stub_blockers" not in attach and "humanist_stub_blockers" not in attach:
        issues.append("composite_attach stub_blockers missing")
    if "macro_blockers" not in attach:
        issues.append("composite_attach.macro_blockers missing")
    if doc.get("lane_id") and doc.get("lane_id") != "science_core_v1":
        issues.append(f"unexpected lane_id: {doc.get('lane_id')}")
    ext = doc.get("extended_audits")
    if ext is not None:
        if not isinstance(ext, dict):
            issues.append("extended_audits must be object")
        else:
            for key in (
                "macro_gate_bias_bundle_window",
                "holdout_slice_ab",
                "news_coverage",
                "era_split_news_policy",
            ):
                if key not in ext:
                    issues.append(f"extended_audits.{key} missing")
            long_macro = ext.get("macro_gate_bias_long_history")
            if long_macro is not None and not isinstance(long_macro, dict):
                issues.append("extended_audits.macro_gate_bias_long_history must be object or null")
            long_cmp = ext.get("long_window_lane_compare")
            if long_cmp is not None:
                if not isinstance(long_cmp, dict):
                    issues.append("extended_audits.long_window_lane_compare must be object")
                else:
                    for leg in ("kospi", "btc"):
                        if leg not in long_cmp:
                            issues.append(f"extended_audits.long_window_lane_compare.{leg} missing")
                        elif not isinstance((long_cmp.get(leg) or {}).get("eras"), dict):
                            issues.append(
                                f"extended_audits.long_window_lane_compare.{leg}.eras must be object"
                            )
    if "instrument_parity_summary" not in doc:
        issues.append("instrument_parity_summary missing")
    elif not isinstance((doc.get("instrument_parity_summary") or {}).get("btc"), dict):
        issues.append("instrument_parity_summary.btc missing")
    if "humanist_combo_holdout" not in doc:
        issues.append("humanist_combo_holdout missing")
    btc_aux = doc.get("btc_holdout_auxiliary")
    if not isinstance(btc_aux, dict):
        issues.append("btc_holdout_auxiliary missing")
    elif btc_aux.get("gates_primary_attach") is True:
        issues.append("btc_holdout_auxiliary.gates_primary_attach must be false")
    pnl = doc.get("pnl_economic_significance")
    if not isinstance(pnl, dict):
        issues.append("pnl_economic_significance missing")
    elif pnl.get("economic_edge_claim_allowed") is True:
        issues.append("pnl_economic_significance.economic_edge_claim_allowed must be false")
    return issues


def build_report(*, strict_governance: bool, governance_path: Path) -> dict[str, Any]:
    present, missing = _check_scripts()
    scripts_ok = len(missing) == 0

    governance_status: dict[str, Any] = {
        "path": _repo_rel(governance_path),
        "exists": governance_path.is_file(),
        "valid": False,
        "issues": [],
    }
    composite_summary: dict[str, Any] | None = None

    if governance_path.is_file():
        try:
            doc = json.loads(governance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            governance_status["issues"] = [f"json_decode_error: {exc}"]
        else:
            issues = _validate_governance(doc)
            governance_status["issues"] = issues
            governance_status["valid"] = len(issues) == 0
            attach = doc.get("composite_attach") or doc.get("attach_recommendation") or {}
            composite_summary = {
                "composite_attach_recommended": attach.get("composite_attach_recommended"),
                "recommended_lane": attach.get("recommended_lane"),
                "stub_blockers": attach.get("stub_blockers") or attach.get("humanist_stub_blockers"),
            }
            wf = doc.get("walkforward") or {}
            if isinstance(wf, dict):
                composite_summary["walkforward_top1_soft"] = wf.get("top1_soft_rate")
            long_wf = doc.get("long_walkforward")
            if long_wf is not None:
                composite_summary["long_walkforward_present"] = True
            ext = doc.get("extended_audits") or {}
            if ext:
                slice_ab = ext.get("holdout_slice_ab") or {}
                composite_summary["holdout_slice_delta_market_minus_stub_soft"] = slice_ab.get(
                    "delta_science_plus_sasang_soft"
                )
                news = ext.get("news_coverage") or {}
                composite_summary["news_causal_exa_share"] = news.get("causal_exa_share")
            shock_only = doc.get("shock_only_attach_policy")
            if isinstance(shock_only, dict):
                composite_summary["shock_only_attach_recommended"] = shock_only.get(
                    "attach_on_shock_only_recommended"
                )
                composite_summary["shock_only_policy_hypothesis"] = shock_only.get(
                    "recommended_hypothesis"
                )
                composite_summary["shock_only_vs_always_sasang_soft_pp"] = shock_only.get(
                    "shock_only_vs_always_sasang_soft_pp"
                )
    elif strict_governance:
        governance_status["issues"] = ["governance_bundle_missing"]

    readiness_ok = scripts_ok and (
        (not strict_governance)
        or (governance_status["exists"] and governance_status["valid"])
    )

    return {
        "schema": "science_core_lane_readiness_v1",
        "generated_at_utc": _utc_now(),
        "lane_id": "science_core_v1",
        "boundary": "[HYPO][research_only] — Track A·실매매 자동 합선 금지",
        "readiness_ok": readiness_ok,
        "scripts": {
            "required_count": len(REQUIRED_SCRIPTS),
            "present_count": len(present),
            "missing": missing,
        },
        "governance": governance_status,
        "composite_summary": composite_summary,
        "strict_governance": strict_governance,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOVERNANCE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--strict-governance",
        action="store_true",
        help="Require governance bundle to exist and pass contract checks.",
    )
    args = ap.parse_args(argv)

    doc = build_report(strict_governance=args.strict_governance, governance_path=args.governance_json)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")

    print(
        f"WROTE: {args.output.resolve()} readiness_ok={doc['readiness_ok']} "
        f"missing_scripts={len(doc['scripts']['missing'])}"
    )
    return 0 if doc["readiness_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
