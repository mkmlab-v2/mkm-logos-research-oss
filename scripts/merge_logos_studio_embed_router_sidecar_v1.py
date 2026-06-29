#!/usr/bin/env python3
"""Merge embed-demo allowlist presets into QA presets + router sidecar (B1b).

Ensures LOGOS_EMBED_DEMO_PRESET_ALLOWLIST presets exist in qa_presets and
router sidecar with verse_refs/node_ids for stub patch + coverage gate.

Reproduce:
  py scripts/merge_logos_studio_embed_router_sidecar_v1.py
  py scripts/patch_logos_studio_graph_slice_router_verse_stubs_v1.py
  py scripts/check_logos_studio_graph_slice_router_coverage_v1.py
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from compute_logos_reasoning_path_v1 import compute_reasoning_path  # noqa: E402
from logos_studio_preset_graph_helpers_v1 import chapter_node_ids, verse_node_ids  # noqa: E402
from logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402
from patch_logos_studio_graph_slice_router_verse_stubs_v1 import STUDIO_PRESET_ALLOWLIST  # noqa: E402

DEFAULT_PRESETS = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"
DEFAULT_SIDECAR = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_router_sidecar_v1_latest.json"
DEFAULT_GRAPH = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_TAXONOMY = ROOT / "docs/final/artifacts/logos_studio_preset_taxonomy_v1_latest.json"

EMBED_FORCE_CHAPTER: dict[str, tuple[str, int, str, list[str]]] = {
    "topic_ezra_1_anchor": (
        "Ezra",
        1,
        "에스라 1장 · 귀환 (Ezra 1)",
        ["에스라 1", "ezra 1", "귀환", "return", "topic_ezra_1_anchor"],
    ),
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_embed_presets(
    presets_doc: dict[str, Any],
    graph_doc: dict[str, Any],
    taxonomy_doc: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    presets = list(presets_doc.get("presets") or [])
    by_id = {str(p.get("id")): i for i, p in enumerate(presets) if p.get("id")}
    upserted: list[str] = []

    for preset_id in STUDIO_PRESET_ALLOWLIST:
        if preset_id in by_id:
            continue
        if preset_id in EMBED_FORCE_CHAPTER:
            book, chapter, prompt_ko, keywords = EMBED_FORCE_CHAPTER[preset_id]
            highlights = chapter_node_ids(graph_doc, book, chapter)
            refs = sorted(
                {
                    canonical_verse_ref(str(n.get("ref") or ""))
                    for n in graph_doc.get("nodes") or []
                    if str(n.get("ref") or "").startswith(f"{book}.{chapter}.")
                }
            )
            refs = [r for r in refs if r]
            if not highlights and not refs:
                continue
            entry = {
                "id": preset_id,
                "preset_kind": "verse_anchor",
                "prompt_ko": prompt_ko,
                "answer_ko": (
                    f"[HYPO] 그래프 슬라이스 **{book}.{chapter}** 장 앵커 프리셋입니다. "
                    f"embed allowlist · research_only · NON_GATING."
                ),
                "answer_ko_product": f"[HYPO] Graph slice {book}.{chapter} anchor · embed demo · NON_GATING.",
                "highlight_node_ids": highlights[:48],
                "keywords": keywords + [f"{book.lower()}.{chapter}", f"{book} {chapter}"],
                "router_path_v1": {
                    "schema_version": "logos_router_path_v1",
                    "verse_refs": refs[:8] or [f"{book}.{chapter}.1"],
                    "research_only": True,
                    "send_gate": "HOLD",
                },
            }
            presets.append(entry)
            by_id[preset_id] = len(presets) - 1
            upserted.append(preset_id)
            continue

        card = (taxonomy_doc.get("insight_cards") or {}).get(preset_id) or {}
        anchors = [canonical_verse_ref(str(r)) for r in (card.get("verse_anchors") or [])]
        anchors = [r for r in anchors if r]
        if not anchors:
            continue
        node_ids = verse_node_ids(graph_doc, set(anchors))
        entry = {
            "id": preset_id,
            "preset_kind": "embed_taxonomy_fallback",
            "prompt_ko": card.get("one_liner_ko") or preset_id,
            "answer_ko": f"[HYPO] {card.get('one_liner_ko') or preset_id} · embed allowlist · NON_GATING.",
            "highlight_node_ids": node_ids[:48],
            "keywords": [preset_id],
            "router_path_v1": {
                "schema_version": "logos_router_path_v1",
                "verse_refs": anchors,
                "research_only": True,
                "send_gate": "HOLD",
            },
        }
        presets.append(entry)
        by_id[preset_id] = len(presets) - 1
        upserted.append(preset_id)

    out = dict(presets_doc)
    out["presets"] = presets
    out["embed_allowlist_merge_at_utc"] = _utc_now()
    return out, upserted


def _router_path_from_preset(
    preset: dict[str, Any],
    graph_doc: dict[str, Any],
) -> dict[str, Any] | None:
    rp = dict(preset.get("router_path_v1") or {})
    verse_refs = [canonical_verse_ref(str(r)) for r in (rp.get("verse_refs") or [])]
    verse_refs = [r for r in verse_refs if r]
    if not verse_refs:
        return None
    node_ids = verse_node_ids(graph_doc, set(verse_refs))
    if not node_ids:
        node_ids = list(preset.get("highlight_node_ids") or [])[:48]
    reasoning = (
        compute_reasoning_path(graph_doc, node_ids, max_nodes=min(8, max(3, len(node_ids))))
        if len(node_ids) >= 1
        else None
    )
    return {
        "schema_version": "showroom_qa_router_path_v1",
        "preset_id": str(preset.get("id") or ""),
        "source": "merge_logos_studio_embed_router_sidecar_v1",
        "query": str(preset.get("prompt_ko") or ""),
        "path_id": rp.get("path_id"),
        "note_ko": rp.get("note_ko")
        or "[HYPO] embed allowlist router path — citation lock·학파 병렬만 · NON_GATING · research_only.",
        "path_steps": list(rp.get("path_steps") or []),
        "match_score": int(rp.get("match_score") or 0),
        "bridges_matched": int(rp.get("bridges_matched") or 0),
        "verse_refs": verse_refs,
        "node_ids": node_ids,
        "reasoning_path_v1": reasoning or preset.get("reasoning_path_v1"),
        "research_only": True,
        "send_gate": "HOLD",
    }


def merge_embed_sidecar(
    presets_doc: dict[str, Any],
    sidecar_doc: dict[str, Any],
    graph_doc: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    presets = list(presets_doc.get("presets") or [])
    presets_by_id = {str(p.get("id")): p for p in presets if p.get("id")}
    sidecar_presets = dict(sidecar_doc.get("presets") or {})
    merged_ids: list[str] = []

    for preset_id in STUDIO_PRESET_ALLOWLIST:
        preset = presets_by_id.get(preset_id)
        if not preset:
            continue
        rp = _router_path_from_preset(preset, graph_doc)
        if not rp or not (rp.get("verse_refs") or rp.get("node_ids")):
            continue
        sidecar_presets[preset_id] = {
            "router_summary": {
                "bridges_matched": rp.get("bridges_matched", 0),
                "paths": 1 if rp.get("path_id") else 0,
                "verse_ids": len(rp.get("verse_refs") or []),
            },
            "router_path_v1": rp,
        }
        preset["router_path_v1"] = rp
        if rp.get("reasoning_path_v1"):
            preset["reasoning_path_v1"] = rp["reasoning_path_v1"]
        merged_ids.append(preset_id)

    sidecar_out = dict(sidecar_doc)
    sidecar_out["presets"] = sidecar_presets
    sidecar_out["preset_count"] = len(sidecar_presets)
    sidecar_out["embed_allowlist_merge_at_utc"] = _utc_now()
    sidecar_out["research_only"] = True

    presets_out = dict(presets_doc)
    presets_out["presets"] = presets
    return presets_out, sidecar_out, merged_ids


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--graph-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--taxonomy-json", type=Path, default=DEFAULT_TAXONOMY)
    args = ap.parse_args()

    presets_doc = _load(args.presets_json)
    sidecar_doc = _load(args.sidecar_json) if args.sidecar_json.is_file() else {
        "schema_version": "showroom_meaning_topology_qa_router_sidecar_v1",
        "presets": {},
    }
    graph_doc = _load(args.graph_json)
    taxonomy_doc = _load(args.taxonomy_json) if args.taxonomy_json.is_file() else {"insight_cards": {}}

    presets_doc, upserted = _ensure_embed_presets(presets_doc, graph_doc, taxonomy_doc)
    presets_doc, sidecar_doc, merged = merge_embed_sidecar(presets_doc, sidecar_doc, graph_doc)

    args.presets_json.write_text(json.dumps(presets_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.sidecar_json.parent.mkdir(parents=True, exist_ok=True)
    args.sidecar_json.write_text(json.dumps(sidecar_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    mirror_presets = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json"
    mirror_sidecar = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_router_sidecar_v1.json"
    mirror_presets.parent.mkdir(parents=True, exist_ok=True)
    mirror_presets.write_text(json.dumps(presets_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mirror_sidecar.write_text(json.dumps(sidecar_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "upserted_presets": upserted,
                "merged_sidecar_ids": merged,
                "sidecar_preset_count": sidecar_doc.get("preset_count"),
                "allowlist": list(STUDIO_PRESET_ALLOWLIST),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
