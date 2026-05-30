#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble magic_orb_question_insight_v1 with embedded graph_bloom ([HYPO], NON_GATING)."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"

DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
DEFAULT_CHAIN = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"
DEFAULT_ROUTER = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_OUT_ART = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
DEFAULT_OUT_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_question_insight_v1_latest.json"

SCHEMA = "magic_orb_question_insight_v1"
VERSION = "1.1.0"
GENERATOR = "build_magic_orb_question_insight_payload_v1.py@1.2.0"
HUD_SCHEMA = "magic_orb_search_hud_v1"
HUD_VERSION = "1.0.0"
DEFAULT_CORPUS_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_ATOMS_SUMMARY = (
    ROOT / "reports/constitution/btrack_pilot/original_language_master_atoms_summary_latest.json"
)
DEFAULT_VERSE_JSONL = ROOT / "data/logos/verse_decoded_v2_single_anchor_v1.jsonl"
SNIPPET_EXCERPT_MAX = 140


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path_sort_key(path: dict[str, Any]) -> tuple[int, str]:
    raw = path.get("match_score")
    try:
        score = int(raw)
    except (TypeError, ValueError):
        score = 0
    return (-score, str(path.get("path_id") or ""))


class _VerseSnippetCache:
    """Lazy verse row lookup for evidence packing (build-time only)."""

    def __init__(self, jsonl_path: Path = DEFAULT_VERSE_JSONL) -> None:
        self._jsonl = jsonl_path
        self._rows: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _normalize_vid(vid: str) -> str:
        v = vid.strip()
        if v.startswith("John."):
            return "Jhn." + v[5:]
        if "::" in v:
            return v.split("::", 1)[-1]
        if v.startswith("verse:"):
            return v.split(":", 1)[-1]
        return v

    def prefetch(self, verse_ids: set[str]) -> None:
        missing = {self._normalize_vid(v) for v in verse_ids if v} - set(self._rows)
        if not missing or not self._jsonl.is_file():
            return
        needles = {f'"verse_id": "{vid}"' for vid in missing}
        with self._jsonl.open(encoding="utf-8") as fh:
            for line in fh:
                if not any(n in line for n in needles):
                    continue
                row = json.loads(line)
                vid = str(row.get("verse_id") or "")
                if vid in missing:
                    self._rows[vid] = row
                    needles.discard(f'"verse_id": "{vid}"')
                if not needles:
                    break

    def excerpt(self, verse_id: str) -> str:
        vid = self._normalize_vid(verse_id)
        row = self._rows.get(vid)
        if not row:
            self.prefetch({vid})
            row = self._rows.get(vid)
        if not row:
            return vid
        label = str(row.get("source_ref") or vid)
        body = str(row.get("text") or row.get("original_text") or "").strip()
        body = " ".join(body.split())
        if len(body) > SNIPPET_EXCERPT_MAX:
            body = body[: SNIPPET_EXCERPT_MAX - 1] + "…"
        return f"{label}: {body}" if body else label


def _verse_ids_from_steps(steps: list[Any]) -> list[str]:
    out: list[str] = []
    for step in steps:
        if isinstance(step, str) and step.startswith("verse:"):
            out.append(step.split(":", 1)[1])
    return out


def _format_path_snippet(path: dict[str, Any], *, verse_cache: _VerseSnippetCache | None) -> str:
    rel = str(path.get("bridge_artifact") or "")
    pid = str(path.get("path_id") or "path")
    note = str(path.get("note_ko") or "").strip()
    lines: list[str] = []
    if note:
        lines.append(note)
    else:
        lines.append(f"GraphRAG 경로 {pid} · {rel}")
    for vid in _verse_ids_from_steps(list(path.get("steps") or []))[:4]:
        if verse_cache:
            lines.append(f"· {verse_cache.excerpt(vid)}")
        else:
            lines.append(f"· {vid}")
    lines.append("---")
    lines.append("[HYPO subgraph router; token overlap; NON_GATING]")
    return "\n".join(lines)


def _rag_path_row(path: dict[str, Any], *, verse_cache: _VerseSnippetCache | None = None) -> dict[str, Any]:
    rel = str(path.get("bridge_artifact") or "")
    pid = str(path.get("path_id") or "path")
    snippet = _format_path_snippet(path, verse_cache=verse_cache)
    return {
        "source_id": f"logos_subgraph:{pid}:{rel}",
        "snippet": snippet,
        "confidence_band": "B",
        "match_score": path.get("match_score"),
        "evidence_kind": "subgraph_path",
    }


def _rag_verse_row(vid: str, *, verse_cache: _VerseSnippetCache | None = None) -> dict[str, Any]:
    norm = _VerseSnippetCache._normalize_vid(vid)
    snippet = verse_cache.excerpt(norm) if verse_cache else f"{norm} (subgraph verse_ref) [HYPO]"
    if "[HYPO" not in snippet:
        snippet = f"{snippet}\n---\n[HYPO verse_ref; NON_GATING]"
    return {
        "source_id": f"logos_subgraph_verse:{norm}",
        "snippet": snippet,
        "confidence_band": "B",
        "uri": f"logos:verse:{norm}",
        "evidence_kind": "subgraph_verse",
    }


def _rag_from_router_ranked(
    router: dict[str, Any],
    *,
    path_cap: int,
    verse_cap: int,
    verse_cache: _VerseSnippetCache | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Ranked path rows + verse rows from router (query-scoped, NON_GATING)."""
    paths = sorted(
        [p for p in (router.get("paths") or []) if isinstance(p, dict)],
        key=_path_sort_key,
    )
    if verse_cache:
        prefetch_ids: set[str] = set()
        for p in paths[: max(0, path_cap)]:
            prefetch_ids.update(_verse_ids_from_steps(list(p.get("steps") or [])))
        for vid in router.get("verse_ids") or []:
            if isinstance(vid, str):
                prefetch_ids.add(vid)
        verse_cache.prefetch(prefetch_ids)

    path_rows = [_rag_path_row(p, verse_cache=verse_cache) for p in paths[: max(0, path_cap)]]
    verse_rows: list[dict[str, Any]] = []
    for vid in router.get("verse_ids") or []:
        if not isinstance(vid, str) or not vid:
            continue
        if len(verse_rows) >= max(0, verse_cap):
            break
        verse_rows.append(_rag_verse_row(vid, verse_cache=verse_cache))
    return path_rows, verse_rows


def _merge_rag_evidence(
    *,
    bundle_rows: list[dict[str, Any]],
    router: dict[str, Any] | None,
    caps: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Router-ranked subgraph evidence first; stale bundle paths never block query paths."""
    path_cap = int(caps.get("subgraph_paths") or 12)
    verse_cap = int(caps.get("subgraph_verses") or 12)
    rag_cap = int(caps.get("rag_evidence") or 24)

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(row: dict[str, Any]) -> None:
        sid = str(row.get("source_id") or "")
        if not sid or sid in seen:
            return
        seen.add(sid)
        merged.append(row)

    path_rows: list[dict[str, Any]] = []
    verse_rows: list[dict[str, Any]] = []
    if router:
        path_rows, verse_rows = _rag_from_router_ranked(
            router,
            path_cap=path_cap,
            verse_cap=verse_cap,
            verse_cache=_VerseSnippetCache(),
        )
        for row in path_rows + verse_rows:
            _add(row)

    ann_appended = 0
    for row in bundle_rows:
        sid = str(row.get("source_id") or "")
        if sid.startswith("logos_ann_lite:"):
            before = len(merged)
            _add(row)
            if len(merged) > before:
                ann_appended += 1

    meta = {
        "fusion_policy": "router_ranked_first_v1",
        "router_paths_available": len(router.get("paths") or []) if router else 0,
        "router_paths_included": len(path_rows),
        "router_verses_included": len(verse_rows),
        "bundle_ann_appended": ann_appended,
        "total_before_rag_cap": len(merged),
        "rag_cap_applied": rag_cap,
    }
    return _cap_rows(merged, rag_cap), meta


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _cap_rows(rows: list[Any], cap: int) -> list[Any]:
    return rows[:cap] if cap > 0 else rows


def _field_logos_overlay_slots(overlay_doc: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not overlay_doc:
        return []
    field = overlay_doc.get("field_observation") if isinstance(overlay_doc.get("field_observation"), dict) else {}
    logos = overlay_doc.get("logos_overlay") if isinstance(overlay_doc.get("logos_overlay"), dict) else {}
    regime = field.get("primary_regime_id_observational") or "unknown"
    cos = logos.get("top_hit_cosine")
    cos_s = f"{cos:.3f}" if isinstance(cos, (int, float)) else "n/a"
    return [
        {
            "slot_id": "field.regime_observational",
            "text": (
                f"Field(1차 regime_map 관측): primary={regime}; "
                f"logos_resonance_cosine={cos_s}. [HYPO][NON_GATING] 실매매·Track A 트리거 아님."
            ),
        },
        {
            "slot_id": "field_logos.overlay_boundary",
            "text": (
                "Field 주(主)·Logos 보(補) 연구 합선 슬롯. "
                "B-track field_logos_overlay_prophecy_v1 — 예측·채점·parameter_only 진화 레일."
            ),
        },
    ]


def _load_field_logos_overlay_latest() -> dict[str, Any] | None:
    path = ROOT / "docs/final/artifacts/field_logos_overlay_prophecy_v1_latest.json"
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return doc if isinstance(doc, dict) else None


def _slots_from_query(
    query: str,
    router: dict[str, Any] | None,
    rag_meta: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    summary = "Logos subgraph router: no router artifact."
    if router:
        meta = rag_meta or {}
        summary = (
            f"Logos subgraph router: bridges_matched={router.get('bridges_matched')}, "
            f"paths={len(router.get('paths') or [])}, verse_ids={len(router.get('verse_ids') or [])}; "
            f"rag_fusion paths_included={meta.get('router_paths_included', 0)}/"
            f"{meta.get('router_paths_available', 0)}; "
            "router_kind=token_overlap_logos_subgraph_v1; ranked match_score desc. [HYPO][NON_GATING]"
        )
    return [
        {"slot_id": "query.intent", "text": query},
        {"slot_id": "subgraph.router_summary", "text": summary, "evidence_index": 0},
        {
            "slot_id": "ann.lite_summary",
            "text": "Logos ANN-lite may be skipped in chain; not prophecy hit_rate; not Track A.",
        },
        {
            "slot_id": "policy.boundary",
            "text": (
                "B-track insight shower only. Do not merge Track A, live trading, or prophecy hit_rate."
            ),
        },
    ]


def _format_pairspace_upper(n: int) -> str:
    if n <= 0:
        return "0"
    exp = len(str(n)) - 1
    mantissa = n / (10**exp)
    return f"~{mantissa:.1f}×10^{exp}"


def _load_corpus_hud_stats() -> dict[str, Any]:
    """SSOT corpus counts — no synthetic runtime counters."""
    verse_count = 31_102
    meaning_edges = 1_196
    atom_count = 41_658
    source_rel = "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"

    bundle = _load_json(DEFAULT_CORPUS_BUNDLE)
    if bundle:
        snap = bundle.get("manifest_snapshot") if isinstance(bundle.get("manifest_snapshot"), dict) else {}
        gf = bundle.get("graph_files") if isinstance(bundle.get("graph_files"), dict) else {}
        try:
            verse_count = int(snap.get("corpus_verse_count") or verse_count)
        except (TypeError, ValueError):
            pass
        try:
            meaning_edges = int(gf.get("edges_line_count") or meaning_edges)
        except (TypeError, ValueError):
            pass
        source_rel = str(bundle.get("manifest_snapshot", {}).get("manifest_path") or source_rel)

    atoms = _load_json(DEFAULT_ATOMS_SUMMARY)
    if atoms and isinstance(atoms.get("stats"), dict):
        try:
            atom_count = int(atoms["stats"].get("unique_master_atoms") or atom_count)
        except (TypeError, ValueError):
            pass

    return {
        "verse_count": verse_count,
        "atom_count": atom_count,
        "meaning_graph_edge_count": meaning_edges,
        "source_artifact_rel": source_rel.replace("\\", "/"),
    }


def _top_router_match_score(router: dict[str, Any] | None) -> int:
    if not router:
        return 0
    best = 0
    for path in router.get("paths") or []:
        if not isinstance(path, dict):
            continue
        try:
            best = max(best, int(path.get("match_score") or 0))
        except (TypeError, ValueError):
            continue
    return best


def build_search_hud_v1(
    *,
    router: dict[str, Any] | None,
    graph_bloom: dict[str, Any] | None,
    subgraph_summary: dict[str, Any],
    ann_status: str,
) -> dict[str, Any]:
    corpus = _load_corpus_hud_stats()
    v = int(corpus["verse_count"])
    pairspace_upper = v * (v - 1) // 2 if v > 1 else 0
    bloom_stats = (graph_bloom or {}).get("stats") if isinstance(graph_bloom, dict) else {}
    bloom_nodes = int(bloom_stats.get("node_count") or 0) if isinstance(bloom_stats, dict) else 0
    bloom_edges = int(bloom_stats.get("edge_count") or 0) if isinstance(bloom_stats, dict) else 0
    bridges = int(subgraph_summary.get("bridges_matched") or 0)
    paths = int(subgraph_summary.get("paths") or 0)
    top_match = _top_router_match_score(router)
    pair_display = _format_pairspace_upper(pairspace_upper)

    display_lines = [
        (
            f"[CORPUS]      Verses {corpus['verse_count']:,} · Atoms {corpus['atom_count']:,} · "
            f"Meaning edges {corpus['meaning_graph_edge_count']:,}"
        ),
        f"[THEORETICAL] Pairspace upper {pair_display} · Mode: offline_4d_knn [HYPO]",
        (
            f"[THIS QUERY]  Bridges {bridges} · Paths {paths} · Bloom {bloom_nodes}/{bloom_edges} · "
            f"Match {top_match}"
        ),
    ]

    return {
        "schema": HUD_SCHEMA,
        "version": HUD_VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "disclaimer_ko": (
            "측정·SSOT 아티팩트 기반 HUD입니다. 실시간 full-graph scan·난수 카운터 없음. "
            "[HYPO][NON_GATING] — Track A·실매매·예언 적중 근거 아님."
        ),
        "corpus": corpus,
        "theoretical": {
            "pairspace_upper": pairspace_upper,
            "pairspace_upper_display": pair_display,
            "mode": "offline_4d_knn",
            "hypothesis_tier": "[HYPO]",
            "not_evaluated_at_runtime": True,
            "note_ko": "이론적 pairspace 상한만 표기; 질의 시 전량 평가하지 않음.",
        },
        "this_query": {
            "bridges_matched": bridges,
            "paths": paths,
            "bloom_nodes": bloom_nodes,
            "bloom_edges": bloom_edges,
            "top_match_score": top_match,
            "ann_status": ann_status,
            "router_kind": str(subgraph_summary.get("router_kind") or "token_overlap_logos_subgraph_v1"),
        },
        "display_lines": display_lines,
    }


def _ann_top_verse_ids(rag: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in rag:
        sid = str(row.get("source_id") or "")
        if not sid.startswith("logos_ann_lite:"):
            continue
        ref = sid.split(":", 1)[-1]
        if ref and ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def build_payload(
    *,
    query: str,
    query_id: str | None,
    bundle: dict[str, Any],
    chain: dict[str, Any] | None,
    router: dict[str, Any] | None,
    graph_bloom: dict[str, Any] | None,
    caps: dict[str, Any] | None = None,
) -> dict[str, Any]:
    default_caps = {
        "rag_evidence": 24,
        "subgraph_paths": 12,
        "subgraph_verses": 12,
        "ann_top_k_default": 8,
        "lod_node_cap": 48,
        "lod_edge_cap": 56,
    }
    merged_caps = {**default_caps, **(chain.get("caps") or {} if chain else {}), **(caps or {})}

    rag, rag_meta = _merge_rag_evidence(
        bundle_rows=list(bundle.get("rag_evidence") or []),
        router=router,
        caps=merged_caps,
    )

    if router:
        slots = _slots_from_query(query, router, rag_meta)
    else:
        slots = list(bundle.get("structured_insight_slots") or [])
        if not slots:
            slots = _slots_from_query(query, None, rag_meta)
    overlay_doc = _load_field_logos_overlay_latest()
    if overlay_doc:
        slots = slots + _field_logos_overlay_slots(overlay_doc)
    lens_route = bundle.get("lens_route") or {
        "lens_id": "logos_graphrag",
        "route_confidence_0_1": 0.5,
    }
    calibration = bundle.get("calibration_reference") or {
        "kind": "logos_4d_state_v1",
        "artifact_path_rel": "docs/final/artifacts/logos_4d_state_v1_latest.json",
        "summary_line": f"question_chain query_len={len(query)} rag={len(rag)}",
    }

    ann_status = "skipped_flag"
    ann_top: list[str] = []
    if chain and isinstance(chain.get("steps"), dict):
        ann_step = chain["steps"].get("ann_lite") or {}
        ann_status = str(ann_step.get("status") or "skipped_flag")
    if ann_status == "ok" or rag:
        ann_top = _ann_top_verse_ids(rag)

    subgraph_summary: dict[str, Any] = {
        "bridges_matched": 0,
        "paths": 0,
        "verse_ids": 0,
        "router_kind": "token_overlap_logos_subgraph_v1",
    }
    if router:
        subgraph_summary = {
            "bridges_matched": int(router.get("bridges_matched") or 0),
            "paths": len(router.get("paths") or []),
            "verse_ids": len(router.get("verse_ids") or []),
            "router_kind": "token_overlap_logos_subgraph_v1",
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "labels": ["HYPO", "NON_GATING", "research_only"],
        "query": query,
        "query_id": query_id,
        "disclaimer_ko": (
            "B-track 관측 샤워입니다. [HYPO][NON_GATING] — 투자·실매매·의료·양육 처방·예언 적중 근거 아님."
        ),
        "rag_evidence": rag,
        "rag_fusion": rag_meta,
        "structured_insight_slots": slots,
        "lens_route": lens_route,
        "calibration_reference": calibration,
        "subgraph_summary": subgraph_summary,
        "ann_summary": {"status": ann_status, "top_verse_ids": ann_top},
        "caps": merged_caps,
        "source_artifacts": {
            "bundle": str(DEFAULT_BUNDLE.relative_to(ROOT)).replace("\\", "/"),
            "chain": str((chain or {}).get("_path") or "reports/question_semantic_rag_bridge_chain_v1_latest.json"),
            "subgraph": str(DEFAULT_ROUTER.relative_to(ROOT)).replace("\\", "/"),
        },
        "generator": GENERATOR,
    }
    if graph_bloom and graph_bloom.get("schema") == "magic_orb_graph_bloom_v1":
        payload["graph_bloom"] = graph_bloom
    payload["search_hud_v1"] = build_search_hud_v1(
        router=router,
        graph_bloom=graph_bloom,
        subgraph_summary=subgraph_summary,
        ann_status=ann_status,
    )
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description="Build magic_orb_question_insight_v1 payload.")
    ap.add_argument("--query", required=True)
    ap.add_argument("--query-id", default="q01")
    ap.add_argument("--bundle-json", type=Path, default=DEFAULT_BUNDLE)
    ap.add_argument("--chain-json", type=Path, default=DEFAULT_CHAIN)
    ap.add_argument("--router-json", type=Path, default=DEFAULT_ROUTER)
    ap.add_argument("--bloom-json", type=Path, default=None, help="prebuilt bloom; else build inline")
    ap.add_argument("--caps-json-inline", type=str, default="", help="JSON object overriding caps")
    ap.add_argument("--expand-graph", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_ART)
    ap.add_argument("--sync-public", action="store_true")
    ap.add_argument("--ann-rag-json", type=Path, default=None, help="ANN-lite rag rows sidecar")
    args = ap.parse_args()

    bundle = _load_json(args.bundle_json)
    if not bundle:
        bundle = {"schema": "semantic_rag_bridge_insight_bundle_v1", "rag_evidence": []}
    if bundle.get("schema") != "semantic_rag_bridge_insight_bundle_v1":
        raise SystemExit(f"invalid bundle: {args.bundle_json}")

    if args.ann_rag_json and args.ann_rag_json.is_file():
        ann_path = args.ann_rag_json if args.ann_rag_json.is_absolute() else ROOT / args.ann_rag_json
        ann_doc = json.loads(ann_path.read_text(encoding="utf-8-sig"))
        ann_rows = list(ann_doc.get("rag_evidence") or []) if isinstance(ann_doc, dict) else []
        if ann_rows:
            existing = list(bundle.get("rag_evidence") or [])
            bundle["rag_evidence"] = existing + ann_rows

    chain = _load_json(args.chain_json)
    if chain:
        chain = {**chain, "_path": str(args.chain_json.relative_to(ROOT)).replace("\\", "/")}

    router = _load_json(args.router_json)

    inline_caps: dict[str, Any] | None = None
    if args.caps_json_inline.strip():
        try:
            parsed = json.loads(args.caps_json_inline)
            if isinstance(parsed, dict):
                inline_caps = parsed
        except json.JSONDecodeError:
            raise SystemExit("invalid --caps-json-inline")

    bloom: dict[str, Any] | None = None
    if args.bloom_json and args.bloom_json.is_file():
        bloom = _load_json(args.bloom_json)
    else:
        bloom_path = SCRIPTS / "build_magic_orb_graph_bloom_v1.py"
        spec = importlib.util.spec_from_file_location("build_magic_orb_graph_bloom_v1", bloom_path)
        if spec is None or spec.loader is None:
            raise SystemExit(f"cannot load bloom builder: {bloom_path}")
        bloom_mod = importlib.util.module_from_spec(spec)
        sys.modules["build_magic_orb_graph_bloom_v1"] = bloom_mod
        spec.loader.exec_module(bloom_mod)
        build_bloom = bloom_mod.build_bloom

        caps = chain.get("caps") if chain else {}
        bloom = build_bloom(
            query=args.query,
            router=router,
            ann_top_verse_ids=_ann_top_verse_ids(list(bundle.get("rag_evidence") or [])),
            expand_graph=args.expand_graph,
            lod_node_cap=int((caps or {}).get("lod_node_cap") or 48),
            lod_edge_cap=int((caps or {}).get("lod_edge_cap") or 56),
            hub_verse_refs=list((caps or {}).get("hub_verse_ids") or []) or None,
        )

    payload = build_payload(
        query=args.query,
        query_id=args.query_id,
        bundle=bundle,
        chain=chain,
        router=router,
        graph_bloom=bloom,
        caps={**(chain.get("caps") if chain else {}), **(inline_caps or {})},
    )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.out_json.write_text(text, encoding="utf-8")

    if args.sync_public:
        DEFAULT_OUT_PUBLIC.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT_PUBLIC.write_text(text, encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "graph_bloom_nodes": (bloom or {}).get("stats", {}).get("node_count"),
                "rag_count": len(payload.get("rag_evidence") or []),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
