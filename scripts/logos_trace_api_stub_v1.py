#!/usr/bin/env python3
"""FastAPI stub: deterministic Logos Observatory trace (showroom presets, no live LLM).

Run: uvicorn scripts.logos_trace_api_stub_v1:app --host 127.0.0.1 --port 8021

Track C / B-track only — NON_GATING, not investment advice, not live trading triggers.
"""
from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402

from scripts.compute_logos_reasoning_path_v1 import (  # noqa: E402
    attach_paths_to_presets,
    compute_reasoning_path,
)

MVP = ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
VPS_STATIC = Path("/var/www/jemaai")


def _resolve_data_path(env_key: str, *candidates: Path) -> Path:
    raw = os.getenv(env_key, "").strip()
    if raw:
        p = Path(raw)
        if p.is_file():
            return p
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


def _data_paths() -> tuple[Path, Path, Path | None]:
    graph = _resolve_data_path(
        "LOGOS_TRACE_GRAPH_JSON",
        MVP / "showroom_meaning_topology_graph_slice_v1.json",
        ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json",
        VPS_STATIC / "showroom_meaning_topology_graph_slice_v1.json",
    )
    presets = _resolve_data_path(
        "LOGOS_TRACE_PRESETS_JSON",
        MVP / "showroom_meaning_topology_qa_presets_v1.json",
        VPS_STATIC / "showroom_meaning_topology_qa_presets_v1.json",
    )
    chrono_candidates = [
        MVP / "showroom_logos_chronology_overlay_v1.json",
        VPS_STATIC / "showroom_logos_chronology_overlay_v1.json",
    ]
    chrono_raw = os.getenv("LOGOS_TRACE_CHRONOLOGY_JSON", "").strip()
    if chrono_raw:
        chrono = Path(chrono_raw)
    else:
        chrono = next((c for c in chrono_candidates if c.is_file()), chrono_candidates[0])
    return graph, presets, chrono if chrono.is_file() else None

API_CONTRACT_VERSION = "logos_trace_stub_v1"
BOUNDARY = {
    "research_only": True,
    "hypothesis_tier": "B",
    "gating_status": "NON_GATING",
    "no_trade_signals": True,
    "no_live_llm": True,
}


class TraceRequest(BaseModel):
    prompt_ko: str | None = Field(default=None, description="Natural-language question (keyword match)")
    preset_id: str | None = Field(default=None, description="Preset id e.g. p3_theme_regime")
    seed_ids: list[str] | None = Field(default=None, description="Explicit graph node ids for path")
    max_path_nodes: int = Field(default=5, ge=2, le=12)


class TraceResponse(BaseModel):
    schema_version: str = API_CONTRACT_VERSION
    boundary: dict[str, Any]
    matched: dict[str, Any]
    answer_ko: str
    highlight_node_ids: list[str]
    reasoning_path_v1: dict[str, Any]


app = FastAPI(title="MKM Logos Trace Stub", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _bundle() -> tuple[dict, dict, dict | None]:
    graph_path, presets_path, chrono_path = _data_paths()
    if not graph_path.is_file():
        raise FileNotFoundError(f"graph json missing: {graph_path}")
    if not presets_path.is_file():
        raise FileNotFoundError(f"presets json missing: {presets_path}")
    graph = _load_json(graph_path)
    presets = attach_paths_to_presets(_load_json(presets_path), graph)
    chrono = _load_json(chrono_path) if chrono_path else None
    return graph, presets, chrono


def _match_preset(
    prompt_ko: str | None,
    preset_id: str | None,
    presets_doc: dict,
    chrono: dict | None,
    graph: dict,
) -> dict[str, Any] | None:
    if preset_id:
        for p in presets_doc.get("presets") or []:
            if str(p.get("id")) == preset_id:
                return dict(p)
    if not prompt_ko or not str(prompt_ko).strip():
        return None
    t = str(prompt_ko).strip().lower()
    for p in presets_doc.get("presets") or []:
        pk = str(p.get("prompt_ko") or "").lower()
        if pk and pk == t:
            return dict(p)
        for kw in p.get("keywords") or []:
            if str(kw).lower() in t:
                return dict(p)
    if chrono:
        node_ids = {str(n["id"]) for n in graph.get("nodes") or []}
        for era in chrono.get("eras") or []:
            label = str(era.get("label_ko") or "").lower()
            eid = str(era.get("era_id") or "").lower()
            if (eid and eid in t) or (label and (label in t or label[:4] in t)):
                refs = [r for r in (era.get("verse_refs") or []) if r in node_ids]
                era_nid = f"era::{era.get('era_id')}"
                highlights = list(dict.fromkeys(refs + ([era_nid] if era_nid in node_ids else [])))
                label_ko = str(era.get("label_ko") or era.get("era_id") or "")
                notes = str(era.get("notes_ko") or "")[:280]
                return {
                    "id": f"era_{era.get('era_id', 'x')}",
                    "prompt_ko": label_ko,
                    "answer_ko": f"[HYPO] 연대기 **{label_ko}** 구간입니다. {notes}".strip(),
                    "highlight_node_ids": highlights,
                    "keywords": [str(era.get("era_id") or "")],
                }
    return None


@app.get("/health")
def health() -> dict[str, Any]:
    graph, presets, chrono = _bundle()
    st = graph.get("stats") or {}
    return {
        "ok": True,
        "contract": API_CONTRACT_VERSION,
        "graph_nodes": st.get("node_count"),
        "preset_count": len(presets.get("presets") or []),
        "chronology_eras": len((chrono or {}).get("eras") or []),
        **BOUNDARY,
    }


@app.post("/v1/logos/trace", response_model=TraceResponse)
def logos_trace(req: TraceRequest) -> TraceResponse:
    graph, presets_doc, chrono = _bundle()
    matched = _match_preset(req.prompt_ko, req.preset_id, presets_doc, chrono, graph)
    fb = presets_doc.get("fallback") or {}

    if req.seed_ids:
        seeds = list(req.seed_ids)
        answer = "[HYPO] Explicit seed trace (research_only)."
        preset_match = {"match_type": "seed_ids", "preset_id": None}
    elif matched:
        seeds = list(matched.get("highlight_node_ids") or [])
        answer = str(matched.get("answer_ko") or "")
        preset_match = {
            "match_type": "preset",
            "preset_id": matched.get("id"),
            "prompt_ko": matched.get("prompt_ko"),
        }
    else:
        seeds = list(fb.get("highlight_node_ids") or [])
        answer = str(fb.get("answer_ko") or "[HYPO] No preset match.")
        preset_match = {"match_type": "fallback", "preset_id": None}

    path = matched.get("reasoning_path_v1") if matched else None
    if not path or not (path.get("node_ids") or []):
        path = compute_reasoning_path(graph, seeds, max_nodes=req.max_path_nodes)
    elif len(path.get("node_ids") or []) > req.max_path_nodes:
        path = compute_reasoning_path(graph, seeds, max_nodes=req.max_path_nodes)

    return TraceResponse(
        boundary=BOUNDARY,
        matched=preset_match,
        answer_ko=answer,
        highlight_node_ids=seeds,
        reasoning_path_v1=path,
    )
