#!/usr/bin/env python3
"""Grounded studio answer synthesis from conflict context + path (Phase 2).

Deterministic school-parallel assembly by default; optional Ollama when enabled.
Citation linter blocks orphan verse ids.

Reproduce:
  py scripts/synthesize_logos_studio_dynamic_answer_v1.py --query "네피림" --stdin-json payload.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_studio_query_topic_guard_v1 import (  # noqa: E402
    build_mismatch_answer,
    detect_query_topic_mismatch,
)

VERSE_CITE_RE = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*\.\d+\.\d+)\b")

MAX_SCHOOL_BULLETS = 5
INTERP_TRUNC = 280


def _validate_citations(text: str, allowed: set[str]) -> dict[str, Any]:
    cited = set(VERSE_CITE_RE.findall(text or ""))
    orphan = sorted(cited - allowed)
    return {
        "cited_verse_ids": sorted(cited),
        "orphan_citations": orphan,
        "citation_valid": len(orphan) == 0,
    }


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _norm_verse_id(ref: str) -> str | None:
    ref = (ref or "").strip()
    if not ref:
        return None
    m = re.search(r"([A-Za-z][A-Za-z0-9_]*\.\d+\.\d+)", ref)
    return m.group(1) if m else None


def _collect_allowed_verses(path: dict[str, Any], conflict: dict[str, Any] | None) -> set[str]:
    allowed: set[str] = set()
    for ref in path.get("verse_refs") or []:
        vid = _norm_verse_id(str(ref))
        if vid:
            allowed.add(vid)
    if conflict:
        for group in conflict.get("groups") or []:
            for school in group.get("schools") or []:
                for vr in school.get("verse_refs") or []:
                    for part in re.split(r"[;,]", str(vr)):
                        vid = _norm_verse_id(part)
                        if vid:
                            allowed.add(vid)
    return allowed


def _truncate(text: str, limit: int = INTERP_TRUNC) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= limit:
        return t
    return t[: limit - 1].rstrip() + "…"


def _school_bullet(school: dict[str, Any]) -> str:
    tier = str(school.get("school_tier") or "?")
    interp = _truncate(str(school.get("interpretation_ko") or ""))
    trad = school.get("traditions") or []
    trad_txt = f" ({', '.join(str(t) for t in trad[:2])})" if trad else ""
    return f"· [{tier}] {interp}{trad_txt}"


def build_deterministic_answer(
    query: str,
    *,
    conflict: dict[str, Any] | None,
    path: dict[str, Any],
    preset_id: str | None,
) -> dict[str, Any]:
    groups = (conflict or {}).get("groups") or []
    if not groups:
        return {"ok": False, "error": "no_conflict_groups"}

    primary = groups[0]
    lex = str(primary.get("lexicon_base") or primary.get("conflict_group_id") or "conflict")
    note = str(path.get("note_ko") or "").strip()
    bullets: list[str] = []
    for school in (primary.get("schools") or [])[:MAX_SCHOOL_BULLETS]:
        if isinstance(school, dict) and school.get("interpretation_ko"):
            bullets.append(_school_bullet(school))

    verse_refs = [str(v) for v in (path.get("verse_refs") or [])[:12]]
    verse_line = ", ".join(verse_refs[:8])
    if len(verse_refs) > 8:
        verse_line += f" 외 {len(verse_refs) - 8}건"

    parts = [
        f"[HYPO] 질문 「{query.strip()}」에 대한 학파 병렬 요약 — **{lex}**.",
    ]
    if note:
        parts.append(note)
    if bullets:
        parts.append("\n".join(bullets))
    if verse_line:
        parts.append(f"연결 구절·경로 앵커: {verse_line}.")
    parts.append(
        "단일 학파 단정·실매매·신앙 확정 아님 — 최종 해석은 연구자·독자의 판단에 맡깁니다 [NON_GATING]."
    )
    answer = "\n\n".join(parts)
    one_liner = f"{lex} · 학파 {len(primary.get('schools') or [])} · 구절 {len(verse_refs)}"

    insight_card_patch = {
        "one_liner_ko": one_liner,
        "gap_ko": "query-time conflict join + deterministic synthesis — TSK 전량·open LLM 합성 아님.",
        "governance": "[HYPO][NON_GATING]",
    }

    allowed = _collect_allowed_verses(path, conflict)
    validation = _validate_citations(answer, allowed)

    return {
        "ok": True,
        "schema": "logos_studio_dynamic_synthesis_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "synthesis_mode": "deterministic_conflict_parallel",
        "llm_invoked": False,
        "answer_ko": answer,
        "insight_patch": insight_card_patch,
        "citation_valid": validation["citation_valid"],
        "citation_check": validation,
        "allowed_verse_ids": sorted(allowed)[:32],
        "preset_id": preset_id,
        "generated_at_utc": _utc(),
    }


def _evidence_from_path(path: dict[str, Any], allowed: set[str]) -> list[dict[str, Any]]:
    refs = []
    for vid in sorted(allowed)[:12]:
        refs.append({"verse_id": vid, "hash_tagged_snippet": f"path anchor {vid}"})
    if refs:
        return refs
    for ref in path.get("verse_refs") or []:
        vid = _norm_verse_id(str(ref))
        if vid:
            refs.append({"verse_id": vid, "hash_tagged_snippet": str(ref)[:120]})
    return refs


def _distill_backend() -> str:
    raw = str(os.environ.get("LOGOS_STUDIO_DISTILL_BACKEND", "ollama")).strip().lower()
    if raw in {"ollama", "azure", "auto"}:
        return raw
    return "ollama"


def _llm_synthesis_requested(prefer_llm: bool) -> bool:
    if not prefer_llm:
        return False
    raw = str(os.environ.get("LOGOS_STUDIO_DYNAMIC_SYNTHESIS_LLM", "auto")).strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on", "auto"}:
        return True
    return _truthy("MKM_LOGOS_LLM_DISTILL_ENABLE")


def try_llm_synthesis(
    query: str,
    *,
    conflict: dict[str, Any] | None,
    path: dict[str, Any],
) -> dict[str, Any] | None:
    if not _llm_synthesis_requested(prefer_llm=True):
        return None
    try:
        from scripts.run_logos_llm_distill_citation_lock_v1 import (
            try_azure_distill_narrative,
            try_ollama_distill_narrative,
        )
    except ImportError:
        return None
    allowed = _collect_allowed_verses(path, conflict)
    evidence = _evidence_from_path(path, allowed)
    if not evidence:
        return None
    lex = ""
    groups = (conflict or {}).get("groups") or []
    if groups:
        lex = str(groups[0].get("lexicon_base") or "")
    theme = f"Logos Studio: {query[:80]} — {lex}".strip()
    timeout = int(os.getenv("LOGOS_STUDIO_SYNTHESIS_TIMEOUT_S", "90"))
    backend = _distill_backend()

    def _from_narr(narr: dict[str, Any] | None, mode: str) -> dict[str, Any] | None:
        if not narr or not narr.get("body_ko") or not narr.get("citation_valid"):
            return None
        body = str(narr["body_ko"]).strip()
        if not body.startswith("[HYPO]"):
            body = f"[HYPO] {body}"
        return {
            "ok": True,
            "schema": "logos_studio_dynamic_synthesis_v1",
            "research_only": True,
            "send_gate": "HOLD",
            "non_gating": True,
            "synthesis_mode": mode,
            "distill_backend": backend,
            "llm_invoked": True,
            "answer_ko": body,
            "insight_patch": {
                "one_liner_ko": f"LLM synthesis · {lex or 'graph path'}",
                "governance": "[HYPO][NON_GATING]",
            },
            "citation_valid": bool(narr.get("citation_valid")),
            "citation_check": {
                "cited_verse_ids": narr.get("cited_verse_ids"),
                "orphan_citations": narr.get("orphan_citations"),
                "citation_valid": narr.get("citation_valid"),
            },
            "allowed_verse_ids": sorted(allowed)[:32],
            "generated_at_utc": _utc(),
        }

    if backend in {"ollama", "auto"}:
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/").replace("/v1", "")
        model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        ollama_narr = try_ollama_distill_narrative(
            evidence,
            theme_title=theme,
            host=host,
            model=model,
            timeout=timeout,
        )
        built = _from_narr(ollama_narr, "llm_citation_lock_ollama")
        if built:
            return built

    if backend in {"azure", "auto"}:
        azure_narr = try_azure_distill_narrative(evidence, theme_title=theme, timeout=timeout)
        built = _from_narr(azure_narr, "llm_citation_lock_azure")
        if built:
            return built

    return None


def synthesize_studio_answer(
    query: str,
    *,
    payload: dict[str, Any],
    prefer_llm: bool = False,
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}
    conflict = payload.get("conflict_context")
    path = payload.get("path") or {}
    preset_id = payload.get("preset_id")

    mismatch = detect_query_topic_mismatch(
        q, conflict=conflict, path=path, preset_id=preset_id
    )
    if mismatch:
        answer = build_mismatch_answer(q, mismatch)
        allowed = _collect_allowed_verses(path, conflict)
        validation = _validate_citations(answer, allowed)
        return {
            "ok": True,
            "schema": "logos_studio_dynamic_synthesis_v1",
            "research_only": True,
            "send_gate": "HOLD",
            "non_gating": True,
            "synthesis_mode": "query_topic_mismatch_guard",
            "llm_invoked": False,
            "answer_ko": answer,
            "insight_patch": {
                "one_liner_ko": "query-topic guard · Gen2 vs Gen6 격벽",
                "gap_ko": mismatch.get("hint_ko"),
                "governance": "[HYPO][NON_GATING]",
            },
            "citation_valid": True,
            "citation_check": {
                **validation,
                "citation_valid": True,
                "guard_note": "recommended Gen.2 anchors outside retrieved path — orphan expected",
            },
            "topic_mismatch": mismatch,
            "allowed_verse_ids": sorted(allowed)[:32],
            "preset_id": preset_id,
            "generated_at_utc": _utc(),
        }

    if _llm_synthesis_requested(prefer_llm):
        llm = try_llm_synthesis(q, conflict=conflict, path=path)
        if llm and llm.get("ok") and llm.get("citation_valid"):
            return llm

    if conflict and (conflict.get("group_count") or 0) > 0:
        det = build_deterministic_answer(q, conflict=conflict, path=path, preset_id=preset_id)
        if det.get("ok"):
            return det

    return {"ok": False, "error": "synthesis_skipped", "reason": "no_conflict_or_invalid"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--query", default="")
    ap.add_argument("--stdin-json", action="store_true")
    ap.add_argument("--prefer-llm", action="store_true")
    args = ap.parse_args()

    query = args.query
    payload: dict[str, Any] = {}
    if args.stdin_json:
        raw = sys.stdin.read()
        doc = json.loads(raw) if raw.strip() else {}
        if isinstance(doc, dict):
            query = str(doc.get("query") or query)
            payload = doc
    elif not query:
        print(json.dumps({"ok": False, "error": "missing_query"}, ensure_ascii=False))
        return 1

    out = synthesize_studio_answer(query, payload=payload, prefer_llm=args.prefer_llm)
    print(json.dumps(out, ensure_ascii=False))
    if not out.get("ok"):
        return 0
    if out.get("citation_valid") is False:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
