#!/usr/bin/env python3
"""B-track hybrid codec router — assistant-turn / economy→literal fallback [HYPO].

Shared by v2 Trust Packet stub and WTT CS PoC runners. research_only · not Track A.
"""

from __future__ import annotations

from typing import Any, Literal

HybridCodecRouter = Literal["off", "assistant_literal", "economy_fallback"]

WTT_CS_ECONOMY_SHORT_THRESHOLD = 30
WTT_CS_ECONOMY_SHORT_MAX_SAVING = 0.20
HYBRID_CODEC_JACCARD_FLOOR = 0.73


def turn_count(session_turns: list[dict[str, Any]] | None) -> int:
    if not session_turns:
        return 0
    return len(session_turns)


def has_assistant_turn(session_turns: list[dict[str, Any]] | None) -> bool:
    if not session_turns:
        return False
    return any(
        isinstance(t, dict) and str(t.get("role") or "").lower() == "assistant" for t in session_turns
    )


def select_profile_turns_gte(
    session_turns: list[dict[str, Any]] | None,
    *,
    min_turns: int,
    literal_profile: str = "literal",
    default_profile: str = "economy",
) -> tuple[str, str]:
    if turn_count(session_turns) >= min_turns:
        return literal_profile, f"turn_count>={min_turns}"
    return default_profile, "economy_default"


def select_profile_assistant_literal(
    session_turns: list[dict[str, Any]] | None,
    *,
    literal_profile: str = "literal",
    default_profile: str = "economy",
) -> tuple[str, str]:
    if has_assistant_turn(session_turns):
        return literal_profile, "has_assistant_turn"
    return default_profile, "economy_default"


def economy_shortcap_kwargs(
    *,
    threshold: int | None = None,
    max_saving: float | None = None,
) -> dict[str, Any]:
    return {
        "short_context_token_threshold": threshold if threshold is not None else WTT_CS_ECONOMY_SHORT_THRESHOLD,
        "short_context_max_saving_rate": max_saving if max_saving is not None else WTT_CS_ECONOMY_SHORT_MAX_SAVING,
        "short_context_disable_min_saving_floor": True,
    }


def resolve_hybrid_codec_plan(
    *,
    router: HybridCodecRouter,
    session_turns: list[dict[str, Any]] | None,
    requested_profile: str,
    short_context_token_threshold: int | None,
    short_context_max_saving_rate: float | None,
) -> dict[str, Any]:
    """Resolve effective compression profile and shortcap for one compress attempt."""
    if router == "off":
        return {
            "router": router,
            "effective_profile": requested_profile,
            "route_reason": "router_off",
            "economy_shortcap": {
                "short_context_token_threshold": short_context_token_threshold,
                "short_context_max_saving_rate": short_context_max_saving_rate,
            },
            "research_only": False,
            "profiles_tried": [requested_profile],
            "fallback_used": False,
        }

    if router == "assistant_literal":
        profile, reason = select_profile_assistant_literal(session_turns)
        shortcap = economy_shortcap_kwargs(
            threshold=short_context_token_threshold,
            max_saving=short_context_max_saving_rate,
        )
        if profile == "literal":
            shortcap = {
                "short_context_token_threshold": None,
                "short_context_max_saving_rate": None,
            }
        return {
            "router": router,
            "effective_profile": profile,
            "route_reason": reason,
            "economy_shortcap": shortcap,
            "research_only": True,
            "hypothesis_tier": "B",
            "profiles_tried": [profile],
            "fallback_used": False,
        }

    if router == "economy_fallback":
        shortcap = economy_shortcap_kwargs(
            threshold=short_context_token_threshold,
            max_saving=short_context_max_saving_rate,
        )
        return {
            "router": router,
            "effective_profile": "economy",
            "route_reason": "economy_primary",
            "economy_shortcap": shortcap,
            "research_only": True,
            "hypothesis_tier": "B",
            "profiles_tried": ["economy"],
            "fallback_used": False,
            "fallback_profile": "literal",
        }

    raise ValueError(f"unknown hybrid_codec_router: {router}")


def hybrid_router_integrity_flags(plan: dict[str, Any]) -> dict[str, Any]:
    flags: dict[str, Any] = {
        "hybrid_codec_router": plan.get("router"),
        "hybrid_codec_route_reason": plan.get("route_reason"),
        "hybrid_codec_profiles_tried": list(plan.get("profiles_tried") or []),
        "hybrid_codec_fallback_used": bool(plan.get("fallback_used")),
    }
    if plan.get("research_only"):
        flags["hybrid_codec_research_only"] = True
        flags["hypothesis_tier"] = plan.get("hypothesis_tier") or "B"
    if plan.get("economy_attempt"):
        flags["hybrid_codec_economy_attempt"] = plan["economy_attempt"]
    return flags
