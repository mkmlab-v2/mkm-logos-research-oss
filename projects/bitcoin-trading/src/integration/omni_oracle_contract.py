#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Omni-Oracle contract constants for integration stability.

This file is intentionally independent from prophecy logic to keep the
router/evaluation/integration track synchronized with API schema changes.
"""
from __future__ import annotations

from typing import Any, Dict, List

CONTRACT_VERSION = "omni-oracle.v1"

TRANSITION_PRIORS_KEYS: List[str] = [
    "current_regime_state",
    "markov_transition",
    "likelihood",
    "prophecy",
    "prior_bias",
]

DOMAIN_INPUT_KEYS: Dict[str, List[str]] = {
    "health": [
        "stress_score",
        "sleep_quality",
        "inflammation_score",
        "activity_score",
        "social_support",
    ],
    "crypto": [
        "price_change_24h",
        "realized_volatility",
        "funding_rate",
        "open_interest_change",
        "liquidity_delta",
    ],
    "macro": ["extras"],
    "general": ["extras"],
}

TRANSITION_OUTPUT_KEYS: List[str] = [
    "domain",
    "predicted_t_plus_1",
    "effective_exogenous_factors",
    "baseline_probability",
    "regime_shift_probability",
    "recommended_action",
]


def build_transition_request(
    *,
    domain: str,
    current_state: Dict[str, float],
    exogenous_factors: Dict[str, float] | None = None,
    priors: Dict[str, Any] | None = None,
    domain_input: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Build a contract-safe transition request payload.
    """
    return {
        "domain": domain,
        "current_state": current_state,
        "exogenous_factors": exogenous_factors or {},
        "priors": priors or {},
        "domain_input": domain_input or {},
        "contract_version": CONTRACT_VERSION,
    }
