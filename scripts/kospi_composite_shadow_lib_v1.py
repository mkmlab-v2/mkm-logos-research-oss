#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Composite shadow direction helpers [HYPO][research_only]."""

from __future__ import annotations


def composite_bear_conditional(
    *,
    v2: str,
    bear_triple: str,
    coord_raw: str,
    unlock_candidate: bool,
    cond_allow: bool,
) -> str:
    """Default approved shadow: unlock when allowed; else bear_triple."""
    if unlock_candidate and cond_allow:
        return coord_raw
    if unlock_candidate and not cond_allow:
        return v2
    return bear_triple


def composite_active_hold(
    *,
    v2: str,
    bear_triple: str,
    coord_raw: str,
    unlock_candidate: bool,
    cond_allow: bool,
) -> str:
    """Fallback A/B arm: non-unlock days keep active (no forced bear_triple)."""
    if unlock_candidate and cond_allow:
        return coord_raw
    return v2


# backward-compatible alias
composite_direction = composite_bear_conditional
