#!/usr/bin/env python3
"""Tier-2 lens profile shadow ablation (Arms A–E) [HYPO][research_only].

Compares operational lens-fusion profiles on KOSPI science-core panel without
Track A promotion or live-trading claims.
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

from scripts.btrack_science_core_v1 import TRIPLE_BLEND_WEIGHTS  # noqa: E402
from scripts.run_prophecy_lens_combo_backtest_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL,
    _build_variants,
    _extract_lens_maps,
    _extract_science_maps,
    _prior_completed_daily_return_by_eval_date,
    _read_json,
    _safe_float,
    _sign_to_dir,
    _simulate_variant,
)

DEFAULT_SCORE = ROOT / "reports/btrack_prophecy_score_science_core_panel_v1.json"
DEFAULT_SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_science_core_panel_v1.json"
DEFAULT_BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
DEFAULT_FUSION_ABLATION = ROOT / "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json"
DEFAULT_COUNTERFACTUAL = ROOT / "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/prophecy_lens_profile_shadow_ablation_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/prophecy_lens_profile_shadow_ablation_v1_latest.json"
SCHEMA = "prophecy_lens_profile_shadow_ablation_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _metrics_summary(result: dict[str, Any]) -> dict[str, Any]:
    m = result.get("metrics") or {}
    return {
        "strategy_id": result.get("strategy_id"),
        "n_active_days": m.get("n_active_days"),
        "directional_hit_rate_active": m.get("directional_hit_rate_active"),
        "total_return": m.get("total_return"),
        "cagr": m.get("cagr"),
        "sharpe": m.get("sharpe"),
        "mdd": m.get("mdd"),
    }


def _delta_vs_baseline(baseline: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    b = baseline.get("metrics") or {}
    o = other.get("metrics") or {}
    hit_b = float(b.get("directional_hit_rate_active") or 0.0)
    hit_o = float(o.get("directional_hit_rate_active") or 0.0)
    ret_b = float(b.get("total_return") or 0.0)
    ret_o = float(o.get("total_return") or 0.0)
    return {
        "hit_rate_delta_pp": round((hit_o - hit_b) * 100.0, 4),
        "total_return_delta_pp": round((ret_o - ret_b) * 100.0, 4),
    }


def _simulate_triple_blend(
    *,
    rows: list[dict[str, Any]],
    btc_prior: dict[str, float],
    myeongni_map: dict[str, int],
    sasang_map: dict[str, int],
    science_sign_map: dict[str, int],
    science_score_map: dict[str, float],
    fee_rate: float,
    deadzone: float,
    annual_trading_days: int,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    w = dict(weights or TRIPLE_BLEND_WEIGHTS)
    prev_pos = 0
    equity = 1.0
    equity_curve: list[float] = []
    pnl_series: list[float] = []
    pred_dirs: list[str] = []
    actual_dirs: list[str] = []
    active_mask: list[bool] = []

    for r in rows:
        eval_date = str(r.get("eval_date") or "")[:10]
        daily_ret = _safe_float(r.get("daily_return"), 0.0)
        actual_dir = str(r.get("actual_direction") or "neutral").strip().lower()
        sci = float(science_score_map.get(eval_date, science_sign_map.get(eval_date, 0)))
        sa = float(sasang_map.get(eval_date, 0))
        my = float(myeongni_map.get(eval_date, 0))
        blended = (w["science"] * sci) + (w["sasang"] * sa) + (w["myeongni"] * my)
        if blended > deadzone:
            pos = 1
        elif blended < -deadzone:
            pos = -1
        else:
            pos = 0

        turnover = abs(pos - prev_pos)
        fee = turnover * fee_rate
        pnl = (pos * daily_ret) - fee
        equity *= 1.0 + pnl
        prev_pos = pos

        pred_dirs.append(_sign_to_dir(pos))
        actual_dirs.append(actual_dir)
        active_mask.append(pos != 0)
        pnl_series.append(pnl)
        equity_curve.append(equity)

    from scripts.run_prophecy_lens_combo_backtest_v1 import _calc_metrics

    metrics = _calc_metrics(
        pnl_series=pnl_series,
        equity_series=equity_curve,
        predicted_dirs=pred_dirs,
        actual_dirs=actual_dirs,
        active_mask=active_mask,
        annual_trading_days=annual_trading_days,
    )
    return {
        "strategy_id": "science+sasang+myeongni",
        "lenses": ["science", "sasang", "myeongni"],
        "use_coordinator": False,
        "resolver": "science_triple_blend",
        "weights": w,
        "metrics": metrics,
    }


def _run_backtest_slice(
    *,
    rows: list[dict[str, Any]],
    sidecar_doc: dict[str, Any],
    science_sign_map: dict[str, int],
    science_score_map: dict[str, float],
    btc_prior: dict[str, float],
    logos_vote_mode: str,
    logos_min_confidence: float,
    fee_rate: float,
    deadzone: float,
    annual_trading_days: int,
) -> dict[str, dict[str, Any]]:
    myeongni_map, sasang_map, logos_sign, logos_confidence = _extract_lens_maps(sidecar_doc)
    variants = _build_variants(include_science=True)
    by_id: dict[str, dict[str, Any]] = {}
    for variant in variants:
        out = _simulate_variant(
            variant=variant,
            rows=rows,
            btc_prior=btc_prior,
            myeongni_map=myeongni_map,
            sasang_map=sasang_map,
            science_sign_map=science_sign_map,
            science_score_map=science_score_map,
            logos_sign=logos_sign,
            logos_confidence=logos_confidence,
            logos_vote_mode=logos_vote_mode,
            logos_min_confidence=logos_min_confidence,
            fee_rate=fee_rate,
            deadzone=deadzone,
            annual_trading_days=annual_trading_days,
        )
        by_id[str(out["strategy_id"])] = out

    triple = _simulate_triple_blend(
        rows=rows,
        btc_prior=btc_prior,
        myeongni_map=myeongni_map,
        sasang_map=sasang_map,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )
    by_id[triple["strategy_id"]] = triple
    return by_id


def _arm_e_regime_mkm_split(
    fusion_path: Path,
    counterfactual_path: Path,
) -> dict[str, Any]:
    fusion = _read_json_optional(fusion_path)
    counter = _read_json_optional(counterfactual_path)
    samsung_cf = ((counter.get("instruments") or {}).get("samsung") or {})
    samsung_fusion = ((fusion.get("instruments") or {}).get("samsung") or {})
    policy_returns = samsung_fusion.get("policy_returns_vs_counterfactual") or {}
    sasang_strategies = samsung_cf.get("strategies_sasang_window") or {}

    def _ret_from_policy(policy_id: str) -> float | None:
        block = policy_returns.get(policy_id) or {}
        window = block.get("sasang_window") if isinstance(block, dict) else {}
        if not isinstance(window, dict):
            return None
        v = window.get("total_return_pct")
        return float(v) if isinstance(v, (int, float)) else None

    def _underperform_pp(policy_id: str) -> float | None:
        block = policy_returns.get(policy_id) or {}
        window = block.get("sasang_window") if isinstance(block, dict) else {}
        if not isinstance(window, dict):
            return None
        v = window.get("underperform_vs_bah_pp")
        return float(v) if isinstance(v, (int, float)) else None

    bah_block = sasang_strategies.get("buy_and_hold") or {}
    bah_v = bah_block.get("total_return_pct") if isinstance(bah_block, dict) else None
    bah_ret = float(bah_v) if isinstance(bah_v, (int, float)) else None
    tac_ret = _ret_from_policy("regime_mkm_split_tactical")
    lit_ret = _ret_from_policy("literal_veto_hold")
    return {
        "arm_id": "E",
        "label": "regime_mkm_split + fusion posture (samsung sasang window)",
        "source_artifacts": {
            "fusion_ablation": str(fusion_path),
            "counterfactual": str(counterfactual_path),
        },
        "sasang_window": samsung_fusion.get("sasang_window") or samsung_cf.get("sasang_window"),
        "recommended_policy": fusion.get("recommended_policy"),
        "recommended_regime_id": fusion.get("recommended_regime_id"),
        "returns_pct": {
            "buy_and_hold": bah_ret,
            "regime_mkm_split_tactical": tac_ret,
            "literal_veto_hold": lit_ret,
        },
        "delta_vs_bah_pp": {
            "regime_mkm_split_tactical": _underperform_pp("regime_mkm_split_tactical"),
            "literal_veto_hold": _underperform_pp("literal_veto_hold"),
        },
        "interpretation_ko": (
            "force_hold=추격 차단(매도 강요 아님). tactical split은 BAH 대비 0pp, "
            "literal veto hold는 −58pp급 underperform."
        ),
    }


def build_ablation(
    *,
    score_json: Path,
    sidecar_json: Path,
    science_jsonl: Path,
    btc_csv: Path,
    target_instrument: str,
    fee_bps: float,
    deadzone: float,
    logos_min_confidence: float,
    annual_trading_days: int,
    fusion_ablation: Path,
    counterfactual: Path,
) -> dict[str, Any]:
    score_doc = _read_json(score_json)
    sidecar_doc = _read_json(sidecar_json)
    rows = score_doc.get("rows") or []
    if not isinstance(rows, list):
        raise SystemExit(f"invalid score rows: {score_json}")

    target = str(target_instrument or "kospi").strip().lower()
    filtered = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == target]
    filtered.sort(key=lambda x: str(x.get("eval_date") or ""))
    if not filtered:
        raise SystemExit(f"no rows for instrument={target} in {score_json}")

    if not science_jsonl.is_file():
        raise SystemExit(f"science jsonl missing: {science_jsonl}")

    science_sign_map, science_score_map = _extract_science_maps(science_jsonl)
    btc_prior = _prior_completed_daily_return_by_eval_date(btc_csv) if btc_csv.is_file() else {}
    fee_rate = float(fee_bps) / 10000.0

    omit = _run_backtest_slice(
        rows=filtered,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior=btc_prior,
        logos_vote_mode="omit",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )
    global_map = _run_backtest_slice(
        rows=filtered,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior=btc_prior,
        logos_vote_mode="global",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )
    gated = _run_backtest_slice(
        rows=filtered,
        sidecar_doc=sidecar_doc,
        science_sign_map=science_sign_map,
        science_score_map=science_score_map,
        btc_prior=btc_prior,
        logos_vote_mode="confidence_gated",
        logos_min_confidence=logos_min_confidence,
        fee_rate=fee_rate,
        deadzone=deadzone,
        annual_trading_days=annual_trading_days,
    )

    _, _, logos_sign, logos_confidence = _extract_lens_maps(sidecar_doc)
    baseline = omit["science+sasang"]

    arm_a = {
        "arm_id": "A",
        "label": "science+sasang quant baseline (logos vote omit)",
        "logos_vote_mode": "omit",
        "strategy_id": "science+sasang",
        "metrics": _metrics_summary(baseline),
        "operational_profile": "Field(science_core)+sasang; Logos sidecar off-vote",
    }

    arm_b = {
        "arm_id": "B",
        "label": "science+sasang + Logos sidecar only (no vote)",
        "logos_vote_mode": "omit",
        "strategy_id": "science+sasang",
        "metrics": _metrics_summary(baseline),
        "logos_sidecar": {
            "sign": logos_sign,
            "confidence": logos_confidence,
            "non_gating": True,
        },
        "note_ko": "투표 omit 시 quant 경로는 A와 동일; sidecar는 narrative/Oracle 레인 전용.",
        "identical_to_arm_a": True,
    }

    triple = omit["science+sasang+myeongni"]
    arm_c = {
        "arm_id": "C",
        "label": "science+sasang vs science+sasang+myeongni",
        "logos_vote_mode": "omit",
        "compare": {
            "science+sasang": _metrics_summary(baseline),
            "science+sasang+myeongni": _metrics_summary(triple),
        },
        "delta_triple_vs_baseline": _delta_vs_baseline(baseline, triple),
        "myeongni_removal_justified": bool(
            float((baseline.get("metrics") or {}).get("total_return") or 0.0)
            >= float((triple.get("metrics") or {}).get("total_return") or 0.0)
        ),
    }

    arm_d = {
        "arm_id": "D",
        "label": "logos vote mode sensitivity (science+logos disaster check)",
        "science+logos_by_mode": {
            "omit": _metrics_summary(omit["science+logos"]),
            "global": _metrics_summary(global_map["science+logos"]),
            "confidence_gated": _metrics_summary(gated["science+logos"]),
        },
        "logos+sasang_by_mode": {
            "omit": _metrics_summary(omit["logos+sasang"]),
            "global": _metrics_summary(global_map["logos+sasang"]),
            "confidence_gated": _metrics_summary(gated["logos+sasang"]),
        },
        "science+sasang_stable": {
            "omit": _metrics_summary(omit["science+sasang"]),
            "global": _metrics_summary(global_map["science+sasang"]),
            "confidence_gated": _metrics_summary(gated["science+sasang"]),
        },
        "verdict_ko": (
            "science+logos blend은 vote mode와 무관하게 손실(블렌드 resolver). "
            "omit/gated는 majority-vote 경로에서 Logos 오염 방지."
        ),
    }

    arm_e = _arm_e_regime_mkm_split(fusion_ablation, counterfactual)

    recommended = {
        "quant_lane": "A",
        "oracle_lane": "B + E",
        "avoid": ["science+logos blend", "literal_veto_hold without regime split"],
        "myeongni_in_prophecy_vote": False,
    }

    return {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "inputs": {
            "score_json": str(score_json),
            "sidecar_json": str(sidecar_json),
            "science_jsonl": str(science_jsonl),
            "target_instrument": target,
            "n_panel_rows": len(filtered),
            "fee_bps": fee_bps,
            "logos_min_confidence": logos_min_confidence,
            "logos_sidecar_sign": logos_sign,
            "logos_sidecar_confidence": logos_confidence,
        },
        "arms": {
            "A": arm_a,
            "B": arm_b,
            "C": arm_c,
            "D": arm_d,
            "E": arm_e,
        },
        "recommended_operational_profile": recommended,
        "headline_ko": [
            f"A science+sasang hit={arm_a['metrics']['directional_hit_rate_active']:.1%} ret={arm_a['metrics']['total_return']:.1%}",
            f"C triple vs baseline ret Δ={arm_c['delta_triple_vs_baseline']['total_return_delta_pp']:+.1f}pp",
            f"D science+logos(omit) ret={arm_d['science+logos_by_mode']['omit']['total_return']:.1%}",
            f"E regime_mkm_split tactical ΔBAH={arm_e['delta_vs_bah_pp']['regime_mkm_split_tactical']}pp",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--target-instrument", default="kospi")
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--coordinator-deadzone", type=float, default=0.001)
    ap.add_argument("--logos-min-confidence", type=float, default=0.25)
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument("--fusion-ablation", type=Path, default=DEFAULT_FUSION_ABLATION)
    ap.add_argument("--counterfactual", type=Path, default=DEFAULT_COUNTERFACTUAL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    payload = build_ablation(
        score_json=args.score_json,
        sidecar_json=args.sidecar_json,
        science_jsonl=args.science_jsonl,
        btc_csv=args.btc_csv,
        target_instrument=args.target_instrument,
        fee_bps=args.fee_bps,
        deadzone=abs(float(args.coordinator_deadzone)),
        logos_min_confidence=float(args.logos_min_confidence),
        annual_trading_days=max(1, int(args.annual_trading_days)),
        fusion_ablation=args.fusion_ablation,
        counterfactual=args.counterfactual,
    )

    for path in (args.output, args.artifact_output):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"OK arms=A-E rows={payload['inputs']['n_panel_rows']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
