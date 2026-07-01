#!/usr/bin/env python3
"""Query-time BigSet conflict surface retrieval for Logos Studio (B-track).

Joins user query (+ optional preset) to conflict_group rows in sidecar JSON.
Deterministic keyword + preset boost; optional embedding rerank when ST available.

Reproduce:
  py scripts/retrieve_logos_studio_conflict_context_v1.py --query "네피림이 뭐야?"
  py scripts/retrieve_logos_studio_conflict_context_v1.py --query "욥기 고난 이유" --preset-id job_job_suffering_reason
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_studio_query_topic_guard_v1 import (  # noqa: E402
    GEN6_CONFLICT_IDS,
    query_flags,
)

DEFAULT_SIDECAR = ROOT / "projects/no1kmedi/public/data/logos_studio/bigset_conflict_sidecar_v1.json"
DEFAULT_PRESETS = ROOT / "projects/no1kmedi/public/data/logos_studio/qa_presets_v1.json"
OSS_PRESETS_FALLBACK = ROOT / "tests/fixtures/logos_studio_conflict_presets_oss_v1.json"

SKIP_GROUP_IDS = frozenset({"UNGROUPED"})

GROUP_KEYWORDS: dict[str, list[str]] = {
    "MKM_CONCEPT_SONS_OF_GOD": [
        "benei",
        "haelohim",
        "ha elohim",
        "베네",
        "엘로힘",
        "하나님의 아들",
        "sons of god",
        "sons-of-god",
        "divine council",
        "신의 회의",
        "창세기 6",
        "genesis 6",
        "beni ha",
    ],
    "MKM_CONCEPT_NEPHILIM": [
        "nephilim",
        "네피림",
        "거인",
        "giants",
        "watchers",
        "감시자",
        "watcher",
        "타락 천사",
        "fallen angel",
        "에녹",
        "enoch",
        "하이브리드",
        "창세기 6",
        "genesis 6",
    ],
    "MKM_CONCEPT_JOB_SUFFERING": [
        "욥",
        "욥기",
        "job",
        "고난",
        "suffering",
        "scope reset",
        "하늘 회의",
        "의회",
        "why question",
        "왜 고난",
        "고통",
        "job.1.6",
        "job 1:6",
    ],
    "MKM_CONCEPT_ISAIAH_YOUTUBE": [
        "isaiah",
        "이사야",
        "이사야서",
        "isa.6.8",
        "isa 6:8",
        "66장",
        "66권",
        "임마누엘",
        "53장",
        "위로하라",
        "youtube",
        "유튜브",
        "16챕터",
        "spine",
    ],
}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _preset_conflict_group(presets_doc: dict[str, Any], preset_id: str | None) -> str | None:
    if not preset_id:
        return None
    for row in presets_doc.get("presets") or []:
        if isinstance(row, dict) and row.get("id") == preset_id:
            gid = row.get("bigset_conflict_group_id")
            return str(gid) if gid else None
    return None


def _group_corpus(group: dict[str, Any]) -> str:
    parts = [
        str(group.get("lexicon_base") or ""),
        str(group.get("conflict_group_id") or ""),
    ]
    for school in group.get("schools") or []:
        if not isinstance(school, dict):
            continue
        parts.append(str(school.get("interpretation_ko") or "")[:400])
        parts.extend(str(t) for t in (school.get("traditions") or [])[:4])
    return _norm(" ".join(parts))


def _keyword_score(query: str, group: dict[str, Any]) -> float:
    q = _norm(query)
    if not q:
        return 0.0
    gid = str(group.get("conflict_group_id") or "")
    score = 0.0
    lex = _norm(str(group.get("lexicon_base") or ""))
    if lex and lex in q:
        score += 12.0
    for kw in GROUP_KEYWORDS.get(gid, []):
        token = _norm(kw)
        if len(token) < 2:
            continue
        if token in q:
            score += 10.0
    corpus = _group_corpus(group)
    for token in re.findall(r"[\w가-힣]{3,}", q):
        if token in corpus:
            score += 1.5
    return score


def _try_embedding_rerank(
    query: str,
    ranked: list[tuple[float, dict[str, Any]]],
) -> list[tuple[float, dict[str, Any]]]:
    if len(ranked) < 2:
        return ranked
    try:
        from scripts.logos_ann_lite_embedding_v1 import load_sentence_transformer

        model = load_sentence_transformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        q_vec = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
        texts = [_group_corpus(g)[:2000] for _, g in ranked]
        g_vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        boosted: list[tuple[float, dict[str, Any]]] = []
        for (base, group), g_vec in zip(ranked, g_vecs):
            sim = float((q_vec * g_vec).sum())
            boosted.append((base + sim * 6.0, group))
        boosted.sort(key=lambda x: x[0], reverse=True)
        return boosted
    except Exception:
        return ranked


def retrieve_conflict_context(
    query: str,
    *,
    preset_id: str | None = None,
    sidecar_path: Path = DEFAULT_SIDECAR,
    presets_path: Path = DEFAULT_PRESETS,
    top_k: int = 2,
    min_score: float = 6.0,
    use_embedding: bool = True,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not sidecar_path.is_file():
        return {"ok": False, "error": "sidecar_missing", "query": q}

    sidecar = _load_json(sidecar_path)
    presets_file = presets_path if presets_path.is_file() else (
        OSS_PRESETS_FALLBACK if OSS_PRESETS_FALLBACK.is_file() else presets_path
    )
    presets_doc = _load_json(presets_file) if presets_file.is_file() else {"presets": []}
    preset_group = _preset_conflict_group(presets_doc, preset_id)

    ranked: list[tuple[float, dict[str, Any]]] = []
    for group in sidecar.get("groups") or []:
        if not isinstance(group, dict):
            continue
        gid = str(group.get("conflict_group_id") or "")
        if gid in SKIP_GROUP_IDS:
            continue
        score = _keyword_score(q, group)
        if preset_group and gid == preset_group:
            score += 100.0
        qflags = query_flags(q)
        if qflags.get("eve_creation") and gid in GEN6_CONFLICT_IDS:
            score = 0.0
        if score > 0:
            ranked.append((score, group))

    ranked.sort(key=lambda x: x[0], reverse=True)

    if use_embedding and q and ranked:
        ranked = _try_embedding_rerank(q, ranked)

    selected = [(s, g) for s, g in ranked if s >= min_score][: max(1, top_k)]

    match_mode = "none"
    if selected:
        top_gid = str(selected[0][1].get("conflict_group_id") or "")
        if preset_group and top_gid == preset_group:
            match_mode = "preset_boost"
        elif use_embedding and len(ranked) > 1:
            match_mode = "keyword+embedding"
        else:
            match_mode = "keyword"

    groups_out = []
    for score, group in selected:
        schools = []
        for school in group.get("schools") or []:
            if not isinstance(school, dict):
                continue
            interp = str(school.get("interpretation_ko") or "").strip()
            if not interp or "404" in interp and "not found" in interp.lower():
                continue
            schools.append(school)
        groups_out.append(
            {
                "conflict_group_id": group.get("conflict_group_id"),
                "lexicon_base": group.get("lexicon_base"),
                "school_count": len(schools) or group.get("school_count"),
                "schools": schools[:12],
                "retrieval_score": round(score, 3),
            }
        )

    return {
        "ok": True,
        "schema": "logos_studio_conflict_retrieval_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "query": q,
        "preset_id": preset_id,
        "preset_conflict_group_id": preset_group,
        "match_mode": match_mode,
        "group_count": len(groups_out),
        "groups": groups_out,
        "ui_contract": sidecar.get("ui_contract") or {},
        "reproduce": "py scripts/retrieve_logos_studio_conflict_context_v1.py --query \"...\"",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default="")
    ap.add_argument("--query-stdin", action="store_true")
    ap.add_argument("--preset-id", default="")
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_SIDECAR)
    ap.add_argument("--presets-json", type=Path, default=DEFAULT_PRESETS)
    ap.add_argument("--top-k", type=int, default=2)
    ap.add_argument("--min-score", type=float, default=6.0)
    ap.add_argument("--no-embedding", action="store_true")
    args = ap.parse_args()

    query = sys.stdin.read() if args.query_stdin else args.query
    out = retrieve_conflict_context(
        query.strip(),
        preset_id=args.preset_id.strip() or None,
        sidecar_path=args.sidecar_json,
        presets_path=args.presets_json,
        top_k=args.top_k,
        min_score=args.min_score,
        use_embedding=not args.no_embedding,
    )
    print(json.dumps(out, ensure_ascii=False))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
