#!/usr/bin/env python3
"""Dialectical insight layers per theme — thesis/antithesis/synthesis with verse_id lock [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_logos_llm_distill_citation_lock_v1 import (
    _validate_citations,
    build_narrative_stub_ko,
    try_ollama_distill_narrative,
)

THEMES = ("dan_aramaic", "john_1_logos")
OUT_DEFAULT = ROOT / "reports/logos_dialectical_insight_layers_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_distill(theme_id: str) -> dict[str, Any]:
    path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _load_xref_neighbors(theme_id: str, anchors: set[str]) -> list[str]:
    path = ROOT / "docs/final/artifacts/logos_themed_xref_edges_v1.jsonl"
    neighbors: set[str] = set()
    if not path.is_file():
        return []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        edge = json.loads(line)
        if edge.get("theme_id") != theme_id:
            continue
        s, d = str(edge.get("src_verse_id") or ""), str(edge.get("dst_verse_id") or "")
        if s in anchors and d not in anchors:
            neighbors.add(d)
        if d in anchors and s not in anchors:
            neighbors.add(s)
    return sorted(neighbors)[:12]


def _layer_stub(layer: str, theme_title: str, verse_ids: list[str]) -> str:
    vids = ", ".join(verse_ids[:6])
    return (
        f"[HYPO][{layer.upper()}] {theme_title} — "
        f"앵커 {len(verse_ids)}건({vids}) 기반 {layer} 층. "
        "교리·시장 단정 금지; NON_GATING."
    )


def _maybe_ollama(
    layer: str,
    evidence_refs: list[dict[str, Any]],
    *,
    theme_title: str,
    allowed_extra: list[str],
) -> dict[str, Any]:
    if os.environ.get("MKM_LOGOS_LLM_DISTILL_ENABLE", "").strip().lower() not in {"1", "true", "yes", "on"}:
        body = _layer_stub(layer, theme_title, [str(r.get("verse_id")) for r in evidence_refs[:8] if r.get("verse_id")])
        return {"body_ko": body, "llm_invoked": False, "layer": layer}

    prompt_refs = list(evidence_refs[:8])
    extra_note = f" Optional tension verses (cite only if listed): {', '.join(allowed_extra[:6])}."
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
    narr = try_ollama_distill_narrative(
        prompt_refs,
        theme_title=f"{theme_title} [{layer}]",
        host=host.rstrip("/").replace("/v1", ""),
        model=model,
        timeout=180,
    )
    if narr and narr.get("body_ko"):
        narr["layer"] = layer
        narr["dialectical_note"] = extra_note.strip()
        return narr
    body = _layer_stub(layer, theme_title, [str(r.get("verse_id")) for r in evidence_refs[:8] if r.get("verse_id")])
    return {"body_ko": body, "llm_invoked": False, "layer": layer, "ollama_fallback": True}


def build_theme(theme_id: str, *, use_ollama: bool) -> dict[str, Any]:
    distill = _load_distill(theme_id)
    evidence = [r for r in (distill.get("evidence_refs") or []) if isinstance(r, dict)]
    anchors = {str(r.get("verse_id")) for r in evidence if r.get("verse_id")}
    title = str((distill.get("source_slice") or {}).get("theme_title_ko") or theme_id)
    thesis_refs = evidence[:8]
    tension_neighbors = _load_xref_neighbors(theme_id, anchors)
    antithesis_refs = [r for r in evidence if str(r.get("verse_id")) in anchors][4:12] or evidence[2:6]
    synthesis_refs = evidence[0:10]

    if use_ollama:
        os.environ.setdefault("MKM_LOGOS_LLM_DISTILL_ENABLE", "1")
        thesis = _maybe_ollama("thesis", thesis_refs, theme_title=title, allowed_extra=[])
        antithesis = _maybe_ollama("antithesis", antithesis_refs, theme_title=title, allowed_extra=tension_neighbors)
        synthesis = _maybe_ollama("synthesis", synthesis_refs, theme_title=title, allowed_extra=tension_neighbors[:4])
    else:
        thesis = {"body_ko": _layer_stub("thesis", title, [str(r.get("verse_id")) for r in thesis_refs]), "llm_invoked": False, "layer": "thesis"}
        antithesis = {
            "body_ko": _layer_stub("antithesis", title, tension_neighbors or [str(r.get("verse_id")) for r in antithesis_refs]),
            "llm_invoked": False,
            "layer": "antithesis",
        }
        synthesis = {"body_ko": _layer_stub("synthesis", title, [str(r.get("verse_id")) for r in synthesis_refs]), "llm_invoked": False, "layer": "synthesis"}

    allowed = anchors | set(tension_neighbors)
    layers_out: list[dict[str, Any]] = []
    layer_specs = [
        (thesis, set()),
        (antithesis, set(tension_neighbors)),
        (synthesis, set(tension_neighbors)),
    ]
    for block, extra in layer_specs:
        validation = _validate_citations(str(block.get("body_ko") or ""), allowed | extra)
        layers_out.append({**block, **validation})

    return {
        "theme_id": theme_id,
        "theme_title_ko": title,
        "tension_neighbor_verses": tension_neighbors,
        "layers": layers_out,
        "insight_unit_count": len(layers_out),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--try-ollama", action="store_true")
    args = ap.parse_args()

    themes = [build_theme(t, use_ollama=args.try_ollama) for t in THEMES]
    total_units = sum(t["insight_unit_count"] for t in themes)
    doc = {
        "schema": "logos_dialectical_insight_layers_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "bible_ai_technique": "verifiable_theology_graph_dialectical_path_ranking",
        "themes": themes,
        "summary": {"insight_units": total_units, "themes": len(themes)},
        "reproduce": "py scripts/build_logos_dialectical_insight_layers_v1.py --try-ollama",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "insight_units": total_units, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
