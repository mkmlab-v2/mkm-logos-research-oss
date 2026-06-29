#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble magic_orb four_slot_response_v1 + interpretive_trajectory_v1 from SSOT artifacts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_FOUR_SLOT = "four_slot_response_v1"
SCHEMA_TRAJECTORY = "interpretive_trajectory_v1"
SCHEMA_WAVEFORM = "pipeline_waveform_v1"

SLOT_ORDER = ("fact_locked", "corpus_bound", "imagination_path", "unknown_gap")

JOB_QUERY_IDS = frozenset({"job_suffering_reason", "job_prologue_suffering"})
JOB_QUERY_RE = re.compile(r"욥|job", re.I)

SCHOOL_COLOR: dict[str, str] = {
    "literal_traditional": "#7ec8ff",
    "symbolic_metaphorical": "#b794f6",
    "dss_qumran_parallels": "#ffb340",
    "modern_demythologization": "#94a3b8",
    "friends_retribution_contrast": "#f472b6",
}

SCHOOL_LEMMA_HINTS: dict[str, list[str]] = {
    "literal_traditional": ["שטן"],
    "symbolic_metaphorical": ["שטן"],
    "dss_qumran_parallels": [],
    "modern_demythologization": [],
    "friends_retribution_contrast": [],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item(
    *,
    item_id: str,
    utterance_class: str,
    text_ko: str,
    source_tier: str = "artifact",
    must_not_present_as_fact: bool = False,
    provenance: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "item_id": item_id,
        "utterance_class": utterance_class,
        "text_ko": text_ko,
        "source_tier": source_tier,
        "must_not_present_as_fact": must_not_present_as_fact,
        "provenance": provenance or {},
    }
    if extra:
        row.update(extra)
    return row


def _why_query(query: str) -> bool:
    q = query.lower()
    return "왜" in query or "why" in q or "이유" in query


def _is_job_context(query: str, query_id: str | None) -> bool:
    if query_id and query_id in JOB_QUERY_IDS:
        return True
    return bool(JOB_QUERY_RE.search(query))


def _classify_rag_row(row: dict[str, Any]) -> str:
    kind = str(row.get("evidence_kind") or "")
    if kind == "subgraph_verse":
        return "corpus_bound"
    return "imagination_path"


def tag_rag_evidence(rag: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, row in enumerate(rag):
        if not isinstance(row, dict):
            continue
        uclass = _classify_rag_row(row)
        tagged = dict(row)
        tagged["utterance_class"] = uclass
        tagged["must_not_present_as_fact"] = uclass != "corpus_bound"
        out.append(tagged)
    return out


def _digest_entry(digest: dict[str, Any] | None, anchor_ref: str) -> dict[str, Any] | None:
    if not digest:
        return None
    entries = digest.get("panorama_entries") or []
    if not entries and digest.get("anchor_ref"):
        return digest
    for e in entries:
        if e.get("anchor_ref") == anchor_ref:
            return e
    return entries[0] if entries else None


def build_interpretive_trajectory(
    *,
    digest_entry: dict[str, Any],
    primary_anchor: str | None = None,
) -> dict[str, Any]:
    anchor_ref = str(primary_anchor or digest_entry.get("anchor_ref") or "Job.1.6")
    anchor = digest_entry.get("anchor_corpus") or {}
    schools = digest_entry.get("school_lanes") or []
    n = max(len(schools), 1)
    trajectories: list[dict[str, Any]] = []
    for i, school in enumerate(schools):
        sid = str(school.get("school_id") or f"school_{i}")
        angle_deg = round((360.0 / n) * i, 1)
        trajectories.append(
            {
                "school_id": sid,
                "label_ko": school.get("label_ko"),
                "color_token": SCHOOL_COLOR.get(sid, "#d4b06a"),
                "angle_deg": angle_deg,
                "weight_display": school.get("display_rank_weight"),
                "utterance_class": school.get("utterance_class"),
                "focus_lemmas": SCHOOL_LEMMA_HINTS.get(sid, []),
                "transform_tags": school.get("metaphor_transform_tags") or [],
                "reading_preview_ko": str(school.get("reading_ko") or "")[:200],
            }
        )

    return {
        "schema_version": SCHEMA_TRAJECTORY,
        "generated_at_utc": _utc_now(),
        "anchor_ref": anchor_ref,
        "center": {
            "verse_id": anchor_ref,
            "text_snippet": anchor.get("text_snippet"),
            "utterance_class": "corpus_bound",
        },
        "trajectories": trajectories,
        "interaction": {
            "hover": "emphasize_trajectory",
            "no_merge_to_single_answer": True,
        },
        "disclaimer_ko": (
            "해석 궤적은 큐레이션 [HYPO] 경로 시각화입니다. "
            "단어 연결은 힌트이며 자동 신학 추론이 아닙니다."
        ),
    }


def build_pipeline_waveform(
    *,
    router: dict[str, Any] | None,
    shadow: dict[str, Any] | None,
    digest: dict[str, Any] | None,
    four_slot_built: bool,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if router:
        steps.append(
            {
                "id": "router",
                "label_ko": "서브그래프 라우터",
                "ok": True,
                "detail": f"paths={len(router.get('paths') or [])}",
            }
        )
    if shadow:
        bp = shadow.get("boundary_proof") or {}
        steps.append(
            {
                "id": "shadow_boundary",
                "label_ko": "Shadow Lane 경계",
                "ok": True,
                "detail": str(bp.get("router_verdict") or "HOLD"),
            }
        )
    if digest:
        steps.append(
            {
                "id": "comparative_digest",
                "label_ko": "학파 digest",
                "ok": True,
                "detail": f"entries={digest.get('entry_count') or len(digest.get('panorama_entries') or [])}",
            }
        )
    if four_slot_built:
        steps.append(
            {
                "id": "four_slot_assemble",
                "label_ko": "4슬롯 조립",
                "ok": True,
                "detail": "artifact-bound",
            }
        )
    return {
        "schema_version": SCHEMA_WAVEFORM,
        "generated_at_utc": _utc_now(),
        "steps": steps,
        "disclaimer_ko": "실제 빌드 단계만 표시. 전세계 지식 전량 스캔 아님.",
    }


def assemble_four_slot_response(
    *,
    query: str,
    query_id: str | None,
    router: dict[str, Any] | None,
    shadow: dict[str, Any] | None,
    digest: dict[str, Any] | None,
    rag: list[dict[str, Any]],
    primary_anchor: str = "Job.1.6",
) -> dict[str, Any]:
    verified = bool((shadow or {}).get("rail_status", {}).get("verified_anchor_achieved"))
    bp = (shadow or {}).get("boundary_proof") or {}
    why = _why_query(query)
    entry = _digest_entry(digest, primary_anchor) if digest else None

    fact_items: list[dict[str, Any]] = []
    empty_reason = "verified_anchor=false"
    if verified:
        empty_reason = ""
        fact_items.append(
            _item(
                item_id="fact.verified_anchor",
                utterance_class="fact_locked",
                text_ko="verified_anchor 달성 — 별도 Integrity 게이트 참조.",
                source_tier="integrity_orb",
                must_not_present_as_fact=False,
            )
        )

    corpus_items: list[dict[str, Any]] = []
    if entry:
        ac = entry.get("anchor_corpus") or {}
        if ac.get("found"):
            corpus_items.append(
                _item(
                    item_id=f"corpus.{primary_anchor}",
                    utterance_class="corpus_bound",
                    text_ko=str(ac.get("text_snippet") or ""),
                    source_tier="resolver_bhs",
                    must_not_present_as_fact=False,
                    provenance={"verse_id": primary_anchor, "edition": ac.get("edition")},
                )
            )
    for row in rag:
        if _classify_rag_row(row) != "corpus_bound":
            continue
        sid = str(row.get("source_id") or "verse")
        corpus_items.append(
            _item(
                item_id=f"corpus.rag.{sid[:48]}",
                utterance_class="corpus_bound",
                text_ko=str(row.get("snippet") or "")[:400],
                source_tier="subgraph_verse",
                must_not_present_as_fact=False,
                provenance={"source_id": sid},
            )
        )

    imagination_items: list[dict[str, Any]] = []
    if entry:
        for school in entry.get("school_lanes") or []:
            if school.get("utterance_class") not in ("imagination_path", "unknown_gap"):
                continue
            if school.get("utterance_class") == "unknown_gap":
                continue
            sid = str(school.get("school_id") or "school")
            imagination_items.append(
                _item(
                    item_id=f"school.{primary_anchor}.{sid}",
                    utterance_class="imagination_path",
                    text_ko=str(school.get("reading_ko") or ""),
                    source_tier="comparative_theology_seed",
                    must_not_present_as_fact=True,
                    extra={
                        "school_id": sid,
                        "label_ko": school.get("label_ko"),
                        "display_rank_weight": school.get("display_rank_weight"),
                    },
                )
            )
    for i, row in enumerate(rag):
        if _classify_rag_row(row) != "imagination_path":
            continue
        imagination_items.append(
            _item(
                item_id=f"rag.path.{i}",
                utterance_class="imagination_path",
                text_ko=str(row.get("snippet") or "")[:320],
                source_tier="subgraph_path",
                must_not_present_as_fact=True,
                provenance={"source_id": row.get("source_id")},
            )
        )

    gap_items: list[dict[str, Any]] = []
    if entry:
        for school in entry.get("school_lanes") or []:
            if school.get("utterance_class") != "unknown_gap":
                continue
            gap_items.append(
                _item(
                    item_id=f"gap.school.{school.get('school_id')}",
                    utterance_class="unknown_gap",
                    text_ko=str(school.get("reading_ko") or ""),
                    source_tier="literature_pointer",
                    must_not_present_as_fact=True,
                    extra={"school_id": school.get("school_id")},
                )
            )
    if why and not bp.get("prologue_causality_refs_in_router_top"):
        gap_items.append(
            _item(
                item_id="gap.why_causality",
                utterance_class="unknown_gap",
                text_ko="「왜」인과 서사를 라우터 top에서 조립하지 않음 — boundary HOLD.",
                source_tier="shadow_boundary",
                must_not_present_as_fact=True,
            )
        )
    if shadow is not None and not bp.get("verified_anchor", False):
        gap_items.append(
            _item(
                item_id="gap.integrity_orb_job",
                utterance_class="unknown_gap",
                text_ko="Integrity Orb verified_anchor 없음 — DSS·외경 단정 금지.",
                source_tier="boundary_proof",
                must_not_present_as_fact=True,
            )
        )

    school_parallel = sum(
        1 for s in (entry or {}).get("school_lanes") or [] if s.get("utterance_class") == "imagination_path"
    )

    return {
        "schema_version": SCHEMA_FOUR_SLOT,
        "generated_at_utc": _utc_now(),
        "slot_order": list(SLOT_ORDER),
        "slots": {
            "fact_locked": {
                "items": fact_items,
                "empty_reason": empty_reason if not fact_items else None,
                "display_gem": "metal_bezel",
            },
            "corpus_bound": {
                "items": corpus_items,
                "display_gem": "stone_plate",
            },
            "imagination_path": {
                "items": imagination_items,
                "display_gem": "hypo_purple",
                "parallel_required": school_parallel >= 2,
            },
            "unknown_gap": {
                "items": gap_items,
                "display_gem": "glass_frost",
            },
        },
        "enforcement": {
            "send_gate": "HOLD",
            "why_query": why,
            "parallel_schools_required": school_parallel >= 2,
            "badge_ko": "검증 슬롯 비움 · 해석 병렬화 · NON_GATING",
            "forbidden_badge": "Fact-Lock 100%",
        },
        "journey_toast_ko": (
            "[HYPO: 학파 시각차 대조 완료]" if school_parallel >= 2 else "[경계 탐색 완료]"
        ),
    }


def enrich_magic_orb_payload(
    payload: dict[str, Any],
    *,
    shadow: dict[str, Any] | None,
    digest: dict[str, Any] | None,
    router: dict[str, Any] | None = None,
    primary_anchor: str = "Job.1.6",
) -> dict[str, Any]:
    query = str(payload.get("query") or "")
    query_id = payload.get("query_id")
    rag = list(payload.get("rag_evidence") or [])

    payload = dict(payload)
    payload["rag_evidence"] = tag_rag_evidence(rag)

    if not _is_job_context(query, str(query_id) if query_id else None) and not digest:
        return payload

    four = assemble_four_slot_response(
        query=query,
        query_id=str(query_id) if query_id else None,
        router=router,
        shadow=shadow,
        digest=digest,
        rag=rag,
        primary_anchor=primary_anchor,
    )
    entry = _digest_entry(digest, primary_anchor)
    trajectory = build_interpretive_trajectory(digest_entry=entry, primary_anchor=primary_anchor) if entry else None
    waveform = build_pipeline_waveform(
        router=router,
        shadow=shadow,
        digest=digest,
        four_slot_built=True,
    )

    payload = dict(payload)
    payload["version"] = "1.2.0"
    payload["four_slot_response_v1"] = four
    if trajectory:
        payload["interpretive_trajectory_v1"] = trajectory
    payload["pipeline_waveform_v1"] = waveform
    if digest:
        payload["comparative_theology_ref"] = {
            "digest_schema": digest.get("schema_version"),
            "primary_anchor_ref": digest.get("primary_anchor_ref") or primary_anchor,
            "anchors": [e.get("anchor_ref") for e in (digest.get("panorama_entries") or [])],
        }
    return payload
