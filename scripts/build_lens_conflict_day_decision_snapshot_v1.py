#!/usr/bin/env python3
"""Conflict-day decision snapshot — fusion vs price/overnight (B-track · human gate).

When fusion consensus disagrees with price lane + overnight risk_off, emit a
deterministic operator posture (REDUCE/WATCH/HOLD). Not live trading.

  py scripts/build_lens_conflict_day_decision_snapshot_v1.py
  py scripts/build_lens_conflict_day_decision_snapshot_v1.py --strict-exit
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

from scripts.sasang_regime_mkm_split_v1 import (  # noqa: E402
    RECOMMENDED_REGIME_ID,
    daily_fusion_posture,
    load_veto_by_date,
    supplier_tight_joseph_calendar,
)

DEFAULT_OUT = ROOT / "docs/final/artifacts/lens_conflict_day_decision_snapshot_v1_latest.json"

RULES_VERSION = "1.3.0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _sign_from_score(score: Any, *, threshold: float = 0.08) -> str:
    try:
        x = float(score)
    except (TypeError, ValueError):
        return "unknown"
    if x > threshold:
        return "bull"
    if x < -threshold:
        return "bear"
    return "flat"


def _max_overnight_move_pct(overnight: dict[str, Any]) -> float | None:
    moves: list[float] = []
    for row in overnight.get("indices") or []:
        if not isinstance(row, dict):
            continue
        ch = row.get("change_pct")
        if isinstance(ch, (int, float)):
            moves.append(abs(float(ch)))
    return max(moves) if moves else None


def _market_sasang_veto(fusion: dict[str, Any]) -> tuple[bool, list[str]]:
    for row in fusion.get("inputs") or []:
        if not isinstance(row, dict) or row.get("lens_id") != "market_sasang":
            continue
        block = row.get("market_sasang_lens_v1")
        if not isinstance(block, dict):
            return False, []
        codes = block.get("veto_reason_codes")
        reason = [str(c) for c in codes] if isinstance(codes, list) else []
        return bool(block.get("veto_force_hold")), reason
    return False, []


def _posture_operator_mapping(posture: str) -> tuple[str, str, str]:
    """Map fusion posture label → (final_action_hint, operator_posture, policy_ko)."""
    table: dict[str, tuple[str, str, str]] = {
        "HOLD_THROUGH_VETO": (
            "HOLD",
            "structural_hold_block_chase_only",
            "supplier_tight 구조 leg 유지; force_hold=추격·레버리지 금지(매도 아님)",
        ),
        "BLOCK_NEW_ENTRY": (
            "HOLD",
            "block_new_entry_supplier_tight",
            "supplier_tight 구간 신규 진입만 차단; 기존 롱 유지",
        ),
        "HOLD_STRUCTURAL": (
            "HOLD",
            "structural_hold",
            "supplier_tight 구조 leg 홀드",
        ),
        "ENTER_STRUCTURAL": (
            "HOLD",
            "enter_structural_when_clear",
            "supplier_tight + veto 해제 시 구조 진입 허용(지휘관)",
        ),
        "EXIT_STRUCTURAL": (
            "WATCH",
            "exit_structural_regime_off",
            "supplier_tight 해제 — 구조 leg 청산 검토",
        ),
        "HOLD_CASH_OR_EXIT": (
            "HOLD",
            "literal_veto_cash",
            "literal R5: force_hold를 현금/매도로 해석(negative control)",
        ),
        "ETERNAL_WAIT": (
            "HOLD",
            "eternal_wait_negative_control",
            "generic 관망 negative control",
        ),
        "PARTICIPATE": (
            "HOLD",
            "participate_no_veto",
            "veto 없음 — 참여 허용(지휘관)",
        ),
    }
    return table.get(
        posture,
        ("HOLD", "unknown_posture", f"미매핑 posture={posture}"),
    )


def _build_fabba_ngram_lut_sidecar_pointer() -> dict[str, Any]:
    p = ROOT / "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
    doc = _read_json(p)
    reg = doc.get("registration") or {}
    shadow = doc.get("shadow_hr_evidence") or {}
    ngram = shadow.get("ngram_lut_kospi_dual_leg_180d_2bps") or {}
    lut = doc.get("lut_ablation_smoke") or {}
    return {
        "schema": "fabba_sidecar_ngram_lut_v1",
        "artifact": "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json",
        "present": p.is_file() and doc.get("ok") is True,
        "lane_role_ko": "symbolic sidecar — merged LUT feature join only",
        "quant_ssot_ko": "science+sasang (Arm A) — ngram_lut HR does not replace quant SSOT",
        "primary_sidecar_arm": reg.get("primary_sidecar_arm"),
        "vote_participation": reg.get("vote_participation"),
        "non_gating": reg.get("non_gating"),
        "opt_in_only": reg.get("opt_in_only"),
        "shadow_hr_kospi_dual_leg_180d_2bps": ngram.get("kospi_pooled_hr"),
        "shadow_hr_btc_dual_leg_180d_2bps": ngram.get("btc_pooled_hr"),
        "arm_a_panel_hr_180d": shadow.get("arm_a_science_sasang_panel_hr_180d"),
        "lut_feature_parity_ok": lut.get("feature_parity_ok"),
        "merged_lut": (doc.get("artifacts") or {}).get("merged_lut"),
    }


def _build_persona_diary_lane_pointer() -> dict[str, Any]:
    p = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
    doc = _read_json(p)
    lane = doc.get("myeongni_sasang_lane") or {}
    metrics = lane.get("metrics") or {}
    return {
        "schema": "persona_diary_myeongni_sasang_lane_v1",
        "artifact": "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json",
        "present": p.is_file(),
        "lane_role_ko": "PersonaDiary/중기 — prophecy vote 제외",
        "quant_ssot_ko": "science+sasang (Arm A) — Track A shadow only",
        "persona_diary_lane_recommended": lane.get("persona_diary_lane_recommended"),
        "prophecy_vote_recommended": bool(lane.get("prophecy_vote_recommended", False)),
        "shadow_sharpe_180d": metrics.get("sharpe"),
        "shadow_hit_rate_180d": metrics.get("directional_hit_rate_active"),
        "vs_arm_a_sharpe_delta": (lane.get("vs_arm_a_science_sasang") or {}).get("sharpe_delta"),
    }


def _build_regime_mkm_split_posture(
    ws: Path,
    *,
    veto_hold: bool,
    veto_codes: list[str],
) -> dict[str, Any]:
    """Parallel [HYPO] branch: supplier_tight × tactical veto (not literal R5)."""
    reports = ws / "reports"
    ablation_path = reports / "sasang_regime_conditional_fusion_ablation_v1_latest.json"
    ablation = _read_json(ablation_path)
    samsung = (ablation.get("instruments") or {}).get("samsung") or {}
    split_daily = (
        ((samsung.get("policy_paths") or {}).get("regime_mkm_split_tactical") or {}).get("daily") or []
    )
    literal_daily = (
        ((samsung.get("policy_paths") or {}).get("literal_veto_hold") or {}).get("daily") or []
    )

    source = "unavailable"
    eval_date: str | None = None
    supplier_tight = False
    force_hold = veto_hold
    posture = "UNKNOWN"
    in_market_after = False

    if split_daily:
        latest = split_daily[-1]
        eval_date = str(latest.get("eval_date") or "")
        supplier_tight = bool(latest.get("supplier_tight"))
        force_hold = bool(latest.get("force_hold"))
        posture = str(latest.get("posture") or "UNKNOWN")
        in_market_after = bool(latest.get("in_market_after"))
        source = "sasang_regime_conditional_fusion_ablation_v1"
    else:
        sasang_path = reports / "btrack_market_sasang_per_date_v1.jsonl"
        veto_map = load_veto_by_date(sasang_path)
        if veto_map:
            eval_date = sorted(veto_map.keys())[-1]
            force_hold = bool(veto_map.get(eval_date))
            joseph = supplier_tight_joseph_calendar([eval_date])
            supplier_tight = bool(joseph.get(eval_date))
            in_market = supplier_tight
            posture, in_market_after = daily_fusion_posture(
                veto=force_hold,
                supplier_tight=supplier_tight,
                in_market=in_market,
                policy="regime_mkm_split_tactical",
            )
            source = "joseph_calendar_fallback"

    literal_posture: str | None = None
    if literal_daily:
        literal_posture = str(literal_daily[-1].get("posture") or "")
    elif eval_date:
        literal_posture, _ = daily_fusion_posture(
            veto=force_hold,
            supplier_tight=supplier_tight,
            in_market=supplier_tight,
            policy="literal_veto_hold",
        )

    action_hint, operator_posture, policy_ko = _posture_operator_mapping(posture)
    diverges_from_literal_r5 = (
        veto_hold
        and literal_posture in ("HOLD_CASH_OR_EXIT", "ETERNAL_WAIT")
        and posture in ("HOLD_THROUGH_VETO", "BLOCK_NEW_ENTRY", "HOLD_STRUCTURAL")
    )
    contrast_ko: str | None = None
    if diverges_from_literal_r5:
        contrast_ko = (
            f"literal R5({literal_posture})는 ADD/현금 해석; "
            f"regime_mkm_split({posture})는 구조 leg 유지·추격만 차단 — counterfactual −58pp 교훈"
        )

    return {
        "schema": "regime_mkm_split_v1_posture",
        "policy": "regime_mkm_split_tactical",
        "recommended_regime_id": RECOMMENDED_REGIME_ID,
        "source": source,
        "eval_date": eval_date,
        "supplier_tight": supplier_tight,
        "force_hold": force_hold,
        "force_hold_codes": list(veto_codes),
        "posture": posture,
        "in_market_after": in_market_after,
        "literal_veto_posture": literal_posture,
        "final_action_hint": action_hint,
        "operator_posture": operator_posture,
        "policy_ko": policy_ko,
        "diverges_from_literal_r5": diverges_from_literal_r5,
        "contrast_literal_r5_ko": contrast_ko,
        "research_only": True,
        "evidence_refs": [
            "scripts/sasang_regime_mkm_split_v1.py",
            "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json",
            "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json",
        ],
    }


def build_conflict_day_snapshot(root: Path | None = None) -> dict[str, Any]:
    ws = (root or ROOT).resolve()
    art = ws / "docs" / "final" / "artifacts"

    fusion = _read_json(art / "independent_lens_fusion_stub_latest.json")
    hypothesis = _read_json(art / "btrack_hypothesis_prophecy_latest.json")
    overnight = _read_json(art / "global_market_overnight_signals_v1_latest.json")
    macro = _read_json(art / "macro_independent_lens_latest.json")
    news = _read_json(art / "news_independent_lens_latest.json")
    narrative = _read_json(ws / "reports" / "lens_conflict_narrative_v1_latest.json")
    advisory_path = ws / "reports" / "mkm_parallel_advisory_brief_v1_latest.json"
    advisory = _read_json(advisory_path)

    advisory_pointer: dict[str, Any] = {
        "pointer": "reports/mkm_parallel_advisory_brief_v1_latest.json",
        "present": advisory_path.is_file(),
    }
    if advisory:
        advisory_pointer.update(
            {
                "schema": advisory.get("schema"),
                "domain_id": advisory.get("domain_id"),
                "epistemic_wiring_ok": advisory.get("epistemic_wiring_ok"),
                "conflict_surface": advisory.get("conflict_surface"),
                "execution_plane": advisory.get("execution_plane"),
                "reproduce": advisory.get("reproduce"),
            }
        )

    consensus = fusion.get("consensus") if isinstance(fusion.get("consensus"), dict) else {}
    consensus_effective = (
        fusion.get("consensus_effective") if isinstance(fusion.get("consensus_effective"), dict) else {}
    )
    headline_gating = fusion.get("headline_gating") if isinstance(fusion.get("headline_gating"), dict) else {}
    conflict_summary = fusion.get("conflict_summary") if isinstance(fusion.get("conflict_summary"), dict) else {}
    agreement_rate = float(consensus.get("agreement_rate") or 0.0)
    conflict_count = int(consensus.get("conflict_count") or 0)
    consensus_sign = str(
        headline_gating.get("headline_sign")
        or consensus_effective.get("consensus_sign")
        or consensus.get("consensus_sign")
        or "unknown"
    )
    fusion_demoted = bool(fusion.get("demote_active")) or conflict_count >= 2 or agreement_rate < 0.65
    fusion_demote_trace = list(fusion.get("demote_trace") or [])

    pred = hypothesis.get("prediction") if isinstance(hypothesis.get("prediction"), dict) else {}
    runtime = hypothesis.get("runtime_meta") if isinstance(hypothesis.get("runtime_meta"), dict) else {}
    lens_values = runtime.get("lens_values") if isinstance(runtime.get("lens_values"), dict) else {}
    price_block = lens_values.get("price") if isinstance(lens_values.get("price"), dict) else {}
    price_meta = runtime.get("price_meta") if isinstance(runtime.get("price_meta"), dict) else {}

    price_score = float(price_block.get("score") or 0.0)
    price_sign = _sign_from_score(price_score)
    hypo_dir = str(pred.get("direction") or "unknown")
    hypo_conf = float(pred.get("confidence") or 0.0)
    price_instrument = str(runtime.get("price_instrument") or price_meta.get("instrument") or "unknown")

    macro_sign = _sign_from_score((macro.get("scores") or {}).get("direction_score"))
    news_sign = _sign_from_score((news.get("scores") or {}).get("direction_score"))

    overnight_tilt = str(overnight.get("composite_tilt") or "")
    max_ov_move = _max_overnight_move_pct(overnight)
    shock_overnight = overnight_tilt == "risk_off_overnight" and (
        max_ov_move is not None and max_ov_move >= 3.0
    )

    recent_abs = price_meta.get("recent_abs_return_mean")
    try:
        recent_abs_f = float(recent_abs) if recent_abs is not None else 0.0
    except (TypeError, ValueError):
        recent_abs_f = 0.0
    shock_vol = recent_abs_f >= 0.025

    price_bear_lane = price_sign == "bear" or (hypo_dir == "bear" and hypo_conf >= 0.35)
    veto_hold, veto_codes = _market_sasang_veto(fusion)

    shock_regime = shock_overnight or shock_vol
    regime_label = "shock" if shock_regime else "normal"

    rule_trace: list[str] = []
    if fusion_demoted:
        rule_trace.append("R1_fusion_demoted: conflict_count>=2 or agreement<0.65 or stub demote_active")
    for item in fusion_demote_trace:
        if item not in rule_trace:
            rule_trace.append(item)
    if shock_overnight:
        rule_trace.append("R2_shock_overnight: risk_off + index move >=3%")
    if shock_vol:
        rule_trace.append("R3_shock_vol: recent_abs_return_mean>=2.5%")
    if price_bear_lane:
        rule_trace.append("R4_price_bear_lane: price sign bear or hypo bear conf>=0.35")
    if veto_hold:
        rule_trace.append("R5_market_sasang_veto: force_hold")

    if price_bear_lane and shock_regime:
        final_action = "REDUCE"
        operator_posture = "watch_tighten_reduce"
        semi_unrealized_2pct_policy_ko = (
            "반도체 합산 +2% 수익 구간: fusion bull·명리/사상 bull이 있어도 "
            "price+shock 우선 → 합산 30~40% 익절·잔량 트레일(+0.5% floor), 신규매수 금지"
        )
    elif price_bear_lane:
        final_action = "WATCH"
        operator_posture = "watch_tighten"
        semi_unrealized_2pct_policy_ko = (
            "하방 가설 유지: 신규매수 금지, +2% 이익은 되돌림 0% 근처까지 트레일"
        )
    elif veto_hold:
        final_action = "HOLD"
        operator_posture = "human_gate_hold"
        semi_unrealized_2pct_policy_ko = "market_sasang veto — 기계적 ADD 금지, 지휘관 확인"
    elif fusion_demoted and consensus_sign == "bull":
        final_action = "HOLD"
        operator_posture = "conflict_hold"
        semi_unrealized_2pct_policy_ko = "fusion bull demoted — consensus 단독 매수 근거 불가"
    elif consensus_sign == "bear":
        final_action = "REDUCE"
        operator_posture = "consensus_bear"
        semi_unrealized_2pct_policy_ko = "합의 bear — 비중 축소 검토"
    else:
        final_action = "HOLD"
        operator_posture = "neutral_hold"
        semi_unrealized_2pct_policy_ko = "충돌·쇼크 없음 — 기존 비중 유지(서킷일은 별도 Field gate)"

    lo = _read_json(art / "logos_independent_lens_latest.json")
    logos_sign = _sign_from_score((lo.get("scores") or {}).get("direction_score"))

    regime_mkm_split = _build_regime_mkm_split_posture(ws, veto_hold=veto_hold, veto_codes=veto_codes)
    if regime_mkm_split.get("diverges_from_literal_r5"):
        rule_trace.append(
            "R5b_regime_mkm_split: veto present but split posture≠literal cash/exit"
        )

    return {
        "schema": "lens_conflict_day_decision_snapshot_v1",
        "version": RULES_VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "boundary_ack": (
            "[HYPO] Conflict-day rules: price+overnight override fusion consensus on shock days. "
            "Logos [NON_GATING]. Not Track A·live trading·auto order."
        ),
        "rules_version": RULES_VERSION,
        "regime": regime_label,
        "final_action": final_action,
        "operator_posture": operator_posture,
        "rule_trace": rule_trace,
        "inputs_snapshot": {
            "fusion_ts_utc": fusion.get("ts_utc"),
            "hypothesis_ts_utc": hypothesis.get("ts_utc"),
            "overnight_generated_at_utc": overnight.get("generated_at_utc"),
            "consensus_sign": consensus_sign,
            "consensus_sign_raw": consensus.get("consensus_sign"),
            "consensus_sign_effective": consensus_effective.get("consensus_sign"),
            "headline_gating": headline_gating,
            "agreement_rate": agreement_rate,
            "conflict_count": conflict_count,
            "fusion_demoted": fusion_demoted,
            "fusion_demote_trace": fusion_demote_trace,
            "minority_lens_ids": conflict_summary.get("minority_lens_ids") or [],
            "hypothesis": {
                "instrument": pred.get("instrument"),
                "direction": hypo_dir,
                "confidence": hypo_conf,
                "price_instrument": price_instrument,
                "price_score": round(price_score, 6),
                "price_sign": price_sign,
                "recent_abs_return_mean": recent_abs_f,
            },
            "overnight": {
                "composite_tilt": overnight_tilt,
                "max_abs_index_change_pct": max_ov_move,
                "shock_overnight": shock_overnight,
            },
            "macro_sign": macro_sign,
            "news_sign": news_sign,
            "logos_sign_non_gating": logos_sign,
            "market_sasang_veto": veto_hold,
            "market_sasang_veto_codes": veto_codes,
            "three_lens_narrative_ko": narrative.get("narrative_ko"),
        },
        "semi_holdings_proxy_policy_ko": semi_unrealized_2pct_policy_ko,
        "regime_mkm_split_v1_posture": regime_mkm_split,
        "persona_diary_myeongni_sasang_lane": _build_persona_diary_lane_pointer(),
        "fabba_sidecar_ngram_lut": _build_fabba_ngram_lut_sidecar_pointer(),
        "parallel_advisory_brief": advisory_pointer,
        "reference_case_2026_06_08": {
            "note": "6/8 KOSPI 서킷·반도체 급락 — 사후 정합 사례(교육용)",
            "pre_open_kst": "가설 BTC bear + overnight risk_off; fusion consensus bull → 본 규칙 REDUCE/WATCH",
            "no_single_lens_called_kospi_minus_5": True,
        },
        "evidence_paths": [
            "scripts/build_lens_conflict_day_decision_snapshot_v1.py",
            "scripts/sasang_regime_mkm_split_v1.py",
            "docs/final/artifacts/independent_lens_fusion_stub_latest.json",
            "docs/final/artifacts/btrack_hypothesis_prophecy_latest.json",
            "docs/final/artifacts/global_market_overnight_signals_v1_latest.json",
            "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json",
            "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json",
            "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json",
            "reports/mkm_parallel_advisory_brief_v1_latest.json",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--strict-exit",
        action="store_true",
        help="Exit 1 if fusion or hypothesis artifacts missing",
    )
    args = ap.parse_args()

    ws = ROOT
    art = ws / "docs" / "final" / "artifacts"
    missing = [
        p.name
        for p in (
            art / "independent_lens_fusion_stub_latest.json",
            art / "btrack_hypothesis_prophecy_latest.json",
        )
        if not p.is_file()
    ]
    if missing and args.strict_exit:
        print(f"FAIL: missing artifacts: {missing}", file=sys.stderr)
        return 1

    doc = build_conflict_day_snapshot(ws)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(f"regime={doc.get('regime')} final_action={doc.get('final_action')}")
    split = doc.get("regime_mkm_split_v1_posture") or {}
    if split.get("posture"):
        print(
            f"regime_mkm_split posture={split.get('posture')} "
            f"diverges_literal_r5={split.get('diverges_from_literal_r5')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
