#!/usr/bin/env python3
"""Build 2030 macro horizon scenario from Logos chronology + general prophecy + macro forward SSOT.

Deterministic assembly only — no LLM. research_only / [HYPO] / [NON_GATING] for Logos overlay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DYNAMIC_MAP = ROOT / "docs/final/artifacts/logos_chronology_dynamic_map_v1_latest.json"
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"
DEFAULT_HOLDOUT = ROOT / "reports/logos_chronology_text_blind_v2_holdout_v1_latest.json"
DEFAULT_DIGEST_MD = ROOT / "reports/logos_chronology_era_blind_eval_digest_v1_latest.md"
DEFAULT_TWO_TRACK = ROOT / "docs/final/artifacts/prophecy_2050_two_track_v1_latest.json"
DEFAULT_MACRO_BRIEF = ROOT / "docs/final/artifacts/trackc_macro_risk_morning_briefing_latest.json"
DEFAULT_FORWARD_WEEKLY = ROOT / "docs/final/artifacts/macro_risk_forward_weekly_report_latest.json"
DEFAULT_GENERAL_PROPHECY = ROOT / "docs/final/artifacts/general_prophecy_latest.json"
DEFAULT_CIV_APOCALYPSE_ARTIFACTS = (
    ROOT / "docs/final/artifacts/general_prophecy_civilization_apocalypse_v1_latest.json"
)
DEFAULT_CIV_APOCALYPSE_REPORTS = ROOT / "reports/general_prophecy_civilization_apocalypse_v1_latest.json"
DEFAULT_CIV_APOCALYPSE = DEFAULT_CIV_APOCALYPSE_ARTIFACTS
DEFAULT_MYEONGNI_LENS = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_SASANG_LENS = ROOT / "docs/final/artifacts/market_sasang_lens_latest.json"
DEFAULT_OUT_JSON = ROOT / "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/logos_macro_horizon_2030_scenario_v1_latest.md"

MACRO_QUESTION_IDS = (
    "gp_2026_h2_kostat_cpi_yoy_below_2_any_month",
    "gp_2026_h2_fed_funds_upper_cut_ge_25bp_vs_2026q2",
    "gp_2026_h2_ecb_deposit_facility_below_2pct",
    "gp_2026_h2_boj_policy_rate_above_1pct",
    "gp_2026_h2_eia_brent_monthly_avg_ge_80_usd",
    "civ.tech.ai_companion_dau_1b_2030",
    "civ.finance.cbdc_retail_oecd10_2035",
    "civ.geo.fao_food_nominal_50pct_spike_2038",
)

STRICT_REQUIRED_KEYS: tuple[tuple[Path, str], ...] = (
    (DEFAULT_DYNAMIC_MAP, "logos_chronology_dynamic_map"),
    (DEFAULT_MACRO_BRIEF, "macro_morning_briefing"),
)

CHRONOLOGY_MS_NOTE = (
    "External MS headline for era blind text_blind v1 remains ~6.4%; "
    "text_blind_v2 holdout (B-track internal) must not replace MS or B2B headlines."
)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_provenance(paths: dict[str, Path]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, path in paths.items():
        doc = _load(path) if path.suffix == ".json" else {}
        out[key] = {
            "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256": _sha256_file(path),
            "generated_at_utc": doc.get("generated_at_utc") if doc else None,
            "present": path.is_file(),
        }
    return out


def _validate_strict(paths: dict[str, Path]) -> list[str]:
    missing: list[str] = []
    for path, label in STRICT_REQUIRED_KEYS:
        if not path.is_file():
            missing.append(f"{label}: {path}")
    brief = _load(paths.get("macro_brief", DEFAULT_MACRO_BRIEF))
    if not (brief.get("market_snapshot") or {}).get("decision_state"):
        missing.append("macro_morning_briefing.market_snapshot.decision_state")
    dynamic = _load(paths.get("dynamic_map", DEFAULT_DYNAMIC_MAP))
    if not dynamic.get("primary_match"):
        missing.append("logos_chronology_dynamic_map.primary_match")
    return missing


def _latest_forecast(q: dict[str, Any]) -> dict[str, Any] | None:
    fc = q.get("forecasts") or []
    if not isinstance(fc, list) or not fc:
        return None
    last = fc[-1]
    return last if isinstance(last, dict) else None


def _extract_macro_questions(*registries: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for registry in registries:
        for q in registry.get("questions") or []:
            if isinstance(q, dict) and q.get("question_id"):
                by_id[str(q["question_id"])] = q
    out: list[dict[str, Any]] = []
    for qid in MACRO_QUESTION_IDS:
        q = by_id.get(qid)
        if not q:
            continue
        fc = _latest_forecast(q)
        out.append(
            {
                "question_id": qid,
                "question_text": q.get("question_text"),
                "probability_0_1": fc.get("probability_0_1") if fc else None,
                "source_kind": fc.get("source_kind") if fc else None,
                "resolution_status": (q.get("resolution") or {}).get("status"),
                "domain_tags": q.get("domain_tags") or [],
            }
        )
    return out


def _resolve_civ_apocalypse_path(explicit: Path | None = None) -> Path:
    if explicit and explicit.is_file():
        return explicit
    if DEFAULT_CIV_APOCALYPSE_ARTIFACTS.is_file():
        return DEFAULT_CIV_APOCALYPSE_ARTIFACTS
    if DEFAULT_CIV_APOCALYPSE_REPORTS.is_file():
        return DEFAULT_CIV_APOCALYPSE_REPORTS
    return explicit or DEFAULT_CIV_APOCALYPSE_ARTIFACTS


def _mirror_civ_apocalypse_to_artifacts(source: Path) -> Path:
    if not source.is_file():
        return source
    if source.resolve() == DEFAULT_CIV_APOCALYPSE_ARTIFACTS.resolve():
        return source
    DEFAULT_CIV_APOCALYPSE_ARTIFACTS.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CIV_APOCALYPSE_ARTIFACTS.write_bytes(source.read_bytes())
    return DEFAULT_CIV_APOCALYPSE_ARTIFACTS


def _two_track_band_by_period(two_track: dict[str, Any], period: str) -> dict[str, Any]:
    bands = ((two_track.get("track_a_trading_theory") or {}).get("operational_bands") or [])
    era_signs = ((two_track.get("track_b_historical_omen") or {}).get("era_signs") or [])
    track_a = next((b for b in bands if isinstance(b, dict) and b.get("period") == period), None)
    track_b = next((s for s in era_signs if isinstance(s, dict) and s.get("period") == period), None)
    return {"track_a": track_a, "track_b": track_b}


def _two_track_2030_band(two_track: dict[str, Any]) -> dict[str, Any]:
    return _two_track_band_by_period(two_track, "2026-2030")


def _chronology_overlay(dynamic_map: dict[str, Any]) -> dict[str, Any]:
    primary = dynamic_map.get("primary_match") or {}
    ranking = dynamic_map.get("era_ranking") or []
    secondary = ranking[1] if len(ranking) > 1 and isinstance(ranking[1], dict) else {}
    return {
        "primary_era_id": primary.get("era_id"),
        "primary_label_ko": primary.get("label_ko"),
        "primary_score": (ranking[0] or {}).get("score") if ranking else None,
        "confidence_band": primary.get("confidence_band"),
        "inferred_regime_tags": dynamic_map.get("inferred_regime_tags") or [],
        "secondary_era_id": secondary.get("era_id"),
        "secondary_label_ko": secondary.get("label_ko"),
        "secondary_score": secondary.get("score"),
        "interpretation_class": "[HYPO]",
        "non_gating": True,
        "ms_headline_note": CHRONOLOGY_MS_NOTE,
    }


def _chronology_evidence(chronology: dict[str, Any], holdout: dict[str, Any]) -> dict[str, Any]:
    bridges = chronology.get("modern_bridges") or []
    bridge_summary: list[dict[str, Any]] = []
    for b in bridges:
        if not isinstance(b, dict):
            continue
        if b.get("bridge_kind") in ("regime_fingerprint", "chronology_window"):
            bridge_summary.append(
                {
                    "era_id": b.get("era_id"),
                    "bridge_kind": b.get("bridge_kind"),
                    "regime_id": b.get("regime_id"),
                    "window_id": b.get("window_id"),
                    "resonance_weight": b.get("resonance_weight"),
                }
            )
    train = ((holdout.get("by_partition") or {}).get("train_holdout") or {})
    v1_h = (train.get("text_blind_v1_ms_baseline") or {}).get("hit_at_1_strict")
    v2_h = (train.get("text_blind_v2_btrack_poc") or {}).get("hit_at_1_strict")
    return {
        "interpretation_class": "[HYPO]",
        "non_gating": True,
        "modern_bridge_count": len(bridges),
        "macro_relevant_bridges": bridge_summary[:12],
        "holdout_internal_only": {
            "schema": holdout.get("schema"),
            "primary_oos_partition": (holdout.get("policy") or {}).get("primary_oos_partition"),
            "train_holdout_n": (train.get("text_blind_v2_btrack_poc") or {}).get("n"),
            "v1_ms_hit_at_1_strict": v1_h,
            "v2_btrack_hit_at_1_strict": v2_h,
            "delta_v2_minus_v1": train.get("delta_v2_minus_v1"),
            "not_for_ms_or_b2b_headline": True,
        },
        "digest_pointer": str(DEFAULT_DIGEST_MD.relative_to(ROOT)),
    }


def _macro_forward_anchor(macro_brief: dict[str, Any], forward_weekly: dict[str, Any]) -> dict[str, Any]:
    snap = macro_brief.get("market_snapshot") or {}
    latest = forward_weekly.get("latest_row") or {}
    return {
        "decision_state": snap.get("decision_state") or latest.get("decision_state"),
        "risk_warning_level": snap.get("risk_warning_level") or latest.get("risk_warning_level"),
        "primary_regime_id": snap.get("primary_regime_id"),
        "operator_posture": snap.get("recommended_operator_posture") or latest.get("recommended_operator_posture"),
        "asset_scope_briefing": snap.get("asset_scope"),
        "top_risk_signals": macro_brief.get("top_risk_signals") or [],
        "forward_rows_total": forward_weekly.get("rows_total"),
        "forward_window_decision_counts": forward_weekly.get("decision_state_counts") or {},
    }


def _conflict_resolver(
    chronology: dict[str, Any],
    macro_anchor: dict[str, Any],
    lens_triad: dict[str, Any] | None = None,
) -> dict[str, Any]:
    regime = macro_anchor.get("primary_regime_id") or "unknown_regime"
    decision = macro_anchor.get("decision_state") or "UNKNOWN"
    risk = macro_anchor.get("risk_warning_level") or "unknown"
    primary = chronology.get("primary_era_id") or "unknown_era"
    secondary = chronology.get("secondary_era_id") or "unknown_era"
    summary = (
        f"1차 Field={regime}+{decision}/{risk} vs "
        f"2차 Logos={primary}+{secondary} — 완전 정상화 아님"
    )
    lens_supplement: list[str] = []
    triad = lens_triad or {}
    mn = triad.get("myeongni") or {}
    if mn.get("status") == "read_only_snapshot":
        lens_supplement.append(
            f"명리 dir={mn.get('direction_score')} conf={mn.get('confidence')} [HYPO/non-gating]"
        )
    sa = triad.get("sasang") or {}
    if sa.get("status") == "read_only_snapshot":
        veto = "veto=HOLD" if sa.get("force_hold") else "veto=off"
        lens_supplement.append(
            f"사상 {sa.get('dominant_constitution')} {veto} [HYPO/non-gating]"
        )
    final = decision if decision in ("GO", "WATCH", "HOLD", "REDUCE") else "WATCH"
    return {
        "summary_ko": summary,
        "lens_supplement_ko": "; ".join(lens_supplement) if lens_supplement else None,
        "final_action": final,
        "final_action_note": "Advisory only; not live trading trigger. Lens rows do not override Field.",
    }


def _rel_path(path: Path) -> str:
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def _dominant_softmax_key(vec: dict[str, Any]) -> str | None:
    if not vec:
        return None
    return max(vec, key=lambda k: float(vec[k]))


def _lens_triad_from_artifacts(
    myeongni: dict[str, Any] | None,
    sasang: dict[str, Any] | None,
    *,
    myeongni_path: Path | None = None,
    sasang_path: Path | None = None,
) -> dict[str, Any]:
    logos_part = {
        "role": "macro_narrative_overlay",
        "status": "chronology_dynamic_map_only",
        "interpretation_class": "[HYPO]",
        "non_gating": True,
    }
    if myeongni and myeongni.get("lens_id") == "myeongni":
        scores = myeongni.get("scores") or {}
        stream = myeongni.get("myeongri_stream_outputs") or {}
        myeongni_part = {
            "role": "mid_horizon_direction",
            "status": "read_only_snapshot",
            "interpretation_class": "[HYPO]",
            "non_gating": True,
            "direction_score": scores.get("direction_score"),
            "confidence": scores.get("confidence"),
            "state_id": stream.get("state_id"),
            "source_path": _rel_path(myeongni_path) if myeongni_path else None,
            "ts_utc": myeongni.get("ts_utc"),
            "note_ko": "명리 독립 렌즈 스냅샷; 거시 시나리오 인과·실매매 트리거 금지.",
        }
    else:
        myeongni_part = {
            "role": "mid_horizon_direction",
            "status": "not_run_in_this_builder",
            "interpretation_class": "[HYPO]",
            "note_ko": "명리 독립 렌즈 JSON 미합선; 거시 시나리오 본문에 인과 단정 금지.",
        }
    if sasang and sasang.get("lens_id") == "market_sasang":
        veto = sasang.get("veto") or {}
        unc = sasang.get("uncertainty") or {}
        softmax = sasang.get("state_vector_sasang_softmax") or {}
        sasang_part = {
            "role": "short_intensity",
            "status": "read_only_snapshot",
            "interpretation_class": "[HYPO]",
            "non_gating": True,
            "force_hold": veto.get("force_hold"),
            "veto_reason_codes": veto.get("reason_codes") or [],
            "dominant_constitution": _dominant_softmax_key(softmax),
            "entropy_norm_4way": unc.get("entropy_norm_4way"),
            "direction_hint": (sasang.get("fusion_bridge") or {}).get("direction_hint"),
            "source_path": _rel_path(sasang_path) if sasang_path else None,
            "ts_utc": sasang.get("ts_utc"),
            "note_ko": "사상 시장 렌즈 스냅샷; veto는 관측만 — Track A 트리거 금지.",
        }
    else:
        sasang_part = {
            "role": "short_intensity",
            "status": "not_run_in_this_builder",
            "interpretation_class": "[HYPO]",
            "note_ko": "사상 시장 렌즈 미합선; Track A 트리거 금지.",
        }
    return {"myeongni": myeongni_part, "sasang": sasang_part, "logos": logos_part}


def _lens_triad_stub() -> dict[str, Any]:
    return _lens_triad_from_artifacts(None, None)


def _p(by_id: dict[str, dict[str, Any]], qid: str) -> float | None:
    row = by_id.get(qid) or {}
    val = row.get("probability_0_1")
    return float(val) if val is not None else None


def _stress_triggers_from_signals(signals: list[dict[str, Any]], extra: list[str]) -> list[str]:
    triggers = list(extra)
    for sig in signals[:3]:
        if isinstance(sig, dict) and sig.get("name"):
            score = sig.get("score")
            triggers.append(f"{sig['name']} score={score}")
    return triggers


def _axis_scenarios(
    macro_questions: list[dict[str, Any]],
    macro_anchor: dict[str, Any],
    chronology: dict[str, Any],
) -> dict[str, Any]:
    by_id = {q["question_id"]: q for q in macro_questions}
    watch = macro_anchor.get("decision_state") == "WATCH"
    elevated = macro_anchor.get("risk_warning_level") == "elevated"
    signals = macro_anchor.get("top_risk_signals") or []

    return {
        "korea": {
            "axis_id": "KR",
            "instruments": ["KOSPI", "KRW", "Korea CPI"],
            "base_scenario": {
                "label": "base",
                "period": "2026-2030",
                "growth_tone": "low_to_mid_single_digit_real; sectoral K-shape (AI/export vs domestic)",
                "inflation_tone": f"CPI YoY sub-2% month at least once before 2027 (registry p={_p(by_id, 'gp_2026_h2_kostat_cpi_yoy_below_2_any_month')})",
                "policy_tone": "BoK follows global easing cycle with lag; FX volatility episodic",
                "logos_era_overlay": chronology.get("secondary_label_ko") or "사사 시대 · 순환 리스크",
                "operator_posture": "WATCH" if watch else macro_anchor.get("decision_state"),
            },
            "stress_scenario": {
                "label": "stress",
                "period": "2026-2030",
                "growth_tone": "external demand shock + household balance-sheet drag; repeated risk-off in KOSPI",
                "inflation_tone": "sticky services inflation despite headline dips; energy/import pass-through",
                "policy_tone": "premature easing hope vs delayed fiscal tightening — narrative whipsaw",
                "tail_triggers": _stress_triggers_from_signals(
                    signals, ["geopolitical supply shock", "property/credit stress", "KRW disorderly move"]
                ),
                "logos_era_overlay": "포로기·귀환 (Exile/Return) [HYPO] — liquidity squeeze metaphor only",
            },
        },
        "usa": {
            "axis_id": "US",
            "instruments": ["Fed funds", "USD", "NDX"],
            "base_scenario": {
                "label": "base",
                "period": "2026-2030",
                "rates_tone": (
                    f"Fed upper bound cut >=25bp vs 2026Q2 by mid-2026 (p={_p(by_id, 'gp_2026_h2_fed_funds_upper_cut_ge_25bp_vs_2026q2')}); "
                    "gradual path not linear"
                ),
                "inflation_tone": "disinflation incomplete; tariff/energy shocks keep risk premium",
                "logos_era_overlay": chronology.get("primary_label_ko") or "현대 관측 필드",
            },
            "stress_scenario": {
                "label": "stress",
                "period": "2026-2030",
                "rates_tone": "stop-go policy; term premium spikes; fiscal dominance fears",
                "inflation_tone": "second inflation wave or growth scare alternating — regime flips",
                "financial_tone": "liquidity stress episodes (lehman-tag shadow from chronology bridges)",
                "tail_triggers": _stress_triggers_from_signals(
                    signals, ["G7 policy coordination break", "commercial real estate cascade", "AI capex bust"]
                ),
                "logos_era_overlay": "침묵기·제국 교체 [HYPO] — governance/payments stack rewiring",
            },
        },
        "japan": {
            "axis_id": "JP",
            "instruments": ["BoJ policy rate", "JPY", "Nikkei"],
            "base_scenario": {
                "label": "base",
                "period": "2026-2030",
                "rates_tone": f"BoJ policy rate above 1% by end-2026 (p={_p(by_id, 'gp_2026_h2_boj_policy_rate_above_1pct')})",
                "policy_tone": "gradual normalization; yield curve control legacy fades",
                "logos_era_overlay": chronology.get("secondary_label_ko"),
            },
            "stress_scenario": {
                "label": "stress",
                "period": "2026-2030",
                "rates_tone": "sharp JPY disorder + BoJ communication shock",
                "tail_triggers": ["carry unwind", "regional geopolitical spillover"],
                "logos_era_overlay": "사사 시대 · 순환 리스크 [HYPO]",
            },
        },
        "eu": {
            "axis_id": "EU",
            "instruments": ["ECB DFR", "EUR", "STOXX"],
            "base_scenario": {
                "label": "base",
                "period": "2026-2030",
                "rates_tone": f"ECB DFR below 2% by end-2026 (p={_p(by_id, 'gp_2026_h2_ecb_deposit_facility_below_2pct')})",
                "energy_tone": f"Brent >=$80 H2 2026 month (p={_p(by_id, 'gp_2026_h2_eia_brent_monthly_avg_ge_80_usd')}) — EU import exposure",
                "logos_era_overlay": chronology.get("primary_label_ko"),
            },
            "stress_scenario": {
                "label": "stress",
                "period": "2026-2030",
                "energy_tone": "energy shock + industrial policy fragmentation",
                "tail_triggers": ["sovereign spread widening", "banking sector stress"],
                "logos_era_overlay": "포로기·귀환 [HYPO]",
            },
        },
        "btc": {
            "axis_id": "BTC-USD",
            "instruments": ["BTC-USD"],
            "base_scenario": {
                "label": "base",
                "period": "2026-2030",
                "regime_tone": macro_anchor.get("primary_regime_id") or "post_covid_normalization",
                "risk_tone": f"decision={macro_anchor.get('decision_state')}; elevated={elevated}",
                "behavior_tone": "macro-sensitive risk asset; benefits from easing hope, hurt by liquidity stress",
                "ai_adjacent": (
                    f"AI platform adoption by 2030 (companion DAU 1B p={_p(by_id, 'civ.tech.ai_companion_dau_1b_2030')}) "
                    "— narrative tailwind, not price guarantee"
                ),
                "operator_posture": macro_anchor.get("operator_posture"),
            },
            "stress_scenario": {
                "label": "stress",
                "period": "2026-2030",
                "behavior_tone": "drawdown clusters when macro forward stays WATCH+elevated for extended windows",
                "liquidity_tone": "elevated briefing risk signals persist",
                "policy_tone": f"CBDC/payments fragmentation (2035 OECD CBDC p={_p(by_id, 'civ.finance.cbdc_retail_oecd10_2035')})",
                "tail_triggers": _stress_triggers_from_signals(
                    signals, ["stablecoin/regulatory shock", "miner/custody concentration", "USD funding squeeze"]
                ),
                "logos_era_overlay": "사사 시대 · 순환 리스크 [HYPO]",
            },
        },
    }


def _scenario_probability_weights(
    macro_questions: list[dict[str, Any]],
    macro_anchor: dict[str, Any],
) -> dict[str, Any]:
    """Heuristic base/stress weights — research_only; not a calibrated joint forecast."""
    ps = [float(q["probability_0_1"]) for q in macro_questions if q.get("probability_0_1") is not None]
    registry_p_mean = round(sum(ps) / len(ps), 3) if ps else None
    signals = macro_anchor.get("top_risk_signals") or []
    signal_mean = (
        round(sum(float(s.get("score") or 0) for s in signals[:3]) / len(signals[:3]), 3) if signals else 0.0
    )

    stress = 0.35
    if macro_anchor.get("decision_state") == "WATCH":
        stress += 0.08
    if macro_anchor.get("risk_warning_level") == "elevated":
        stress += 0.12
    stress += min(0.15, signal_mean * 0.2)
    stress = round(min(0.65, max(0.15, stress)), 3)
    base = round(1.0 - stress, 3)

    def axis(base_delta: float = 0.0, stress_delta: float = 0.0) -> dict[str, float]:
        b = round(min(0.85, max(0.1, base + base_delta)), 3)
        s = round(min(0.85, max(0.1, 1.0 - b)), 3)
        _ = stress_delta  # reserved for future calibrated axis skew
        return {"base": b, "stress": s}

    return {
        "interpretation_class": "[HYPO]",
        "method": "heuristic_macro_forward_plus_briefing_signals",
        "not_calibrated": True,
        "registry_p_mean": registry_p_mean,
        "briefing_signal_mean_top3": signal_mean,
        "global": {"base": base, "stress": stress},
        "by_axis": {
            "korea": axis(0.05, -0.05),
            "usa": axis(0.0, 0.0),
            "japan": axis(-0.03, 0.03),
            "eu": axis(-0.02, 0.02),
            "btc": axis(-0.08, 0.08),
        },
        "composition_note": (
            "Weights derive from macro forward WATCH/elevated and briefing risk signal scores; "
            "not a joint distribution over GDP/price paths."
        ),
    }


def _phases(
    macro_questions: list[dict[str, Any]],
    band: dict[str, Any],
    two_track: dict[str, Any],
) -> list[dict[str, Any]]:
    track_a = band.get("track_a") or {}
    track_b = band.get("track_b") or {}
    band_2031 = _two_track_band_by_period(two_track, "2031-2040")
    track_b_forward = band_2031.get("track_b") or {}
    return [
        {
            "phase_id": "2026_2027",
            "label_ko": "고변동·레짐 플립",
            "track_a_thesis": track_a.get("thesis"),
            "track_a_phase_note": (
                "Opening sub-band: rate/CPI path discovery; regime flips dominate operator attention."
            ),
            "track_b_sign": track_b.get("sign_cluster"),
            "focus": ["rates path", "Korea CPI soft patch", "macro forward WATCH persistence"],
        },
        {
            "phase_id": "2028_2029",
            "label_ko": "신뢰·결제·AI 마찰",
            "track_a_thesis": track_a.get("thesis"),
            "track_a_phase_note": (
                "Closing sub-band: trust/payments/AI adoption friction toward 2030 registry anchors."
            ),
            "track_b_sign": track_b.get("sign_cluster"),
            "track_b_forward_lean": track_b_forward.get("sign_cluster"),
            "track_b_interpretation": track_b.get("interpretation"),
            "focus": ["payments/rails fragmentation", "AI adoption metrics", "food/energy tail monitors"],
        },
        {
            "phase_id": "2030_checkpoint",
            "label_ko": "2030 측정 앵커",
            "measurable_anchors": [
                q for q in macro_questions if q.get("question_id") == "civ.tech.ai_companion_dau_1b_2030"
            ],
            "focus": ["registry resolution deadlines", "scenario refresh vs realized data"],
        },
    ]


def build(
    *,
    dynamic_map: dict[str, Any],
    chronology: dict[str, Any],
    holdout: dict[str, Any],
    two_track: dict[str, Any],
    macro_brief: dict[str, Any],
    forward_weekly: dict[str, Any],
    general_prophecy: dict[str, Any],
    civ_apocalypse: dict[str, Any] | None = None,
    myeongni_lens: dict[str, Any] | None = None,
    sasang_lens: dict[str, Any] | None = None,
    myeongni_lens_path: Path | None = None,
    sasang_lens_path: Path | None = None,
    input_provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    macro_questions = _extract_macro_questions(general_prophecy, civ_apocalypse or {})
    chronology_overlay = _chronology_overlay(dynamic_map)
    macro_anchor = _macro_forward_anchor(macro_brief, forward_weekly)
    band_2030 = _two_track_2030_band(two_track)
    lens_triad = _lens_triad_from_artifacts(
        myeongni_lens,
        sasang_lens,
        myeongni_path=myeongni_lens_path,
        sasang_path=sasang_lens_path,
    )

    return {
        "schema": "logos_macro_horizon_2030_scenario_v1",
        "version": "1.2.1",
        "generated_at_utc": _now(),
        "scenario_kind": "narrative_template",
        "hypothesis_tier": "[HYPO]",
        "research_rail": "B",
        "boundary_ack": True,
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_trading_signal": True,
            "auto_merge_to_live_trading": False,
            "logos_ms_external_headline_pct": "~6.4% (text_blind v1 only)",
        },
        "scope": {"horizon_end_year": 2030, "start_anchor_year": 2026},
        "inputs": input_provenance or {},
        "field_primary": {
            "regime_id": macro_anchor.get("primary_regime_id"),
            "decision_state": macro_anchor.get("decision_state"),
            "risk_warning_level": macro_anchor.get("risk_warning_level"),
        },
        "lens_triad_stub": lens_triad,
        "logos_chronology_overlay": chronology_overlay,
        "chronology_evidence": _chronology_evidence(chronology, holdout),
        "macro_forward_anchor": macro_anchor,
        "two_track_2030_band": band_2030,
        "macro_prophecy_questions": macro_questions,
        "phases": _phases(macro_questions, band_2030, two_track),
        "scenario_probability_weights": _scenario_probability_weights(macro_questions, macro_anchor),
        "tri_axis_scenarios": _axis_scenarios(macro_questions, macro_anchor, chronology_overlay),
        "conflict_resolver": _conflict_resolver(chronology_overlay, macro_anchor, lens_triad),
        "disclaimer_ko": (
            "본 산출은 SSOT 아티팩트 조립 시나리오(narrative_template)이다. "
            "GDP/주가 확정 예언·실매매 지시·Track A/B2B 대외 헤드라인으로 사용 금지."
        ),
    }


def _render_md(doc: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Logos · 거시경제 2030 Horizon 시나리오")
    lines.append("")
    lines.append(f"- generated_at_utc: `{doc.get('generated_at_utc')}`")
    lines.append(f"- schema: `{doc.get('schema')}` v`{doc.get('version')}` · `{doc.get('scenario_kind')}` · `{doc.get('hypothesis_tier')}`")
    cr = doc.get("conflict_resolver") or {}
    lines.append(f"- Final action: **{cr.get('final_action')}** (advisory)")
    lines.append("")
    lines.append("## Field → Lens → Conflict")
    field = doc.get("field_primary") or {}
    logos = doc.get("logos_chronology_overlay") or {}
    lines.append(f"- **Field:** `{field.get('regime_id')}` · decision=`{field.get('decision_state')}` · risk=`{field.get('risk_warning_level')}`")
    lines.append(
        f"- **Lens (Logos `[NON_GATING]`):** `{logos.get('primary_label_ko')}` score={logos.get('primary_score')} · "
        f"2nd `{logos.get('secondary_label_ko')}`"
    )
    stub = doc.get("lens_triad_stub") or {}
    mn = stub.get("myeongni") or {}
    sa = stub.get("sasang") or {}
    if mn.get("status") == "read_only_snapshot":
        lines.append(
            f"- **명리 `[HYPO]`:** dir={mn.get('direction_score')} conf={mn.get('confidence')} "
            f"state_id={mn.get('state_id')}"
        )
    else:
        lines.append(f"- **명리:** `{mn.get('status')}`")
    if sa.get("status") == "read_only_snapshot":
        lines.append(
            f"- **사상 `[HYPO]`:** dominant={sa.get('dominant_constitution')} "
            f"force_hold={sa.get('force_hold')} entropy={sa.get('entropy_norm_4way')}"
        )
    else:
        lines.append(f"- **사상:** `{sa.get('status')}`")
    lines.append(f"- **Conflict:** {cr.get('summary_ko')}")
    if cr.get("lens_supplement_ko"):
        lines.append(f"- **Lens supplement:** {cr.get('lens_supplement_ko')}")
    lines.append(f"- **Final:** **{cr.get('final_action')}**")
    lines.append("")
    ev = doc.get("chronology_evidence") or {}
    hi = (ev.get("holdout_internal_only") or {})
    lines.append("## Chronology evidence (internal)")
    lines.append("")
    lines.append(
        f"- holdout train n={hi.get('train_holdout_n')} · v1 MS={hi.get('v1_ms_hit_at_1_strict')} · "
        f"v2 B-track={hi.get('v2_btrack_hit_at_1_strict')} · **not for MS headline**"
    )
    lines.append(f"- digest: `{ev.get('digest_pointer')}`")
    lines.append("")
    lines.append("## Phase bands (2026→2030)")
    lines.append("")
    for ph in doc.get("phases") or []:
        lines.append(f"### {ph.get('phase_id')} — {ph.get('label_ko')}")
        if ph.get("track_a_thesis"):
            lines.append(f"- Track A: {ph.get('track_a_thesis')}")
        if ph.get("track_a_phase_note"):
            lines.append(f"- Track A (phase): {ph.get('track_a_phase_note')}")
        if ph.get("track_b_sign"):
            lines.append(f"- Track B sign: {ph.get('track_b_sign')}")
        if ph.get("track_b_forward_lean"):
            lines.append(f"- Track B forward lean (2031 band): {ph.get('track_b_forward_lean')}")
        lines.append(f"- Focus: {', '.join(ph.get('focus') or [])}")
        lines.append("")
    weights = doc.get("scenario_probability_weights") or {}
    if weights.get("global"):
        lines.append("## Scenario weights (heuristic `[HYPO]`)")
        lines.append("")
        g = weights["global"]
        lines.append(f"- global base/stress: **{g.get('base')}** / **{g.get('stress')}**")
        if weights.get("registry_p_mean") is not None:
            lines.append(f"- registry p mean: {weights.get('registry_p_mean')}")
        lines.append(f"- note: {weights.get('composition_note')}")
        lines.append("")
    lines.append("## Tri-axis (+ JP/EU): base vs stress")
    lines.append("")
    for axis_key in ("korea", "usa", "japan", "eu", "btc"):
        axis = (doc.get("tri_axis_scenarios") or {}).get(axis_key) or {}
        lines.append(f"### {axis.get('axis_id')} ({', '.join(axis.get('instruments') or [])})")
        for kind in ("base_scenario", "stress_scenario"):
            sc = axis.get(kind) or {}
            lines.append(f"**{sc.get('label', kind)}** ({sc.get('period')})")
            for k, v in sc.items():
                if k in ("label", "period"):
                    continue
                lines.append(f"- {k}: {v}")
            lines.append("")
    anchor = doc.get("macro_forward_anchor") or {}
    if anchor.get("top_risk_signals"):
        lines.append("## Macro risk signals (briefing)")
        lines.append("")
        for sig in anchor["top_risk_signals"]:
            if isinstance(sig, dict):
                lines.append(f"- `{sig.get('name')}` score={sig.get('score')}")
        lines.append("")
    lines.append("## Macro prophecy anchors (p)")
    lines.append("")
    lines.append("| question_id | p | status |")
    lines.append("|-------------|---|--------|")
    for q in doc.get("macro_prophecy_questions") or []:
        lines.append(f"| `{q.get('question_id')}` | {q.get('probability_0_1')} | {q.get('resolution_status')} |")
    lines.append("")
    lines.append(f"> {doc.get('disclaimer_ko')}")
    lines.append("")
    lines.append(f"> Chronology MS: {logos.get('ms_headline_note')}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dynamic-map-json", type=Path, default=DEFAULT_DYNAMIC_MAP)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--holdout-json", type=Path, default=DEFAULT_HOLDOUT)
    ap.add_argument("--two-track-json", type=Path, default=DEFAULT_TWO_TRACK)
    ap.add_argument("--macro-brief-json", type=Path, default=DEFAULT_MACRO_BRIEF)
    ap.add_argument("--forward-weekly-json", type=Path, default=DEFAULT_FORWARD_WEEKLY)
    ap.add_argument("--general-prophecy-json", type=Path, default=DEFAULT_GENERAL_PROPHECY)
    ap.add_argument("--civ-apocalypse-json", type=Path, default=DEFAULT_CIV_APOCALYPSE)
    ap.add_argument("--myeongni-lens-json", type=Path, default=DEFAULT_MYEONGNI_LENS)
    ap.add_argument("--sasang-lens-json", type=Path, default=DEFAULT_SASANG_LENS)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument("--strict", action="store_true", help="Exit 1 if required inputs missing or empty anchors.")
    args = ap.parse_args()

    def resolve(p: Path) -> Path:
        return p if p.is_absolute() else ROOT / p

    path_map = {
        "dynamic_map": resolve(args.dynamic_map_json),
        "chronology": resolve(args.chronology_json),
        "holdout": resolve(args.holdout_json),
        "two_track": resolve(args.two_track_json),
        "macro_brief": resolve(args.macro_brief_json),
        "forward_weekly": resolve(args.forward_weekly_json),
        "general_prophecy": resolve(args.general_prophecy_json),
        "civ_apocalypse": resolve(args.civ_apocalypse_json),
        "myeongni_lens": resolve(args.myeongni_lens_json),
        "sasang_lens": resolve(args.sasang_lens_json),
    }

    if args.strict:
        missing = _validate_strict(path_map)
        if missing:
            print(json.dumps({"ok": False, "missing": missing}, ensure_ascii=False), file=sys.stderr)
            return 1

    civ_path = _resolve_civ_apocalypse_path(path_map["civ_apocalypse"])
    if civ_path.is_file() and civ_path.resolve() != DEFAULT_CIV_APOCALYPSE_ARTIFACTS.resolve():
        civ_path = _mirror_civ_apocalypse_to_artifacts(civ_path)
    path_map["civ_apocalypse"] = civ_path
    civ = _load(civ_path) if civ_path.is_file() else {}
    myeongni_path = path_map["myeongni_lens"]
    sasang_path = path_map["sasang_lens"]
    myeongni_lens = _load(myeongni_path) if myeongni_path.is_file() else {}
    sasang_lens = _load(sasang_path) if sasang_path.is_file() else {}
    provenance = _input_provenance(path_map)

    doc = build(
        dynamic_map=_load(path_map["dynamic_map"]),
        chronology=_load(path_map["chronology"]),
        holdout=_load(path_map["holdout"]),
        two_track=_load(path_map["two_track"]),
        macro_brief=_load(path_map["macro_brief"]),
        forward_weekly=_load(path_map["forward_weekly"]),
        general_prophecy=_load(path_map["general_prophecy"]),
        civ_apocalypse=civ,
        myeongni_lens=myeongni_lens or None,
        sasang_lens=sasang_lens or None,
        myeongni_lens_path=myeongni_path if myeongni_path.is_file() else None,
        sasang_lens_path=sasang_path if sasang_path.is_file() else None,
        input_provenance=provenance,
    )

    out_json = resolve(args.out_json)
    out_md = resolve(args.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(_render_md(doc), encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": str(out_json), "out_md": str(out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
