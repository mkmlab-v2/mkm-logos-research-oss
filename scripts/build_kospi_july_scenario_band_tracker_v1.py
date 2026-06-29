#!/usr/bin/env python3
"""[HYPO] July KOSPI scenario band tracker — 3-axis flow observation + weight nudge.

Reads daily investor-flow CSV (foreign / institution / pension_proxy), optional KOSPI
daily returns for shock-day active-arm advisory, and monthly prophecy prior for July.

Outputs JSON + Markdown. observation_only — does not unlock price output or Track A.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "kospi_july_scenario_band_tracker_v1"
DEFAULT_FLOW = ROOT / "research" / "market_data" / "kospi_daily_flow_external.csv"
DEFAULT_KOSPI = ROOT / "research" / "market_data" / "kospi_daily_external_yf.csv"
DEFAULT_PROPHECY = ROOT / "docs" / "final" / "artifacts" / "prophecy_2026_monthly_kospi_btc_fact_safe_v1.json"
DEFAULT_SHOCK = ROOT / "reports" / "kospi_four_lens_shock_fusion_walkforward_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "kospi_july_scenario_band_tracker_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports" / "kospi_july_scenario_band_tracker_v1_latest.md"
DEFAULT_LOG = ROOT / "reports" / "kospi_july_scenario_band_tracker_v1_log.jsonl"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_flow_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            d = str(r.get("date") or "")[:10]
            if len(d) != 10:
                continue

            def _f(k: str) -> float | None:
                raw = str(r.get(k) or "").strip()
                if raw == "":
                    return None
                try:
                    return float(raw)
                except ValueError:
                    return None

            rows.append(
                {
                    "date": d,
                    "foreign_net_buy": _f("foreign_net_buy"),
                    "institution_net_buy": _f("institution_net_buy"),
                    "program_net_buy": _f("program_net_buy"),
                    "pension_proxy_net_buy": _f("pension_proxy_net_buy"),
                    "individual_net_buy": _f("individual_net_buy"),
                    "source_note": str(r.get("source_note") or ""),
                }
            )
    rows.sort(key=lambda x: x["date"])
    return rows


def _load_kospi_returns(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    out: dict[str, float] = {}
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        prev: float | None = None
        for row in rd:
            d = str(row.get("Date") or "").strip()[:10]
            raw = str(row.get("Close") or "").strip()
            if not d or not raw:
                continue
            try:
                c = float(raw)
            except ValueError:
                continue
            if prev is not None and prev > 0:
                out[d] = (c / prev - 1.0) * 100.0
            prev = c
    return out


def _load_july_prior(prophecy_path: Path, *, target_month: int) -> dict[str, Any]:
    if not prophecy_path.is_file():
        return {"ok": False, "reason": "missing_prophecy_json"}
    doc = json.loads(prophecy_path.read_text(encoding="utf-8-sig"))
    for m in doc.get("months") or []:
        if int(m.get("month") or 0) == target_month:
            k = m.get("kospi") or {}
            return {
                "ok": True,
                "month": target_month,
                "phase": m.get("phase"),
                "direction": k.get("direction"),
                "up_pct": int(k.get("up_pct") or 0),
                "neutral_pct": int(k.get("neutral_pct") or 0),
                "down_pct": int(k.get("down_pct") or 0),
            }
    return {"ok": False, "reason": f"month_{target_month}_not_in_prophecy"}


def _streak_sign(values: list[float | None]) -> str | None:
    clean = [v for v in values if v is not None]
    if len(clean) < 3:
        return None
    tail = clean[-3:]
    if all(v > 0 for v in tail):
        return "buy_streak"
    if all(v < 0 for v in tail):
        return "sell_streak"
    return "mixed"


def _renormalize_weights(bull: float, neutral: float, bear: float) -> dict[str, float]:
    total = bull + neutral + bear
    if total <= 0:
        return {"bull_pct": 0.0, "neutral_pct": 0.0, "bear_pct": 0.0}
    return {
        "bull_pct": round(bull / total * 100, 1),
        "neutral_pct": round(neutral / total * 100, 1),
        "bear_pct": round(bear / total * 100, 1),
    }


def build_doc(
    *,
    flow_csv: Path,
    kospi_csv: Path,
    prophecy_json: Path,
    shock_json: Path,
    target_month: int,
    lookback_days: int,
    foreign_streak_days: int,
    pension_5d_sell_threshold: float,
    shock_return_pct: float,
    nudge_pp: float,
) -> dict[str, Any]:
    flow_rows = _load_flow_rows(flow_csv)
    returns = _load_kospi_returns(kospi_csv)
    prior = _load_july_prior(prophecy_json, target_month=target_month)

    tail = flow_rows[-lookback_days:] if flow_rows else []
    as_of = tail[-1]["date"] if tail else None

    foreign_vals = [r.get("foreign_net_buy") for r in tail]
    pension_vals = [r.get("pension_proxy_net_buy") for r in tail]
    program_vals = [r.get("program_net_buy") for r in tail]

    foreign_streak = _streak_sign(foreign_vals[-foreign_streak_days:])
    pension_5d = sum(v for v in pension_vals if v is not None)
    program_gap = not program_vals or all((v is None or v == 0.0) for v in program_vals)

    latest_ret = returns.get(as_of) if as_of else None
    shock_today = (
        latest_ret is not None and abs(latest_ret) >= shock_return_pct
    )

    shock_policy: dict[str, Any] = {"loaded": False}
    if shock_json.is_file():
        shock_doc = json.loads(shock_json.read_text(encoding="utf-8-sig"))
        holdout = (shock_doc.get("holdout_pooled") or {}).get("active") or {}
        fusion = (shock_doc.get("holdout_pooled") or {}).get("fusion_always") or {}
        shock_policy = {
            "loaded": True,
            "active_soft_hit_rate": holdout.get("soft_hit_rate"),
            "fusion_always_soft_hit_rate": fusion.get("soft_hit_rate"),
            "advisory": "prefer_active_arm_on_shock_day",
        }

    base_bull = float(prior.get("up_pct") or 21)
    base_neutral = float(prior.get("neutral_pct") or 40)
    base_bear = float(prior.get("down_pct") or 39)
    adj_bull, adj_neutral, adj_bear = base_bull, base_neutral, base_bear
    nudges: list[str] = []

    if foreign_streak == "buy_streak":
        adj_bull += nudge_pp
        adj_bear -= nudge_pp
        nudges.append(f"foreign_{foreign_streak_days}d_buy_streak:+bull/-bear")
    elif foreign_streak == "sell_streak":
        adj_bull -= nudge_pp
        adj_bear += nudge_pp
        nudges.append(f"foreign_{foreign_streak_days}d_sell_streak:-bull/+bear")

    if pension_5d <= pension_5d_sell_threshold:
        adj_bull -= nudge_pp
        adj_bear += nudge_pp
        nudges.append("pension_proxy_5d_cum_sell: -bull/+bear")

    if program_gap:
        nudges.append("program_axis: GAP (weight=0)")

    if shock_today:
        nudges.append(f"shock_day_|r|>={shock_return_pct}%: active_arm_only")

    adjusted = _renormalize_weights(adj_bull, adj_neutral, adj_bear)
    base_w = _renormalize_weights(base_bull, base_neutral, base_bear)

    primary = max(
        [("bull", adjusted["bull_pct"]), ("neutral", adjusted["neutral_pct"]), ("bear", adjusted["bear_pct"])],
        key=lambda x: x[1],
    )[0]

    falsifiers: list[dict[str, str]] = []
    if foreign_streak == "buy_streak":
        falsifiers.append(
            {
                "id": "bear_promotion_block",
                "condition": "foreign 3d buy streak active",
                "effect": "bear scenario demoted unless pension 5d sell overwhelms",
            }
        )
    if pension_5d <= pension_5d_sell_threshold:
        falsifiers.append(
            {
                "id": "bull_promotion_block",
                "condition": f"pension_proxy 5d cum {pension_5d:.1f} <= {pension_5d_sell_threshold}",
                "effect": "bull scenario demoted",
            }
        )

    return {
        "schema": SCHEMA,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "observation_only": True,
        "send_gate": "HOLD",
        "price_output_locked": True,
        "ts_utc": _utc_now(),
        "as_of_trade_date": as_of,
        "target_month": target_month,
        "label": (
            "[HYPO] KOSPI July scenario band tracker: 3-axis flow observation + "
            "prophecy prior nudge. research_only; not Track A / live trigger."
        ),
        "inputs": {
            "flow_csv": _rel(flow_csv),
            "kospi_csv": _rel(kospi_csv),
            "prophecy_json": _rel(prophecy_json),
            "shock_json": _rel(shock_json),
            "lookback_days": lookback_days,
            "foreign_streak_days": foreign_streak_days,
            "pension_5d_sell_threshold_ekr_bil": pension_5d_sell_threshold,
            "shock_return_pct": shock_return_pct,
            "nudge_pp": nudge_pp,
        },
        "disclaimers": [
            "pension_proxy = pykrx 연기금등 순매수; not NPS-isolated.",
            "program_net_buy remains GAP until a sourced feed is wired.",
            "Adjusted weights are observation nudges only; prophecy meta HOLD unchanged.",
            "Daily flow CSV must use 순매수 (net buy), not gross trading value.",
        ],
        "prophecy_prior": prior,
        "axes": {
            "foreign": {
                "lookback_rows": len(tail),
                "last_3d": foreign_vals[-3:],
                "streak": foreign_streak,
            },
            "pension_proxy": {
                "lookback_rows": len(tail),
                "last_5d_cum_ekr_bil": round(pension_5d, 2),
                "threshold_ekr_bil": pension_5d_sell_threshold,
                "pressure": pension_5d <= pension_5d_sell_threshold,
            },
            "program": {
                "status": "GAP" if program_gap else "partial",
                "last_values": program_vals[-3:],
                "weight": 0.0 if program_gap else 1.0,
            },
        },
        "market": {
            "latest_daily_return_pct": round(latest_ret, 4) if latest_ret is not None else None,
            "shock_day": shock_today,
            "shock_fusion_policy": shock_policy,
        },
        "scenario_weights": {
            "base": base_w,
            "adjusted": adjusted,
            "delta_bull_minus_base": round(adjusted["bull_pct"] - base_w["bull_pct"], 1),
            "delta_bear_minus_base": round(adjusted["bear_pct"] - base_w["bear_pct"], 1),
            "primary_scenario": primary,
            "nudges_applied": nudges,
        },
        "scenario_bands_hypo": {
            "bull": "9,300–10,000 (external ref only; not system price unlock)",
            "base": "8,200–9,500 box with ±8–12% intramonth swings",
            "bear": "7,800–8,200 retest if NPS accel + shock cascade",
        },
        "falsifiers": falsifiers,
        "ok": bool(tail and prior.get("ok")),
        "missing": [] if tail else ["flow_rows"],
    }


def _render_md(doc: dict[str, Any]) -> str:
    w = doc.get("scenario_weights") or {}
    adj = w.get("adjusted") or {}
    axes = doc.get("axes") or {}
    lines = [
        "# KOSPI July Scenario Band Tracker [HYPO]",
        "",
        f"- generated: {doc.get('ts_utc')}",
        f"- as_of: {doc.get('as_of_trade_date')}",
        f"- send_gate: {doc.get('send_gate')} · price_output_locked: {doc.get('price_output_locked')}",
        "",
        "## Scenario weights (prior → adjusted)",
        "",
        f"- base: bull {w.get('base', {}).get('bull_pct')}% / "
        f"neutral {w.get('base', {}).get('neutral_pct')}% / "
        f"bear {w.get('base', {}).get('bear_pct')}%",
        f"- adjusted: bull {adj.get('bull_pct')}% / "
        f"neutral {adj.get('neutral_pct')}% / "
        f"bear {adj.get('bear_pct')}%",
        f"- primary: **{w.get('primary_scenario')}**",
        f"- nudges: {', '.join(w.get('nudges_applied') or []) or 'none'}",
        "",
        "## 3-axis snapshot",
        "",
        f"- foreign streak: {axes.get('foreign', {}).get('streak')} · last3 {axes.get('foreign', {}).get('last_3d')}",
        f"- pension_proxy 5d cum: {axes.get('pension_proxy', {}).get('last_5d_cum_ekr_bil')} 억",
        f"- program: {axes.get('program', {}).get('status')}",
        "",
        "## Shock advisory",
        "",
        f"- latest return %: {doc.get('market', {}).get('latest_daily_return_pct')}",
        f"- shock_day: {doc.get('market', {}).get('shock_day')} → prefer **active arm only** on shock days",
        "",
        "## Band labels (hypo, not price unlock)",
        "",
    ]
    bands = doc.get("scenario_bands_hypo") or {}
    for k, v in bands.items():
        lines.append(f"- {k}: {v}")
    lines.extend(
        [
            "",
            "*observation_only · Track A blocked*",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--flow-csv", type=Path, default=DEFAULT_FLOW)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI)
    ap.add_argument("--prophecy-json", type=Path, default=DEFAULT_PROPHECY)
    ap.add_argument("--shock-json", type=Path, default=DEFAULT_SHOCK)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument("--target-month", type=int, default=7)
    ap.add_argument("--lookback-days", type=int, default=5)
    ap.add_argument("--foreign-streak-days", type=int, default=3)
    ap.add_argument("--pension-5d-sell-threshold", type=float, default=-20000.0)
    ap.add_argument("--shock-return-pct", type=float, default=5.0)
    ap.add_argument("--nudge-pp", type=float, default=10.0)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args(argv)

    doc = build_doc(
        flow_csv=args.flow_csv,
        kospi_csv=args.kospi_csv,
        prophecy_json=args.prophecy_json,
        shock_json=args.shock_json,
        target_month=int(args.target_month),
        lookback_days=max(3, int(args.lookback_days)),
        foreign_streak_days=max(3, int(args.foreign_streak_days)),
        pension_5d_sell_threshold=float(args.pension_5d_sell_threshold),
        shock_return_pct=float(args.shock_return_pct),
        nudge_pp=float(args.nudge_pp),
    )

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = _render_md(doc)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md, encoding="utf-8")

    if args.append_log:
        args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
        args.log_jsonl.open("a", encoding="utf-8").write(line)

    print(str(args.output_json.resolve()))
    print(str(args.output_md.resolve()))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
