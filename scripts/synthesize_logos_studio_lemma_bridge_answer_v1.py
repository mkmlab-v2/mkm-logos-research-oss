#!/usr/bin/env python3
"""Deterministic lemma-neighbor bridge summary for Logos Studio free queries.

Input (--stdin-json):
  {"query": "...", "path": {"verse_refs": ["Ps.23.1", ...]}}

Reproduce:
  py scripts/synthesize_logos_studio_lemma_bridge_answer_v1.py --stdin-json
"""
from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = ROOT / "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.json"
DEFAULT_PKL = ROOT / "docs/final/artifacts/logos_studio_lemma_neighbor_index_v1_latest.pkl"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_INDEX_CACHE: dict[str, Any] | None = None


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_verse(raw: str) -> str:
    from scripts.logos_verse_ref_canonical_v1 import normalize_verse_ref

    return normalize_verse_ref(raw)


def _load_index(path: Path) -> dict[str, Any]:
    global _INDEX_CACHE
    pkl_path = path.with_suffix(".pkl")
    if path == DEFAULT_INDEX and DEFAULT_PKL.is_file():
        pkl_path = DEFAULT_PKL
    key = str(pkl_path.resolve() if pkl_path.is_file() else path.resolve())
    if _INDEX_CACHE is not None and _INDEX_CACHE.get("_cache_key") == key:
        return _INDEX_CACHE
    if pkl_path.is_file():
        with pkl_path.open("rb") as fh:
            core = pickle.load(fh)
        doc = dict(core)
        doc["_cache_key"] = key
        _INDEX_CACHE = doc
        return doc
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    doc["_cache_key"] = key
    _INDEX_CACHE = doc
    return doc


def _book_of(ref: str) -> str:
    return ref.split(".", 1)[0] if ref else ""


def collect_neighbors(
    anchor_refs: list[str],
    index: dict[str, Any],
    *,
    max_neighbors: int = 12,
) -> list[dict[str, Any]]:
    verse_to_lemmas: dict[str, list[str]] = index.get("verse_to_lemmas") or {}
    lemma_to_verses: dict[str, list[str]] = index.get("lemma_to_verses") or {}
    anchors = [_norm_verse(r) for r in anchor_refs if r]
    anchors = [a for a in dict.fromkeys(anchors) if a]
    anchor_set = set(anchors)

    score: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"shared_lemma_count": 0, "lemma_ids": set(), "anchor_hits": set()}
    )
    for anchor in anchors:
        lemmas = verse_to_lemmas.get(anchor) or []
        for lemma in lemmas:
            for neighbor in lemma_to_verses.get(lemma) or []:
                nref = _norm_verse(neighbor)
                if not nref or nref in anchor_set:
                    continue
                row = score[nref]
                row["shared_lemma_count"] += 1
                row["lemma_ids"].add(lemma)
                row["anchor_hits"].add(anchor)

    ranked = sorted(
        score.items(),
        key=lambda item: (-item[1]["shared_lemma_count"], item[0]),
    )[:max_neighbors]
    out: list[dict[str, Any]] = []
    for verse_ref, meta in ranked:
        out.append(
            {
                "verse_ref": verse_ref,
                "book": _book_of(verse_ref),
                "shared_lemma_count": meta["shared_lemma_count"],
                "lemma_ids": sorted(meta["lemma_ids"])[:6],
                "anchor_hits": sorted(meta["anchor_hits"])[:4],
            }
        )
    return out


def build_answer_ko(
    query: str,
    anchor_refs: list[str],
    neighbors: list[dict[str, Any]],
) -> str:
    anchors = [_norm_verse(r) for r in anchor_refs if r]
    anchors = [a for a in dict.fromkeys(anchors) if a]
    lines = [
        f"[HYPO] lemma bridge — 질문: {query.strip() or '(query)'}",
        "GraphRAG 경로 앵커에서 lemma 1-hop 이웃 구절을 **인출**했습니다. 신학적 단정·인과 단답 없음 [NON_GATING].",
    ]
    if anchors:
        lines.append("")
        lines.append("### 1. 경로 앵커 (citation lock)")
        lines.append(" · ".join(anchors[:12]))
    if neighbors:
        lines.append("")
        lines.append("### 2. Lemma 연결 이웃 구절")
        for idx, row in enumerate(neighbors, start=1):
            lemmas = ", ".join(row.get("lemma_ids") or [])[:120]
            hits = ", ".join(row.get("anchor_hits") or [])
            lines.append(
                f"{idx}. **{row['verse_ref']}** — shared_lemma={row['shared_lemma_count']}"
                + (f" · via {hits}" if hits else "")
                + (f" · {lemmas}" if lemmas else "")
            )
        books = sorted({str(n.get("book") or "") for n in neighbors if n.get("book")})
        if books:
            lines.append("")
            lines.append(f"### 3. 주변 권·책 분포")
            lines.append(" · ".join(books[:16]))
    else:
        lines.append("")
        lines.append("### 2. Lemma 이웃")
        lines.append("앵커 구절에서 lemma 공유 이웃을 찾지 못했습니다 — bloom/graphrag 경로만 확인하세요.")
    lines.append("")
    lines.append(
        "단일 학파·단일 해석 아님. conflict surface·reading pack·citation shard와 함께 보조 입력으로만 사용하세요."
    )
    return "\n".join(lines)


def _anchors_from_path(path: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for raw in path.get("verse_refs") or []:
        norm = _norm_verse(str(raw))
        if norm:
            refs.append(norm)
    if not refs:
        for nid in path.get("node_ids") or []:
            norm = _norm_verse(str(nid))
            if norm and re.match(r"^[A-Za-z0-9]+\.\d+\.\d+$", norm):
                refs.append(norm)
    out: list[str] = []
    seen: set[str] = set()
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out[:24]


def synthesize_lemma_bridge(
    payload: dict[str, Any],
    *,
    index_path: Path = DEFAULT_INDEX,
    max_neighbors: int = 12,
) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    path = payload.get("path") if isinstance(payload.get("path"), dict) else {}
    anchor_refs = _anchors_from_path(path)
    if not anchor_refs:
        return {"ok": False, "error": "lemma_bridge_skipped", "reason": "no_anchor_verse_refs"}
    if not index_path.is_file():
        return {"ok": False, "error": "lemma_index_missing", "path": str(index_path)}
    index = _load_index(index_path)
    neighbors = collect_neighbors(anchor_refs, index, max_neighbors=max_neighbors)
    answer_ko = build_answer_ko(query, anchor_refs, neighbors)
    return {
        "ok": True,
        "schema": "logos_studio_lemma_bridge_answer_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "non_gating": True,
        "synthesis_mode": "deterministic_lemma_neighbor_bridge",
        "llm_invoked": False,
        "answer_ko": answer_ko,
        "anchor_verse_refs": [_norm_verse(r) for r in anchor_refs if r][:24],
        "neighbor_count": len(neighbors),
        "neighbors": neighbors,
        "citation_valid": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stdin-json", action="store_true")
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--max-neighbors", type=int, default=12)
    ap.add_argument("--query", default="")
    ap.add_argument("--verse-refs", nargs="*", default=[])
    args = ap.parse_args()
    if args.stdin_json:
        payload = json.loads(sys.stdin.read() or "{}")
    else:
        payload = {"query": args.query, "path": {"verse_refs": args.verse_refs}}
    doc = synthesize_lemma_bridge(payload, index_path=args.index, max_neighbors=args.max_neighbors)
    print(json.dumps(doc, ensure_ascii=False))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
