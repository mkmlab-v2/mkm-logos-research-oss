"""Router Psalm / hope-path verse stubs for showroom slice ([HYPO])."""

from __future__ import annotations

from typing import Any

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

THEME_ID = "theme::hope_endurance_psalm"
THEME_LABEL = "hope · endurance · psalm"


def _psalm_verse_id(ref: str) -> str:
    return f"showroom_psalm_verse::{canonical_verse_ref(ref)}"


def collect_psalm_refs_from_presets(presets_doc: dict[str, Any] | None) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for preset in (presets_doc or {}).get("presets") or []:
        rp = preset.get("router_path_v1") or {}
        for raw in rp.get("verse_refs") or []:
            canon = canonical_verse_ref(str(raw))
            if not canon.startswith("Ps."):
                continue
            if canon not in seen:
                seen.add(canon)
                refs.append(canon)
    return refs


def default_psalm_router_refs() -> list[str]:
    return [
        "Ps.27.14",
        "Ps.23.3",
        "Ps.37.7",
        "Ps.89.28",
        "Ps.103.8",
    ]


def append_router_psalm_stubs(bundle: dict[str, Any], psalm_refs: list[str]) -> dict[str, Any]:
    """Append Psalm verse nodes + hope theme hub to an existing seed bundle."""
    if not psalm_refs:
        return bundle
    nodes: list[dict[str, Any]] = list(bundle.get("nodes") or [])
    edges: list[dict[str, Any]] = list(bundle.get("edges") or [])
    node_ids = set(bundle.get("node_ids") or [])
    verse_refs = list(bundle.get("verse_refs") or [])

    if THEME_ID not in node_ids:
        node_ids.add(THEME_ID)
        nodes.append(
            {
                "id": THEME_ID,
                "label": THEME_LABEL,
                "kind": "theme",
                "schema": "showroom_psalm_theme_node_v1",
                "hub_score": 0.9,
            }
        )

    for raw in psalm_refs:
        canon = canonical_verse_ref(raw)
        if not canon:
            continue
        vid = _psalm_verse_id(canon)
        if vid in node_ids:
            continue
        node_ids.add(vid)
        nodes.append(
            {
                "id": vid,
                "label": canon,
                "ref": canon,
                "kind": "verse",
                "schema": "showroom_psalm_verse_node_v1",
                "hub_score": 0.86,
                "theme_id": THEME_ID,
            }
        )
        edges.append(
            {
                "src": THEME_ID,
                "dst": vid,
                "edge_type": "hope_psalm",
                "weight": 0.88,
            }
        )
        if canon not in verse_refs:
            verse_refs.append(canon)

    # dedupe edges
    seen_e: set[tuple[str, str, str]] = set()
    edges_out: list[dict[str, Any]] = []
    for e in edges:
        key = (e["src"], e["dst"], e.get("edge_type") or "link")
        if key in seen_e:
            continue
        seen_e.add(key)
        edges_out.append(e)

    out = dict(bundle)
    out["nodes"] = nodes
    out["edges"] = edges_out
    out["node_ids"] = sorted(node_ids)
    out["verse_refs"] = verse_refs
    out["psalm_router_refs"] = [canonical_verse_ref(r) for r in psalm_refs]
    out["psalm_verse_count"] = sum(1 for n in nodes if str(n.get("id", "")).startswith("showroom_psalm_verse::"))
    return out
