#!/usr/bin/env python3
"""Myeongni corpus GraphRAG router — ijeoma chunk spine + keyword paths [HYPO]."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_CHUNK_TABLE = ROOT / "data/corpus/ijeoma/_inventory/IJEOMA_CHUNK_TABLE_2026-03-29.jsonl"
DEFAULT_STATE_PROBE = ROOT / "data/myeongni/16_STATE_MASTER_PROBE_v1.json"
DEFAULT_MYEONGNI_LENS = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
DEFAULT_OUT = ROOT / "reports/btrack_lens_graphrag_myeongni_corpus_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/btrack_lens_graphrag_myeongni_corpus_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _tokens(q: str) -> list[str]:
    raw = re.findall(r"[\w가-힣]{2,}", q.lower())
    seen: set[str] = set()
    out: list[str] = []
    for t in raw:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out[:24]


# Korean query terms → corpus aliases (ijeoma chunk spine, Chinese/Korean mix).
_TERM_ALIASES: dict[str, list[str]] = {
    "급락": ["極蕩", "蕩", "蕩也", "極大", "極廣"],
    "중기": ["天時", "世會", "人倫", "地方", "性命", "xingming"],
    "명리": ["xingming", "性命", "性命論", "天時", "世會", "人倫"],
    "타이밍": ["天時", "時", "耳聽天時"],
    "일진": ["天時", "世會", "人倫"],
    "흐름": ["世會", "天時", "極蕩"],
    "코스피": ["世會", "天時", "地方"],
    "관측": ["天時", "世會", "視世會"],
}
_XINGMING_QUERY_TERMS = frozenset({"명리", "중기", "타이밍", "일진", "흐름", "관측"})
_DIRECT_CJK_TERMS = frozenset({"天時", "世會", "人倫", "地方", "性命"})


def _query_prefers_xingming(query: str, tokens: list[str]) -> bool:
    if any(t in _XINGMING_QUERY_TERMS for t in tokens):
        return True
    return any(t in query for t in _XINGMING_QUERY_TERMS)


def _expand_match_terms(tokens: list[str], query: str) -> list[str]:
    terms: list[str] = list(tokens)
    seen = set(tokens)
    for t in tokens:
        for alias in _TERM_ALIASES.get(t, []):
            al = alias.lower()
            if al not in seen:
                seen.add(al)
                terms.append(al)
    for cjk in _DIRECT_CJK_TERMS:
        if cjk in query and cjk.lower() not in seen:
            seen.add(cjk.lower())
            terms.append(cjk.lower())
    return terms


def _read_jsonl_chunks(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _score_chunk(
    match_terms: list[str],
    chunk: dict[str, Any],
    *,
    prefers_xingming: bool,
) -> int:
    text = " ".join(
        str(chunk.get(k) or "")
        for k in ("section_label", "section_key", "preview_80chars", "chunk_id")
    ).lower()
    score = sum(1 for t in match_terms if t in text)
    section_key = str(chunk.get("section_key") or "").lower()
    if prefers_xingming:
        if section_key == "xingming":
            score += 3
        elif section_key == "hdr":
            score -= 1
    return max(score, 0)


def build_router(
    *,
    query: str,
    chunk_table: Path,
    state_probe: Path,
    myeongni_lens: Path,
    top_k: int,
) -> dict[str, Any]:
    tokens = _tokens(query)
    prefers_xingming = _query_prefers_xingming(query, tokens)
    match_terms = _expand_match_terms(tokens, query)

    def _score(c: dict[str, Any]) -> int:
        return _score_chunk(match_terms, c, prefers_xingming=prefers_xingming)

    chunks = _read_jsonl_chunks(chunk_table)
    ranked = sorted(chunks, key=_score, reverse=True)
    hits = [c for c in ranked if _score(c) > 0][:top_k]
    if not hits and ranked:
        hits = ranked[: min(3, len(ranked))]
    if prefers_xingming and hits:
        hits = sorted(hits, key=_score, reverse=True)

    state_doc = None
    if state_probe.is_file():
        try:
            state_doc = json.loads(state_probe.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            state_doc = None

    lens_doc = None
    if myeongni_lens.is_file():
        try:
            lens_doc = json.loads(myeongni_lens.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            lens_doc = None

    paths: list[dict[str, Any]] = []
    for i, ch in enumerate(hits, start=1):
        paths.append(
            {
                "path_id": f"path_{i}",
                "steps": [
                    "node_myeongni_query",
                    f"chunk::{ch.get('chunk_id')}",
                    f"section::{ch.get('section_key')}",
                ],
                "note_ko": (
                    f"{ch.get('section_label')} — {str(ch.get('preview_80chars') or '')[:60]}"
                ),
                "match_score": max(_score(ch), 1),
                "chunk_id": ch.get("chunk_id"),
            }
        )

    if state_doc:
        paths.append(
            {
                "path_id": "path_state_probe",
                "steps": ["node_16_state_master_probe", "state_vector_4d"],
                "note_ko": "16-state 실험 축 — B-track 관측 좌표 (D형 예측 미증명)",
                "match_score": 1,
            }
        )

    direction_score = 0.0
    if lens_doc and isinstance(lens_doc.get("scores"), dict):
        direction_score = float(lens_doc["scores"].get("direction_score") or 0.0)

    return {
        "schema": "btrack_lens_graphrag_router_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lens_id": "myeongni",
        "corpus_plane": "ijeoma_chunk_spine",
        "query": query,
        "query_tokens": tokens,
        "direction_score_from_lens": direction_score,
        "chunk_hits": len(hits),
        "paths": paths,
        "policy": {
            "no_prophecy_claim": True,
            "router_kind": "myeongni_corpus_graphrag_v1",
            "send_gate": "HOLD",
        },
        "pointers": {
            "chunk_table": str(chunk_table.as_posix()),
            "state_probe": str(state_probe.as_posix()),
            "myeongni_lens": str(myeongni_lens.as_posix()),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--query",
        default="코스피 급락 후 명리 중기 타이밍 관측 일진 흐름",
    )
    ap.add_argument("--chunk-table", type=Path, default=DEFAULT_CHUNK_TABLE)
    ap.add_argument("--state-probe", type=Path, default=DEFAULT_STATE_PROBE)
    ap.add_argument("--myeongni-lens", type=Path, default=DEFAULT_MYEONGNI_LENS)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_router(
        query=args.query,
        chunk_table=args.chunk_table,
        state_probe=args.state_probe,
        myeongni_lens=args.myeongni_lens,
        top_k=args.top_k,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "chunk_hits": doc["chunk_hits"], "paths": len(doc["paths"]), "out": str(args.out_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
