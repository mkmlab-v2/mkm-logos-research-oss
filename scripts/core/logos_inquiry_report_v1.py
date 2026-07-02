"""Logos inquiry report v1 — Standard tier S1-S5 (C-layer bound · IP-safe)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.logos_research_text_mvp_report_v1 import (  # noqa: WPS433
    _build_school_groups,
    _extract_citation_lock_anchors,
    _split_bullets,
    _strip_hypo,
)

SCHEMA = "logos_inquiry_report_v1"
VERSION = "1.0.0"
TIER = "standard"
OUTPUT_FORMAT = "inquiry_report_v1"
FREEZE_MANIFEST_REL = "docs/final/artifacts/logos_corpus_knowledge_freeze_manifest_v1_latest.json"
FREEZE_ARTIFACT_REL = "reports/logos_inquiry_report_schema_freeze_v1_latest.json"
LEMMA_FLOOR = 290_000

ROOT = Path(__file__).resolve().parents[2]

_BOILERPLATE_RES = (
    re.compile(r"전량\s*TSK\s*교차참조", re.I),
    re.compile(r"Tier\s*C\s*로드맵", re.I),
    re.compile(r"큐레이션\s*프리셋", re.I),
    re.compile(r"^lemma bridge\s*—", re.I),
)


def _is_studio_boilerplate(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    return any(rx.search(t) for rx in _BOILERPLATE_RES)


def _filter_boilerplate_bullets(items: list[str]) -> list[str]:
    return [x for x in items if not _is_studio_boilerplate(x)]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json_rel(rel: str) -> dict[str, Any]:
    path = ROOT / rel.replace("/", "\\") if "\\" in str(ROOT) else ROOT / rel
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_freeze_lexicon_meta(*, root: Path = ROOT) -> dict[str, Any]:
    manifest_path = root / FREEZE_MANIFEST_REL
    manifest_sha256: str | None = None
    if manifest_path.is_file():
        raw = manifest_path.read_text(encoding="utf-8")
        manifest_sha256 = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        manifest = json.loads(raw)
    elif root == ROOT:
        manifest = _read_json_rel(FREEZE_MANIFEST_REL)
    else:
        manifest = {}
    assets = manifest.get("assets") if isinstance(manifest.get("assets"), dict) else {}
    lemma = assets.get("lemma_verse_edges_jsonl") or {}
    sidecar = assets.get("sidecar_v2_corpus_full") or {}
    line_count = int(lemma.get("line_count") or 0)
    floor = int(lemma.get("min_line_count_floor") or LEMMA_FLOOR)
    return {
        "lemma_edge_line_count": line_count,
        "min_line_count_floor": floor,
        "floor_pass": line_count >= floor if line_count else False,
        "freeze_manifest_pointer": FREEZE_MANIFEST_REL,
        "manifest_sha256": manifest_sha256,
        "lemma_edges_sha256": str(lemma.get("sha256") or ""),
        "sidecar_corpus_sha256": str(sidecar.get("sha256") or ""),
    }


def load_sasang_regime_hint_b_track(*, root: Path = ROOT) -> dict[str, Any] | None:
    rel = "docs/final/artifacts/sasang_independent_lens_latest.json"
    path = root / rel
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    stream = doc.get("sasang_stream_outputs") if isinstance(doc.get("sasang_stream_outputs"), dict) else {}
    hypothesis = str(stream.get("regime_hypothesis") or "").strip() or None
    mapping = str(stream.get("mapping_target") or "").strip() or None
    if not hypothesis and not mapping:
        return None
    return {
        "schema": "sasang_regime_hint_b_track_v1",
        "research_only": True,
        "non_gating": True,
        "regime_hypothesis": hypothesis,
        "mapping_target": mapping,
        "token": f"Sasang_Regime:{hypothesis or 'unknown'}",
        "disclaimer_ko": "[HYPO][NON_GATING] B-track 사상 렌즈 토큰만 — 임상·Track A·실매매 트리거 아님.",
    }


def _path_token_preview(payload: dict[str, Any], cap: int = 16) -> list[str]:
    path = payload.get("path") or {}
    tokens: list[str] = []
    seen: set[str] = set()

    def _push(t: str) -> None:
        v = t.strip()
        if not v or v in seen:
            return
        seen.add(v)
        tokens.append(v)

    for raw in list(path.get("node_ids") or []) + list(path.get("steps") or []):
        t = str(raw).strip()
        if re.match(r"^[A-Za-z0-9]+\.\d", t):
            _push(t)
        elif t.startswith("lemma_") or t.startswith("node:"):
            _push(t.replace("node:", ""))
        elif re.search(r"gematria", t, re.I):
            _push(t)
        if len(tokens) >= cap:
            break

    for ref in path.get("verse_refs") or []:
        if len(tokens) >= cap:
            break
        verse = str(ref).strip()
        if not verse:
            continue
        pin = hashlib.sha256(f"gematria_pin:{verse}".encode("utf-8")).hexdigest()[:12]
        _push(f"Gematria_Pin:{pin}")

    return tokens[:cap]


def _sections_payload_for_hash(sections_s1_s4: dict[str, Any]) -> str:
    canonical = json.dumps(sections_s1_s4, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return canonical


def build_inquiry_report(
    payload: dict[str, Any],
    *,
    query: str,
    intake: dict[str, Any] | None = None,
    freeze_meta: dict[str, Any] | None = None,
    chain_exit_code: int = 0,
    artifact_path: str = FREEZE_ARTIFACT_REL,
    sasang_hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = payload.get("path") or {}
    answer = _strip_hypo(str(payload.get("answer") or ""))
    verse_refs = [str(v).strip() for v in (path.get("verse_refs") or []) if str(v).strip()]
    insight = payload.get("insight_card") or {}
    summary_bullets = _filter_boilerplate_bullets(_split_bullets(str(payload.get("answer") or "")))
    if isinstance(insight, dict) and insight.get("gap_ko"):
        gap = _strip_hypo(str(insight["gap_ko"]))
        if not _is_studio_boilerplate(gap):
            summary_bullets.append(gap)

    lex_meta = freeze_meta or load_freeze_lexicon_meta()
    school_groups = _build_school_groups(payload)
    regime_hint = sasang_hint if sasang_hint is not None else load_sasang_regime_hint_b_track()

    s1 = {
        "section_id": "S1_citation_lock",
        "title_ko": "Citation Lock (구절 인용)",
        "verse_refs": verse_refs[:24],
        "citation_lock_anchors": _extract_citation_lock_anchors(payload)[:24],
        "security_note_ko": "canonical verse ref·citation lock 인덱스만 — KRV/31k 원문 전문 노출 금지.",
    }
    s2 = {
        "section_id": "S2_lexicon_hash",
        "title_ko": "Lexicon Hash (원어 렉시콘)",
        "lemma_edge_line_count": lex_meta.get("lemma_edge_line_count"),
        "min_line_count_floor": lex_meta.get("min_line_count_floor", LEMMA_FLOOR),
        "floor_pass": bool(lex_meta.get("floor_pass")),
        "freeze_manifest_pointer": lex_meta.get("freeze_manifest_pointer", FREEZE_MANIFEST_REL),
        "manifest_sha256": lex_meta.get("manifest_sha256"),
        "lemma_edges_sha256": lex_meta.get("lemma_edges_sha256", ""),
        "sidecar_corpus_sha256": lex_meta.get("sidecar_corpus_sha256", ""),
        "path_token_preview": _path_token_preview(payload),
        "security_note_ko": "29만 행 원문 덤프 금지 — line_count·sha256 pin·경로 토큰 preview만.",
    }
    s3 = {
        "section_id": "S3_context_divergence",
        "title_ko": "Context Divergence (맥락/학파 분기)",
        "groups": school_groups,
        "note_ko": "[NON_GATING] conflict_context 기반 — Track A·실매매 트리거 아님.",
    }
    if regime_hint:
        s3["regime_hint_b_track"] = regime_hint
    s4 = {
        "section_id": "S4_dynamic_synthesis",
        "title_ko": "Dynamic Synthesis (고차원 통찰)",
        "body_ko": answer or "응답 본문을 생성하지 못했습니다.",
        "bullets_ko": summary_bullets[:8],
        "streaming_deferred": "active",
    }

    s1_s4 = {"S1": s1, "S2": s2, "S3": s3, "S4": s4}
    payload_canonical = _sections_payload_for_hash(s1_s4)
    payload_sha256 = hashlib.sha256(payload_canonical.encode("utf-8")).hexdigest()

    s5 = {
        "section_id": "S5_jema_integrity_signoff",
        "title_ko": "JEMA Integrity Signoff (무결성 서명)",
        "signoff_status": "final",
        "chain_exit_code": chain_exit_code,
        "artifact_path": artifact_path,
        "sections_payload_sha256": payload_sha256,
        "freeze_verify_command": "py scripts/check_logos_corpus_knowledge_freeze_manifest_v1.py",
        "signed_at_utc": _utc_now(),
    }

    intake_doc = intake or {"intake_gate": "PASS", "domain_lane": "logos", "intent_chip": "reports"}

    return {
        "schema": SCHEMA,
        "version": VERSION,
        "tier": TIER,
        "output_format": OUTPUT_FORMAT,
        "generated_at_utc": _utc_now(),
        "research_only": bool(payload.get("research_only", True)),
        "non_gating": bool(payload.get("non_gating", True)),
        "send_gate": str(payload.get("send_gate") or "HOLD"),
        "query": query.strip(),
        "preset_id": payload.get("preset_id"),
        "intake": intake_doc,
        "sections": {**s1_s4, "S5": s5},
        "governance": {
            "disclaimer_ko": (
                "logos inquiry Standard — Track B [HYPO] · research_only · NON_GATING. "
                "의료·진단·투자·실거래 지시가 아닙니다."
            ),
            "forbidden_claims": [
                "무환각 0%",
                "GPT 대체",
                "KRV/31k 원문 전체 공개",
                "투자·실매매 트리거",
            ],
            "quality_basis_ko": "eval·Brier·citation lock·freeze pin — 마케팅 환각률 주장 금지.",
        },
        "evidence_confidence": payload.get("evidence_confidence"),
    }
