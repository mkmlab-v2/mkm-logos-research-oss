#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core weekly governance bundle [HYPO][research_only].

Runs: per-date build, horizon eval, holdout, walk-forward, shock discordant, attach composite gate.
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

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.build_btrack_humanist_jsonl_from_sidecar_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_OUT as SIDECAR_MYEONGNI_OUT,
    DEFAULT_SASANG_OUT as SIDECAR_SASANG_OUT,
    DEFAULT_SIDECAR,
    export_humanist_jsonl_from_sidecar,
    _write_jsonl,
)
from scripts.build_science_core_shock_discordant_day_report_v1 import build_report as build_shock_report  # noqa: E402
from scripts.run_science_core_holdout_combo_v1 import run_holdout_bundle  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_BTC,
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _ensure_science_jsonl,
    build_daily_short_rows,
    run_eval,
)
from scripts.run_science_core_walkforward_v1 import run_walkforward  # noqa: E402
from scripts.btrack_logos_per_date_core_v1 import DEFAULT_LOGOS_PER_DATE_JSONL  # noqa: E402
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_governance_bundle_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_governance_bundle_v1_latest.json"
DEFAULT_MARKET_SASANG_JSONL = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE_JSONL = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"

DEFAULT_FROM = "2026-01-01"
DEFAULT_TO = "2026-06-08"
DEFAULT_MACRO_LONG_FROM = "1997-01-01"
DEFAULT_BTC_LONG_FROM = "2014-09-17"
MIN_WF_TOP1 = 0.20
MIN_WF_UPLIFT = 0.02
MIN_SCIENCE_JSONL_ROWS = 30


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _humanist_inputs_are_calendar_stub(*paths: Path) -> dict[str, Any]:
    out: dict[str, Any] = {
        "any_stub": False,
        "sidecar_dated_origin": False,
        "underlying_stub_caution": False,
        "manseryeok_session_per_date": False,
        "paths": {},
    }
    for path in paths:
        rel = str(path.relative_to(ROOT)).replace("\\", "/") if path.is_relative_to(ROOT) else str(path)
        stub = False
        sidecar_origin = False
        underlying_caution = False
        manseryeok = False
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("stub") is True:
                    stub = True
                sp = str(row.get("source_provenance") or row.get("source") or "")
                if sp == "sidecar_dated_snapshot_v1":
                    sidecar_origin = True
                if "manseryeok_session" in sp:
                    manseryeok = True
                if row.get("underlying_may_be_calendar_stub") is True:
                    underlying_caution = True
        out["paths"][rel] = {
            "stub_flag": stub,
            "sidecar_dated_origin": sidecar_origin,
            "underlying_may_be_calendar_stub": underlying_caution,
            "manseryeok_session_per_date": manseryeok,
        }
        out["any_stub"] = out["any_stub"] or stub
        out["sidecar_dated_origin"] = out["sidecar_dated_origin"] or sidecar_origin
        out["underlying_stub_caution"] = out["underlying_stub_caution"] or underlying_caution
        out["manseryeok_session_per_date"] = out["manseryeok_session_per_date"] or manseryeok
    out["note_ko"] = (
        "calendar stub humanist JSONL이면 attach/composite uplift는 연구용 caution. "
        "sidecar export도 원천이 calendar stub이면 underlying_stub_caution 유지."
    )
    return out


def _science_jsonl_needs_rebuild(path: Path, date_from: str, date_to: str) -> bool:
    if not path.is_file():
        return True
    dates: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        dk = str(row.get("session_date") or "")[:10]
        if len(dk) == 10:
            dates.append(dk)
    if len(dates) < MIN_SCIENCE_JSONL_ROWS:
        return True
    dates.sort()
    return dates[0] > date_from or dates[-1] < date_to


def _audit_news_coverage_from_science_jsonl(path: Path) -> dict[str, Any]:
    from collections import Counter

    modes: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        news = (row.get("components") or {}).get("news") or {}
        modes[str(news.get("mode") or "missing")] += 1
    causal = int(modes.get("causal_exa_news_window", 0))
    total = sum(modes.values()) or 1
    return {
        "n_rows": total,
        "news_mode_counts": dict(modes),
        "causal_exa_days": causal,
        "causal_exa_share": round(causal / total, 4),
        "sparse_causal_coverage": causal < max(10, int(total * 0.01)),
        "note_ko": "news causal_exa가 희소하면 science_core는 price+macro 지배. EXA ingest는 B-track PoC.",
    }


DEFAULT_SHOCK_ONLY_ATTACH_ART = (
    ROOT / "docs/final/artifacts/science_core_kospi_shock_only_attach_backtest_v1_latest.json"
)


def _slim_shock_only_attach_policy(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    if not doc:
        return None
    pv = doc.get("policy_verdict") or {}
    soft_policies = (doc.get("soft_hit") or {}).get("policies") or {}
    shock_arm = soft_policies.get("shock_only_attach") or {}
    always_sas = soft_policies.get("always_science_plus_sasang") or {}
    pnl_policies = (doc.get("pnl_sim") or {}).get("policies") or {}
    return {
        "attach_on_shock_only_recommended": pv.get("attach_on_shock_only_recommended"),
        "recommended_hypothesis": pv.get("recommended_hypothesis"),
        "shock_only_vs_always_sasang_soft_pp": pv.get("shock_only_vs_always_sasang_soft_pp"),
        "holdout_n_scored": shock_arm.get("n_scored"),
        "shock_only_soft": shock_arm.get("soft_hit_rate"),
        "always_sasang_soft": always_sas.get("soft_hit_rate"),
        "shock_only_total_return": (pnl_policies.get("shock_only_attach") or {}).get("total_return"),
        "always_sasang_total_return": (pnl_policies.get("always_science_plus_sasang") or {}).get(
            "total_return"
        ),
        "economic_edge_claim_allowed": False,
        "active_lane_unchanged": "science_plus_sasang",
        "note_ko": (
            "shock_only 혼합 정책이 always 부착을 이기지 못하면 상시 부착 유지. "
            "Track A·실매매 승격 근거 아님."
        ),
    }


def _load_or_run_shock_only_attach_policy(
    *,
    date_to: str,
    science_jsonl: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_jsonl: Path | None,
    neutral_bps: float,
) -> dict[str, Any] | None:
    if DEFAULT_SHOCK_ONLY_ATTACH_ART.is_file():
        try:
            cached = json.loads(DEFAULT_SHOCK_ONLY_ATTACH_ART.read_text(encoding="utf-8-sig"))
            win = cached.get("window") or {}
            if str(win.get("to") or "")[:10] >= date_to[:10]:
                slim = _slim_shock_only_attach_policy(cached)
                if slim:
                    return slim
        except (OSError, json.JSONDecodeError):
            pass
    try:
        from scripts.run_science_core_kospi_shock_only_attach_backtest_v1 import run_backtest

        full = run_backtest(
            csv_path=v1.KOSPI_CSV,
            science_jsonl=science_jsonl,
            myeongni_jsonl=myeongni_jsonl,
            sasang_jsonl=sasang_jsonl,
            logos_jsonl=logos_jsonl,
            date_from="2026-05-01",
            date_to=date_to,
            neutral_bps=neutral_bps,
            fee_bps=5.0,
            shock_bps=100.0,
        )
        return _slim_shock_only_attach_policy(full)
    except Exception:  # noqa: BLE001 — governance bundle must still succeed
        return None


def _pnl_strategy_pick(pnl_doc: dict[str, Any] | None, strategy_id: str) -> dict[str, Any]:
    strat = ((pnl_doc or {}).get("strategies") or {}).get(strategy_id) or {}
    return {
        "total_return": strat.get("total_return"),
        "n_active_days": strat.get("n_active_days"),
        "directional_hit_rate_active": strat.get("directional_hit_rate_active"),
    }


def _slim_pnl_economic_significance(holdout_kospi: dict[str, Any] | None) -> dict[str, Any]:
    holdout_kospi = holdout_kospi or {}
    train_pnl = holdout_kospi.get("pnl_backtest_train") or {}
    hold_pnl = holdout_kospi.get("pnl_backtest_holdout") or {}
    ids = (
        "science_core",
        "science_plus_sasang",
        "science_plus_myeongni",
        "science_plus_sasang_myeongni",
    )
    train = {sid: _pnl_strategy_pick(train_pnl, sid) for sid in ids}
    holdout = {sid: _pnl_strategy_pick(hold_pnl, sid) for sid in ids}
    science_ret = holdout["science_core"].get("total_return")
    deltas: dict[str, float | None] = {}
    for sid in ("science_plus_sasang", "science_plus_myeongni", "science_plus_sasang_myeongni"):
        combo_ret = holdout[sid].get("total_return")
        deltas[sid] = (
            round(float(combo_ret) - float(science_ret), 6)
            if combo_ret is not None and science_ret is not None
            else None
        )
    blockers: list[str] = []
    if science_ret is not None and float(science_ret) <= 0:
        blockers.append("holdout_science_core_pnl_non_positive")
    for sid in ("science_plus_sasang", "science_plus_myeongni", "science_plus_sasang_myeongni"):
        d = deltas.get(sid)
        if d is not None and float(d) <= 0:
            blockers.append(f"holdout_{sid}_pnl_delta_vs_science_non_positive")
    return {
        "fee_bps": hold_pnl.get("fee_bps"),
        "train": train,
        "holdout": holdout,
        "holdout_delta_total_return_vs_science": deltas,
        "economic_edge_claim_allowed": False,
        "pnl_blockers": blockers,
        "note_ko": (
            "단순 방향 PnL 시뮬(수수료 포함). 적중률 uplift와 PnL은 분리 관측. "
            "Track A·실매매 경제적 유의 승격 근거 아님."
        ),
    }


def _humanist_combo_holdout_compare(holdout_horizon: dict[str, Any] | None) -> dict[str, Any]:
    matrix = (holdout_horizon or {}).get("rate_matrix") or {}

    def _soft(lens_id: str, horizon: str) -> float | None:
        block = (matrix.get(lens_id) or {}).get(horizon) or {}
        v = block.get("soft_hit_rate")
        return float(v) if v is not None else None

    combo_ids = (
        "science_core",
        "science_plus_sasang",
        "science_plus_myeongni",
        "science_plus_logos",
        "science_plus_sasang_myeongni",
    )
    attach_combo_ids = (
        "science_core",
        "science_plus_sasang",
        "science_plus_myeongni",
        "science_plus_logos",
    )
    short_rows: list[dict[str, Any]] = []
    for lid in combo_ids:
        soft = _soft(lid, "short_1d")
        if soft is None:
            continue
        short_rows.append({"lens_id": lid, "short_1d_soft": soft})
    short_rows.sort(key=lambda r: float(r["short_1d_soft"]), reverse=True)
    sasang_soft = _soft("science_plus_sasang", "short_1d")
    myeongni_soft = _soft("science_plus_myeongni", "short_1d")
    triple_soft = _soft("science_plus_sasang_myeongni", "short_1d")
    science_soft = _soft("science_core", "short_1d")
    attach_ranked = [r for r in short_rows if r["lens_id"] in attach_combo_ids]
    return {
        "n_eval_dates": holdout_horizon.get("n_eval_dates") if holdout_horizon else None,
        "short_1d_soft": {lid: _soft(lid, "short_1d") for lid in combo_ids},
        "mid_5d_soft": {lid: _soft(lid, "mid_5d") for lid in combo_ids},
        "short_1d_ranking": short_rows,
        "attach_eligible_short_1d_ranking": attach_ranked,
        "sasang_vs_myeongni_delta_short_1d": (
            round(float(sasang_soft) - float(myeongni_soft), 4)
            if sasang_soft is not None and myeongni_soft is not None
            else None
        ),
        "triple_vs_sasang_delta_short_1d": (
            round(float(triple_soft) - float(sasang_soft), 4)
            if triple_soft is not None and sasang_soft is not None
            else None
        ),
        "science_plus_myeongni_uplift_vs_science_short_1d": (
            round(float(myeongni_soft) - float(science_soft), 4)
            if myeongni_soft is not None and science_soft is not None
            else None
        ),
        "science_plus_sasang_myeongni_uplift_vs_science_short_1d": (
            round(float(triple_soft) - float(science_soft), 4)
            if triple_soft is not None and science_soft is not None
            else None
        ),
        "triple_beats_sasang_on_holdout": (
            triple_soft is not None
            and sasang_soft is not None
            and float(triple_soft) > float(sasang_soft)
        ),
        "note_ko": (
            "composite attach 게이트는 2-way combo 4종만(COMBO_LENS_IDS). "
            "science_plus_sasang_myeongni는 B-track 3-way 관측 전용."
        ),
    }


def _btc_holdout_auxiliary_gate(
    btc_holdout_horizon: dict[str, Any] | None,
    kospi_holdout_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    matrix = (btc_holdout_horizon or {}).get("rate_matrix") or {}

    def _soft(lens_id: str, horizon: str) -> float | None:
        block = (matrix.get(lens_id) or {}).get(horizon) or {}
        v = block.get("soft_hit_rate")
        return float(v) if v is not None else None

    n_eval = btc_holdout_horizon.get("n_eval_dates") if btc_holdout_horizon else None
    science_soft = _soft("science_core", "short_1d")
    sasang_soft = _soft("science_plus_sasang", "short_1d")
    triple_soft = _soft("science_plus_sasang_myeongni", "short_1d")
    kospi_uplift = (kospi_holdout_summary or {}).get("kospi_holdout_uplift_soft")
    btc_uplift = (
        round(float(sasang_soft) - float(science_soft), 4)
        if sasang_soft is not None and science_soft is not None
        else None
    )
    parity = "insufficient_n"
    if (
        btc_uplift is not None
        and kospi_uplift is not None
        and n_eval is not None
        and int(n_eval) >= 10
    ):
        same_sign = (btc_uplift >= 0) == (float(kospi_uplift) >= 0)
        parity = "aligned" if same_sign else "divergent"
    return {
        "primary_attach_instrument": "kospi",
        "gates_primary_attach": False,
        "n_eval_dates": n_eval,
        "short_1d_soft": {
            "science_core": science_soft,
            "science_plus_sasang": sasang_soft,
            "science_plus_myeongni": _soft("science_plus_myeongni", "short_1d"),
            "science_plus_sasang_myeongni": triple_soft,
        },
        "science_plus_sasang_uplift_vs_science_short_1d": btc_uplift,
        "kospi_holdout_uplift_soft_reference": kospi_uplift,
        "uplift_directional_parity_with_kospi": parity,
        "auxiliary_recommendation": "observe_only",
        "note_ko": (
            "BTC holdout는 KOSPI attach 게이트에 영향 없음. "
            "방향 uplift 부호만 KOSPI와 대조."
        ),
    }


def _slim_instrument_parity(
    holdout_summary: dict[str, Any] | None,
    extended_audits: dict[str, Any] | None,
    humanist_combo_holdout: dict[str, Any] | None = None,
) -> dict[str, Any]:
    holdout_summary = holdout_summary or {}
    long_cmp = (extended_audits or {}).get("long_window_lane_compare") or {}
    kospi_bundle = ((long_cmp.get("kospi") or {}).get("eras") or {}).get("bundle_window_market_sasang") or {}
    btc_bundle = ((long_cmp.get("btc") or {}).get("eras") or {}).get("bundle_window_market_sasang") or {}
    humanist_combo_holdout = humanist_combo_holdout or {}
    return {
        "kospi": {
            "holdout_uplift_soft": holdout_summary.get("kospi_holdout_uplift_soft"),
            "attach_recommended": holdout_summary.get("always_attach_recommended"),
            "bundle_market_sasang_combo_soft": kospi_bundle.get("science_plus_sasang_soft"),
            "bundle_market_myeongni_combo_soft": kospi_bundle.get("science_plus_myeongni_soft"),
            "holdout_science_plus_myeongni_short_1d_soft": (
                (humanist_combo_holdout.get("short_1d_soft") or {}).get("science_plus_myeongni")
            ),
            "holdout_triple_combo_short_1d_soft": (
                (humanist_combo_holdout.get("short_1d_soft") or {}).get("science_plus_sasang_myeongni")
            ),
            "bundle_triple_combo_soft": kospi_bundle.get("science_plus_sasang_myeongni_soft"),
        },
        "btc": {
            "holdout_science_best_horizon": holdout_summary.get("btc_holdout_science_best"),
            "bundle_market_sasang_combo_soft": btc_bundle.get("science_plus_sasang_soft"),
            "bundle_market_myeongni_combo_soft": btc_bundle.get("science_plus_myeongni_soft"),
            "bundle_triple_combo_soft": btc_bundle.get("science_plus_sasang_myeongni_soft"),
            "note_ko": "BTC는 KOSPI holdout attach 게이트의 보조 관측. Track A·실매매 승격 근거 아님.",
        },
    }


def _era_split_news_policy(kospi_jsonl: Path) -> dict[str, Any]:
    cov = _audit_news_coverage_from_science_jsonl(kospi_jsonl)
    share = cov.get("causal_exa_share")
    return {
        "pre_exa_era_end": "2019-12-31",
        "exa_era_start": "2020-01-01",
        "full_history_causal_exa_share": share,
        "sparse_pre_exa_exa_expected": True,
        "recommended_science_news_mode_by_era": {
            "pre_exa_era": "news_zero_renorm_or_global_snapshot",
            "exa_era": "causal_exa_news_window_when_available",
        },
        "policy_ko": (
            "1997-2019 stored EXA 뉴스 없음 — long-window pre_exa는 price+macro·news_off 정책. "
            "2020+ EXA backfill·bundle window는 causal 우선. Track A 승격 아님."
        ),
    }


def _slim_slice_eval(doc: dict[str, Any]) -> dict[str, Any]:
    holdout = ((doc.get("slices") or {}).get("by_coverage") or {}).get("holdout_2026_h1")
    if not holdout:
        holdout = {
            "n_days": doc.get("n_eval_days"),
            "lenses": (doc.get("slices") or {}).get("by_coverage", {}).get("all", {}).get("lenses"),
            "best_lens_id": doc.get("headline", {}).get("all_history_best_lens"),
        }
    lenses = holdout.get("lenses") or {}
    combo = lenses.get("science_plus_sasang") or {}
    myeongni = lenses.get("science_plus_myeongni") or {}
    science = lenses.get("science_core") or {}
    macro = lenses.get("macro_only") or {}
    return {
        "n_days": holdout.get("n_days"),
        "best_lens_id": holdout.get("best_lens_id"),
        "science_plus_sasang_soft_hit_short_1d": combo.get("soft_hit_rate"),
        "science_plus_myeongni_soft_hit_short_1d": myeongni.get("soft_hit_rate"),
        "science_core_soft_hit_short_1d": science.get("soft_hit_rate"),
        "macro_only_soft_hit_short_1d": macro.get("soft_hit_rate"),
    }


def _slim_macro_bias_audit(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "n_eval_days": doc.get("n_eval_days"),
        "bias_flags": doc.get("bias_flags") or [],
        "observed_hit_rates": doc.get("observed_hit_rates"),
        "shuffle_null": doc.get("shuffle_null"),
        "trailing21_agreement": doc.get("trailing21_agreement"),
        "verdict_ko": doc.get("verdict_ko"),
    }


def _slim_humanist_ab(doc: dict[str, Any]) -> dict[str, Any]:
    arms = doc.get("arms") or {}
    return {
        "windows": doc.get("windows"),
        "calendar_stub": arms.get("calendar_stub"),
        "market_sasang_v2": arms.get("market_sasang_v2"),
        "delta_market_sasang_minus_stub": doc.get("delta_market_sasang_minus_stub"),
    }


def _run_extended_audits(
    *,
    date_from: str,
    date_to: str,
    macro_long_from: str,
    neutral_bps: float,
    kospi_jsonl: Path,
    myeongni_jsonl: Path,
    logos_lens: Path,
    run_humanist_ab: bool,
    run_news_weight_ablation: bool,
    run_long_window_lane_compare: bool,
    run_triple_blend_weight_sweep: bool,
    run_pnl_bootstrap: bool,
    sasang_jsonl: Path,
    shuffle_trials: int,
    include_macro_long_history: bool = True,
) -> dict[str, Any]:
    from scripts.run_science_core_macro_gate_bias_audit_v1 import run_audit as run_macro_bias_audit
    from scripts.run_science_core_long_history_slice_eval_v1 import run_slice_eval

    macro_bundle = run_macro_bias_audit(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        shuffle_trials=shuffle_trials,
        seed=42,
    )
    macro_long: dict[str, Any] | None = None
    if include_macro_long_history:
        macro_long = run_macro_bias_audit(
            csv_path=v1.KOSPI_CSV,
            science_jsonl=kospi_jsonl,
            date_from=macro_long_from,
            date_to=date_to,
            neutral_bps=neutral_bps,
            shuffle_trials=min(30, shuffle_trials),
            seed=42,
        )
    macro_2026 = run_macro_bias_audit(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from="2026-01-01",
        date_to=date_to,
        neutral_bps=neutral_bps,
        shuffle_trials=min(50, shuffle_trials),
        seed=42,
    )
    slice_market = run_slice_eval(
        instrument="kospi",
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=DEFAULT_MARKET_SASANG_JSONL,
        logos_lens=logos_lens,
    )
    slice_stub = run_slice_eval(
        instrument="kospi",
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=DEFAULT_SASANG_JSONL,
        logos_lens=logos_lens,
    )
    slim_market = _slim_slice_eval(slice_market)
    slim_stub = _slim_slice_eval(slice_stub)
    m_soft = slim_market.get("science_plus_sasang_soft_hit_short_1d")
    s_soft = slim_stub.get("science_plus_sasang_soft_hit_short_1d")
    humanist_ab: dict[str, Any] | None = None
    if run_humanist_ab:
        from scripts.run_science_core_humanist_source_ab_v1 import run_ab

        humanist_ab = _slim_humanist_ab(
            run_ab(
                date_from=date_from,
                date_to=date_to,
                train_to="2026-04-30",
                holdout_from="2026-05-01",
                holdout_to=date_to,
                sidecar_path=DEFAULT_SIDECAR if DEFAULT_SIDECAR.is_file() else None,
                market_sasang_jsonl=DEFAULT_MARKET_SASANG_JSONL,
                myeongni_per_date_jsonl=DEFAULT_MYEONGNI_PER_DATE_JSONL,
                rebuild_science=False,
            )
        )
    return {
        "macro_gate_bias_bundle_window": _slim_macro_bias_audit(macro_bundle),
        "macro_gate_bias_full_window": _slim_macro_bias_audit(macro_bundle),
        "macro_gate_bias_long_history": _slim_macro_bias_audit(macro_long) if macro_long else None,
        "macro_gate_bias_2026_h1": _slim_macro_bias_audit(macro_2026),
        "holdout_slice_ab": {
            "market_sasang_per_date": slim_market,
            "calendar_stub": slim_stub,
            "delta_science_plus_sasang_soft": (
                round(float(m_soft) - float(s_soft), 4) if m_soft is not None and s_soft is not None else None
            ),
            "note_ko": "calendar stub sasang은 science+sasang 적중을 깎음. composite는 market_sasang 필수.",
        },
        "humanist_source_ab": humanist_ab,
        "news_coverage": _audit_news_coverage_from_science_jsonl(kospi_jsonl),
        "era_split_news_policy": _era_split_news_policy(kospi_jsonl),
        "news_coverage_simulated": _simulated_news_coverage_audit(
            kospi_jsonl=kospi_jsonl,
            date_from=date_from,
            date_to=date_to,
        ),
        "news_weight_ablation": _maybe_news_weight_ablation(
            date_from=date_from,
            date_to=date_to,
            sasang_jsonl=DEFAULT_MARKET_SASANG_JSONL,
            myeongni_jsonl=myeongni_jsonl,
            run=run_news_weight_ablation,
        ),
        "long_window_lane_compare": _maybe_long_window_lane_compare(
            date_to=date_to,
            bundle_from=date_from,
            bundle_to=date_to,
            run=run_long_window_lane_compare,
        ),
        "triple_blend_weight_sweep": _maybe_triple_blend_weight_sweep(
            date_from=date_from,
            date_to=date_to,
            train_to="2026-04-30",
            holdout_from="2026-05-01",
            holdout_to=date_to,
            science_jsonl=kospi_jsonl,
            sasang_jsonl=sasang_jsonl,
            myeongni_jsonl=myeongni_jsonl,
            run=run_triple_blend_weight_sweep,
        ),
        "pnl_bootstrap_holdout": _maybe_pnl_bootstrap(
            science_jsonl=kospi_jsonl,
            sasang_jsonl=sasang_jsonl,
            myeongni_jsonl=myeongni_jsonl,
            holdout_from="2026-05-01",
            holdout_to=date_to,
            run=run_pnl_bootstrap,
        ),
    }


def _maybe_long_window_lane_compare(
    *,
    date_to: str,
    bundle_from: str,
    bundle_to: str,
    run: bool,
) -> dict[str, Any] | None:
    if not run:
        return None
    from scripts.run_science_core_long_window_lane_compare_v1 import (
        run_compare,
        slim_eras_from_compare_doc,
    )

    kospi_full = run_compare(
        instrument="kospi",
        science_jsonl=DEFAULT_SCIENCE_JSONL_KOSPI,
        date_to=date_to,
        bundle_from=bundle_from,
        bundle_to=bundle_to,
        neutral_bps=5.0,
    )
    btc_full = run_compare(
        instrument="btc",
        science_jsonl=DEFAULT_SCIENCE_JSONL_BTC,
        date_to=date_to,
        bundle_from=bundle_from,
        bundle_to=bundle_to,
        neutral_bps=5.0,
    )
    return {
        "kospi": {"eras": slim_eras_from_compare_doc(kospi_full), "verdict_ko": kospi_full.get("verdict_ko")},
        "btc": {"eras": slim_eras_from_compare_doc(btc_full), "verdict_ko": btc_full.get("verdict_ko")},
        "verdict_ko": kospi_full.get("verdict_ko"),
    }


def _slim_triple_blend_sweep(doc: dict[str, Any]) -> dict[str, Any]:
    best = doc.get("best_holdout_triple") or {}
    return {
        "best_holdout_profile": best.get("profile_id"),
        "best_holdout_triple_soft": best.get("holdout_triple_soft"),
        "holdout_sasang_combo_reference_soft": doc.get("holdout_sasang_combo_reference_soft"),
        "any_triple_beats_sasang_combo_on_holdout": doc.get("any_triple_beats_sasang_combo_on_holdout"),
        "ranked_holdout_top3": (doc.get("ranked_holdout_by_triple_soft") or [])[:3],
    }


def _slim_pnl_bootstrap(doc: dict[str, Any]) -> dict[str, Any]:
    sasang = (doc.get("strategies") or {}).get("science_plus_sasang") or {}
    return {
        "window": doc.get("window"),
        "bootstrap_trials": doc.get("bootstrap_trials"),
        "science_plus_sasang_total_return": sasang.get("total_return"),
        "science_plus_sasang_ci_95": sasang.get("ci_95"),
        "sasang_combo_ci_excludes_zero": doc.get("sasang_combo_ci_excludes_zero"),
        "economic_edge_claim_allowed": doc.get("economic_edge_claim_allowed"),
        "delta_vs_science_science_plus_sasang": (doc.get("delta_vs_science") or {}).get("science_plus_sasang"),
    }


def _maybe_triple_blend_weight_sweep(
    *,
    date_from: str,
    date_to: str,
    train_to: str,
    holdout_from: str,
    holdout_to: str,
    science_jsonl: Path,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    run: bool,
) -> dict[str, Any] | None:
    if not run:
        return None
    from scripts.run_science_core_triple_blend_weight_sweep_v1 import run_sweep

    full = run_sweep(
        science_jsonl=science_jsonl,
        sasang_jsonl=sasang_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        date_from=date_from,
        date_to=date_to,
        train_to=train_to,
        holdout_from=holdout_from,
        holdout_to=holdout_to,
        neutral_bps=5.0,
    )
    return _slim_triple_blend_sweep(full)


def _maybe_pnl_bootstrap(
    *,
    science_jsonl: Path,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    holdout_from: str,
    holdout_to: str,
    run: bool,
) -> dict[str, Any] | None:
    if not run:
        return None
    from scripts.run_science_core_pnl_bootstrap_v1 import run_bootstrap

    full = run_bootstrap(
        science_jsonl=science_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        holdout_from=holdout_from,
        holdout_to=holdout_to,
        fee_bps=5.0,
        neutral_bps=5.0,
        trials=2000,
        seed=42,
    )
    return _slim_pnl_bootstrap(full)


def _maybe_news_weight_ablation(
    *,
    date_from: str,
    date_to: str,
    sasang_jsonl: Path,
    myeongni_jsonl: Path,
    run: bool,
) -> dict[str, Any] | None:
    if not run:
        return None
    from scripts.run_science_core_news_weight_ablation_v1 import run_ablation

    full = run_ablation(
        science_jsonl=DEFAULT_SCIENCE_JSONL_KOSPI,
        sasang_jsonl=sasang_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        date_from=date_from,
        date_to=date_to,
        train_to="2026-04-30",
        holdout_from="2026-05-01",
        holdout_to=date_to,
        neutral_bps=5.0,
    )
    ranked = full.get("holdout_ranking_science_plus_sasang") or []
    baseline = (full.get("profiles") or {}).get("baseline_default", {}).get("holdout", {})
    return {
        "best_holdout_profile": full.get("best_holdout_profile"),
        "baseline_holdout_science_plus_sasang_soft": (
            baseline.get("science_plus_sasang_short_1d") or {}
        ).get("soft_hit_rate"),
        "holdout_ranking_top3": ranked[:3],
        "news_zero_holdout_delta_vs_baseline": next(
            (
                r.get("delta_vs_baseline_soft")
                for r in ranked
                if r.get("profile_id") == "news_zero_renorm"
            ),
            None,
        ),
        "science_plus_sasang_news_off": full.get("science_plus_sasang_news_off"),
    }


def _simulated_news_coverage_audit(
    *,
    kospi_jsonl: Path,
    date_from: str,
    date_to: str,
) -> dict[str, Any]:
    from scripts.run_science_core_news_coverage_audit_v1 import run_audit

    full = run_audit(
        science_jsonl=kospi_jsonl,
        exa_jsonl=ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl",
        date_from=date_from,
        date_to=date_to,
    )
    return {
        "n_science_rows": full.get("n_science_rows"),
        "exa_unique_published_days": full.get("exa_unique_published_days"),
        "causal_exa_share_stored": full.get("causal_exa_share_stored"),
        "causal_exa_share_simulated": full.get("causal_exa_share_simulated"),
        "sparse_causal_coverage": full.get("sparse_causal_coverage"),
        "simulated_news_modes": full.get("simulated_news_modes"),
    }


def _macro_audit_from_daily(daily: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    macro_dirs = [str((r.get("predictions") or {}).get("macro_only") or "missing") for r in daily]
    counts = Counter(macro_dirs)
    n = len(daily)
    dominant = counts.most_common(1)[0] if counts else ("missing", 0)
    return {
        "n_days": n,
        "direction_counts": dict(counts),
        "dominant_direction": dominant[0],
        "dominant_share": round(dominant[1] / n, 4) if n else None,
        "sticky_regime_suspect": bool(n and dominant[1] / n >= 0.85 and dominant[0] in {"bear", "bull"}),
    }


LONG_WF_PATH = ROOT / "reports/science_core_long_walkforward_v1_latest.json"


def _slim_long_walkforward() -> dict[str, Any] | None:
    if not LONG_WF_PATH.is_file():
        return None
    try:
        doc = json.loads(LONG_WF_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    profiles_out: list[dict[str, Any]] = []
    for prof in doc.get("profiles") or []:
        if not isinstance(prof, dict):
            continue
        arms_in = prof.get("arms") or {}
        arms_out: dict[str, Any] = {}
        for key, arm in arms_in.items():
            if not isinstance(arm, dict):
                continue
            arms_out[key] = {
                "n_folds": arm.get("n_folds"),
                "selection_top1_hit_rate": arm.get("selection_top1_hit_rate"),
                "mean_test_uplift_vs_science_alone": arm.get("mean_test_uplift_vs_science_alone"),
            }
        profiles_out.append(
            {
                "profile_id": prof.get("profile_id"),
                "delta_full_minus_stub": prof.get("delta_full_minus_stub"),
                "arms": arms_out,
            }
        )
    return {
        "artifact": str(LONG_WF_PATH.relative_to(ROOT)).replace("\\", "/"),
        "aggregate_window": doc.get("aggregate_window"),
        "profiles": profiles_out,
        "note_ko": doc.get("interpretation_ko"),
    }


def _composite_attach(
    holdout_attach: dict[str, Any],
    walkforward_summary: dict[str, Any],
    *,
    humanist_stub: dict[str, Any] | None = None,
    macro_bias: dict[str, Any] | None = None,
    holdout_slice_ab: dict[str, Any] | None = None,
) -> dict[str, Any]:
    holdout_ok = bool(holdout_attach.get("always_attach_recommended"))
    wf_top1 = walkforward_summary.get("selection_top1_hit_rate")
    wf_uplift = walkforward_summary.get("mean_test_uplift_vs_science_alone")
    wf_blockers: list[str] = []
    if wf_top1 is None or float(wf_top1) < MIN_WF_TOP1:
        wf_blockers.append(f"walkforward_top1<{MIN_WF_TOP1}")
    if wf_uplift is None or float(wf_uplift) < MIN_WF_UPLIFT:
        wf_blockers.append(f"walkforward_uplift<{MIN_WF_UPLIFT}")
    stub_blockers: list[str] = []
    if humanist_stub and humanist_stub.get("any_stub"):
        stub_blockers.append("humanist_calendar_stub_input")
    if humanist_stub and humanist_stub.get("underlying_stub_caution"):
        stub_blockers.append("humanist_sidecar_underlying_calendar_stub")
    macro_blockers: list[str] = []
    bias_flags = (macro_bias or {}).get("bias_flags") or []
    if "macro21_hit_above_shuffle_margin" in bias_flags:
        macro_blockers.append("macro_only_in_sample_bias_suspect")
    if "low_macro_score_entropy" in bias_flags:
        macro_blockers.append("macro_gate_low_entropy_binary")
    slice_delta = (holdout_slice_ab or {}).get("delta_science_plus_sasang_soft")
    if slice_delta is not None and float(slice_delta) >= 0.20 and humanist_stub and humanist_stub.get("any_stub"):
        stub_blockers.append("holdout_slice_stub_depresses_science_plus_sasang")
    recommended = holdout_attach.get("recommended_combo_lens_id")
    if recommended == "macro_only" or "macro_only" in str(recommended or ""):
        recommended = "science_plus_sasang"
        macro_blockers.append("macro_only_not_recommended_lane")
    composite = holdout_ok and not wf_blockers and not stub_blockers
    return {
        "composite_attach_recommended": composite,
        "holdout_attach_recommended": holdout_ok,
        "walkforward_blockers": wf_blockers,
        "stub_blockers": stub_blockers,
        "macro_blockers": macro_blockers,
        "humanist_input_audit": humanist_stub,
        "recommended_lane": recommended if composite else "science_core_only",
        "holdout_slice_delta_market_minus_stub_soft": slice_delta,
        "note": "Composite requires holdout attach + walk-forward stability + non-stub humanist inputs. Not Track A promotion.",
    }


def run_bundle(
    *,
    date_from: str,
    date_to: str,
    neutral_bps: float,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_lens: Path,
    logos_jsonl: Path | None,
    rebuild_science: bool,
    export_sidecar_humanist: bool = False,
    sidecar_json: Path = DEFAULT_SIDECAR,
    include_extended_audits: bool = True,
    run_humanist_ab: bool = False,
    run_news_weight_ablation: bool = False,
    run_long_window_lane_compare: bool = False,
    run_triple_blend_weight_sweep: bool = False,
    run_pnl_bootstrap: bool = False,
    macro_shuffle_trials: int = 100,
    macro_long_from: str = DEFAULT_MACRO_LONG_FROM,
    include_macro_long_history: bool = True,
) -> dict[str, Any]:
    if export_sidecar_humanist:
        sidecar_doc = export_humanist_jsonl_from_sidecar(sidecar_path=sidecar_json, instrument="kospi")
        _write_jsonl(sidecar_doc["myeongni_rows"], SIDECAR_MYEONGNI_OUT)
        _write_jsonl(sidecar_doc["sasang_rows"], SIDECAR_SASANG_OUT)
        myeongni_jsonl = SIDECAR_MYEONGNI_OUT
        sasang_jsonl = SIDECAR_SASANG_OUT
    kospi_jsonl = DEFAULT_SCIENCE_JSONL_KOSPI
    btc_jsonl = DEFAULT_SCIENCE_JSONL_BTC
    science_date_from = date_from
    if include_extended_audits and include_macro_long_history:
        science_date_from = min(date_from, macro_long_from)
    if run_long_window_lane_compare:
        science_date_from = min(science_date_from, macro_long_from)
    btc_science_from = date_from
    if run_long_window_lane_compare:
        btc_science_from = min(btc_science_from, DEFAULT_BTC_LONG_FROM)
    if rebuild_science or _science_jsonl_needs_rebuild(kospi_jsonl, science_date_from, date_to):
        _ensure_science_jsonl(
            instrument="kospi",
            csv_path=v1.KOSPI_CSV,
            out_path=kospi_jsonl,
            date_from=science_date_from,
            date_to=date_to,
            apply_overnight=True,
        )
    if rebuild_science or _science_jsonl_needs_rebuild(btc_jsonl, btc_science_from, date_to):
        _ensure_science_jsonl(
            instrument="btc",
            csv_path=v1.BTC_CSV,
            out_path=btc_jsonl,
            date_from=date_from,
            date_to=date_to,
            apply_overnight=False,
        )

    common = dict(
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=5,
    )

    kospi_horizon = run_eval(
        instrument="kospi",
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=date_from,
        date_to=date_to,
        **common,
    )
    btc_horizon = run_eval(
        instrument="btc",
        csv_path=v1.BTC_CSV,
        science_jsonl=btc_jsonl,
        date_from=date_from,
        date_to=date_to,
        **common,
    )
    holdout = run_holdout_bundle(
        train_from=date_from,
        train_to="2026-04-30",
        holdout_from="2026-05-01",
        holdout_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=logos_jsonl,
        rebuild_science=False,
    )
    walkforward = run_walkforward(
        kospi_csv=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        train_days=40,
        test_days=15,
        step_days=12,
        max_window_days=None,
        date_from=date_from,
        date_to=date_to,
        **common,
    )
    shock = build_shock_report(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from="2026-05-01",
        date_to=date_to,
        shock_move_bps=100.0,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=logos_lens,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=5,
        neutral_bps=neutral_bps,
    )
    full_daily = build_daily_short_rows(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=kospi_jsonl,
        date_from=date_from,
        date_to=date_to,
        **common,
    )
    macro_full_audit = _macro_audit_from_daily(full_daily)
    extended_audits: dict[str, Any] | None = None
    if include_extended_audits:
        extended_audits = _run_extended_audits(
            date_from=date_from,
            date_to=date_to,
            macro_long_from=macro_long_from,
            neutral_bps=neutral_bps,
            kospi_jsonl=kospi_jsonl,
            myeongni_jsonl=myeongni_jsonl,
            logos_lens=logos_lens,
            run_humanist_ab=run_humanist_ab,
            run_news_weight_ablation=run_news_weight_ablation,
            run_long_window_lane_compare=run_long_window_lane_compare,
            run_triple_blend_weight_sweep=run_triple_blend_weight_sweep,
            run_pnl_bootstrap=run_pnl_bootstrap,
            sasang_jsonl=sasang_jsonl,
            shuffle_trials=macro_shuffle_trials,
            include_macro_long_history=include_macro_long_history,
        )

    attach = holdout["kospi"]["attach_recommendation"]
    stub_audit = _humanist_inputs_are_calendar_stub(myeongni_jsonl, sasang_jsonl)
    ext = extended_audits or {}
    macro_bias_slim = ext.get("macro_gate_bias_long_history") or ext.get("macro_gate_bias_bundle_window")
    slice_ab = (extended_audits or {}).get("holdout_slice_ab")
    composite = _composite_attach(
        attach,
        walkforward.get("summary") or {},
        humanist_stub=stub_audit,
        macro_bias=macro_bias_slim,
        holdout_slice_ab=slice_ab,
    )

    promo_reason = (
        "composite attach gate 통과 (research_only; Track A 아님)."
        if composite["composite_attach_recommended"]
        else "holdout/walk-forward/stub blockers로 composite attach 비권고."
    )
    humanist_combo_holdout = _humanist_combo_holdout_compare(
        (holdout.get("kospi") or {}).get("horizon_holdout")
    )
    btc_holdout_auxiliary = _btc_holdout_auxiliary_gate(
        (holdout.get("btc") or {}).get("horizon_holdout"),
        holdout.get("summary"),
    )

    return {
        "schema": "science_core_governance_bundle_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "window": {"from": date_from, "to": date_to},
        "artifact_paths": {
            "kospi_science_jsonl": str(kospi_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "btc_science_jsonl": str(btc_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "myeongni_jsonl": str(myeongni_jsonl.relative_to(ROOT)).replace("\\", "/"),
            "sasang_jsonl": str(sasang_jsonl.relative_to(ROOT)).replace("\\", "/"),
        },
        "logos_input": {
            "mode": "per_date_macro_gate" if logos_jsonl else "global_snapshot",
            "logos_jsonl": str(logos_jsonl.relative_to(ROOT)).replace("\\", "/") if logos_jsonl else None,
            "logos_lens": str(logos_lens.relative_to(ROOT)).replace("\\", "/"),
            "non_gating": True,
        },
        "horizon_eval": {
            "kospi": {
                "n_eval_dates": kospi_horizon.get("n_eval_dates"),
                "science_core_summary": kospi_horizon.get("science_core_summary"),
                "top_combo_short_1d": (kospi_horizon.get("combo_ranking_short_1d") or [{}])[0].get("lens_id"),
            },
            "btc": {
                "n_eval_dates": btc_horizon.get("n_eval_dates"),
                "science_core_summary": btc_horizon.get("science_core_summary"),
            },
        },
        "holdout": holdout.get("summary"),
        "humanist_combo_holdout": humanist_combo_holdout,
        "btc_holdout_auxiliary": btc_holdout_auxiliary,
        "pnl_economic_significance": _slim_pnl_economic_significance(holdout.get("kospi")),
        "triple_blend_weight_sweep": (extended_audits or {}).get("triple_blend_weight_sweep"),
        "pnl_bootstrap_holdout": (extended_audits or {}).get("pnl_bootstrap_holdout"),
        "instrument_parity_summary": _slim_instrument_parity(
            holdout.get("summary"),
            extended_audits,
            humanist_combo_holdout,
        ),
        "walkforward": walkforward.get("summary"),
        "long_walkforward": _slim_long_walkforward(),
        "shock_discordant": {
            "n_calendar_days": shock.get("n_calendar_days"),
            "n_shock_move_days": shock.get("n_shock_move_days"),
            "short_1d_soft_rates": shock.get("short_1d_soft_rates"),
            "macro_only_diversity_audit": shock.get("macro_only_diversity_audit"),
        },
        "shock_only_attach_policy": _load_or_run_shock_only_attach_policy(
            date_to=date_to,
            science_jsonl=kospi_jsonl,
            myeongni_jsonl=myeongni_jsonl,
            sasang_jsonl=sasang_jsonl,
            logos_jsonl=logos_jsonl,
            neutral_bps=neutral_bps,
        ),
        "macro_only_full_window_audit": macro_full_audit,
        "extended_audits": extended_audits,
        "attach_recommendation": attach,
        "composite_attach": composite,
        "promotion_gate": {
            "track_a_ready": False,
            "live_trading_ready": False,
            "research_lane_status": "observe_only",
            "reason_ko": promo_reason,
        },
        "methodology_ko": (
            "Science Core governance bundle — 정량 레인 + 조합 uplift 관측. "
            "Absolute Balance(조율 state)와 분리. Track A·실매매 승격 근거 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", type=str, default=DEFAULT_FROM)
    ap.add_argument("--date-to", type=str, default=DEFAULT_TO)
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument(
        "--export-sidecar-humanist",
        action="store_true",
        help="Export myeongni/sasang JSONL from insight sidecar dated snapshots before eval.",
    )
    ap.add_argument(
        "--use-market-sasang-per-date",
        action="store_true",
        help="Use market_psych v2 per-date sasang JSONL instead of calendar stub.",
    )
    ap.add_argument(
        "--use-manseryeok-myeongni-per-date",
        action="store_true",
        help="Use manseryeok session per-date myeongni JSONL instead of calendar stub.",
    )
    ap.add_argument(
        "--use-logos-per-date-macro-gate",
        action="store_true",
        help="Use per-date Logos macro gate JSONL ([NON_GATING] advisory blend).",
    )
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--myeongni-jsonl", type=Path, default=None)
    ap.add_argument("--sasang-jsonl", type=Path, default=None)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--skip-extended-audits", action="store_true")
    ap.add_argument("--skip-macro-long-history", action="store_true")
    ap.add_argument("--macro-long-from", default=DEFAULT_MACRO_LONG_FROM)
    ap.add_argument("--run-humanist-ab", action="store_true")
    ap.add_argument("--run-news-weight-ablation", action="store_true")
    ap.add_argument("--run-long-window-lane-compare", action="store_true")
    ap.add_argument("--run-triple-blend-weight-sweep", action="store_true")
    ap.add_argument("--run-pnl-bootstrap", action="store_true")
    ap.add_argument("--macro-shuffle-trials", type=int, default=100)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    sasang_jsonl = args.sasang_jsonl
    if sasang_jsonl is None:
        if args.use_market_sasang_per_date or DEFAULT_MARKET_SASANG_JSONL.exists():
            sasang_jsonl = DEFAULT_MARKET_SASANG_JSONL
        else:
            sasang_jsonl = DEFAULT_SASANG_JSONL

    myeongni_jsonl = args.myeongni_jsonl
    if myeongni_jsonl is None:
        if args.use_manseryeok_myeongni_per_date or DEFAULT_MYEONGNI_PER_DATE_JSONL.is_file():
            myeongni_jsonl = DEFAULT_MYEONGNI_PER_DATE_JSONL
        else:
            myeongni_jsonl = DEFAULT_MYEONGNI_JSONL

    logos_jsonl = DEFAULT_LOGOS_PER_DATE_JSONL if args.use_logos_per_date_macro_gate else None

    doc = run_bundle(
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=args.logos_lens,
        logos_jsonl=logos_jsonl,
        rebuild_science=args.rebuild_science,
        export_sidecar_humanist=bool(args.export_sidecar_humanist),
        sidecar_json=args.sidecar_json,
        include_extended_audits=not bool(args.skip_extended_audits),
        run_humanist_ab=bool(args.run_humanist_ab),
        run_news_weight_ablation=bool(args.run_news_weight_ablation),
        run_long_window_lane_compare=bool(args.run_long_window_lane_compare),
        run_triple_blend_weight_sweep=bool(args.run_triple_blend_weight_sweep),
        run_pnl_bootstrap=bool(args.run_pnl_bootstrap),
        macro_shuffle_trials=max(20, int(args.macro_shuffle_trials)),
        macro_long_from=str(args.macro_long_from),
        include_macro_long_history=not bool(args.skip_macro_long_history),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    try:
        from scripts.run_science_core_kospi_shock_only_attach_backtest_v1 import main as shock_only_main

        shock_only_main(["--date-to", args.date_to])
    except Exception as exc:  # noqa: BLE001 — governance bundle must still succeed
        print(f"WARN: shock-only attach backtest skipped: {exc}", file=sys.stderr)

    try:
        from scripts.run_science_core_conditional_attach_research_v1 import main as cond_research_main

        cond_research_main(
            [
                "--governance-json",
                str(args.artifact_output),
            ]
        )
    except Exception as exc:  # noqa: BLE001 — governance bundle must still succeed
        print(f"WARN: conditional attach research skipped: {exc}", file=sys.stderr)

    try:
        from scripts.run_science_core_prophecy_combo_sensitivity_v1 import main as prophecy_sens_main

        prophecy_sens_main(["--governance-json", str(args.artifact_output)])
    except Exception as exc:  # noqa: BLE001 — governance bundle must still succeed
        print(f"WARN: prophecy combo sensitivity skipped: {exc}", file=sys.stderr)

    try:
        from scripts.build_science_core_instrument_matrix_v1 import main as build_matrix_main

        cond_art = ROOT / "docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json"
        sens_art = ROOT / "docs/final/artifacts/science_core_prophecy_combo_sensitivity_v1_latest.json"
        matrix_argv = [
            "--governance-json",
            str(args.artifact_output),
        ]
        if cond_art.is_file():
            matrix_argv.extend(["--conditional-research-json", str(cond_art)])
        if sens_art.is_file():
            matrix_argv.extend(["--prophecy-sensitivity-json", str(sens_art)])
        build_matrix_main(matrix_argv)
    except Exception as exc:  # noqa: BLE001 — governance bundle must still succeed
        print(f"WARN: instrument matrix build skipped: {exc}", file=sys.stderr)

    c = doc["composite_attach"]
    print(
        f"WROTE: {args.output.resolve()} composite_attach={c.get('composite_attach_recommended')} "
        f"lane={c.get('recommended_lane')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
