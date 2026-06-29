#!/usr/bin/env python3
"""Gate-driven axis scores for lens maturity v2 (B-track · [HYPO] · not Track A proof)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

# Caps: no axis reaches 10 without dedicated human sign-off artifact.
AXIS_CAP_DEFAULT = 8.5
AXIS_CAP_LOGOS_D = 8.0  # [NON_GATING] OOS is auxiliary only


def _clamp(v: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, round(v, 1)))


def _shadow_hit_d_bonus(hit: Any, n_eval: Any, notes: List[str], *, prefix: str) -> float:
    """Counterfactual per-lens hit tiers ([HYPO] · not headline proof)."""
    bonus = 0.0
    try:
        h = float(hit)
        n = int(n_eval or 0)
    except (TypeError, ValueError):
        notes.append(f"{prefix}_hit_missing")
        return bonus
    if n < 20:
        notes.append(f"{prefix}_hit_low_n={n}")
        return bonus
    notes.append(f"{prefix}_hit={h:.3f} n={n}")
    if h >= 0.58:
        bonus = 0.75
    elif h >= 0.55:
        bonus = 0.5
    elif h >= 0.50:
        bonus = 0.25
    return bonus


def score_myeongni_d_v2(ws: Path, read_json) -> Tuple[float, List[str]]:
    """① 명리 D: observation report + gates (not hit-rate headline)."""
    notes: List[str] = []
    obs = read_json(ws / "reports" / "myeongni_lens_observation_report_v1_latest.json")
    art = ws / "docs" / "final" / "artifacts"
    stage2 = read_json(art / "myeongni_stage2_realset_gate_latest.json")

    d = 5.0
    if obs.get("schema") == "myeongni_lens_observation_report_v1":
        notes.append("observation_report_v1")
        if obs.get("separation_contract_ok"):
            d += 1.0
            notes.append("separation_contract_ok")
        gates = obs.get("gates") if isinstance(obs.get("gates"), dict) else {}
        if gates.get("stage2_realset_pass") or stage2.get("pass"):
            d += 0.5
        promo = str(gates.get("promotion_status") or "")
        if promo == "PASS" or "GO" in str(gates.get("promotion_decision") or ""):
            d += 0.5
        if not (obs.get("warnings") or []):
            d += 0.5
        snaps = obs.get("snapshots") if isinstance(obs.get("snapshots"), dict) else {}
        if snaps.get("market_direction_score") is not None:
            d += 0.5
            notes.append("market_overlay_present")
        shadows = obs.get("shadow_price_hits") if isinstance(obs.get("shadow_price_hits"), dict) else {}
        my_row = shadows.get("myeongni") if isinstance(shadows.get("myeongni"), dict) else {}
        if my_row:
            d += _shadow_hit_d_bonus(
                my_row.get("price_directional_hit_rate"),
                my_row.get("n_evaluated"),
                notes,
                prefix="myeongni_shadow",
            )
        else:
            legacy = obs.get("shadow_price_hit") if isinstance(obs.get("shadow_price_hit"), dict) else {}
            if legacy:
                d += _shadow_hit_d_bonus(
                    legacy.get("price_directional_hit_rate"),
                    legacy.get("n_evaluated"),
                    notes,
                    prefix="myeongni_shadow",
                )
    else:
        notes.append("missing_observation_report")
        if stage2.get("pass"):
            d += 0.5

    if obs.get("not_hit_rate_proof"):
        notes.append("not_hit_rate_proof_cap")
    notes.append("myeongni_d_shadow_counterfactual")
    return _clamp(d, hi=AXIS_CAP_DEFAULT), notes


def score_logos_d_v2(ws: Path, read_json) -> Tuple[float, List[str]]:
    """② 성경 D: OOS revalidation gate + hit-rate tiers ([NON_GATING])."""
    notes: List[str] = ["logos_oos_non_gating"]
    oos = read_json(ws / "docs" / "final" / "artifacts" / "prophecy_logos_revalidation_oos_gate_latest.json")
    gate = oos.get("gate") if isinstance(oos.get("gate"), dict) else {}
    metrics = oos.get("oos_metrics") if isinstance(oos.get("oos_metrics"), dict) else {}

    if not gate.get("go"):
        notes.append("oos_gate_not_go")
        return _clamp(5.5, hi=AXIS_CAP_LOGOS_D), notes

    hit = metrics.get("directional_hit_rate_active")
    try:
        h = float(hit)
    except (TypeError, ValueError):
        notes.append("oos_hit_missing")
        return _clamp(6.0, hi=AXIS_CAP_LOGOS_D), notes

    notes.append(f"oos_hit={h:.4f}")
    if h >= 0.58:
        d = 7.5
    elif h >= 0.55:
        d = 7.25
    elif h >= 0.52:
        d = 7.0
    elif h >= 0.50:
        d = 6.5
    else:
        d = 6.0
    checks = gate.get("checks") if isinstance(gate.get("checks"), dict) else {}
    if checks.get("oos_sharpe_pass"):
        d += 0.25
    return _clamp(d, hi=AXIS_CAP_LOGOS_D), notes


def score_sasang_b_c_v2(ws: Path, read_json) -> Tuple[float, float, List[str]]:
    """③ 사상 B/C: fusion pass · promotion · product artifacts."""
    notes: List[str] = []
    art = ws / "docs" / "final" / "artifacts"
    b = 7.0
    c = 6.5

    fusion = read_json(art / "sasang_4agent_fusion_gate_latest.json")
    if str(fusion.get("decision") or "") == "FUSION_GATE_PASS":
        b += 0.5
        notes.append("fusion_gate_PASS")
    else:
        b -= 0.5
        notes.append("fusion_gate_not_pass")

    s12 = read_json(art / "sasang12_promotion_candidate_gate_latest.json")
    if s12.get("status") == "PASS":
        b += 0.25
    else:
        b = min(b, 6.5)

    ag = read_json(art / "sasang_4agent_promotion_gate_latest.json")
    checks = ag.get("checks") if isinstance(ag.get("checks"), dict) else {}
    if checks.get("fusion_gate_pass") or ag.get("decision") != "HOLD":
        b += 0.25
        notes.append("4agent_promotion_ok")

    hr = read_json(art / "sasang_high_reliability_gate_latest.json")
    if hr.get("decision") == "PASS":
        b += 0.25
        notes.append("high_reliability_PASS")

    if (ws / "reports" / "sasang_rule_based_response_v1_latest.md").is_file():
        c += 0.5
        notes.append("rule_based_md_v1")
    if (ws / "reports" / "sasang_rule_based_response_v1_latest.json").is_file():
        c += 0.25
    sa = read_json(art / "sasang_independent_lens_latest.json")
    out = sa.get("sasang_stream_outputs") if isinstance(sa.get("sasang_stream_outputs"), dict) else {}
    if (out.get("machine_readables") or {}).get("heat_proxy") is not None:
        c += 0.25
        notes.append("heat_proxy_in_lens")

    return _clamp(b, hi=AXIS_CAP_DEFAULT), _clamp(c, hi=AXIS_CAP_DEFAULT), notes


def score_sasang_d_v2(ws: Path, read_json) -> Tuple[float, List[str]]:
    """④ 사상 D: observation + high-reliability + shadow per-lens hit ([HYPO] counterfactual)."""
    notes: List[str] = ["sasang_d_shadow_counterfactual"]
    art = ws / "docs" / "final" / "artifacts"
    obs = read_json(ws / "reports" / "sasang_lens_observation_report_v1_latest.json")
    hr = read_json(art / "sasang_high_reliability_gate_latest.json")

    d = 6.0
    if obs.get("schema") == "sasang_lens_observation_report_v1":
        notes.append("sasang_observation_report_v1")
        if obs.get("separation_contract_ok"):
            d += 0.5
        sh = obs.get("shadow_price_hit") if isinstance(obs.get("shadow_price_hit"), dict) else {}
        d += _shadow_hit_d_bonus(
            sh.get("price_directional_hit_rate"),
            sh.get("n_evaluated"),
            notes,
            prefix="sasang_shadow",
        )
    else:
        per_lens = read_json(art / "prophecy_hit_rate_per_lens_latest.json")
        for inst_legs in (per_lens.get("legs") or {}).values():
            if not isinstance(inst_legs, dict):
                continue
            for row in inst_legs.get("lenses") or []:
                if isinstance(row, dict) and row.get("lens_id") == "sasang":
                    try:
                        hit = float(row.get("price_directional_hit_rate"))
                        if int(row.get("n_evaluated") or 0) >= 20:
                            notes.append(f"per_lens_hit={hit:.3f}")
                            if hit >= 0.55:
                                d += 0.5
                    except (TypeError, ValueError):
                        pass
                    break

    snap = hr.get("snapshot") if isinstance(hr.get("snapshot"), dict) else {}
    if hr.get("decision") == "PASS":
        d += 0.5
        notes.append("high_reliability_PASS")
        try:
            if float(snap.get("brier_score")) <= 0.18:
                d += 0.25
            if float(snap.get("recall_macro")) >= 0.68:
                d += 0.25
        except (TypeError, ValueError):
            pass

    if obs.get("not_hit_rate_proof"):
        notes.append("not_price_headline_proof")
    return _clamp(d, hi=AXIS_CAP_DEFAULT), notes


def score_myeongni_a_c_v2(ws: Path, read_json) -> Tuple[float, float, List[str]]:
    """명리 A/C: chain·주간요약·관측·프로모션 (D는 별도)."""
    notes: List[str] = []
    art = ws / "docs" / "final" / "artifacts"
    a = 8.0
    c = 7.0
    chain = read_json(art / "myeongni_independent_lens_from_chain_latest.json")
    promo = read_json(art / "myeongni_promotion_gate_latest.json")
    obs = read_json(ws / "reports" / "myeongni_lens_observation_report_v1_latest.json")

    adv = chain.get("advanced") if isinstance(chain.get("advanced"), dict) else {}
    math = (adv.get("coordinator") or {}).get("mkm_myeongni_math") if isinstance(adv.get("coordinator"), dict) else {}
    if isinstance(math, dict) and math.get("status") == "ok":
        a += 0.5
        notes.append("mkm_myeongni_math_ok")
    if read_json(art / "myeongni_stage2_realset_gate_latest.json").get("pass"):
        a += 0.25
    if str(promo.get("status") or "") == "PASS" or "GO" in str(promo.get("decision") or ""):
        c += 0.5
        notes.append("promotion_gate_ok")
    if (ws / "reports" / "myeongni_weekly_ops_summary_latest.md").is_file():
        c += 0.5
        notes.append("weekly_ops_summary_md")
    if obs.get("separation_contract_ok"):
        c += 0.5
        notes.append("observation_in_product_path")
    return _clamp(a, hi=AXIS_CAP_DEFAULT), _clamp(c, hi=AXIS_CAP_DEFAULT), notes


def score_logos_a_v2(ws: Path, read_json) -> Tuple[float, List[str]]:
    """성경 A: production evidence + 브리핑 산출물."""
    notes: List[str] = []
    a = 7.5
    art = ws / "docs" / "final" / "artifacts"
    lo = read_json(art / "logos_independent_lens_latest.json")
    prov = lo.get("provenance") if isinstance(lo.get("provenance"), dict) else {}
    if prov.get("source") == "ann_resonance_graphrag":
        a += 1.0
        notes.append("production_evidence")
    stream = lo.get("logos_stream_outputs") if isinstance(lo.get("logos_stream_outputs"), dict) else {}
    if int(stream.get("evidence_row_count") or 0) >= 8:
        a += 0.25
    for rel in (
        "reports/logos_2026_market_news_prophecy_graphrag_v1_latest.md",
        "reports/logos_2026_ai_industry_max_util_insight_v1_latest.md",
    ):
        if (ws / rel).is_file():
            a += 0.125
            notes.append(f"briefing:{rel.split('/')[-1]}")
    return _clamp(a, hi=AXIS_CAP_DEFAULT), notes


def score_sasang_a_v2(ws: Path, read_json) -> Tuple[float, List[str]]:
    """사상 A: fusion·4agent·프로토콜·rule 엔진."""
    notes: List[str] = []
    art = ws / "docs" / "final" / "artifacts"
    a = 7.0
    fusion = read_json(art / "sasang_4agent_fusion_gate_latest.json")
    if str(fusion.get("decision") or "") == "FUSION_GATE_PASS":
        a += 0.75
        notes.append("fusion_engine_PASS")
        checks = fusion.get("checks") if isinstance(fusion.get("checks"), dict) else {}
        if checks.get("protocol_significance_pass") and checks.get("sample_size_gte_300"):
            a += 0.25
    ag = read_json(art / "sasang_4agent_promotion_gate_latest.json")
    if (ag.get("checks") or {}).get("significance_pass"):
        a += 0.25
    if read_json(art / "sasang12_promotion_candidate_gate_latest.json").get("status") == "PASS":
        a += 0.25
    if (ws / "reports" / "sasang_rule_based_response_v1_latest.json").is_file():
        a += 0.25
        notes.append("rule_engine_json")
    return _clamp(a, hi=AXIS_CAP_DEFAULT), notes


def score_sasang_c_v2(ws: Path, read_json) -> Tuple[float, List[str]]:
    """사상 C: rule MD + 관측 리포트 + heat in lens."""
    notes: List[str] = []
    c = 6.5
    if (ws / "reports" / "sasang_rule_based_response_v1_latest.md").is_file():
        c += 0.75
        notes.append("rule_based_md")
    obs = read_json(ws / "reports" / "sasang_lens_observation_report_v1_latest.json")
    if obs.get("separation_contract_ok"):
        c += 0.5
        notes.append("sasang_observation_report")
    sa = read_json(ws / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json")
    out = sa.get("sasang_stream_outputs") if isinstance(sa.get("sasang_stream_outputs"), dict) else {}
    if (out.get("machine_readables") or {}).get("heat_proxy") is not None:
        c += 0.25
    return _clamp(c, hi=AXIS_CAP_DEFAULT), notes
