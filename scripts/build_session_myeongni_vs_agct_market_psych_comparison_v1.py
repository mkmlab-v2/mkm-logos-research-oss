#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Side-by-side: AGCT+market_psych B-track lane vs session-myeongni hybrid ([HYPO])."""

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

DEFAULT_OUT = ROOT / "reports/session_myeongni_vs_agct_market_psych_comparison_v1.json"
ARTIFACT_OUT = ROOT / "docs/final/artifacts/session_myeongni_vs_agct_market_psych_comparison_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p)


def _pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{float(v) * 100:.1f}%"


def _pp_delta(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round((float(a) - float(b)) * 100, 2)


def _per_lens_hits(doc: dict[str, Any] | None, lens_id: str) -> dict[str, float | int | None]:
    out: dict[str, float | int | None] = {"kospi": None, "btc": None, "n": None}
    if not doc:
        return out
    legs = doc.get("legs") or {}
    for inst in ("kospi", "btc"):
        block = legs.get(inst) or {}
        for row in block.get("lenses") or []:
            if str(row.get("lens_id")) == lens_id:
                out[inst] = row.get("price_directional_hit_rate")
                if out["n"] is None:
                    out["n"] = row.get("n_evaluated")
    return out


def _paired_kospi_252d() -> dict[str, Any] | None:
    """Same-calendar KOSPI days: AGCT per-date vs session hybrid KOSPI leg."""
    agct_score = ROOT / "reports/btrack_prophecy_score_agct_market_psych_252d.json"
    hyb_score = ROOT / "reports/btrack_prophecy_score_hybrid_session_kospi_252d_v1.json"
    if not agct_score.is_file() or not hyb_score.is_file():
        return None

    def _kospi_map(path: Path) -> dict[str, tuple[str, str]]:
        sc = json.loads(path.read_text(encoding="utf-8"))
        return {
            str(r.get("eval_date")): (
                str(r.get("predicted_direction") or ""),
                str(r.get("actual_direction") or ""),
            )
            for r in sc.get("rows") or []
            if r.get("instrument") == "kospi"
        }

    agct = _kospi_map(agct_score)
    hyb = _kospi_map(hyb_score)
    keys = sorted(set(agct) & set(hyb))
    if not keys:
        return None
    n = len(keys)
    agct_h = hyb_h = both_h = agct_only = hyb_only = 0
    for k in keys:
        ap, aa = agct[k]
        hp, ha = hyb[k]
        ah = ap == aa
        hh = hp == ha
        if ah:
            agct_h += 1
        if hh:
            hyb_h += 1
        if ah and hh:
            both_h += 1
        elif ah and not hh:
            agct_only += 1
        elif hh and not ah:
            hyb_only += 1
    return {
        "n_paired_days": n,
        "agct_hit_rate": round(agct_h / n, 6),
        "hybrid_kospi_leg_hit_rate": round(hyb_h / n, 6),
        "delta_pp_agct_minus_hybrid": round((agct_h - hyb_h) / n * 100, 2),
        "days_agct_only_correct": agct_only,
        "days_hybrid_only_correct": hyb_only,
        "days_both_correct": both_h,
        "note_ko": "동일 eval_date·KOSPI만. BTC bear leg 제외.",
    }


def _build_comparison_table(
    *,
    agct_price: dict[str, Any] | None,
    agct_price_252: dict[str, Any] | None,
    hybrid_30: dict[str, Any] | None,
    hybrid_252: dict[str, Any] | None,
    per_lens: dict[str, Any] | None,
    agct_daily: dict[str, Any] | None,
) -> list[dict[str, str]]:
    agct_30 = (agct_price or {}).get("price_hit_rate_eval") or {}
    agct_252_hr = (agct_price_252 or {}).get("price_hit_rate_eval") or {}
    h30 = (hybrid_30 or {}).get("comparison_eval_prophecy_hit_rate") or {}
    h252 = (hybrid_252 or {}).get("eval_prophecy_hit_rate") or {}
    ext_acc = (agct_daily or {}).get("metrics", {}).get("external_accuracy_observed")
    ext_s = f"~{_pct(ext_acc)} (GO, threshold 31%)" if ext_acc is not None else "~35.8% (GO, threshold 31%)"
    lens_s = _per_lens_hits(per_lens, "sasang")
    lens_m = _per_lens_hits(per_lens, "market_sasang")
    d252_k = _pp_delta(
        agct_252_hr.get("kospi"),
        (h252.get("hybrid") or {}).get("kospi"),
    )
    d252_txt = (
        f"fusion {_pct(agct_252_hr.get('kospi'))}"
        + (f" ({d252_k:+.2f}pp vs hybrid)" if d252_k is not None else "")
        if agct_252_hr.get("kospi") is not None
        else "not run"
    )
    return [
        {
            "metric": "B-track internal gate (proxy axis alignment)",
            "agct_dna_market_psych": ext_s,
            "session_myeongni_hybrid": "N/A (different metric)",
        },
        {
            "metric": "KOSPI price directional hit (30d eval)",
            "agct_dna_market_psych": f"fusion per-date {_pct(agct_30.get('kospi'))}",
            "session_myeongni_hybrid": (
                f"hybrid {_pct((h30.get('hybrid_session_kospi_btc_bear') or {}).get('kospi'))} / "
                f"baseline {_pct((h30.get('baseline_frozen_both') or {}).get('kospi'))}"
            ),
        },
        {
            "metric": "BTC price directional hit (30d eval)",
            "agct_dna_market_psych": f"fusion per-date {_pct(agct_30.get('btc'))}",
            "session_myeongni_hybrid": (
                f"hybrid {_pct((h30.get('hybrid_session_kospi_btc_bear') or {}).get('btc'))} "
                "(frozen bear leg)"
            ),
        },
        {
            "metric": "KOSPI price directional hit (252d holdout)",
            "agct_dna_market_psych": d252_txt,
            "session_myeongni_hybrid": (
                f"hybrid {_pct((h252.get('hybrid') or {}).get('kospi'))} "
                f"(+{_pp_delta((h252.get('hybrid') or {}).get('kospi'), (h252.get('baseline_frozen_both') or {}).get('kospi')) or 0:.2f}pp vs frozen baseline)"
            ),
        },
        {
            "metric": "BTC price directional hit (252d holdout)",
            "agct_dna_market_psych": f"fusion {_pct(agct_252_hr.get('btc'))}",
            "session_myeongni_hybrid": f"hybrid {_pct((h252.get('hybrid') or {}).get('btc'))} (frozen bear leg)",
        },
        {
            "metric": "BTC price directional hit (30d, lens snapshot)",
            "agct_dna_market_psych": (
                f"sasang lens {_pct(lens_s.get('btc'))}; market_sasang {_pct(lens_m.get('btc'))}"
            ),
            "session_myeongni_hybrid": (
                f"hybrid {_pct((h30.get('hybrid_session_kospi_btc_bear') or {}).get('btc'))} "
                "(frozen bear leg)"
            ),
        },
        {
            "metric": "Operational verdict",
            "agct_dna_market_psych": "B-track GO / Stage2 — observation lane alive",
            "session_myeongni_hybrid": "Dual-leg observation candidate; not Track A",
        },
    ]


def _build_verdict_ko(
    *,
    agct_price_252: dict[str, Any] | None,
    hybrid_252: dict[str, Any] | None,
    doc_lane_252: dict[str, Any] | None,
) -> str:
    agct_k = (doc_lane_252 or {}).get("kospi")
    hyb_k = (hybrid_252 or {}).get("eval_prophecy_hit_rate", {}).get("hybrid", {}).get("kospi")
    d = _pp_delta(agct_k, hyb_k)
    extra = ""
    if d is not None:
        if d > 0.5:
            who = "AGCT 우위"
        elif d < -0.5:
            who = "세션 hybrid 우위"
        else:
            who = "동률"
        extra = (
            f" 252d 코스피 AGCT fusion {_pct(agct_k)} vs 세션 hybrid {_pct(hyb_k)} "
            f"({d:+.2f}pp, {who})."
        )
    return (
        "원칙: 인간=DNA/체질, 시장=일별 심리(per-date dna=0·market=1). "
        "B-track 코호트 0.6/0.4 GO(36%대)는 프록시 라벨용. "
        "가격: 시장심리만이 0.6/0.4 융합보다 우위(ablation). 252d 코스피는 세션 hybrid와 비교."
        + extra
        + " 통계·승격 없음. 본선 합선 금지."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--also-artifact", action="store_true", default=True)
    args = ap.parse_args()

    agct_daily = _load(ROOT / "reports/agct_sasang_btrack_daily_chain_v1_latest.json")
    agct_gowatch = _load(ROOT / "reports/agct_sasang_go_watch_pack_v1_latest.json")
    agct_sigma = _load(ROOT / "reports/agct_sigma_locked_baseline_chain_v1_latest.json")
    dna_market = _load(ROOT / "reports/sasang_dna_market_reasoning_v1_latest.json")
    dna_kospi = _load(ROOT / "reports/sasang_dna_market_reasoning_kospi_from_yfinance_latest.json")
    per_lens = _load(ROOT / "docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json")
    hybrid_30 = _load(ROOT / "reports/session_myeongni_ab_hybrid_30d_v1.json")
    hybrid_252 = _load(ROOT / "reports/session_myeongni_hybrid_holdout_252d_v1.json")
    obs_latest = _load(ROOT / "docs/final/artifacts/session_myeongni_hybrid_observation_latest.json")
    agct_price = _load(ROOT / "reports/agct_market_psych_price_eval_chain_v1_latest.json")
    agct_price_252 = _load(ROOT / "reports/agct_market_psych_price_eval_252d_v1_latest.json")
    ablation = _load(ROOT / "docs/final/artifacts/agct_market_psych_weight_ablation_v1_latest.json")
    paired_kospi = _paired_kospi_252d()
    paired_stats = _load(ROOT / "docs/final/artifacts/session_myeongni_vs_agct_paired_stats_v1_latest.json")
    ablation = _load(ROOT / "reports/agct_market_psych_weight_ablation_v1_latest.json")
    market_sweep = _load(ROOT / "reports/agct_market_psych_market_weight_sweep_v1_latest.json")
    psych_v1_v2 = _load(ROOT / "reports/market_psych_v1_vs_v2_price_ablation_v1_latest.json")
    manifest_val = _load(ROOT / "reports/market_psych_manifest_candidate_price_validation_v1_latest.json")

    gowatch_acc: list[float] = []
    if agct_gowatch:
        for run in agct_gowatch.get("runs") or []:
            m = run.get("metrics") or {}
            v = m.get("external_accuracy_observed")
            if v is not None:
                gowatch_acc.append(float(v))

    doc = {
        "schema": "session_myeongni_vs_agct_market_psych_comparison_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autotrigger_forbidden": True,
        "disclaimer_ko": (
            "두 레일은 목적·지표가 다름. AGCT external_accuracy는 4축↔프록시 라벨 정합; "
            "session/hybrid는 eval_prophecy_hit_rate 가격 방향. per-lens 73%는 counterfactual 스냅샷."
        ),
        "operating_principle_v1": {
            "label_ko": "인간=DNA·체질 / 시장=일별 심리·레짐 (격벽)",
            "human_rail": "AGCT·출생 명리·환자 번들 — 가격 per-date·Track A 자동 합선 금지",
            "market_rail": "yfinance 시장심리→4축 [HYPO]; per-date 기본 dna=0 market=1 (가격 체인)",
            "b_track_cohort_timeline": "run_sasang_dna_market_reasoning — legacy 0.6/0.4 코호트 융합",
            "artifacts": {
                "ablation": _rel(ROOT / "reports/agct_market_psych_weight_ablation_v1_latest.json"),
                "market_weight_sweep": _rel(
                    ROOT / "reports/agct_market_psych_market_weight_sweep_v1_latest.json"
                ),
            },
            "ablation_verdict_ko": (ablation or {}).get("verdict_ko"),
            "market_sweep_best_kospi": (market_sweep or {}).get("best_kospi_by_window"),
            "market_sweep_verdict_ko": (market_sweep or {}).get("verdict_ko"),
            "psych_v1_vs_v2_ablation": _rel(ROOT / "reports/market_psych_v1_vs_v2_price_ablation_v1_latest.json"),
            "psych_v1_vs_v2_delta": (psych_v1_v2 or {}).get("delta_v2_minus_v1"),
            "psych_v1_vs_v2_verdict_ko": (psych_v1_v2 or {}).get("verdict_ko"),
        },
        "lane_market_psych_v2_sandbox": {
            "label_ko": "시장심리 v2 샌드박스 (manifest + 확장 피처)",
            "manifest": _rel(ROOT / "docs/final/artifacts/market_psych_to_sasang_axis_manifest_v2.json"),
            "psych_csv": _rel(ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_v2_latest.csv"),
            "per_date_default": _rel(ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"),
            "ablation": (psych_v1_v2 or {}).get("delta_v2_minus_v1"),
            "lens_v2_bridge": _rel(
                ROOT / "docs/final/artifacts/market_sasang_lens_from_market_psych_v2_latest.json"
            ),
            "lens_upstream_compare": _rel(
                ROOT / "reports/market_sasang_lens_upstream_vs_v2_bridge_v1_latest.json"
            ),
            "daily_chain_hook": {
                "script": "scripts/run_btrack_daily_hypothesis_chain.ps1",
                "market_psych_v2_primary": "default ON — refresh_market_sasang_lens_v2_light_v1.py",
                "skip_primary": "-SkipMarketPsychV2FusionPrimary",
                "legacy_full_bridge": "-IncludeMarketPsychV2LensBridge (deprecated parallel rebuild)",
                "recommended_ops": "scripts/run_market_psych_v2_recommended_ops_v1.py",
            },
            "phase4_manifest_holdout": {
                "sweep": "reports/market_psych_manifest_holdout_sweep_v1_latest.json",
                "candidate_manifest": "reports/market_psych_manifest_candidate_holdout_best_v1.json",
                "script": "scripts/sweep_market_psych_manifest_holdout_v1.py",
                "ssot_promoted": True,
                "ssot_version": "2.0.1",
                "ssot_profile_id": "ty_hot_x125",
                "promotion_audit": _rel(
                    ROOT / "reports/market_psych_manifest_ssot_promotion_audit_v1_latest.json"
                ),
                "promote_script": "scripts/promote_market_psych_manifest_candidate_to_ssot_v1.py",
            },
            "phase4_price_validation_30_252": _rel(
                ROOT / "reports/market_psych_manifest_candidate_price_validation_v1_latest.json"
            ),
            "phase4_candidate_minus_ssot_delta": (manifest_val or {}).get("delta_candidate_minus_ssot"),
            "phase4_candidate_validation_verdict_ko": (manifest_val or {}).get("verdict_ko"),
            "scripts": [
                "scripts/build_market_psychology_kospi_from_yfinance_v2.py",
                "scripts/map_market_psych_to_sasang_axis_v2.py",
                "scripts/build_btrack_per_date_directions_market_psych_v2.py",
                "scripts/run_market_sasang_lens_from_market_psych_v2_v1.py",
                "scripts/run_market_psych_v1_vs_v2_price_ablation_v1.py",
                "scripts/sweep_market_psych_manifest_holdout_v1.py",
                "scripts/run_market_psych_manifest_candidate_price_validation_v1.py",
            ],
        },
        "lane_agct_dna_market_psych": {
            "label_ko": "사상 4축(DNA AGCT) + 시장심리 CSV 융합 (2026-05 · 코호트/B-track)",
            "fusion_rule": "fused_axis = 0.6*dna_axis + 0.4*market_axis (cohort timeline — not index per-date default)",
            "scripts": [
                "scripts/run_sasang_dna_market_reasoning_v1.py",
                "scripts/run_agct_sasang_btrack_daily_chain_v1.py",
                "scripts/run_agct_sigma_locked_baseline_chain_v1.py",
            ],
            "b_track_gate": {
                "decision": (agct_daily or {}).get("decision"),
                "external_accuracy_threshold_min": 0.31,
                "external_accuracy_aggressive": (agct_daily or {}).get("metrics", {}).get(
                    "external_accuracy_observed"
                ),
                "external_profiles": (agct_daily or {}).get("external_profiles"),
                "external_risk_corr": (agct_daily or {}).get("metrics", {}).get(
                    "external_risk_corr_observed"
                ),
                "time_split_gap": (agct_daily or {}).get("metrics", {}).get("time_split_gap_observed"),
                "robustness": (agct_daily or {}).get("metrics", {}).get("robustness_observed"),
                "go_watch_5run_external_accuracy_range": (
                    [min(gowatch_acc), max(gowatch_acc)] if gowatch_acc else None
                ),
                "sigma_locked_status": (agct_sigma or {}).get("summary", {}).get("status"),
            },
            "market_psych_inputs": {
                "sample_5d_csv": _rel(ROOT / "data/market_sasang/market_psychology_sample_v1.csv"),
                "kospi_yfinance_csv": _rel(
                    ROOT / "data/market_sasang/market_psychology_kospi_from_yfinance_latest.csv"
                ),
                "kospi_market_rows": (dna_kospi or {}).get("summary", {}).get("market_rows_used"),
                "latest_top_axis_sample": (dna_market or {}).get("summary", {}).get("latest_top_axis"),
                "latest_top_axis_kospi": (dna_kospi or {}).get("summary", {}).get("latest_top_axis"),
            },
            "artifacts": {
                "daily_chain": _rel(ROOT / "reports/agct_sasang_btrack_daily_chain_v1_latest.json"),
                "go_watch": _rel(ROOT / "reports/agct_sasang_go_watch_pack_v1_latest.json"),
                "dna_market": _rel(ROOT / "reports/sasang_dna_market_reasoning_v1_latest.json"),
                "dna_kospi": _rel(ROOT / "reports/sasang_dna_market_reasoning_kospi_from_yfinance_latest.json"),
            },
        },
        "lane_agct_price_eval_30d": {
            "label_ko": "시장심리 only per-date (dna=0, market=1) → price eval",
            "source": _rel(ROOT / "reports/agct_market_psych_price_eval_chain_v1_latest.json"),
            "price_hit_rate": (agct_price or {}).get("price_hit_rate_eval"),
            "b_track_proxy_gate": (agct_price or {}).get("b_track_proxy_gate"),
        },
        "lane_agct_price_eval_252d": {
            "label_ko": "시장심리 only per-date (dna=0, market=1) → price eval 252d",
            "source": _rel(ROOT / "reports/agct_market_psych_price_eval_252d_v1_latest.json"),
            "price_hit_rate": (agct_price_252 or {}).get("price_hit_rate_eval"),
            "delta_vs_session_hybrid_pp": {
                "kospi": _pp_delta(
                    (agct_price_252 or {}).get("price_hit_rate_eval", {}).get("kospi"),
                    (hybrid_252 or {})
                    .get("eval_prophecy_hit_rate", {})
                    .get("hybrid", {})
                    .get("kospi"),
                ),
                "btc": _pp_delta(
                    (agct_price_252 or {}).get("price_hit_rate_eval", {}).get("btc"),
                    (hybrid_252 or {})
                    .get("eval_prophecy_hit_rate", {})
                    .get("hybrid", {})
                    .get("btc"),
                ),
            },
        },
        "session_daily_snapshot": _rel(
            ROOT / "docs/final/artifacts/session_myeongni_daily_snapshot_latest.json"
        ),
        "lane_session_myeongni_hybrid": {
            "label_ko": "개장 09:00 세션 四柱 일주 → per-date 방향 (2026-06)",
            "hybrid_rule": "KOSPI=session per-date; BTC=frozen bear",
            "scripts": [
                "scripts/build_btrack_session_instant_myeongni_panel_v1.py",
                "scripts/build_btrack_prophecy_score_hybrid_session_kospi_v1.py",
                "scripts/build_session_myeongni_hybrid_observation_latest_v1.py",
            ],
            "price_hit_rate_eval": {
                "window_30d": (hybrid_30 or {}).get("comparison_eval_prophecy_hit_rate"),
                "delta_hybrid_vs_baseline_pp_30d": (hybrid_30 or {}).get("delta_hybrid_vs_baseline_pp"),
                "window_252d": (hybrid_252 or {}).get("eval_prophecy_hit_rate"),
                "delta_hybrid_vs_baseline_pp_252d": (hybrid_252 or {}).get(
                    "delta_hybrid_minus_baseline_pp"
                ),
                "rolling_obs_latest": (obs_latest or {}).get("rolling_eval"),
            },
            "today_2026_06_05": (obs_latest or {}).get("today") or (hybrid_30 or {}).get("target_2026_06_05"),
            "artifacts": {
                "ab_30d": _rel(ROOT / "reports/session_myeongni_ab_hybrid_30d_v1.json"),
                "holdout_252d": _rel(ROOT / "reports/session_myeongni_hybrid_holdout_252d_v1.json"),
                "observation_latest": _rel(
                    ROOT / "docs/final/artifacts/session_myeongni_hybrid_observation_latest.json"
                ),
            },
        },
        "lens_snapshot_price_hit_30d_counterfactual": {
            "source": _rel(ROOT / "docs/final/artifacts/prophecy_hit_rate_per_lens_latest.json"),
            "note": "Latest lens direction held constant across rows — not per-date sasang training.",
            "sasang_independent": _per_lens_hits(per_lens, "sasang"),
            "market_sasang_overlay": _per_lens_hits(per_lens, "market_sasang"),
            "myeongni_independent": _per_lens_hits(per_lens, "myeongni"),
        },
        "agct_weight_ablation_pointer": _rel(
            ROOT / "docs/final/artifacts/agct_market_psych_weight_ablation_v1_latest.json"
        ),
        "agct_weight_ablation_verdict_ko": (ablation or {}).get("verdict_ko"),
        "paired_kospi_252d": paired_kospi,
        "paired_stats_pointer": _rel(
            ROOT / "docs/final/artifacts/session_myeongni_vs_agct_paired_stats_v1_latest.json"
        ),
        "paired_stats_mcnemar": (paired_stats or {}).get("mcnemar"),
        "paired_stats_bootstrap": (paired_stats or {}).get("bootstrap_delta_hit_rate_pp"),
        "paired_stats_verdict_ko": (paired_stats or {}).get("verdict_ko"),
        "comparison_table": _build_comparison_table(
            agct_price=agct_price,
            agct_price_252=agct_price_252,
            hybrid_30=hybrid_30,
            hybrid_252=hybrid_252,
            per_lens=per_lens,
            agct_daily=agct_daily,
        ),
        "verdict_ko": _build_verdict_ko(
            agct_price_252=agct_price_252,
            hybrid_252=hybrid_252,
            doc_lane_252=(agct_price_252 or {}).get("price_hit_rate_eval"),
        ),
        "not_promoted_track_a": True,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(str(args.out.resolve()))

    if args.also_artifact:
        ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_OUT.write_text(text, encoding="utf-8")
        print(str(ARTIFACT_OUT.resolve()))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
