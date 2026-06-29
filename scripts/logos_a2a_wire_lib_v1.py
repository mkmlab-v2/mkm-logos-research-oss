"""Logos A2A wire helpers — vector_4d + anchor ids only ([HYPO] / B-track)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BRIDGE = Path("docs/final/artifacts/logos_cosmic_anchor_graph_bridge_v1_latest.json")
STATE_4D = Path("docs/final/artifacts/logos_4d_state_v1_latest.json")
ROUTER_BUNDLE = Path("reports/logos_router_regression_bundle_v1_latest.json")
NARRATIVE_EVAL = Path("docs/final/artifacts/logos_narrative_path_eval_v1_latest.json")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    return doc if isinstance(doc, dict) else {}


def load_logos_wire_refs(root: Path, *, max_anchors: int = 3) -> dict[str, Any]:
    """Minimal Logos refs for inter-agent wire — no full corpus."""
    bridge = _read_json(root / BRIDGE)
    state = _read_json(root / STATE_4D)
    bundle = _read_json(root / ROUTER_BUNDLE)
    narrative = _read_json(root / NARRATIVE_EVAL)

    anchor_ids: list[str] = []
    vector_4d: dict[str, float] | None = None
    for row in bridge.get("per_anchor") or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("anchor_id") or "")
        v4 = row.get("vector_4d")
        if aid and isinstance(v4, dict) and all(k in v4 for k in ("S", "L", "K", "M")):
            anchor_ids.append(aid)
            if vector_4d is None:
                vector_4d = {k: round(float(v4[k]), 6) for k in ("S", "L", "K", "M")}
        if len(anchor_ids) >= max_anchors:
            break

    if vector_4d is None:
        vector_4d = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}

    quadrant = state.get("quadrant_info") if isinstance(state.get("quadrant_info"), dict) else {}
    narrative_oracle = (
        state.get("narrative_oracle") if isinstance(state.get("narrative_oracle"), dict) else {}
    )
    ne = narrative.get("summary") if isinstance(narrative.get("summary"), dict) else {}

    return {
        "kernel_recipe_id": str(bridge.get("kernel_recipe_id") or "gematria_bridge_v1"),
        "vector_4d": vector_4d,
        "anchor_ids": anchor_ids,
        "regime_tag": str(quadrant.get("regime_tag") or "WATCH"),
        "policy_tag": str(narrative_oracle.get("policy_tag") or "[NON_GATING]"),
        "router_hit_rate": ne.get("router_hit_rate"),
        "bloom_cap": bundle.get("bloom_cap"),
        "send_gate": str(bundle.get("send_gate") or narrative.get("send_gate") or "HOLD"),
        "research_only": True,
        "track_a_blocked": True,
    }


def build_logos_wire_plaintext(refs: dict[str, Any]) -> str:
    """Plaintext long enough for v2 compress skip threshold (>=32 tok)."""
    v4 = refs.get("vector_4d") or {}
    anchors = ", ".join(refs.get("anchor_ids") or [])
    tail = (
        "gematria_bridge_v1 cosmic anchor graph resonance narrative router gold eval "
        "structural gate only research_only send_gate HOLD no Track A live trigger "
        "[NON_GATING] pedagogical isomorphism [HYPO] "
    )
    head = (
        f"Logos oracle B-track A2A wire handoff [HYPO] research_only. "
        f"vector_4d S={v4.get('S')} L={v4.get('L')} K={v4.get('K')} M={v4.get('M')}. "
        f"anchor_ids={anchors}. regime_tag={refs.get('regime_tag')} "
        f"policy_tag={refs.get('policy_tag')}. router_hit_rate structural "
        f"{refs.get('router_hit_rate')} bloom_cap={refs.get('bloom_cap')} "
        f"kernel_recipe_id={refs.get('kernel_recipe_id')}. "
    )
    return (head + tail * 4).strip()
