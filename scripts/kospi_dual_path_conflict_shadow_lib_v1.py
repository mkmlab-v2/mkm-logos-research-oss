#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dual-path conflict router: per_date baseline vs static bear rescue [HYPO][research_only]."""

from __future__ import annotations

from typing import Any

from scripts.build_kospi_june2026_channel_input_audit_v1 import _momentum_from_row
from scripts.kospi_composite_shadow_lib_v1 import composite_bear_conditional

FOREIGN_SELL_THRESHOLD = -25000.0
FOREIGN_WEAK_FLOW_GUARD = -5000.0


def suppressed_bear_channel_count(cal_row: dict[str, Any]) -> int:
    blend = cal_row.get("blend") if isinstance(cal_row.get("blend"), dict) else {}
    n = 0
    for ch in blend.get("channels") or []:
        if not isinstance(ch, dict):
            continue
        if str(ch.get("direction")) == "bear" and float(ch.get("weight") or 0) == 0:
            n += 1
    return n


def per_date_lens_bull_consensus(per_static_lenses: dict[str, Any]) -> bool:
    my_dir = str((per_static_lenses.get("myeongni_independent") or {}).get("direction") or "neutral")
    sa_dir = str((per_static_lenses.get("sasang") or {}).get("direction") or "neutral")
    return my_dir == "bull" and sa_dir == "bull"


def detect_momentum_perdate_bull_conflict(
    cal_row: dict[str, Any],
    per_static_lenses: dict[str, Any],
    *,
    active_direction: str,
    min_suppressed_bear: int = 2,
) -> tuple[bool, list[str]]:
    """Morning-feasible conflict: momentum bear vs per_date myeongni+sasang bull while active bull."""
    reasons: list[str] = []
    mom = _momentum_from_row(cal_row)
    if mom != "bear":
        return False, ["momentum_not_bear"]
    if str(active_direction).lower() != "bull":
        return False, ["active_not_bull"]
    if not per_date_lens_bull_consensus(per_static_lenses):
        return False, ["per_date_lens_not_bull_consensus"]
    suppressed = suppressed_bear_channel_count(cal_row)
    if suppressed < min_suppressed_bear:
        return False, [f"suppressed_bear_lt_{min_suppressed_bear}"]
    reasons.extend(
        [
            "momentum_bear",
            "per_date_bull_consensus",
            "active_bull",
            f"suppressed_bear_{suppressed}",
        ]
    )
    return True, reasons


def detect_macro_bear_session_bull_trap(
    cal_row: dict[str, Any],
    per_static_lenses: dict[str, Any],
    *,
    active_direction: str,
    min_suppressed_bear: int = 2,
) -> tuple[bool, list[str]]:
    """Tier B: per_date macro bear vs session bull trap while active bull (06-19 class)."""
    if str(active_direction).lower() != "bull":
        return False, ["active_not_bull"]
    session = str(cal_row.get("session_mapping_target") or "").lower()
    if session != "bull":
        return False, ["session_not_bull"]
    macro_dir = str((per_static_lenses.get("macro") or {}).get("direction") or "neutral")
    if macro_dir != "bear":
        return False, ["per_date_macro_not_bear"]
    suppressed = suppressed_bear_channel_count(cal_row)
    if suppressed < min_suppressed_bear:
        return False, [f"suppressed_bear_lt_{min_suppressed_bear}"]
    return True, [
        "per_date_macro_bear",
        "session_bull",
        "active_bull",
        f"suppressed_bear_{suppressed}",
    ]


def should_apply_tier_a_bear_rescue(
    *,
    tier_a_conflict: bool,
    prior_foreign_net_buy: float | None,
    foreign_sell_threshold: float = FOREIGN_SELL_THRESHOLD,
    foreign_weak_guard: float = FOREIGN_WEAK_FLOW_GUARD,
) -> tuple[bool, list[str]]:
    """Flow guard: skip tier-A bear rescue on weak foreign outflow (06-09 false-positive fix)."""
    if not tier_a_conflict:
        return False, ["tier_a_not_detected"]
    foreign_sell = prior_foreign_net_buy is not None and prior_foreign_net_buy < foreign_sell_threshold
    if foreign_sell:
        return True, ["foreign_sell_stress"]
    weak_flow = prior_foreign_net_buy is not None and prior_foreign_net_buy > foreign_weak_guard
    if weak_flow:
        return False, ["foreign_flow_weak_guard"]
    return True, ["foreign_flow_stress_ok"]


def dual_path_v2_direction(
    *,
    tier_a_apply: bool,
    tier_b_conflict: bool,
    per_date_baseline_dir: str,
    static_bear_triple_dir: str,
    macro_off_per_date_dir: str,
) -> tuple[str, str]:
    """Returns (direction, route_id)."""
    if tier_a_apply:
        return static_bear_triple_dir, "tier_a_momentum_bear_rescue"
    if tier_b_conflict:
        return macro_off_per_date_dir, "tier_b_macro_bear_trap"
    return per_date_baseline_dir, "per_date_baseline_with_macro"


def dual_path_direction(
    *,
    conflict: bool,
    per_date_active_dir: str,
    static_bear_triple_dir: str,
    composite_dir: str | None = None,
    router_mode: str = "bear_triple_on_conflict",
) -> str:
    if not conflict:
        return per_date_active_dir
    if router_mode == "composite_on_conflict" and composite_dir is not None:
        return composite_dir
    return static_bear_triple_dir


def build_composite_for_conflict(
    *,
    active: str,
    bear_triple: str,
    coord_raw: str,
    unlock_candidate: bool,
    cond_allow: bool,
) -> str:
    return composite_bear_conditional(
        v2=active,
        bear_triple=bear_triple,
        coord_raw=coord_raw,
        unlock_candidate=unlock_candidate,
        cond_allow=cond_allow,
    )
