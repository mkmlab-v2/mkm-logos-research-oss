#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit envelope vs MKM bench closure summary [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_TIER1_DUAL = ROOT / "reports/btrack_envelope_vs_prophecy_dual_report_v1_latest.json"
DEFAULT_TIER2_DUAL = ROOT / "reports/btrack_envelope_tier2_dual_report_v1_latest.json"
DEFAULT_KNIFE = ROOT / "reports/btrack_envelope_severe_knife_panel_v1_latest.json"
DEFAULT_DESIGN = ROOT / "reports/btrack_envelope_ma_vs_prophecy_benchmark_hypo_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_envelope_benchmark_closure_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(tier2: dict, arm_id: str, scope: str) -> dict | None:
    for row in tier2.get("envelope_equity_pooled_vs_mkm") or []:
        if row.get("arm_id") == arm_id and row.get("scope") == scope:
            return row
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tier1-dual", type=Path, default=DEFAULT_TIER1_DUAL)
    ap.add_argument("--tier2-dual", type=Path, default=DEFAULT_TIER2_DUAL)
    ap.add_argument("--knife-json", type=Path, default=DEFAULT_KNIFE)
    ap.add_argument("--design-json", type=Path, default=DEFAULT_DESIGN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-design-patch", action="store_true")
    args = ap.parse_args()

    for p in (args.tier1_dual, args.tier2_dual, args.knife_json):
        if not p.is_file():
            print(f"missing: {p}", file=sys.stderr)
            return 1

    tier1 = json.loads(args.tier1_dual.read_text(encoding="utf-8"))
    tier2 = json.loads(args.tier2_dual.read_text(encoding="utf-8"))
    knife = json.loads(args.knife_json.read_text(encoding="utf-8"))

    mkm_raw = tier1.get("mkm_frozen_kospi_leg", {}).get("directional_hit_rate_raw")
    arm_a_full = _row(tier2, "arm_a_naked_60d_6", "pooled_full") or {}
    arm_a_trend = _row(tier2, "arm_a_naked_60d_6", "pooled_envelope_trend_gate_v1") or {}
    arm_c_full = _row(tier2, "arm_c_120d_up_60d_pullback", "pooled_full") or {}
    arm_c_trend = _row(tier2, "arm_c_120d_up_60d_pullback", "pooled_envelope_trend_gate_v1") or {}

    knife_a = (knife.get("by_arm") or {}).get("arm_a_naked_60d_6", {}).get("pooled_severe_knife") or {}

    tier1_arm_c = None
    for row in tier1.get("envelope_arms_vs_mkm") or []:
        if row.get("arm_id") == "arm_c_120d_up_60d_pullback" and row.get("scope") == "full_180d":
            tier1_arm_c = row
            break

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            return str(p)

    closure = {
        "schema": "btrack_envelope_benchmark_closure_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "combined_all_passed": False,
        "track_a_auto_promote": False,
        "oper_score_ssot_read_only": {
            "path": "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json",
            "generated_at_utc": tier1.get("mkm_frozen_kospi_leg", {}).get("oper_score_generated_at_utc"),
            "kospi_directional_hit_rate_raw": mkm_raw,
            "note": "not overwritten by envelope bench",
        },
        "eval_window": knife.get("eval_window"),
        "kpi_caveat_ko": (
            "envelope=entry 후 익일 bull hit; MKM kospi=per-date direction match — "
            "Tier-2는 종목 basket vs 지수 leg (weak fairness)"
        ),
        "decision_tree_outcome": {
            "branch_id": "similar_or_incomparable_within_ci",
            "rationale_ko": (
                "Tier-1: arm_a/b 0신호·arm_c n=3 — MKM 57.2%와 공정 우열 불가. "
                "Tier-2: arm_a pooled +5.6pp이나 KPI·universe 상이·severe knife bear 37% — "
                "oper score 대체·Track A 승격 근거 아님. default=H2 governance/OS 차별."
            ),
            "never": ["envelope_oper_score_overwrite", "track_a_auto_merge", "headline_superiority_claim"],
        },
        "hypothesis_outcomes": {
            "H0_null": "not_falsified_tier1_underpowered; tier2_narrative_only",
            "H1_envelope_better_dips": "weak_partial_tier2_arm_a_only_with_caveats",
            "H2_mkm_better_governance": "affirmed_primary_posture",
            "H4_smct_gated_envelope": "legacy_light_medium_0_signals; trend_gate_v1_risk_filter_not_hit_lift",
        },
        "results_snapshot": {
            "tier1_kospi": {
                "arm_a_b_signals": 0,
                "arm_c_full": {
                    "directional_hit_rate_raw": (tier1_arm_c or {}).get("envelope", {})
                    .get("raw", {})
                    .get("directional_hit_rate"),
                    "n_entry_signals": (tier1_arm_c or {}).get("envelope", {})
                    .get("raw", {})
                    .get("n_entry_signals"),
                    "delta_pp_vs_mkm": (tier1_arm_c or {}).get("delta", {}).get(
                        "directional_hit_rate_pp_envelope_minus_mkm"
                    ),
                },
                "arm_c_trend_gate_v1_hit": 1.0,
                "arm_c_trend_gate_v1_n": 1,
            },
            "tier2_equity_pooled": {
                "arm_a_full": {
                    "directional_hit_rate_raw": arm_a_full.get("envelope_pooled", {})
                    .get("raw", {})
                    .get("directional_hit_rate"),
                    "n_entry_signals": arm_a_full.get("envelope_pooled", {})
                    .get("raw", {})
                    .get("n_entry_signals"),
                    "delta_pp_vs_mkm": arm_a_full.get("delta_pp_envelope_minus_mkm"),
                },
                "arm_a_trend_gate_v1_signals": arm_a_trend.get("envelope_pooled", {})
                .get("raw", {})
                .get("n_entry_signals"),
                "arm_c_full_delta_pp": arm_c_full.get("delta_pp_envelope_minus_mkm"),
                "arm_c_trend_gate_v1": {
                    "directional_hit_rate_raw": arm_c_trend.get("envelope_pooled", {})
                    .get("raw", {})
                    .get("directional_hit_rate"),
                    "delta_pp_vs_mkm": arm_c_trend.get("delta_pp_envelope_minus_mkm"),
                },
            },
            "severe_knife_arm_a_pooled": {
                "severe_fraction": knife_a.get("severe_fraction_of_signals"),
                "severe_bear_rate": knife_a.get("severe_bear_rate"),
                "n_signals_total": knife_a.get("n_signals_total"),
            },
        },
        "required_output_block_raw_repair": {
            "raw": "envelope directional_hit + counts; MKM kospi frozen raw",
            "repair_v2": "not_applicable_envelope_path",
            "delta": "tier2_pp_narrative_only_where_shown",
        },
        "verdict_ko": (
            "research_only CLOSED — 커뮤니티 envelope는 B-track 서사·리스크 교육용. "
            "MKM frozen kospi 57.2%·combined false·SEND HOLD 유지. "
            "상승 complement [HYPO]만 가능; oper/live·Track A 자동 합선 금지."
        ),
        "sources": {
            "tier1_dual": _rel(args.tier1_dual),
            "tier2_dual": _rel(args.tier2_dual),
            "severe_knife": _rel(args.knife_json),
            "design": _rel(args.design_json) if args.design_json.is_file() else str(args.design_json),
        },
        "repro": "py scripts/build_btrack_envelope_benchmark_closure_v1.py",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.write_design_patch and args.design_json.is_file():
        design = json.loads(args.design_json.read_text(encoding="utf-8"))
        design["generated_at_utc"] = _utc()
        design["verdict_preview"] = closure["verdict_ko"]
        design["bench_closure_v1"] = {
            "artifact": _rel(args.output),
            "status": "closed_research_only_2026-06-13",
            "decision_tree_branch": closure["decision_tree_outcome"]["branch_id"],
        }
        design["implementation_sketch"]["status"] = "closure_2026-06-13"
        design["implementation_sketch"]["verification"] = (
            "py -m pytest tests/test_envelope_ma_backtest_hypo_v1.py -q && "
            "py scripts/build_btrack_envelope_benchmark_closure_v1.py --write-design-patch"
        )
        design["implementation_sketch"]["pilot_artifacts"].append(
            "reports/btrack_envelope_benchmark_closure_v1_latest.json"
        )
        design["operator_lines"] = [
            "- [ENVELOPE-BENCH-HYPO] CLOSED research_only 2026-06-13; oper score NOT overwritten.",
            "- [ENVELOPE-BENCH-HYPO] Tier-1 KOSPI: arm_a/b 0 signals; arm_c n=3 vs MKM kospi 57.2% — fair 우열 불가.",
            "- [ENVELOPE-BENCH-HYPO] Tier-2 6종 arm_a pooled 62.8% (+5.6pp weak); severe 100%·bear-next 37% — narrative only.",
            "- [ENVELOPE-BENCH-HYPO] H4: legacy SMCT subset 0; trend_gate_v1=knife filter (arm_a/b tier2 0 signals).",
            "- [ENVELOPE-BENCH-HYPO] Posture=H2 MKM governance; complement dip rule [HYPO] only; SEND_GATE HOLD.",
            f"- [ENVELOPE-BENCH-HYPO] Closure SSOT: {args.output.name}",
        ]
        disallowed = design.get("disallowed_claims") or []
        design["disallowed_claims"] = [
            c for c in disallowed if "백테스트 전" not in c
        ] + [
            "Tier-2 envelope +5.6pp as MKM kospi replacement",
            "severe-knife ignored dip-buy promotion",
        ]
        args.design_json.write_text(json.dumps(design, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
