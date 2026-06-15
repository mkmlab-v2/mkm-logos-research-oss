#!/usr/bin/env python3
"""Track A / B-track routing kwargs for v2 Trust Packet compress (Fact-Lock)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
DECISION = ROOT / "docs/final/artifacts/MULTILENS_ULTRA_COMPRESSION_DECISION_V1.json"
SIGNOFF = ROOT / "docs/final/artifacts/multilens_ultra_compression_track_a_promotion_signoff_v1_latest.json"
LOW_SAVING_SWEEP = ROOT / "docs/final/artifacts/compression_low_saving_local_cap_sweep_v1_latest.json"
HEALTH_COMMANDER_APPROVAL = (
    ROOT / "docs/final/artifacts/mkm_inter_agent_health_domain_commander_approval_v1_latest.json"
)

RoutingProfile = Literal["default", "track_a_promoted", "b_track_domain_relax", "candidate_pool_on"]

CANDIDATE_POOL_ON = (
    ROOT / "docs/final/artifacts/compression_candidate_pool_on_track_a_candidate_v1_latest.json"
)

ROUTING_EVAL_EXCLUDE_KEYS = frozenset(
    {
        "routing_profile",
        "promotion_signoff_path",
        "sweep_pointer",
        "note",
        "hypothesis_tier",
        "research_only",
        "routing_profile_degraded",
        "health_commander_approval_path",
        "approved_variant_id",
        "candidate_artifact_path",
        "candidate_id",
    }
)


def routing_profile_eval_kwargs(profile: RoutingProfile) -> dict[str, Any]:
    """Kwargs safe to pass to evaluate_report (metadata stripped)."""
    return {k: v for k, v in routing_profile_kwargs(profile).items() if k not in ROUTING_EVAL_EXCLUDE_KEYS}


@lru_cache(maxsize=1)
def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def resolve_v2_case_id(client_request_id: str | None) -> str:
    cid = (client_request_id or "").strip()
    return cid if cid else "v2-trust-packet"


@lru_cache(maxsize=1)
def decision_selected_profile() -> dict[str, Any]:
    doc = _load_json(DECISION)
    sel = doc.get("selected_candidate")
    return sel if isinstance(sel, dict) else {}


def promotion_signoff_run_config() -> dict[str, Any] | None:
    doc = _load_json(SIGNOFF)
    cfg = doc.get("selected_run_config")
    return cfg if isinstance(cfg, dict) else None


def health_commander_approval_doc() -> dict[str, Any] | None:
    doc = _load_json(HEALTH_COMMANDER_APPROVAL)
    if not doc.get("commander_approved"):
        return None
    return doc


def routing_profile_kwargs(profile: RoutingProfile) -> dict[str, Any]:
    """Extra evaluate_report kwargs for v2 compress (not full report args)."""
    if profile == "default":
        return {}
    if profile == "track_a_promoted":
        cfg = promotion_signoff_run_config()
        if not cfg:
            return {"routing_profile_degraded": "signoff_missing"}
        overrides = cfg.get("domain_relaxed_max_saving_overrides") or {}
        allow = cfg.get("domain_relaxed_max_saving_case_allowlist")
        exclude = cfg.get("domain_relaxed_max_saving_exclude_case_ids")
        kw: dict[str, Any] = {
            "routing_profile": profile,
            "promotion_signoff_path": SIGNOFF.relative_to(ROOT).as_posix(),
        }
        if isinstance(overrides, dict) and overrides:
            kw["domain_relaxed_max_saving_overrides"] = {str(k): float(v) for k, v in overrides.items()}
        if isinstance(allow, list) and allow:
            kw["domain_relaxed_max_saving_case_allowlist"] = frozenset(str(x) for x in allow)
        if isinstance(exclude, list) and exclude:
            kw["domain_relaxed_max_saving_exclude_case_ids"] = frozenset(str(x) for x in exclude)
        return kw
    if profile == "b_track_domain_relax":
        approval = health_commander_approval_doc()
        if approval:
            cfg = approval.get("approved_run_config")
            cfg = cfg if isinstance(cfg, dict) else {}
            overrides = dict(cfg.get("domain_relaxed_max_saving_overrides") or {})
            overrides.setdefault("ssot", 0.45)
            return {
                "routing_profile": profile,
                "research_only": True,
                "hypothesis_tier": "B",
                "domain_relaxed_max_saving_overrides": overrides,
                "domain_relaxed_max_saving_case_allowlist": None,
                "health_commander_approval_path": HEALTH_COMMANDER_APPROVAL.relative_to(ROOT).as_posix(),
                "approved_variant_id": approval.get("approved_variant_id"),
                "note": (
                    "B-track health/hangul caps from commander-approved candidate — "
                    "not Track A bench allowlist."
                ),
            }
        sweep = _load_json(LOW_SAVING_SWEEP)
        best = sweep.get("best_by_floor_then_saving") or {}
        knobs = best.get("knobs") if isinstance(best.get("knobs"), dict) else {}
        overrides = dict(knobs.get("domain_relaxed_max_saving_overrides") or {})
        overrides.setdefault("ssot", 0.45)
        overrides.setdefault("health", 0.50)
        overrides.setdefault("hangul", 0.50)
        return {
            "routing_profile": profile,
            "research_only": True,
            "hypothesis_tier": "B",
            "domain_relaxed_max_saving_overrides": overrides,
            "domain_relaxed_max_saving_case_allowlist": None,
            "sweep_pointer": LOW_SAVING_SWEEP.relative_to(ROOT).as_posix(),
            "note": "B-track open domain caps — not Track A bench allowlist; do not cite as production default.",
        }
    if profile == "candidate_pool_on":
        cand = _load_json(CANDIDATE_POOL_ON)
        rc = cand.get("run_config") if isinstance(cand.get("run_config"), dict) else {}
        overrides = dict(rc.get("domain_relaxed_max_saving_overrides") or {})
        allow = rc.get("domain_relaxed_max_saving_case_allowlist")
        kw_pool: dict[str, Any] = {
            "routing_profile": profile,
            "research_only": True,
            "hypothesis_tier": "B",
            "enable_candidate_pool_expansion": True,
            "use_master_codebook_lexicon_v1": bool(rc.get("use_master_codebook_lexicon_v1", True)),
            "apply_gematria_4d_bridge_policy": bool(rc.get("apply_gematria_4d_bridge_policy", False)),
            "candidate_artifact_path": CANDIDATE_POOL_ON.relative_to(ROOT).as_posix(),
            "candidate_id": cand.get("candidate_id") or "candidate_pool_on",
            "note": (
                "41k combo grid best arm — candidate pool expansion + ACTIVE-parity relaxed ssot. "
                "research_only; does not overwrite Track A ACTIVE."
            ),
        }
        if overrides:
            kw_pool["domain_relaxed_max_saving_overrides"] = {str(k): float(v) for k, v in overrides.items()}
        if isinstance(allow, list) and allow:
            kw_pool["domain_relaxed_max_saving_case_allowlist"] = frozenset(str(x) for x in allow)
        if not cand:
            kw_pool["routing_profile_degraded"] = "candidate_pool_artifact_missing"
        return kw_pool
    return {}
