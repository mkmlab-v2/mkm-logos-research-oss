#!/usr/bin/env python3
"""Backtest lens-combination strategies on BTC panel rows.

Research-only evaluator comparing:
- single lens (logos/myeongni/sasang)
- 2-lens combinations
- 3-lens combination
- 3-lens + coordinator tie-break

Logos (성경) default: ``--logos-vote-mode omit`` — Logos does not vote in directional
majority (NON_GATING-aligned). Use ``global`` only for explicit Logos vote A/B studies.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

DEFAULT_SCORE_JSON = ART / "btrack_prophecy_score_pre_causal_active_latest.json"
DEFAULT_SIDECAR_JSON = ART / "btrack_prophecy_score_insight_sidecar_v1_latest.json"
DEFAULT_BTC_CSV = ROOT / "research" / "market_data" / "btc_daily_external_yf.csv"
DEFAULT_OUT = ART / "prophecy_lens_combo_backtest_v1_latest.json"

LENS_LOGOS = "logos"
LENS_MYEONGNI = "myeongni"
LENS_SASANG = "sasang"
LENSES = (LENS_LOGOS, LENS_MYEONGNI, LENS_SASANG)
VALID_DIR = {"bull", "bear", "neutral"}

# Ranking tie-break when primary metrics tie (see _rank_strategies).
TIE_BREAK_POLICY_ID = "non_logos_multi_lens_then_lens_count_v1"


def _tie_break_policy_doc() -> dict[str, Any]:
    return {
        "policy_id": TIE_BREAK_POLICY_ID,
        "primary_sort_keys_desc": [
            "metrics.cagr (higher wins)",
            "metrics.sharpe (higher wins)",
            "metrics.mdd (less negative wins)",
        ],
        "tie_break_keys_desc": [
            "prefer strategies with >=2 lenses where logos is NOT included (captures myeongni+sasang vs single-lens ties)",
            "prefer higher lens count when still tied",
        ],
        "implementation_ref": "scripts/run_prophecy_lens_combo_backtest_v1.py:_rank_strategies",
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(v: Any, default: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else default


def _prior_completed_daily_return_by_eval_date(csv_path: Path) -> dict[str, float]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.logos_shadow_eval_lib import load_kospi_yf_rows

    rows = load_kospi_yf_rows(csv_path)
    out: dict[str, float] = {}
    if len(rows) < 3:
        return out
    for i in range(2, len(rows)):
        eval_date = str(rows[i]["date"])[:10]
        try:
            c1 = float(rows[i - 1]["close"])
            c2 = float(rows[i - 2]["close"])
        except (TypeError, ValueError):
            continue
        if c2 == 0.0:
            continue
        out[eval_date] = (c1 - c2) / c2
    return out


def _dir_to_sign(direction: str) -> int:
    d = (direction or "").strip().lower()
    if d == "bull":
        return 1
    if d == "bear":
        return -1
    return 0


def _sign_to_dir(sign: int) -> str:
    if sign > 0:
        return "bull"
    if sign < 0:
        return "bear"
    return "neutral"


def _majority_sign(signs: list[int]) -> int:
    if not signs:
        return 0
    s = sum(signs)
    if s > 0:
        return 1
    if s < 0:
        return -1
    return 0


def _stddev(values: list[float]) -> float:
    n = len(values)
    if n <= 1:
        return 0.0
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return var ** 0.5


def _extract_lens_maps(sidecar: dict[str, Any]) -> tuple[dict[str, int], dict[str, int], int, float]:
    logos_block = (sidecar.get("lens_globals_for_sidecar") or {}).get("logos") or {}
    logos_global = logos_block.get("direction_score")
    logos_sign = 0
    try:
        logos_sign = 1 if float(logos_global) > 0 else (-1 if float(logos_global) < 0 else 0)
    except (TypeError, ValueError):
        logos_sign = 0
    logos_confidence = 0.0
    try:
        logos_confidence = float(logos_block.get("confidence") or 0.0)
    except (TypeError, ValueError):
        logos_confidence = 0.0

    myeongni_by_date: dict[str, int] = {}
    sasang_by_date: dict[str, int] = {}
    features = sidecar.get("per_date_features") or []
    if isinstance(features, list):
        for row in features:
            if not isinstance(row, dict):
                continue
            eval_date = str(row.get("eval_date") or "")[:10]
            if not eval_date:
                continue
            dated = row.get("dated_source_snapshots_asof_eval_date") or {}
            my_snapshot = (((dated.get("myeongni_16_state_jsonl") or {}).get("snapshot")) or {})
            sa_snapshot = (((dated.get("sasang_dynamics_jsonl") or {}).get("snapshot")) or {})
            myeongni_by_date[eval_date] = _dir_to_sign(str(my_snapshot.get("mapping_target") or "neutral"))
            sasang_by_date[eval_date] = _dir_to_sign(str(sa_snapshot.get("mapping_target") or "neutral"))
    return myeongni_by_date, sasang_by_date, logos_sign, logos_confidence


def _build_variants() -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for lens in LENSES:
        variants.append({"id": lens, "lenses": [lens], "use_coordinator": False})
    for a, b in itertools.combinations(LENSES, 2):
        variants.append({"id": f"{a}+{b}", "lenses": [a, b], "use_coordinator": False})
    variants.append({"id": "logos+myeongni+sasang", "lenses": list(LENSES), "use_coordinator": False})
    variants.append({"id": "logos+myeongni+sasang+coordinator", "lenses": list(LENSES), "use_coordinator": True})
    return variants


def _calc_metrics(
    *,
    pnl_series: list[float],
    equity_series: list[float],
    predicted_dirs: list[str],
    actual_dirs: list[str],
    active_mask: list[bool],
    annual_trading_days: int,
) -> dict[str, Any]:
    n_days = len(pnl_series)
    n_active = sum(1 for x in active_mask if x)
    n_hits = 0
    for p, a, active in zip(predicted_dirs, actual_dirs, active_mask):
        if active and p in VALID_DIR and a in VALID_DIR and p == a:
            n_hits += 1
    hit_rate = (n_hits / n_active) if n_active else 0.0

    wins = sum(1 for p, active in zip(pnl_series, active_mask) if active and p > 0)
    win_rate = (wins / n_active) if n_active else 0.0
    total_return = equity_series[-1] - 1.0 if equity_series else 0.0
    avg_daily = (sum(pnl_series) / n_days) if n_days else 0.0
    stdev_daily = _stddev(pnl_series)
    neg = [x for x in pnl_series if x < 0]
    downside_stdev = _stddev(neg) if len(neg) > 1 else 0.0
    sharpe = (avg_daily / stdev_daily) * (annual_trading_days**0.5) if stdev_daily > 0 else 0.0
    sortino = (avg_daily / downside_stdev) * (annual_trading_days**0.5) if downside_stdev > 0 else 0.0

    peak = 1.0
    mdd = 0.0
    for eq in equity_series:
        peak = max(peak, eq)
        dd = 0.0 if peak <= 0 else (eq / peak) - 1.0
        mdd = min(mdd, dd)

    years = (n_days / annual_trading_days) if n_days else 0.0
    cagr = ((equity_series[-1] ** (1.0 / years)) - 1.0) if years > 0 and equity_series[-1] > 0 else 0.0

    return {
        "n_days": n_days,
        "n_active_days": n_active,
        "directional_hit_rate_active": round(hit_rate, 6),
        "win_rate_active": round(win_rate, 6),
        "total_return": round(total_return, 6),
        "cagr": round(cagr, 6),
        "mdd": round(mdd, 6),
        "sharpe": round(sharpe, 6),
        "sortino": round(sortino, 6),
    }


def _simulate_variant(
    *,
    variant: dict[str, Any],
    rows: list[dict[str, Any]],
    btc_prior: dict[str, float],
    myeongni_map: dict[str, int],
    sasang_map: dict[str, int],
    logos_sign: int,
    logos_confidence: float,
    logos_vote_mode: str,
    logos_min_confidence: float,
    fee_rate: float,
    deadzone: float,
    annual_trading_days: int,
) -> dict[str, Any]:
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
        if actual_dir not in VALID_DIR:
            actual_dir = "neutral"

        lens_signs: list[int] = []
        for lens in variant["lenses"]:
            if lens == LENS_LOGOS:
                if logos_vote_mode == "omit":
                    continue
                if logos_vote_mode == "confidence_gated" and logos_confidence < logos_min_confidence:
                    continue
                lens_signs.append(logos_sign)
            elif lens == LENS_MYEONGNI:
                lens_signs.append(int(myeongni_map.get(eval_date, 0)))
            elif lens == LENS_SASANG:
                lens_signs.append(int(sasang_map.get(eval_date, 0)))
        pos = _majority_sign(lens_signs)

        # NON_GATING omit: lens abstain (pos==0) must not be overridden by BTC prior tie-break.
        if variant["use_coordinator"] and pos == 0 and logos_vote_mode != "omit":
            prior_ret = _safe_float(btc_prior.get(eval_date), 0.0)
            if prior_ret > deadzone:
                pos = 1
            elif prior_ret < -deadzone:
                pos = -1

        turnover = abs(pos - prev_pos)
        fee = turnover * fee_rate
        pnl = (pos * daily_ret) - fee
        equity *= (1.0 + pnl)
        prev_pos = pos

        pred_dirs.append(_sign_to_dir(pos))
        actual_dirs.append(actual_dir)
        active_mask.append(pos != 0)
        pnl_series.append(pnl)
        equity_curve.append(equity)

    metrics = _calc_metrics(
        pnl_series=pnl_series,
        equity_series=equity_curve,
        predicted_dirs=pred_dirs,
        actual_dirs=actual_dirs,
        active_mask=active_mask,
        annual_trading_days=annual_trading_days,
    )
    return {
        "strategy_id": variant["id"],
        "lenses": variant["lenses"],
        "use_coordinator": bool(variant["use_coordinator"]),
        "metrics": metrics,
    }


def _rank_strategies(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _is_non_logos_multi_lens(strategy: dict[str, Any]) -> int:
        lenses = strategy.get("lenses") or []
        if not isinstance(lenses, list):
            return 0
        lens_set = {str(x).strip().lower() for x in lenses}
        # Tie-break preference: preserve "cross-lens blend" intent without
        # forcing weaker logos paths when core performance is tied.
        return 1 if len(lens_set) >= 2 and LENS_LOGOS not in lens_set else 0

    def _lens_count(strategy: dict[str, Any]) -> int:
        lenses = strategy.get("lenses") or []
        return len(lenses) if isinstance(lenses, list) else 0

    return sorted(
        items,
        key=lambda x: (
            float((x.get("metrics") or {}).get("cagr") or -999.0),
            float((x.get("metrics") or {}).get("sharpe") or -999.0),
            float((x.get("metrics") or {}).get("mdd") or -999.0),
            _is_non_logos_multi_lens(x),
            _lens_count(x),
        ),
        reverse=True,
    )


def _build_walkforward_folds(rows: list[dict[str, Any]], n_folds: int) -> list[list[dict[str, Any]]]:
    if n_folds <= 1 or len(rows) < 4:
        return [rows]
    size = max(2, len(rows) // n_folds)
    folds: list[list[dict[str, Any]]] = []
    i = 0
    while i < len(rows):
        folds.append(rows[i : i + size])
        i += size
    if len(folds) > 1 and len(folds[-1]) < 2:
        folds[-2].extend(folds[-1])
        folds = folds[:-1]
    return folds


def _build_expanding_walkforward_blocks(
    rows: list[dict[str, Any]],
    *,
    min_train_rows: int,
    test_window_rows: int,
) -> list[dict[str, list[dict[str, Any]]]]:
    if len(rows) < (min_train_rows + test_window_rows):
        return []
    blocks: list[dict[str, list[dict[str, Any]]]] = []
    train_end = max(1, min_train_rows)
    while (train_end + test_window_rows) <= len(rows):
        train_rows = rows[:train_end]
        test_rows = rows[train_end : train_end + test_window_rows]
        blocks.append({"train_rows": train_rows, "test_rows": test_rows})
        train_end += test_window_rows
    return blocks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE_JSON)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR_JSON)
    ap.add_argument("--btc-csv", type=Path, default=DEFAULT_BTC_CSV)
    ap.add_argument("--target-instrument", type=str, default="btc")
    ap.add_argument("--fee-bps", type=float, default=5.0, help="Applied on position turnover (one-way bps).")
    ap.add_argument("--fee-bps-grid", type=str, default="", help="Comma list like 5,10,20 for sensitivity.")
    ap.add_argument("--coordinator-deadzone", type=float, default=0.001)
    ap.add_argument("--walkforward-folds", type=int, default=5)
    ap.add_argument(
        "--walkforward-mode",
        type=str,
        choices=("chunk", "expanding"),
        default="expanding",
        help="chunk=equal chunks, expanding=expanding train + fixed test window",
    )
    ap.add_argument("--walkforward-test-window-rows", type=int, default=5)
    ap.add_argument("--walkforward-min-train-rows", type=int, default=10)
    ap.add_argument(
        "--emit-top1-candidate",
        type=Path,
        default=ART / "btc_top1_limited_live_candidate_from_lens_combo_latest.json",
        help="Write top strategy as non-execution limited-live candidate artifact.",
    )
    ap.add_argument("--annual-trading-days", type=int, default=252)
    ap.add_argument(
        "--logos-vote-mode",
        choices=("global", "omit", "confidence_gated"),
        default="omit",
        help=(
            "How Logos participates in directional majority vote. "
            "global=always append global logos_sign (legacy). "
            "omit=Logos excluded from vote ([NON_GATING]-aligned research). "
            "confidence_gated=append only when sidecar logos confidence >= --logos-min-confidence."
        ),
    )
    ap.add_argument(
        "--logos-min-confidence",
        type=float,
        default=0.25,
        help="Used when --logos-vote-mode=confidence_gated (aligns with btrack min_direction_confidence band).",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    score_doc = _read_json(args.score_json)
    sidecar_doc = _read_json(args.sidecar_json)
    rows = score_doc.get("rows") or []
    if not isinstance(rows, list):
        raise SystemExit(f"invalid score rows: {args.score_json}")

    target = str(args.target_instrument or "btc").strip().lower()
    filtered = [r for r in rows if isinstance(r, dict) and str(r.get("instrument") or "").strip().lower() == target]
    filtered.sort(key=lambda x: str(x.get("eval_date") or ""))
    if not filtered:
        raise SystemExit(f"no rows for instrument={target} in {args.score_json}")

    myeongni_map, sasang_map, logos_sign, logos_confidence = _extract_lens_maps(sidecar_doc)
    logos_vote_mode = str(args.logos_vote_mode or "global").strip().lower()
    logos_min_confidence = float(args.logos_min_confidence)
    btc_prior = _prior_completed_daily_return_by_eval_date(args.btc_csv) if args.btc_csv.is_file() else {}
    fee_rate = float(args.fee_bps) / 10000.0
    fee_grid = (
        [float(x.strip()) for x in args.fee_bps_grid.split(",") if x.strip()]
        if str(args.fee_bps_grid).strip()
        else [float(args.fee_bps)]
    )
    deadzone = abs(float(args.coordinator_deadzone))
    annual_td = max(1, int(args.annual_trading_days))

    variants = _build_variants()
    strategy_results = [
        _simulate_variant(
            variant=v,
            rows=filtered,
            btc_prior=btc_prior,
            myeongni_map=myeongni_map,
            sasang_map=sasang_map,
            logos_sign=logos_sign,
            logos_confidence=logos_confidence,
            logos_vote_mode=logos_vote_mode,
            logos_min_confidence=logos_min_confidence,
            fee_rate=fee_rate,
            deadzone=deadzone,
            annual_trading_days=annual_td,
        )
        for v in variants
    ]
    ranked = _rank_strategies(strategy_results)

    fee_sensitivity: list[dict[str, Any]] = []
    for fee_bps in fee_grid:
        items = [
            _simulate_variant(
                variant=v,
                rows=filtered,
                btc_prior=btc_prior,
                myeongni_map=myeongni_map,
                sasang_map=sasang_map,
                logos_sign=logos_sign,
                logos_confidence=logos_confidence,
                logos_vote_mode=logos_vote_mode,
                logos_min_confidence=logos_min_confidence,
                fee_rate=(fee_bps / 10000.0),
                deadzone=deadzone,
                annual_trading_days=annual_td,
            )
            for v in variants
        ]
        r = _rank_strategies(items)
        fee_sensitivity.append(
            {
                "fee_bps": fee_bps,
                "best_strategy": r[0] if r else None,
                "ranked_strategies": r,
            }
        )

    wf_mode = str(args.walkforward_mode).strip().lower()
    fold_rows = _build_walkforward_folds(filtered, max(1, int(args.walkforward_folds)))
    wf_blocks: list[dict[str, list[dict[str, Any]]]] = []
    if wf_mode == "expanding":
        wf_blocks = _build_expanding_walkforward_blocks(
            filtered,
            min_train_rows=max(2, int(args.walkforward_min_train_rows)),
            test_window_rows=max(2, int(args.walkforward_test_window_rows)),
        )
    else:
        wf_blocks = [{"train_rows": [], "test_rows": xs} for xs in fold_rows]
    walkforward: list[dict[str, Any]] = []
    for idx, block in enumerate(wf_blocks):
        train_rows = block.get("train_rows") or []
        test_rows = block.get("test_rows") or []
        items = [
            _simulate_variant(
                variant=v,
                rows=test_rows,
                btc_prior=btc_prior,
                myeongni_map=myeongni_map,
                sasang_map=sasang_map,
                logos_sign=logos_sign,
                logos_confidence=logos_confidence,
                logos_vote_mode=logos_vote_mode,
                logos_min_confidence=logos_min_confidence,
                fee_rate=fee_rate,
                deadzone=deadzone,
                annual_trading_days=annual_td,
            )
            for v in variants
        ]
        r = _rank_strategies(items)
        walkforward.append(
            {
                "fold_index": idx,
                "mode": wf_mode,
                "n_train_rows": len(train_rows),
                "n_test_rows": len(test_rows),
                "train_date_start": str((train_rows[0] or {}).get("eval_date") or "") if train_rows else "",
                "train_date_end": str((train_rows[-1] or {}).get("eval_date") or "") if train_rows else "",
                "test_date_start": str((test_rows[0] or {}).get("eval_date") or "") if test_rows else "",
                "test_date_end": str((test_rows[-1] or {}).get("eval_date") or "") if test_rows else "",
                "best_strategy": r[0] if r else None,
                "ranked_strategies": r,
            }
        )

    payload = {
        "schema": "prophecy_lens_combo_backtest_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "inputs": {
            "score_json": str(args.score_json),
            "sidecar_json": str(args.sidecar_json),
            "target_instrument": target,
            "btc_csv": str(args.btc_csv),
            "fee_bps": float(args.fee_bps),
            "fee_bps_grid": fee_grid,
            "coordinator_deadzone": deadzone,
            "walkforward_mode": wf_mode,
            "walkforward_folds_requested": int(args.walkforward_folds),
            "walkforward_folds_effective": len(wf_blocks),
            "walkforward_test_window_rows": int(args.walkforward_test_window_rows),
            "walkforward_min_train_rows": int(args.walkforward_min_train_rows),
            "annual_trading_days": int(args.annual_trading_days),
            "logos_vote_mode": logos_vote_mode,
            "logos_min_confidence": logos_min_confidence,
            "logos_sidecar_confidence": logos_confidence,
            "logos_sidecar_sign": logos_sign,
        },
        "universe": {
            "strategies_total": len(strategy_results),
            "includes": [
                "single_lens_3",
                "two_lens_3",
                "three_lens_1",
                "three_lens_plus_coordinator_1",
            ],
        },
        "tie_break_policy": _tie_break_policy_doc(),
        "best_strategy": ranked[0] if ranked else None,
        "ranked_strategies": ranked,
        "fee_sensitivity": fee_sensitivity,
        "walkforward": walkforward,
        "note": (
            "Coordinator is a tie-break overlay for neutral votes only; "
            "it uses prior completed BTC return sign in this research harness. "
            f"logos_vote_mode={logos_vote_mode}: Logos excluded from directional vote when omit "
            "(strategy ids may still list logos for A/B labeling)."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.emit_top1_candidate:
        top = ranked[0] if ranked else {}
        top_metrics = (top.get("metrics") or {}) if isinstance(top, dict) else {}
        tradable = (
            float(top_metrics.get("directional_hit_rate_active") or 0.0) >= 0.55
            and float(top_metrics.get("mdd") or 0.0) >= -0.15
            and float(top_metrics.get("sharpe") or 0.0) > 0.0
        )
        candidate = {
            "schema": "btc_top1_limited_live_candidate_from_lens_combo_v1",
            "generated_at_utc": _utc_now(),
            "research_only": True,
            "non_execution": True,
            "tie_break_policy": _tie_break_policy_doc(),
            "source_backtest": str(args.output),
            "candidate": {
                "strategy_id": top.get("strategy_id") if isinstance(top, dict) else None,
                "lenses": top.get("lenses") if isinstance(top, dict) else None,
                "use_coordinator": top.get("use_coordinator") if isinstance(top, dict) else None,
                "metrics": top_metrics,
            },
            "guards": {
                "min_hit_rate_0p55": float(top_metrics.get("directional_hit_rate_active") or 0.0) >= 0.55,
                "max_mdd_-0p15": float(top_metrics.get("mdd") or 0.0) >= -0.15,
                "sharpe_positive": float(top_metrics.get("sharpe") or 0.0) > 0.0,
            },
            "limited_live_policy": {
                "mode": "S4_LIMITED_LIVE",
                "base_position_usd": 100.0,
                "position_ratio": 0.1,
                "limited_position_usd": 10.0,
                "max_consecutive_losses": 3,
                "max_drawdown_pct": 2.0,
                "auto_scale_up": False,
                "auto_bridge_enabled": False,
                "auto_live_trigger_enabled": False,
            },
            "decision": {
                "status": "READY_LIMITED_LIVE" if tradable else "HOLD_SHADOW_ONLY",
                "tradable_candidate": tradable,
                "action": "human_review_then_submit_to_engine" if tradable else "keep_shadow_and_recalibrate",
            },
        }
        args.emit_top1_candidate.parent.mkdir(parents=True, exist_ok=True)
        args.emit_top1_candidate.write_text(json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    if ranked:
        top = ranked[0]
        print(
            "TOP="
            f"{top.get('strategy_id')} "
            f"cagr={((top.get('metrics') or {}).get('cagr'))} "
            f"mdd={((top.get('metrics') or {}).get('mdd'))}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
