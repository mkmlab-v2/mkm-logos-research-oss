#!/usr/bin/env python3
"""Layer B — Saving the News perspective appendix (semantic flavor, not fact fusion).

Reads headline from Phase2 matrix / pre_news, lens snapshots for myeongni/sasang,
Logos subgraph GraphRAG for [NON_GATING] metaphor paths. No LLM; B-track only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MATRIX = ART / "saving_the_news_phase2_matrix_view_v1_latest.json"
DEFAULT_PRE_NEWS = ART / "pre_news_shadow_input_latest.json"
DEFAULT_OUT = ART / "saving_the_news_perspective_appendix_v1_latest.json"
DEFAULT_FLYWHEEL = ART / "saving_the_news_flywheel_as_snapshot_v1_latest.json"
DEFAULT_REGISTRY = ART / "logos_concept_bridge_registry_v1_latest.json"
DEFAULT_LEMMA = ART / "logos_lemma_verse_edges_v1.jsonl"
DEFAULT_SEED_CHAIN = ART / "logos_graph_seed_chain_v1_latest.json"
DEFAULT_LOGOS_ROUTER_OUT = ART / "saving_the_news_logos_subgraph_router_v1_latest.json"

TOKEN_RE = re.compile(r"[A-Za-z0-9_가-힣]{2,}")
STOP = frozenset(
    "the and for with after from that this news global market policy".split()
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _load_graphrag_router():
    repo_root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "run_logos_subgraph_graphrag_router_v1",
        repo_root / "scripts/run_logos_subgraph_graphrag_router_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _headline_anchor(matrix_path: Path, pre_news_path: Path) -> dict[str, Any]:
    matrix = _read_json(matrix_path)
    if matrix and matrix.get("headline_anchor"):
        return dict(matrix["headline_anchor"])
    doc = _read_json(pre_news_path) or {}
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    if rows and isinstance(rows[0], dict):
        row = rows[0]
        return {
            "headline": str(row.get("headline", "")),
            "timestamp_utc": row.get("timestamp_utc"),
            "source": str(row.get("source", "")),
            "input_path": _display_path(pre_news_path),
        }
    return {"headline": "", "timestamp_utc": None, "source": "missing"}


def _entity_tokens(headline: str, *, max_tokens: int = 12) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for m in TOKEN_RE.finditer(headline.lower()):
        t = m.group(0)
        if t in STOP or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_tokens:
            break
    return out


def _myeongni_slot() -> dict[str, Any]:
    doc = _read_json(ART / "myeongni_independent_lens_latest.json")
    if not doc:
        return {
            "lens_id": "myeongni",
            "source_kind": "lens_snapshot",
            "non_gating": False,
            "tags": ["[HYPO]"],
            "flavor_ko": "명리 스냅샷 없음 — 관측 생략.",
            "present": False,
        }
    outs = doc.get("myeongri_stream_outputs") or {}
    state_id = outs.get("state_id")
    rationale = str(outs.get("rationale", ""))[:160]
    scores = doc.get("scores") or {}
    flavor = (
        f"명리 관측(state_id={state_id}): {rationale or '방향·신뢰는 독립 렌즈 JSON 기준.'} "
        f"(direction_score={scores.get('direction_score')})"
    )
    return {
        "lens_id": "myeongni",
        "source_kind": "lens_snapshot",
        "non_gating": False,
        "tags": ["[HYPO]"],
        "flavor_ko": flavor,
        "present": True,
        "artifact_path": _display_path(ART / "myeongni_independent_lens_latest.json"),
    }


def _sasang_slot() -> dict[str, Any]:
    doc = _read_json(ART / "sasang_independent_lens_latest.json")
    if not doc:
        return {
            "lens_id": "sasang",
            "source_kind": "lens_snapshot",
            "non_gating": False,
            "tags": ["[HYPO]"],
            "flavor_ko": "사상 스냅샷 없음 — 관측 생략.",
            "present": False,
        }
    outs = doc.get("sasang_stream_outputs") or {}
    regime = str(outs.get("regime_hypothesis", ""))[:120]
    scores = doc.get("scores") or {}
    flavor = (
        f"사상 동역학 관측: {regime or 'phase_transition 스텁'} "
        f"(direction_score={scores.get('direction_score')})"
    )
    return {
        "lens_id": "sasang",
        "source_kind": "lens_snapshot",
        "non_gating": False,
        "tags": ["[HYPO]"],
        "flavor_ko": flavor,
        "present": True,
        "artifact_path": _display_path(ART / "sasang_independent_lens_latest.json"),
    }


def _logos_graphrag_slot(
    query: str,
    *,
    registry_path: Path,
    lemma_path: Path,
    seed_chain_path: Path,
    router_out: Path,
    top_bridges: int,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    mod = _load_graphrag_router()
    registry = _read_json(registry_path)
    if not registry:
        return (
            {
                "lens_id": "logos",
                "source_kind": "logos_subgraph_graphrag",
                "non_gating": True,
                "tags": ["[NON_GATING]", "[HYPO]"],
                "flavor_ko": "Logos subgraph GraphRAG: registry 없음 — 부록 생략.",
                "present": False,
            },
            None,
        )
    doc = mod.route(
        query,
        registry=registry,
        lemma_rows=mod._load_jsonl(lemma_path),
        seed_chain=_read_json(seed_chain_path),
        top_bridges=top_bridges,
    )
    router_out.parent.mkdir(parents=True, exist_ok=True)
    router_out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    paths = doc.get("paths") or []
    path_note = ""
    if paths and isinstance(paths[0], dict):
        path_note = str(paths[0].get("note_ko") or "")[:120]
    verse_n = len(doc.get("verse_ids") or [])
    flavor = (
        f"Logos [NON_GATING] GraphRAG: bridges={doc.get('bridges_matched', 0)}, "
        f"paths={len(paths)}, verses={verse_n}. {path_note}".strip()
    )
    slot = {
        "lens_id": "logos",
        "source_kind": "logos_subgraph_graphrag",
        "non_gating": True,
        "tags": ["[NON_GATING]", "[HYPO]"],
        "flavor_ko": flavor,
        "present": doc.get("bridges_matched", 0) > 0,
        "router_artifact_path": _display_path(router_out),
    }
    return slot, doc


def _coordinator_brief(headline: str, slots: list[dict[str, Any]]) -> str:
    lines = [
        "[HYPO] MKM AI Layer B — 의미론적 시선 부록(팩트 합성·투자 권유·송출 트리거 아님).",
        f"헤드라인: {headline[:200] or '(none)'}",
    ]
    for s in slots:
        tag = ",".join(s.get("tags") or [])
        lines.append(f"- {s.get('lens_id')} ({tag}): {s.get('flavor_ko', '')[:220]}")
    lines.append("조율: Field(레짐)는 Layer A Matrix가 주도; 본 부록은 해설 탭 전용.")
    return "\n".join(lines)


def build_appendix(
    *,
    matrix_path: Path,
    pre_news_path: Path,
    flywheel_path: Path,
    registry_path: Path,
    lemma_path: Path,
    seed_chain_path: Path,
    router_out: Path,
    top_bridges: int,
) -> dict[str, Any]:
    anchor = _headline_anchor(matrix_path, pre_news_path)
    headline = str(anchor.get("headline") or "")
    tokens = _entity_tokens(headline)
    query = headline.strip() or "위기 가운데 언약의 안정과 신실"

    myeongni = _myeongni_slot()
    sasang = _sasang_slot()
    logos, logos_doc = _logos_graphrag_slot(
        query,
        registry_path=registry_path,
        lemma_path=lemma_path,
        seed_chain_path=seed_chain_path,
        router_out=router_out,
        top_bridges=top_bridges,
    )
    slots = [myeongni, sasang, logos]

    fly_ref = _display_path(flywheel_path) if flywheel_path.is_file() else None

    return {
        "schema": "saving_the_news_perspective_appendix_v1",
        "version": "1.0.0",
        "lane": "research_only",
        "hypothesis_tier": "B",
        "ready_for_external_send": False,
        "generated_at_utc": _utc_now(),
        "layer": "B",
        "bridge_mode": "read_only_semantic_flavor",
        "fact_synthesis_forbidden": True,
        "a_track_autotrigger_forbidden": True,
        "headline_anchor": anchor,
        "entity_tokens": tokens,
        "perspective_slots": slots,
        "logos_graphrag": logos_doc,
        "coordinator_brief_ko": _coordinator_brief(headline, slots),
        "flywheel_as_ref": fly_ref,
        "refs": {
            "matrix": _display_path(matrix_path),
            "blueprint": "docs/research/saving_the_news_blueprint_v1.md",
            "logos_bridge_doc": "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md",
        },
    }


def patch_matrix_layer_b(matrix_path: Path, appendix_path: Path) -> bool:
    matrix = _read_json(matrix_path)
    if not matrix:
        return False
    matrix["layer_b"] = {
        "perspective_appendix_ref": _display_path(appendix_path),
        "bridge_mode": "read_only_semantic_flavor",
        "note": "Layer A matrix rows unchanged; Layer B tab only [HYPO].",
    }
    matrix_path.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-json", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--pre-news-json", type=Path, default=DEFAULT_PRE_NEWS)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--flywheel-json", type=Path, default=DEFAULT_FLYWHEEL)
    ap.add_argument("--registry-json", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--lemma-jsonl", type=Path, default=DEFAULT_LEMMA)
    ap.add_argument("--seed-chain-json", type=Path, default=DEFAULT_SEED_CHAIN)
    ap.add_argument("--router-out-json", type=Path, default=DEFAULT_LOGOS_ROUTER_OUT)
    ap.add_argument("--top-bridges", type=int, default=2)
    ap.add_argument("--patch-matrix", action="store_true")
    args = ap.parse_args()

    doc = build_appendix(
        matrix_path=args.matrix_json,
        pre_news_path=args.pre_news_json,
        flywheel_path=args.flywheel_json,
        registry_path=args.registry_json,
        lemma_path=args.lemma_jsonl,
        seed_chain_path=args.seed_chain_json,
        router_out=args.router_out_json,
        top_bridges=args.top_bridges,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.patch_matrix:
        patch_matrix_layer_b(args.matrix_json, args.output_json)

    logos_present = any(
        s.get("lens_id") == "logos" and s.get("present") for s in doc.get("perspective_slots") or []
    )
    print(
        f"WROTE: {args.output_json} "
        f"tokens={len(doc.get('entity_tokens') or [])} logos_graph={logos_present}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
