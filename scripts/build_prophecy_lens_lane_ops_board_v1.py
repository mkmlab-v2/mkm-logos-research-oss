#!/usr/bin/env python3
"""Assemble prophecy lens lane ops board from disk SSOT artifacts [HYPO].

Quant / PersonaDiary / Oracle / fABBA sidecar — one operator-facing JSON.
Does not mutate scores, votes, or Track A paths.
"""
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

DEFAULT_V2 = ROOT / "reports/prophecy_lens_profile_shadow_ablation_v2_latest.json"
DEFAULT_PHASE3 = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
DEFAULT_FABBA_REG = ROOT / "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
DEFAULT_PHASE1 = ROOT / "reports/prophecy_protocol_harmonization_phase1_v1_latest.json"
DEFAULT_P2_COMPARE = ROOT / "reports/prophecy_protocol_phase1_moirai_dual_leg_compare_v1_latest.json"
DEFAULT_MOIRAI_DUAL = ROOT / "reports/rq025_moirai2_dual_leg_wf_shadow_v1_latest.json"
DEFAULT_NARRATIVE_MAP = ROOT / "docs/final/artifacts/narrative_knowledge_map_bundle_v1_latest.json"
DEFAULT_SIDEBAR_SMOKE = ROOT / "docs/final/artifacts/personadiary_logos_sidebar_smoke_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_lane_ops_board_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_lens_lane_ops_board_v1_latest.json"

SCHEMA = "prophecy_lens_lane_ops_board_v1"
VERSION = "1.3.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def build_board(
    *,
    v2_path: Path,
    phase3_path: Path,
    fabba_reg_path: Path,
    phase1_path: Path,
    p2_compare_path: Path,
    moirai_dual_path: Path,
    narrative_map_path: Path,
    sidebar_smoke_path: Path,
) -> dict[str, Any]:
    v2 = _read_json(v2_path)
    phase3 = _read_json(phase3_path)
    fabba_reg = _read_json(fabba_reg_path)
    phase1 = _read_json(phase1_path)
    p2_compare = _read_json(p2_compare_path)
    moirai_dual = _read_json(moirai_dual_path)
    narrative_map = _read_json(narrative_map_path)
    sidebar_smoke = _read_json(sidebar_smoke_path)

    protocol = v2.get("protocol") or {}
    arm_a = ((v2.get("arms") or {}).get("A") or {}).get("metrics") or {}
    arm_e = (v2.get("arms") or {}).get("E") or {}
    arm_e_dyn = (v2.get("arms") or {}).get("E_dynamic") or {}
    arm_d = (v2.get("arms") or {}).get("D") or {}
    wf_a = (v2.get("walkforward") or {}).get("A_science_sasang") or {}
    wf_e_dyn = (v2.get("walkforward") or {}).get("E_dynamic") or {}

    persona_lane = phase3.get("myeongni_sasang_lane") or {}
    persona_metrics = persona_lane.get("metrics") or {}
    persona_wf = persona_lane.get("walkforward_blocked") or {}

    fabba_registration = fabba_reg.get("registration") or {}
    fabba_shadow = fabba_reg.get("shadow_hr_evidence") or {}
    fabba_ngram = fabba_shadow.get("ngram_lut_kospi_dual_leg_180d_2bps") or {}
    fabba_lut = fabba_reg.get("lut_ablation_smoke") or {}

    science_logos_omit = ((arm_d.get("science+logos_by_mode") or {}).get("omit") or {})

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "decision_authority": "human_only",
        "protocol": {
            "cohort": protocol.get("protocol_id") or "180d_2bps_blocked_wf",
            "date_start": protocol.get("date_start"),
            "date_end": protocol.get("date_end"),
            "n_panel_rows": protocol.get("n_panel_rows"),
            "fee_bps": protocol.get("fee_bps"),
            "neutral_bps": protocol.get("neutral_bps"),
        },
        "lanes": {
            "quant": {
                "lane_id": "quant",
                "role_ko": "Quant shadow — prophecy direction vote SSOT",
                "strategy_id": "science+sasang",
                "logos_vote_mode": "omit",
                "prophecy_vote": "on_shadow_only",
                "track_a_promotion": False,
                "metrics_180d_2bps": arm_a if arm_a else None,
                "walkforward_mean_test_hr": wf_a.get("mean_test_directional_hit_rate_active"),
                "evidence_artifact": _rel(v2_path),
            },
            "persona_diary": {
                "lane_id": "persona_diary",
                "role_ko": "PersonaDiary/중기 — prophecy vote 제외",
                "strategy_id": "myeongni+sasang",
                "prophecy_vote": "off",
                "persona_diary_lane_recommended": persona_lane.get("persona_diary_lane_recommended"),
                "metrics_180d_2bps": persona_metrics if persona_metrics else None,
                "walkforward_mean_test_hr": persona_wf.get("mean_test_directional_hit_rate_active"),
                "vs_quant_sharpe_delta": (persona_lane.get("vs_arm_a_science_sasang") or {}).get(
                    "sharpe_delta"
                ),
                "evidence_artifact": _rel(phase3_path),
            },
            "oracle": {
                "lane_id": "oracle",
                "role_ko": "Oracle — Logos sidecar + Samsung regime_mkm_split (NON_GATING)",
                "logos": {
                    "non_gating": True,
                    "vote_mode_default": "omit",
                    "science_logos_blend_hr_180d": science_logos_omit.get("directional_hit_rate_active"),
                    "note_ko": "science+logos linear blend 열세 — quant vote에 Logos 합류 금지",
                },
                "regime_mkm_split": {
                    "recommended_policy": arm_e.get("recommended_policy"),
                    "recommended_regime_id": arm_e.get("recommended_regime_id"),
                    "returns_pct": arm_e.get("returns_pct"),
                    "delta_vs_bah_pp": arm_e.get("delta_vs_bah_pp"),
                    "interpretation_ko": arm_e.get("interpretation_ko"),
                },
                "evidence_artifacts": [
                    _rel(v2_path),
                    "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json",
                    "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json",
                ],
            },
            "fabba_sidecar": {
                "lane_id": "fabba_sidecar",
                "role_ko": "fABBA ngram_lut — merged LUT feature join only",
                "primary_sidecar_arm": fabba_registration.get("primary_sidecar_arm"),
                "vote_participation": fabba_registration.get("vote_participation"),
                "non_gating": fabba_registration.get("non_gating"),
                "opt_in_only": fabba_registration.get("opt_in_only"),
                "shadow_hr_kospi_dual_leg_180d_2bps": fabba_ngram.get("kospi_pooled_hr"),
                "shadow_hr_btc_dual_leg_180d_2bps": fabba_ngram.get("btc_pooled_hr"),
                "lut_feature_parity_ok": fabba_lut.get("feature_parity_ok"),
                "quant_ssot_unchanged": True,
                "evidence_artifact": _rel(fabba_reg_path),
                "merged_lut": (fabba_reg.get("artifacts") or {}).get("merged_lut"),
            },
        },
        "avoid": [
            {
                "id": "science_logos_blend",
                "reason_ko": "science+logos 180d HR ~33.9% — quant vote 합류 금지",
                "hr_180d": science_logos_omit.get("directional_hit_rate_active"),
            },
            {
                "id": "science_sasang_myeongni_triple",
                "reason_ko": "3-way linear blend −37.5pp vs Arm A",
                "delta_pp": ((v2.get("arms") or {}).get("C") or {})
                .get("delta_triple_vs_baseline", {})
                .get("hit_rate_delta_pp"),
            },
            {
                "id": "e_dynamic_quant_promotion",
                "reason_ko": "E_dynamic −33.7pp vs Arm A — quant SSOT 아님",
                "hr_180d": (arm_e_dyn.get("metrics") or {}).get("directional_hit_rate_active"),
                "wf_mean_test_hr": wf_e_dyn.get("mean_test_directional_hit_rate_active"),
            },
            {
                "id": "literal_veto_without_split",
                "reason_ko": "literal veto hold −58pp vs BAH — regime_mkm_split 대비 negative control",
                "delta_pp": (arm_e.get("delta_vs_bah_pp") or {}).get("literal_veto_hold"),
            },
            {
                "id": "fabba_native_kospi_primary",
                "reason_ko": "WSL native fABBA KOSPI HR stub 대비 열세 — sidecar backend apca_stub",
            },
        ],
        "artifact_pointers": {
            "shadow_ablation_v2": _rel(v2_path),
            "shadow_ablation_phase3": _rel(phase3_path),
            "fabba_ngram_lut_registration": _rel(fabba_reg_path),
            "protocol_harmonization_phase1": _rel(phase1_path),
            "protocol_phase1_moirai_compare": _rel(p2_compare_path),
            "moirai_dual_leg_2bps": _rel(moirai_dual_path),
            "narrative_knowledge_map_bundle": _rel(narrative_map_path),
            "personadiary_logos_sidebar_smoke": _rel(sidebar_smoke_path),
            "insight_bundle": "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json",
            "conflict_snapshot": "docs/final/artifacts/lens_conflict_day_decision_snapshot_v1_latest.json",
        },
        "protocol_harmonization_phase1": {
            "present": phase1_path.is_file() and phase1.get("ok") is True,
            "neutral_bps": (phase1.get("protocol") or {}).get("neutral_bps"),
            "recent_trading_days": (phase1.get("protocol") or {}).get("recent_trading_days"),
            "instrument_wf_mean_hr": (
                (phase1.get("recommended_chain_252d_5bps") or {})
                .get("instrument_combo_walkforward", {})
                .get("mean_test_accuracy")
            ),
            "rq025_ensemble_pooled_hr": (phase1.get("rq025_reference_kospi_252d_5bps") or {}).get(
                "per_date_kospi_ensemble_pooled_hr"
            ),
        },
        "tsfm_shadow_p2": {
            "present": moirai_dual_path.is_file(),
            "moirai_dual_leg_pooled_hr": next(
                (
                    r.get("hr")
                    for r in (p2_compare.get("rows") or [])
                    if r.get("row_id") == "moirai2_dual_leg_pooled"
                ),
                None,
            ),
            "protocol": moirai_dual.get("protocol"),
            "verdict_ko": (p2_compare.get("verdict_ko") or [None])[0],
            "track_a_promotion": False,
        },
        "narrative_knowledge_map": {
            "present": narrative_map_path.is_file() and narrative_map.get("ok") is True,
            "lane_id": narrative_map.get("lane_id"),
            "prophecy_vote": narrative_map.get("prophecy_vote"),
            "narrative_block_count": len(narrative_map.get("narrative_blocks") or []),
            "graphrag_observation_only": (narrative_map.get("graphrag_snapshot") or {}).get(
                "observation_only"
            ),
        },
        "personadiary_logos_sidebar": {
            "present": sidebar_smoke_path.is_file() and sidebar_smoke.get("ok") is True,
            "lane_id": sidebar_smoke.get("lane_id"),
            "prophecy_vote": sidebar_smoke.get("prophecy_vote"),
            "sidebar_generation_ok": sidebar_smoke.get("sidebar_generation_ok"),
            "hit_count": len(sidebar_smoke.get("hits") or []),
        },
        "consumer_contract_ko": (
            "본 보드는 B-track 운영 참조판입니다. Quant SSOT=science+sasang(Logos omit). "
            "PersonaDiary=myeongni+sasang(vote off). Oracle=Logos sidecar+regime split(NON_GATING). "
            "fABBA ngram_lut=merged LUT opt-in sidecar(vote none). Track A·실매매·send_gate 자동 승격 금지."
        ),
        "ok": bool(v2) and bool(phase3) and bool(fabba_reg.get("ok")),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--v2", type=Path, default=DEFAULT_V2)
    ap.add_argument("--phase3", type=Path, default=DEFAULT_PHASE3)
    ap.add_argument("--fabba-registration", type=Path, default=DEFAULT_FABBA_REG)
    ap.add_argument("--phase1", type=Path, default=DEFAULT_PHASE1)
    ap.add_argument("--p2-compare", type=Path, default=DEFAULT_P2_COMPARE)
    ap.add_argument("--moirai-dual", type=Path, default=DEFAULT_MOIRAI_DUAL)
    ap.add_argument("--narrative-map", type=Path, default=DEFAULT_NARRATIVE_MAP)
    ap.add_argument("--sidebar-smoke", type=Path, default=DEFAULT_SIDEBAR_SMOKE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = build_board(
        v2_path=args.v2,
        phase3_path=args.phase3,
        fabba_reg_path=args.fabba_registration,
        phase1_path=args.phase1,
        p2_compare_path=args.p2_compare,
        moirai_dual_path=args.moirai_dual,
        narrative_map_path=args.narrative_map,
        sidebar_smoke_path=args.sidebar_smoke,
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not payload.get("ok"):
        print("FAIL: missing upstream artifacts", file=sys.stderr)
        return 1

    quant = (payload.get("lanes") or {}).get("quant") or {}
    print(
        f"OK lanes=4 quant_hr={(quant.get('metrics_180d_2bps') or {}).get('directional_hit_rate_active')} "
        f"-> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
