#!/usr/bin/env python3
"""Build concept_bridge artifacts terminating at themed distill anchor verses."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref

ART = ROOT / "docs/final/artifacts"
PRESETS = ART / "LOGOS_TRACK_B_THEME_PRESETS_V1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None


def _vr_node_id(vid: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", vid).strip("_").lower()
    return f"vr_{safe}"


def _anchor_verse_ids(theme_id: str) -> list[str]:
    distill = _load(ART / f"logos_deep_research_distill_{theme_id}_citation_lock_latest.json")
    if not distill:
        distill = _load(ART / f"logos_deep_research_distill_{theme_id}_latest.json")
    if not distill:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for ref in distill.get("evidence_refs") or []:
        if not isinstance(ref, dict):
            continue
        vid = canonical_verse_ref(str(ref.get("verse_id") or ""))
        if vid and vid not in seen:
            seen.add(vid)
            out.append(vid)
    return out


def build_bridge(theme_id: str, *, max_paths: int) -> dict[str, Any]:
    presets = _load(PRESETS) or {}
    theme = (presets.get("themes") or {}).get(theme_id) or {}
    title = str(theme.get("title_ko") or theme_id)
    query_ko = str(theme.get("graphrag_query_ko") or title)
    anchors = _anchor_verse_ids(theme_id)
    if not anchors:
        raise SystemExit(f"no anchors for theme: {theme_id}")

    concept_id = f"concept:themed_{theme_id}"
    mc_id = f"mc_{theme_id}"
    func_id = f"func_{theme_id}_citation_anchor"
    lp_id = f"lp_{theme_id}_distill_proxy"

    nodes: list[dict[str, Any]] = [
        {
            "node_id": mc_id,
            "kind": "modern_concept",
            "label_ko": title,
            "rationale_ko": query_ko,
        },
        {
            "node_id": func_id,
            "kind": "function",
            "label_ko": "증거 앵커 역추적",
            "rationale_ko": "citation-lock distill anchor wiring (B-track, pedagogical proxy only)",
        },
        {
            "node_id": lp_id,
            "kind": "lemma_proxy",
            "label_ko": f"{title} 원어 앵커",
            "rationale_ko": query_ko,
        },
    ]
    paths: list[dict[str, Any]] = []
    for vid in anchors[:max_paths]:
        nid = _vr_node_id(vid)
        nodes.append(
            {
                "node_id": nid,
                "kind": "verse_ref",
                "verse_id": vid,
                "label_ko": vid.replace(".", " "),
            }
        )
        paths.append(
            {
                "path_id": f"path_themed_{theme_id}_{nid}",
                "steps": [mc_id, func_id, lp_id, nid],
                "note_ko": f"[HYPO] {query_ko} — distill anchor {vid} (themed organic wiring).",
            }
        )

    return {
        "schema": "logos_concept_bridge_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_prophecy_claim": True,
            "generation_method": "themed_distill_anchor_wiring_v1",
            "human_reviewed": False,
            "theme_id": theme_id,
        },
        "query": {"concept_id": concept_id, "label_ko": query_ko},
        "nodes": nodes,
        "paths": paths,
        "graph_rag_hooks": {"seed_verse_ids": anchors[:max_paths]},
        "known_limitations": [
            "Themed anchor paths wire distill citation-lock verses for GraphRAG organic recall — not theological claims.",
            "B-track only; do not promote to Track A or external copy.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--theme", required=True, help="dan_aramaic | john_1_logos")
    ap.add_argument("--max-paths", type=int, default=24)
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="default: docs/final/artifacts/logos_concept_bridge_themed_<theme>_v1_latest.json",
    )
    args = ap.parse_args()

    doc = build_bridge(args.theme.strip(), max_paths=args.max_paths)
    out = args.out or (ART / f"logos_concept_bridge_themed_{args.theme.strip()}_v1_latest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "theme": args.theme,
                "paths": len(doc.get("paths") or []),
                "out": str(out.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
