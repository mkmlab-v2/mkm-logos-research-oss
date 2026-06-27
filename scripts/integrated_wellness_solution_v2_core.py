# -*- coding: utf-8 -*-
"""Integrated Wellness Solution v2 — Tier 0–3 resolver + A-Code lexicon."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "final" / "schemas" / "integrated_wellness_solution_v2.schema.json"
ACODE_LEXICON_PATH = ROOT / "docs" / "final" / "artifacts" / "a_code_wellness_archetype_lexicon_v1.json"

SASANG_KO = {
    "taeyang": "태양인",
    "soyang": "소양인",
    "taeum": "태음인",
    "soeum": "소음인",
    "unknown": "미확정",
}

DEFAULT_RHYTHM_BY_SASANG = {
    "taeyang": "spark",
    "soyang": "flow",
    "taeum": "anchor",
    "soeum": "quiet",
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def pick_rhythm_band(profile: dict[str, Any]) -> str:
    sasang = profile.get("sasang_internal", "unknown")
    age_band = profile.get("computed_age_band", "unknown")
    growth = bool(profile.get("growth_phase"))

    if growth or age_band == "minor":
        if sasang == "soeum":
            return "restore"
        if sasang == "taeum":
            return "steady"
        return "flow"

    return DEFAULT_RHYTHM_BY_SASANG.get(sasang, "quiet")


def resolve_a_code(profile: dict[str, Any], lexicon: dict[str, Any]) -> dict[str, Any] | None:
    sasang = profile.get("sasang_internal", "unknown")
    rhythm = pick_rhythm_band(profile)
    for entry in lexicon.get("entries", []):
        if entry.get("sasang_internal") == sasang and entry.get("rhythm_band") == rhythm:
            return entry
    return None


def _policy_blocked(node: dict[str, Any], profile: dict[str, Any]) -> str | None:
    guards = node.get("policy_guards") or {}
    age_band = profile.get("computed_age_band")
    growth = bool(profile.get("growth_phase"))
    node_id = str(node.get("node_id") or "")

    blocked_bands = guards.get("blocked_if_age_band") or []
    if age_band in blocked_bands:
        return f"age_band={age_band}"

    if guards.get("blocked_if_growth_phase") and growth:
        return "growth_phase=true"

    required_bands = guards.get("required_if_age_band") or []
    if required_bands and age_band not in required_bands:
        return f"age_band={age_band} not in required {required_bands}"

    if guards.get("required_if_growth_phase") and not growth:
        return "growth_phase=false"

    if not growth and age_band != "minor":
        if node_id.startswith("policy_minor_") or node_id.startswith("action_minor_"):
            return "minor_only_node"

    return None


def _collect_suppressions_from_node(
    node: dict[str, Any],
    tier_label: str,
    suppressed: dict[str, dict[str, Any]],
) -> None:
    rules = node.get("conflict_rules") or {}
    trigger = node["node_id"]

    for target in rules.get("suppress_nodes") or []:
        if target not in suppressed:
            suppressed[target] = {
                "node_id": target,
                "reason": f"conflict_rules.suppress_nodes from {trigger}",
                "tier_blocked_by": tier_label,
                "triggered_by": trigger,
            }

    for tag in rules.get("suppress_tags") or []:
        suppressed[f"__tag__:{tag}"] = {
            "node_id": f"__tag__:{tag}",
            "reason": f"conflict_rules.suppress_tags tag={tag} from {trigger}",
            "tier_blocked_by": tier_label,
            "triggered_by": trigger,
        }


def _node_has_suppressed_tag(node: dict[str, Any], suppressed_tags: set[str]) -> str | None:
    tags = node.get("action_tags") or []
    for tag in tags:
        if f"__tag__:{tag}" in suppressed_tags:
            return tag
    return None


def resolve_integrated_wellness(seed: dict[str, Any], lexicon_path: Path | None = None) -> dict[str, Any]:
    """Run Tier 0–3 resolver; mutate copy with resolved_evidence_stream + suppression_log."""
    out = copy.deepcopy(seed)
    profile = out["client_profile"]
    nodes = out.get("evidence_nodes_seed") or []

    lex_path = lexicon_path or ACODE_LEXICON_PATH
    lexicon = load_json(lex_path) if lex_path.is_file() else {"entries": []}

    suppressed: dict[str, dict[str, Any]] = {}
    suppressed_tags: set[str] = set()

    tier_order = ["POLICY", "FACT", "ACTION", "HYPO", "NON_GATING"]
    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in tier_order}
    for node in nodes:
        tier = node.get("tier", "FACT")
        by_tier.setdefault(tier, []).append(node)

    # Tier 0: POLICY + policy_guards on all nodes
    for node in nodes:
        block_reason = _policy_blocked(node, profile)
        if block_reason:
            suppressed[node["node_id"]] = {
                "node_id": node["node_id"],
                "reason": f"policy_guard: {block_reason}",
                "tier_blocked_by": "Tier0",
                "triggered_by": "policy_guards",
            }

    for node in by_tier.get("POLICY", []):
        _collect_suppressions_from_node(node, "Tier0", suppressed)

    # Tier 1: FACT — pass through unless already suppressed
    # Tier 2: HYPO sasang — apply conflict_rules after FACT kept
    for node in by_tier.get("HYPO", []):
        if node["node_id"] not in suppressed:
            _collect_suppressions_from_node(node, "Tier2", suppressed)

    # Tier 3: cross-node ACTION conflicts (e.g. sasang suppresses hiit)
    for node in nodes:
        if node.get("tier") == "ACTION" and node["node_id"] not in suppressed:
            _collect_suppressions_from_node(node, "Tier3", suppressed)

    for key in list(suppressed.keys()):
        if key.startswith("__tag__:"):
            suppressed_tags.add(key)

    resolved: list[dict[str, Any]] = []
    for node in nodes:
        nid = node["node_id"]
        if nid in suppressed:
            continue
        hit_tag = _node_has_suppressed_tag(node, suppressed_tags)
        if hit_tag:
            suppressed[nid] = {
                "node_id": nid,
                "reason": f"action_tag={hit_tag} suppressed by Tier0 tag rule",
                "tier_blocked_by": "cross_node",
                "triggered_by": f"__tag__:{hit_tag}",
            }
            continue
        resolved.append(node)

    suppression_log = [
        v for k, v in suppressed.items() if not k.startswith("__tag__:")
    ]
    suppression_log.sort(key=lambda x: x["node_id"])

    a_entry = resolve_a_code(profile, lexicon)
    sasang = profile.get("sasang_internal", "unknown")

    lexicon_profile: dict[str, Any] = {
        "clinician_native": {
            "sasang_ko": SASANG_KO.get(sasang, "미확정"),
            "organ_pair_ko": (a_entry or {}).get("organ_pair_ko", ""),
        },
    }
    if a_entry:
        profile["a_code_consumer"] = a_entry["code_id"]
        lexicon_profile["consumer_a_code"] = {
            "code_id": a_entry["code_id"],
            "display_name_ko": a_entry["display_name_ko"],
            "display_name_en": a_entry["display_name_en"],
            "tagline_ko": a_entry["tagline_ko"],
        }
        lexicon_profile["psy_facade_optional"] = {
            "big5_hint": a_entry.get("big5_hint", {}),
            "disclaimer": lexicon.get(
                "disclaimer_ko",
                "not_a_psychometric_test",
            ),
        }

    out["resolved_evidence_stream"] = resolved
    out["suppression_log"] = suppression_log
    out["lexicon_profile"] = lexicon_profile

    return out


def validate_against_schema(doc: dict[str, Any], schema_path: Path | None = None) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema required for validation") from exc

    sp = schema_path or SCHEMA_PATH
    schema = load_json(sp)
    jsonschema.validate(instance=doc, schema=schema)
