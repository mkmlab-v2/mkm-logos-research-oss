#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core conditional attach research bundle [HYPO][research_only].

Synthesizes:
  - KOSPI vs BTC holdout uplift divergence
  - shock vs non-shock short_1d subsets
  - horizon-conditional attach (short_1d vs mid_5d)
  - triple blend vs fixed combo (from governance snapshot)

Track A / live trading auto-merge forbidden.
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

import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402
from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_BTC,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    build_daily_short_rows,
    run_eval,
)

DEFAULT_GOV = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/science_core_conditional_attach_research_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"
DEFAULT_LOGOS_PER_DATE = ROOT / "reports/btrack_logos_per_date_v1.jsonl"

HOLDOUT_FROM = "2026-05-01"
HOLDOUT_TO = "2026-06-08"
DEFAULT_SHOCK_BPS = 100.0
FOCUS_LENS = ("science_core", "science_plus_sasang")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _soft_from_daily(
    rows: list[dict[str, Any]],
    lens_id: str,
    *,
    outcome_key: str = "outcomes_short_1d",
) -> dict[str, Any]:
    hits = fails = neutral = 0
    for r in rows:
        oc = (r.get(outcome_key) or {}).get(lens_id)
        if oc == "HIT":
            hits += 1
        elif oc == "FAIL":
            fails += 1
        elif oc == "NEUTRAL_DRAW":
            neutral += 1
    n = hits + fails + neutral
    soft = round((hits + 0.5 * neutral) / n, 4) if n else None
    science = _soft_from_daily(rows, "science_core", outcome_key=outcome_key) if lens_id != "science_core" else None
    uplift = None
    if soft is not None and science and science.get("soft_hit_rate") is not None:
        uplift = round(soft - float(science["soft_hit_rate"]), 4)
    return {
        "lens_id": lens_id,
        "n_scored": n,
        "hit": hits,
        "fail": fails,
        "neutral_draw": neutral,
        "soft_hit_rate": soft,
        "uplift_vs_science_pp": uplift,
    }


def _subset_daily(
    daily: list[dict[str, Any]],
    *,
    shock_bps: float,
    shock_only: bool | None,
) -> list[dict[str, Any]]:
    if shock_only is None:
        return daily
    out: list[dict[str, Any]] = []
    for r in daily:
        fr = r.get("forward_return_bps")
        if fr is None:
            continue
        is_shock = abs(float(fr)) >= shock_bps
        if shock_only and is_shock:
            out.append(r)
        elif not shock_only and not is_shock:
            out.append(r)
    return out


def _horizon_slice(matrix: dict[str, Any], horizon: str) -> dict[str, Any]:
    science = ((matrix.get("science_core") or {}).get(horizon) or {})
    sasang = ((matrix.get("science_plus_sasang") or {}).get(horizon) or {})
    s_soft = science.get("soft_hit_rate")
    c_soft = sasang.get("soft_hit_rate")
    uplift = round(float(c_soft) - float(s_soft), 4) if s_soft is not None and c_soft is not None else None
    attach_hint = bool(uplift is not None and uplift >= 0.03)
    return {
        "horizon": horizon,
        "science_core_soft": s_soft,
        "science_plus_sasang_soft": c_soft,
        "uplift_vs_science_pp": uplift,
        "conditional_attach_hint": attach_hint,
        "n_scored": sasang.get("n_scored"),
    }


def _instrument_holdout(
    *,
    instrument: str,
    csv_path: Path,
    science_jsonl: Path,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    logos_jsonl: Path | None,
    neutral_bps: float,
    shock_bps: float,
) -> dict[str, Any]:
    holdout_eval = run_eval(
        instrument=instrument,
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        date_from=HOLDOUT_FROM,
        date_to=HOLDOUT_TO,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=DEFAULT_LOGOS_LENS,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=5,
        required_horizons=("short_1d", "mid_5d"),
    )
    matrix = holdout_eval.get("rate_matrix") or {}
    daily = build_daily_short_rows(
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        date_from=HOLDOUT_FROM,
        date_to=HOLDOUT_TO,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=DEFAULT_LOGOS_LENS,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=5,
    )
    shock_rows = _subset_daily(daily, shock_bps=shock_bps, shock_only=True)
    calm_rows = _subset_daily(daily, shock_bps=shock_bps, shock_only=False)

    short_all = _horizon_slice(matrix, "short_1d")
    mid_all = _horizon_slice(matrix, "mid_5d")
    short_u = short_all.get("uplift_vs_science_pp")
    mid_u = mid_all.get("uplift_vs_science_pp")
    uplift_gap_short_minus_mid = (
        round(float(short_u) - float(mid_u), 4) if short_u is not None and mid_u is not None else None
    )
    horizon_split = bool(
        short_all.get("conditional_attach_hint")
        and (
            not mid_all.get("conditional_attach_hint")
            or (uplift_gap_short_minus_mid is not None and uplift_gap_short_minus_mid >= 0.15)
        )
    )

    shock_rates = {lid: _soft_from_daily(shock_rows, lid) for lid in FOCUS_LENS}
    calm_rates = {lid: _soft_from_daily(calm_rows, lid) for lid in FOCUS_LENS}
    all_rates = {lid: _soft_from_daily(daily, lid) for lid in FOCUS_LENS}

    sasang_agree = 0
    sasang_disagree = 0
    combo_wins_on_disagree = 0
    for r in daily:
        preds = r.get("predictions") or {}
        sc = preds.get("science_core")
        sa = preds.get("sasang_humanist") or preds.get("science_plus_sasang")
        if sc in (None, "neutral") or sa in (None, "neutral"):
            continue
        if sc == sa:
            sasang_agree += 1
        else:
            sasang_disagree += 1
            oc_sc = (r.get("outcomes_short_1d") or {}).get("science_core")
            oc_combo = (r.get("outcomes_short_1d") or {}).get("science_plus_sasang")
            if oc_combo == "HIT" and oc_sc != "HIT":
                combo_wins_on_disagree += 1

    return {
        "instrument": instrument,
        "holdout_window": {"from": HOLDOUT_FROM, "to": HOLDOUT_TO},
        "n_calendar_days": len(daily),
        "n_shock_days": len(shock_rows),
        "n_calm_days": len(calm_rows),
        "holdout_horizon": {
            "short_1d": short_all,
            "mid_5d": mid_all,
            "uplift_gap_short_minus_mid_pp": uplift_gap_short_minus_mid,
            "horizon_attach_split_recommended": horizon_split,
        },
        "shock_subset_short_1d": shock_rates,
        "calm_subset_short_1d": calm_rates,
        "all_days_short_1d": all_rates,
        "sasang_science_direction_audit": {
            "agree_days": sasang_agree,
            "disagree_days": sasang_disagree,
            "combo_hit_when_disagree": combo_wins_on_disagree,
            "note_ko": "disagree일 때 combo가 science 단독 miss를 구제한 날 수",
        },
    }


def _btc_divergence_diagnosis(
    kospi: dict[str, Any],
    btc: dict[str, Any],
    *,
    btc_long_window: dict[str, Any] | None,
) -> dict[str, Any]:
    k_uplift = (kospi.get("holdout_horizon") or {}).get("short_1d", {}).get("uplift_vs_science_pp")
    b_uplift = (btc.get("holdout_horizon") or {}).get("short_1d", {}).get("uplift_vs_science_pp")
    hypotheses: list[dict[str, str]] = []

    if k_uplift is not None and b_uplift is not None and k_uplift > 0.03 and b_uplift < 0:
        hypotheses.append(
            {
                "id": "instrument_specific_sasang_blend",
                "summary_ko": "동일 sasang overlay가 KOSPI holdout에선 +, BTC holdout에선 − — instrument-specific attach",
            }
        )

    b_shock = ((btc.get("shock_subset_short_1d") or {}).get("science_plus_sasang") or {}).get(
        "uplift_vs_science_pp"
    )
    b_calm = ((btc.get("calm_subset_short_1d") or {}).get("science_plus_sasang") or {}).get("uplift_vs_science_pp")
    if b_shock is not None and b_calm is not None:
        hypotheses.append(
            {
                "id": "btc_shock_calm_asymmetry",
                "summary_ko": f"BTC shock uplift {b_shock}pp vs calm {b_calm}pp — 변동성 레짐별 attach 분리 가설",
            }
        )

    if btc_long_window:
        eras = btc_long_window.get("eras") or {}
        bw_ms = eras.get("bundle_window_market_sasang") or {}
        bw_lenses = bw_ms.get("lenses") or {}
        sc_full = ((bw_lenses.get("science_core") or {}).get("soft_hit_rate"))
        sa_full = ((bw_lenses.get("science_plus_sasang") or {}).get("soft_hit_rate"))
        if sc_full is not None and sa_full is not None and float(sc_full) >= float(sa_full):
            hypotheses.append(
                {
                    "id": "btc_full_window_sasang_dilution",
                    "summary_ko": "BTC bundle_window(H1) 전체에선 market sasang blend가 science 단독 이하 — holdout-only uplift와 부호 불일치 설명",
                }
            )

    return {
        "kospi_holdout_uplift_pp": k_uplift,
        "btc_holdout_uplift_pp": b_uplift,
        "parity_label": "divergent" if k_uplift and b_uplift and (k_uplift > 0) != (b_uplift > 0) else "aligned",
        "hypotheses": hypotheses,
        "final_action": "btc_observe_only_kospi_primary_attach",
    }


def _triple_blend_policy(governance: dict[str, Any] | None) -> dict[str, Any]:
    sweep = (governance or {}).get("triple_blend_weight_sweep") or {}
    humanist = (governance or {}).get("humanist_combo_holdout") or {}
    fixed_uplift = (governance or {}).get("holdout") or {}
    return {
        "fixed_combo_recommended": fixed_uplift.get("recommended_combo") or "science_plus_sasang",
        "fixed_combo_holdout_soft": ((humanist.get("short_1d_soft") or {}).get("science_plus_sasang")),
        "best_weight_profile": sweep.get("best_holdout_profile"),
        "best_weight_holdout_triple_soft": sweep.get("best_holdout_triple_soft"),
        "weight_beats_fixed_on_holdout": sweep.get("any_triple_beats_sasang_combo_on_holdout"),
        "policy_hypothesis_ko": (
            "train-optimized 가중(triple sweep) vs 고정 COMBO_BLEND — "
            "holdout에서 weight 1위여도 walk-forward·재현성 확인 전 attach 정책 변경 금지"
        ),
        "attach_policy_recommendation": "keep_fixed_science_plus_sasang",
    }


def _kospi_shock_calm_attach_policy(
    kospi: dict[str, Any],
    *,
    shock_bps: float,
    shock_gap_min_pp: float = 0.15,
    calm_min_n: int = 5,
    shock_min_n: int = 10,
) -> dict[str, Any]:
    shock_arm = (kospi.get("shock_subset_short_1d") or {}).get("science_plus_sasang") or {}
    calm_arm = (kospi.get("calm_subset_short_1d") or {}).get("science_plus_sasang") or {}
    shock_u = shock_arm.get("uplift_vs_science_pp")
    calm_u = calm_arm.get("uplift_vs_science_pp")
    n_shock = int(kospi.get("n_shock_days") or 0)
    n_calm = int(kospi.get("n_calm_days") or 0)
    gap = (
        round(float(shock_u) - float(calm_u), 4)
        if shock_u is not None and calm_u is not None
        else None
    )
    attach_on_shock_only = bool(
        gap is not None
        and gap >= shock_gap_min_pp
        and n_shock >= shock_min_n
        and n_calm >= calm_min_n
        and shock_u is not None
        and float(shock_u) > 0.03
        and (calm_u is None or float(calm_u) >= 0.0)
    )
    return {
        "shock_uplift_pp": shock_u,
        "calm_uplift_pp": calm_u,
        "uplift_gap_shock_minus_calm_pp": gap,
        "n_shock_days": n_shock,
        "n_calm_days": n_calm,
        "attach_on_shock_only_recommended": attach_on_shock_only,
        "recommended_hypothesis": (
            "attach_sasang_on_shock_days_only"
            if attach_on_shock_only
            else "needs_more_calm_n_or_confirm_shock_gap"
        ),
        "note_ko": (
            f"KOSPI holdout shock/calm split (|move|>={shock_bps}bps). "
            "calm n 작으면 shock-only attach 가설만 유지. Track A·실매매 승격 아님."
        ),
    }


def build_research_bundle(
    *,
    governance: dict[str, Any] | None,
    btc_long_window: dict[str, Any] | None,
    neutral_bps: float,
    shock_bps: float,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    logos_jsonl: Path | None,
) -> dict[str, Any]:
    kospi = _instrument_holdout(
        instrument="kospi",
        csv_path=v1.KOSPI_CSV,
        science_jsonl=DEFAULT_SCIENCE_JSONL_KOSPI,
        sasang_jsonl=sasang_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        logos_jsonl=logos_jsonl,
        neutral_bps=neutral_bps,
        shock_bps=shock_bps,
    )
    btc = _instrument_holdout(
        instrument="btc",
        csv_path=v1.BTC_CSV,
        science_jsonl=DEFAULT_SCIENCE_JSONL_BTC,
        sasang_jsonl=sasang_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        logos_jsonl=logos_jsonl,
        neutral_bps=neutral_bps,
        shock_bps=shock_bps,
    )
    divergence = _btc_divergence_diagnosis(kospi, btc, btc_long_window=btc_long_window)
    triple = _triple_blend_policy(governance)

    k_hor = kospi.get("holdout_horizon") or {}
    horizon_policy = {
        "kospi_short_1d_attach_hint": ((k_hor.get("short_1d") or {}).get("conditional_attach_hint")),
        "kospi_mid_5d_attach_hint": ((k_hor.get("mid_5d") or {}).get("conditional_attach_hint")),
        "recommended_hypothesis": "attach_sasang_on_short_1d_only"
        if (kospi.get("holdout_horizon") or {}).get("horizon_attach_split_recommended")
        else "always_or_never_needs_more_n",
        "note_ko": f"holdout n={kospi.get('n_calendar_days', '?')} — 정책 확정 아님, 조건부 attach 가설만",
    }
    kospi_shock_calm = _kospi_shock_calm_attach_policy(kospi, shock_bps=shock_bps)
    return {
        "schema": "science_core_conditional_attach_research_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "field_id": "regime_science_core_v1_evaluation",
        "shock_move_bps_threshold": shock_bps,
        "instrument_slices": {
            "kospi": kospi,
            "btc": btc,
        },
        "btc_divergence": divergence,
        "horizon_conditional_attach": horizon_policy,
        "kospi_shock_calm_attach": kospi_shock_calm,
        "triple_blend_vs_fixed_combo": triple,
        "reporting_order": ["Field", "Instrument", "Horizon/Shock subset", "Conflict", "Final Action"],
        "final_action": {
            "action_id": "WATCH_CONDITIONAL_ATTACH_HYPOTHESES",
            "kospi": "research_attach_candidate_unchanged",
            "btc": "observe_only",
            "next_data_trigger": "extend_holdout_after_new_ohlcv",
        },
        "fact_lock": {
            "governance_bundle": str(DEFAULT_GOV.relative_to(ROOT)).replace("\\", "/"),
            "btc_long_window": "docs/final/artifacts/science_core_long_window_lane_compare_btc_v1_latest.json",
        },
        "methodology_ko": (
            "holdout·shock·horizon 조건부 attach 연구 번들. "
            "Track A·실매매·압축 KPI 합선 금지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--governance-json", type=Path, default=DEFAULT_GOV)
    ap.add_argument("--btc-long-window-json", type=Path, default=ART_OUT.parent / "science_core_long_window_lane_compare_btc_v1_latest.json")
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_PER_DATE)
    ap.add_argument("--logos-jsonl", type=Path, default=DEFAULT_LOGOS_PER_DATE)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--shock-move-bps", type=float, default=DEFAULT_SHOCK_BPS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    if not args.sasang_jsonl.is_file():
        print(f"ERROR: missing sasang jsonl: {args.sasang_jsonl}", file=sys.stderr)
        return 2
    if not v1.KOSPI_CSV.is_file():
        print(f"ERROR: missing KOSPI CSV: {v1.KOSPI_CSV}", file=sys.stderr)
        return 2
    if not v1.BTC_CSV.is_file():
        print(f"ERROR: missing BTC CSV: {v1.BTC_CSV}", file=sys.stderr)
        return 2

    logos_jsonl = args.logos_jsonl if args.logos_jsonl.is_file() else None
    doc = build_research_bundle(
        governance=_load_json(args.governance_json),
        btc_long_window=_load_json(args.btc_long_window_json),
        neutral_bps=args.neutral_bps,
        shock_bps=args.shock_move_bps,
        sasang_jsonl=args.sasang_jsonl,
        myeongni_jsonl=args.myeongni_jsonl,
        logos_jsonl=logos_jsonl,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    k_u = doc["btc_divergence"]["kospi_holdout_uplift_pp"]
    b_u = doc["btc_divergence"]["btc_holdout_uplift_pp"]
    print(
        f"WROTE: {args.output.resolve()} kospi_uplift={k_u} btc_uplift={b_u} "
        f"horizon_hypothesis={doc['horizon_conditional_attach']['recommended_hypothesis']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
