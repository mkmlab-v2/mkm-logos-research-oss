#!/usr/bin/env python3
"""Side-by-side B-track prophecy KPI vs VPS/live trading PnL — observability only.

Does not prove causality or auto-link prophecy hit rate to trading promotion.
research_only — [HYPO] B-track lane only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "btrack_vps_pnl_separation_v1_latest.json"
DEFAULT_PROPHECY_EVAL = ROOT / "docs/final/artifacts/prophecy_hit_rate_eval_latest.json"
DEFAULT_TRADING_GATE = (
    ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/strategy_promotion_gate_latest.json"
)
DEFAULT_TRADE_WINDOW = (
    ROOT / "projects/bitcoin-trading/exports/cursor_trade_history/cursor_trade_history_latest_24h.json"
)
SCHEMA = "btrack_vps_pnl_separation_report_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _prophecy_axis(eval_path: Path) -> dict[str, Any]:
    doc = _load_json(eval_path)
    if not doc:
        return {
            "available": False,
            "path": _rel(eval_path),
            "reason": "missing_or_invalid",
        }
    metrics = doc.get("metrics") if isinstance(doc.get("metrics"), dict) else {}
    inputs = doc.get("inputs") if isinstance(doc.get("inputs"), dict) else {}
    return {
        "available": True,
        "path": _rel(eval_path),
        "generated_at_utc": doc.get("generated_at_utc"),
        "run_mode": doc.get("run_mode"),
        "score_json": inputs.get("score_json"),
        "headline_instrument": metrics.get("headline_instrument"),
        "scoring_mode": metrics.get("scoring_mode"),
        "price_directional_hit_rate_all_rows": metrics.get("price_directional_hit_rate"),
        "n_evaluated": metrics.get("n_evaluated"),
        "price_hit_rate_on_directional_calls": metrics.get("price_hit_rate_on_directional_calls"),
        "n_directional_calls": metrics.get("n_directional_calls"),
        "n_neutral_predictions": metrics.get("n_neutral_predictions"),
        "wf_mean_test_accuracy_path": "docs/final/artifacts/prophecy_per_date_combo_walkforward_v1_latest.json",
        "lane": "btrack_research_hypo",
        "auto_triggers_live_trading": False,
    }


def _trading_axis(gate_path: Path, window_path: Path) -> dict[str, Any]:
    gate = _load_json(gate_path)
    window = _load_json(window_path)
    if not gate:
        return {
            "available": False,
            "path": _rel(gate_path),
            "reason": "strategy_promotion_gate missing_or_invalid",
        }
    metrics = gate.get("metrics") if isinstance(gate.get("metrics"), dict) else {}
    treatment = metrics.get("treatment") if isinstance(metrics.get("treatment"), dict) else {}
    shadow = metrics.get("shadow") if isinstance(metrics.get("shadow"), dict) else {}
    decision = gate.get("decision") if isinstance(gate.get("decision"), dict) else {}
    out: dict[str, Any] = {
        "available": True,
        "path": _rel(gate_path),
        "generated_at_utc": gate.get("generated_at_utc"),
        "schema": gate.get("schema"),
        "pm2_app_name_hint": "bitcoin-live-small-24h",
        "entry_script_hint": "projects/bitcoin-trading/start_live_trading.py",
        "treatment": {
            "trades": treatment.get("trades"),
            "hit_rate": treatment.get("hit_rate"),
            "net_pnl": treatment.get("net_pnl"),
            "profit_factor": treatment.get("profit_factor"),
            "max_drawdown": treatment.get("max_drawdown"),
        },
        "shadow_note": (
            "shadow metrics in gate file are backtest/shadow lane — not B-track OHLCV hit rate"
        ),
        "shadow_net_pnl": shadow.get("net_pnl"),
        "promotion_ready": decision.get("promotion_ready"),
        "recommended_mode": decision.get("recommended_mode"),
        "lane": "vps_live_trading_execution",
        "drives_btrack_promotion_gates": False,
    }
    if window:
        counts = window.get("counts") if isinstance(window.get("counts"), dict) else {}
        out["cursor_trade_history_24h"] = {
            "path": _rel(window_path),
            "generated_at_utc": window.get("generated_at_utc"),
            "window_hours": window.get("window_hours"),
            "trade_counts": counts,
        }
    return out


def format_observation_line(report: dict[str, Any]) -> str:
    """Single console line for 09:05 panel obs block (no causality)."""
    snap = report.get("contrast_snapshot") if isinstance(report.get("contrast_snapshot"), dict) else {}

    def _pct(v: Any) -> str:
        if v is None:
            return "n/a"
        try:
            return f"{float(v):.1%}"
        except (TypeError, ValueError):
            return "n/a"

    b_all = _pct(snap.get("btrack_headline_hit_all_rows"))
    b_calls = _pct(snap.get("btrack_hit_on_directional_calls_only"))
    t_hit = _pct(snap.get("trading_treatment_hit_rate"))
    t_pnl = snap.get("trading_treatment_net_pnl")
    pnl_s = "n/a" if t_pnl is None else f"{float(t_pnl):.4f}"
    return (
        f"- [MKM-BTRACK-vs-VPS] B-track BTC {b_all} (all-rows) / {b_calls} (directional-calls) "
        f"| VPS treatment hit {t_hit} net_pnl={pnl_s} "
        f"| same_metric=false correlation_claim_allowed=false"
    )


def build_report(
    *,
    prophecy_eval: Path,
    trading_gate: Path,
    trade_window: Path,
) -> dict[str, Any]:
    btrack = _prophecy_axis(prophecy_eval)
    trading = _trading_axis(trading_gate, trade_window)
    b_hit = btrack.get("price_directional_hit_rate_all_rows")
    t_hit = (trading.get("treatment") or {}).get("hit_rate") if trading.get("available") else None
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "correlation_claim_allowed": False,
        "summary": (
            "B-track price hit rate measures OHLCV direction match on research score rows. "
            "VPS PnL measures executed trades on bitcoin-trading path. "
            "Do not infer trading edge from prophecy hit rate or vice versa."
        ),
        "separation_rules": [
            "B-track: docs/final/artifacts/prophecy_hit_rate_eval_latest.json + promotion gates (research).",
            "Live trading: projects/bitcoin-trading/exports/cursor_trade_history/* + PM2 aroon path.",
            "prophecy_hit_rate does not auto-promote to Track A or ENABLE_TRADING.",
            "treatment.hit_rate in strategy_promotion_gate is trade win-rate, not B-track OHLCV headline.",
        ],
        "axes": {
            "btrack_prophecy": btrack,
            "vps_live_trading": trading,
        },
        "contrast_snapshot": {
            "btrack_headline_hit_all_rows": b_hit,
            "btrack_hit_on_directional_calls_only": btrack.get("price_hit_rate_on_directional_calls"),
            "trading_treatment_hit_rate": t_hit,
            "trading_treatment_net_pnl": (trading.get("treatment") or {}).get("net_pnl")
            if trading.get("available")
            else None,
            "same_metric": False,
            "note": (
                "If both hit_rate fields appear, they use different definitions and samples — "
                "never cite as one number."
            ),
        },
        "operator_actions": {
            "btrack_daily": "MISSION_LOG.md 일일 08:35/08:55/09:05",
            "trading_ops": "projects/bitcoin-trading/AGENTS.md · VPS pm2 show bitcoin-live-small-24h",
            "combined_briefing_forbidden": [
                "prophecy 62% proves live PnL",
                "live loss means B-track failed",
                "single blended hit rate",
            ],
        },
    }
    out["observation_line"] = format_observation_line(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prophecy-eval", type=Path, default=DEFAULT_PROPHECY_EVAL)
    ap.add_argument("--trading-gate", type=Path, default=DEFAULT_TRADING_GATE)
    ap.add_argument("--trade-window", type=Path, default=DEFAULT_TRADE_WINDOW)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument(
        "--format-obs-line",
        action="store_true",
        help="Print one observation line to stdout (for panel 09:05).",
    )
    args = ap.parse_args()

    prophecy = args.prophecy_eval if args.prophecy_eval.is_absolute() else ROOT / args.prophecy_eval
    gate = args.trading_gate if args.trading_gate.is_absolute() else ROOT / args.trading_gate
    window = args.trade_window if args.trade_window.is_absolute() else ROOT / args.trade_window

    report = build_report(prophecy_eval=prophecy, trading_gate=gate, trade_window=window)
    if args.format_obs_line:
        print(format_observation_line(report))
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if args.stdout_only:
        print(text)
    if args.output:
        out = args.output if args.output.is_absolute() else ROOT / args.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print(f"WROTE: {out}", file=sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
