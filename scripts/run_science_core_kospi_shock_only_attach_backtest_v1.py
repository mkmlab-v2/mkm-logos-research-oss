#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI shock-only sasang attach policy backtest [HYPO][research_only].

Compares:
  - always science_core
  - always science_plus_sasang
  - shock_only_attach (sasang on |move|>=shock_bps, else science)
  - calm_only_attach (inverse; contrast arm)

Track A / live trading promotion forbidden.
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
    logos_global,
    read_jsonl,
    rows_by_calendar_day,
)
from scripts.logos_shadow_eval_lib import load_kospi_yf_rows  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    build_daily_short_rows,
)
from scripts.run_science_core_kospi_combo_backtest_v1 import (  # noqa: E402
    _actual_dir_from_return,
    _dir_to_sign,
    _predictions_extended,
)

DEFAULT_OUT = ROOT / "reports/science_core_kospi_shock_only_attach_backtest_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_kospi_shock_only_attach_backtest_v1_latest.json"
DEFAULT_MARKET_SASANG = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"
DEFAULT_LOGOS_PER_DATE = ROOT / "reports/btrack_logos_per_date_v1.jsonl"
DEFAULT_HOLDOUT_FROM = "2026-05-01"
DEFAULT_SHOCK_BPS = 100.0

POLICY_IDS = (
    "always_science_core",
    "always_science_plus_sasang",
    "shock_only_attach",
    "calm_only_attach",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pick_lens(policy_id: str, *, is_shock: bool) -> str:
    if policy_id == "always_science_core":
        return "science_core"
    if policy_id == "always_science_plus_sasang":
        return "science_plus_sasang"
    if policy_id == "shock_only_attach":
        return "science_plus_sasang" if is_shock else "science_core"
    if policy_id == "calm_only_attach":
        return "science_plus_sasang" if not is_shock else "science_core"
    raise ValueError(f"unknown policy_id: {policy_id}")


def _soft_metrics(outcomes: list[str]) -> dict[str, Any]:
    hits = sum(1 for o in outcomes if o == "HIT")
    fails = sum(1 for o in outcomes if o == "FAIL")
    neutral = sum(1 for o in outcomes if o == "NEUTRAL_DRAW")
    n = len(outcomes)
    n_dir = hits + fails
    return {
        "n_scored": n,
        "hit": hits,
        "fail": fails,
        "neutral_draw": neutral,
        "directional_hit_rate": round(hits / n_dir, 4) if n_dir else None,
        "soft_hit_rate": round((hits + 0.5 * neutral) / n, 4) if n else None,
    }


def _index_daily_short_rows(daily: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("session_date") or "")[:10]: r for r in daily if r.get("session_date")}


def _eval_soft_policies(
    daily: list[dict[str, Any]],
    *,
    shock_bps: float,
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for pid in POLICY_IDS:
        outcomes: list[str] = []
        n_shock = n_calm = 0
        for r in daily:
            fr = r.get("forward_return_bps")
            if fr is None:
                continue
            is_shock = abs(float(fr)) >= shock_bps
            if is_shock:
                n_shock += 1
            else:
                n_calm += 1
            lens = _pick_lens(pid, is_shock=is_shock)
            oc = (r.get("outcomes_short_1d") or {}).get(lens)
            if oc in {"HIT", "FAIL", "NEUTRAL_DRAW"}:
                outcomes.append(str(oc))
        m = _soft_metrics(outcomes)
        m["n_shock_days_scored"] = n_shock
        m["n_calm_days_scored"] = n_calm
        arms[pid] = m

    base_sci = arms["always_science_core"].get("soft_hit_rate")
    base_sas = arms["always_science_plus_sasang"].get("soft_hit_rate")
    shock_soft = arms["shock_only_attach"].get("soft_hit_rate")
    for arm in arms.values():
        s = arm.get("soft_hit_rate")
        arm["delta_vs_always_science_pp"] = (
            round(float(s) - float(base_sci), 4) if s is not None and base_sci is not None else None
        )
        arm["delta_vs_always_sasang_pp"] = (
            round(float(s) - float(base_sas), 4) if s is not None and base_sas is not None else None
        )

    return {
        "policies": arms,
        "shock_only_vs_always_sasang_soft_pp": (
            round(float(shock_soft) - float(base_sas), 4)
            if shock_soft is not None and base_sas is not None
            else None
        ),
        "shock_only_beats_always_sasang_soft": bool(
            shock_soft is not None and base_sas is not None and float(shock_soft) >= float(base_sas)
        ),
    }


def _eval_pnl_policies(
    *,
    csv_path: Path,
    science_jsonl: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    date_from: str,
    date_to: str,
    neutral_bps: float,
    fee_bps: float,
    shock_bps: float,
    daily_by_date: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rows = sorted(load_kospi_yf_rows(csv_path), key=lambda r: str(r.get("date", "")))
    daily_rets: list[tuple[str, float]] = []
    for i in range(1, len(rows)):
        d = str(rows[i].get("date", ""))[:10]
        try:
            c0 = float(rows[i - 1]["close"])
            c1 = float(rows[i]["close"])
        except (TypeError, ValueError, KeyError):
            continue
        if c0 <= 0:
            continue
        if d < date_from or d > date_to:
            continue
        daily_rets.append((d, (c1 - c0) / c0))

    science_by: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(science_jsonl):
        dk = str(row.get("session_date") or "")[:10]
        if dk:
            science_by[dk] = row
    my_by = rows_by_calendar_day(read_jsonl(myeongni_jsonl))
    sa_by = rows_by_calendar_day(read_jsonl(sasang_jsonl))
    logos_block = logos_global(DEFAULT_LOGOS_LENS)
    fee_rate = fee_bps / 10000.0

    results: dict[str, Any] = {}
    for pid in POLICY_IDS:
        prev_pos = 0
        equity = 1.0
        hits = active = 0
        for dk, ret in daily_rets:
            short_row = daily_by_date.get(dk) or {}
            fr = short_row.get("forward_return_bps")
            is_shock = fr is not None and abs(float(fr)) >= shock_bps
            lens = _pick_lens(pid, is_shock=is_shock)
            preds = _predictions_extended(
                dk,
                science_row=science_by.get(dk),
                myeongni_by_day=my_by,
                sasang_by_day=sa_by,
                logos_block=logos_block,
                myeongni_momentum_window=5,
            )
            pos = _dir_to_sign(preds.get(lens, "neutral"))
            turnover = abs(pos - prev_pos)
            pnl = (pos * ret) - (turnover * fee_rate)
            equity *= 1.0 + pnl
            prev_pos = pos
            actual = _actual_dir_from_return(ret, neutral_bps)
            if pos != 0 and actual in {"bull", "bear"}:
                active += 1
                if _dir_to_sign(actual) == pos:
                    hits += 1
        results[pid] = {
            "n_days": len(daily_rets),
            "n_active_days": active,
            "directional_hit_rate_active": round(hits / active, 4) if active else None,
            "total_return": round(equity - 1.0, 6),
        }

    sci_tr = float(results["always_science_core"].get("total_return") or 0.0)
    sas_tr = float(results["always_science_plus_sasang"].get("total_return") or 0.0)
    shock_tr = float(results["shock_only_attach"].get("total_return") or 0.0)
    for row in results.values():
        tr = float(row.get("total_return") or 0.0)
        row["delta_total_return_vs_science"] = round(tr - sci_tr, 6)
        row["delta_total_return_vs_always_sasang"] = round(tr - sas_tr, 6)

    return {
        "fee_bps": fee_bps,
        "policies": results,
        "shock_only_beats_always_sasang_pnl": shock_tr >= sas_tr,
        "economic_edge_claim_allowed": False,
        "note_ko": "단순 방향 PnL 시뮬. Track A·실매매 승격 근거 아님.",
    }


def run_backtest(
    *,
    csv_path: Path,
    science_jsonl: Path,
    myeongni_jsonl: Path,
    sasang_jsonl: Path,
    logos_jsonl: Path | None,
    date_from: str,
    date_to: str,
    neutral_bps: float,
    fee_bps: float,
    shock_bps: float,
) -> dict[str, Any]:
    daily = build_daily_short_rows(
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        logos_lens=DEFAULT_LOGOS_LENS,
        logos_jsonl=logos_jsonl,
        myeongni_momentum_window=5,
    )
    daily_by = _index_daily_short_rows(daily)
    soft_block = _eval_soft_policies(daily, shock_bps=shock_bps)
    pnl_block = _eval_pnl_policies(
        csv_path=csv_path,
        science_jsonl=science_jsonl,
        myeongni_jsonl=myeongni_jsonl,
        sasang_jsonl=sasang_jsonl,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=neutral_bps,
        fee_bps=fee_bps,
        shock_bps=shock_bps,
        daily_by_date=daily_by,
    )

    shock_soft = soft_block["policies"]["shock_only_attach"].get("soft_hit_rate")
    always_sas_soft = soft_block["policies"]["always_science_plus_sasang"].get("soft_hit_rate")
    soft_gap_pp = (
        round(float(shock_soft) - float(always_sas_soft), 4)
        if shock_soft is not None and always_sas_soft is not None
        else None
    )
    within_half_pp = soft_gap_pp is not None and soft_gap_pp >= -0.005
    shock_policy_recommended = bool(
        soft_block.get("shock_only_beats_always_sasang_soft")
        or (within_half_pp and pnl_block.get("shock_only_beats_always_sasang_pnl"))
    )

    return {
        "schema": "science_core_kospi_shock_only_attach_backtest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "instrument": "kospi",
        "window": {"from": date_from, "to": date_to},
        "shock_move_bps_threshold": shock_bps,
        "neutral_bps": neutral_bps,
        "soft_hit": soft_block,
        "pnl_sim": pnl_block,
        "policy_verdict": {
            "attach_on_shock_only_recommended": shock_policy_recommended,
            "recommended_hypothesis": (
                "attach_sasang_on_shock_days_only"
                if shock_policy_recommended
                else "keep_always_science_plus_sasang"
            ),
            "shock_only_vs_always_sasang_soft_pp": soft_gap_pp,
            "beats_always_sasang_soft": soft_block.get("shock_only_beats_always_sasang_soft"),
            "beats_always_sasang_pnl": pnl_block.get("shock_only_beats_always_sasang_pnl"),
            "note_ko": (
                "shock_only는 calm일 science 단독·shock일 sasang 블렌드 혼합 정책. "
                "always_sasang 대비 soft/PnL이 같거나 높으면 운영 단순화 후보. 승격 아님."
            ),
        },
        "methodology_ko": "holdout short_1d per-date outcomes + 방향 PnL. Track A·실매매 합선 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE_JSONL_KOSPI)
    ap.add_argument("--sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG)
    ap.add_argument("--myeongni-jsonl", type=Path, default=DEFAULT_MYEONGNI_PER_DATE)
    ap.add_argument("--logos-jsonl", type=Path, default=DEFAULT_LOGOS_PER_DATE)
    ap.add_argument("--date-from", default=DEFAULT_HOLDOUT_FROM)
    ap.add_argument("--date-to", default="2026-06-15")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--fee-bps", type=float, default=5.0)
    ap.add_argument("--shock-move-bps", type=float, default=DEFAULT_SHOCK_BPS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    if not v1.KOSPI_CSV.is_file():
        print(f"ERROR: missing KOSPI CSV: {v1.KOSPI_CSV}", file=sys.stderr)
        return 2
    logos_jsonl = args.logos_jsonl if args.logos_jsonl.is_file() else None

    doc = run_backtest(
        csv_path=v1.KOSPI_CSV,
        science_jsonl=args.science_jsonl,
        myeongni_jsonl=args.myeongni_jsonl,
        sasang_jsonl=args.sasang_jsonl,
        logos_jsonl=logos_jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        fee_bps=args.fee_bps,
        shock_bps=args.shock_move_bps,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    shock_soft = doc["soft_hit"]["policies"]["shock_only_attach"].get("soft_hit_rate")
    always_sas = doc["soft_hit"]["policies"]["always_science_plus_sasang"].get("soft_hit_rate")
    print(
        f"WROTE: {args.output.resolve()} shock_only_soft={shock_soft} "
        f"always_sasang_soft={always_sas} recommended={doc['policy_verdict']['recommended_hypothesis']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
