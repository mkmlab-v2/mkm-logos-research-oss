#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Forward-aware foreign flow gate for KOSPI composite shadow [HYPO][research_only].

When prior flow observation is stale relative to session_date, skip foreign-flow
blocks (causal honesty — do not gate on repeated last-real stub).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_FLOW_CSV = Path(__file__).resolve().parents[1] / "research/market_data/kospi_daily_flow_external.csv"
DEFAULT_MAX_LAG_CALENDAR_DAYS = 14


@dataclass(frozen=True)
class PriorForeignContext:
    value: float | None
    source_date: str | None
    gate_mode: str  # live | skipped_stale_forward | missing
    lag_calendar_days: int | None

    @property
    def apply_foreign_flow_gate(self) -> bool:
        return self.gate_mode == "live"


def load_flow_daily(path: Path | None = None) -> dict[str, float | None]:
    p = path or DEFAULT_FLOW_CSV
    out: dict[str, float | None] = {}
    if not p.is_file():
        return out
    with p.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dk = str(row.get("date") or "")[:10]
            raw = row.get("foreign_net_buy")
            if len(dk) != 10:
                continue
            try:
                out[dk] = float(raw) if raw not in (None, "") else None
            except (ValueError, TypeError):
                out[dk] = None
    return out


def last_flow_observation_date(flow: dict[str, float | None]) -> str | None:
    dates = sorted(d for d, v in flow.items() if v is not None)
    return dates[-1] if dates else None


def prior_foreign_raw(flow: dict[str, float | None], session_date: str) -> tuple[float | None, str | None]:
    older = sorted(d for d in flow if d < session_date)
    if not older:
        return None, None
    src = older[-1]
    return flow.get(src), src


def resolve_prior_foreign_for_gate(
    flow: dict[str, float | None],
    session_date: str,
    *,
    max_lag_calendar_days: int = DEFAULT_MAX_LAG_CALENDAR_DAYS,
) -> PriorForeignContext:
    val, src = prior_foreign_raw(flow, session_date)
    if src is None:
        return PriorForeignContext(None, None, "missing", None)
    lag = (date.fromisoformat(session_date[:10]) - date.fromisoformat(src[:10])).days
    if lag > max_lag_calendar_days:
        return PriorForeignContext(val, src, "skipped_stale_forward", lag)
    return PriorForeignContext(val, src, "live", lag)


def evaluate_conditional_unlock(
    *,
    prior_foreign: float | None,
    shock_pred: bool,
    foreign_sell_threshold: float = -25000.0,
    block_on_prior_foreign_sell: bool = True,
    block_shock_with_foreign_sell: bool = True,
    apply_foreign_flow_gate: bool = True,
) -> tuple[bool, list[str]]:
    blocks: list[str] = []
    if apply_foreign_flow_gate:
        if block_on_prior_foreign_sell and prior_foreign is not None and prior_foreign < foreign_sell_threshold:
            blocks.append(f"prior_foreign_net_buy_lt_{int(foreign_sell_threshold)}")
        if (
            block_shock_with_foreign_sell
            and shock_pred
            and prior_foreign is not None
            and prior_foreign < 0
        ):
            blocks.append("shock_pred_with_prior_foreign_sell")
    return (len(blocks) == 0, blocks)


def resolve_and_evaluate_unlock(
    flow: dict[str, float | None],
    session_date: str,
    *,
    shock_pred: bool,
    foreign_sell_threshold: float = -25000.0,
    max_lag_calendar_days: int = DEFAULT_MAX_LAG_CALENDAR_DAYS,
) -> tuple[PriorForeignContext, bool, list[str]]:
    ctx = resolve_prior_foreign_for_gate(flow, session_date, max_lag_calendar_days=max_lag_calendar_days)
    allow, blocks = evaluate_conditional_unlock(
        prior_foreign=ctx.value,
        shock_pred=shock_pred,
        foreign_sell_threshold=foreign_sell_threshold,
        apply_foreign_flow_gate=ctx.apply_foreign_flow_gate,
    )
    if ctx.gate_mode == "skipped_stale_forward":
        blocks = list(blocks) + ["flow_gate_skipped_stale_forward"]
    return ctx, allow, blocks


def flow_gate_policy_from_rules(rules: dict[str, Any] | None) -> dict[str, Any]:
    pol = (rules or {}).get("forward_flow_gate_policy_v1")
    if isinstance(pol, dict):
        return pol
    return {"max_lag_calendar_days": DEFAULT_MAX_LAG_CALENDAR_DAYS}


def max_lag_from_rules(rules: dict[str, Any] | None) -> int:
    pol = flow_gate_policy_from_rules(rules)
    try:
        return int(pol.get("max_lag_calendar_days") or DEFAULT_MAX_LAG_CALENDAR_DAYS)
    except (TypeError, ValueError):
        return DEFAULT_MAX_LAG_CALENDAR_DAYS


def summarize_flow_gate_usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from collections import Counter

    modes = Counter(str(r.get("flow_gate_mode") or "unknown") for r in rows)
    block_reasons = Counter(
        b
        for r in rows
        for b in ((r.get("blocks") or "").split(";") if r.get("blocks") else [])
        if b
    )
    return {"flow_gate_mode_counts": dict(modes), "block_counts": dict(block_reasons)}
