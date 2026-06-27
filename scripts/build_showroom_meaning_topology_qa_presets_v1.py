#!/usr/bin/env python3
"""Build showroom Q&A preset pack from meaning topology graph slice ([HYPO] demo only)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.logos_verse_ref_canonical_v1 import canonical_verse_ref  # noqa: E402

DEFAULT_SLICE = ROOT / "docs/final/artifacts/showroom_meaning_topology_graph_slice_v1_latest.json"
DEFAULT_CHRONOLOGY = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_logos_chronology_overlay_v1.json"
)
DEFAULT_JOB_READING_PACK = (
    ROOT
    / "docs/final/artifacts/showroom_logos_job_reading_pack_slice_v1_latest.json"
)
OUT_MVP = (
    ROOT
    / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp"
    / "showroom_meaning_topology_qa_presets_v1.json"
)
OUT_ART = ROOT / "docs/final/artifacts/showroom_meaning_topology_qa_presets_v1_latest.json"

# Curated KO synonyms for era preset routing (static index; commander sign-off to extend).
ERA_KO_SYNONYMS: dict[str, list[str]] = {
    "genesis_order_and_fall": [
        "우주",
        "창조",
        "창조 원리",
        "창조의 원리",
        "창세기",
        "creation",
        "genesis",
        "태초",
        "최초",
    ],
}

ERA_KEYWORD_LEADS_KO: dict[str, dict[str, str]] = {
    "genesis_order_and_fall": {
        "_default": "창세 질서가 드러나고, 경계·타락 직전까지의 서사 프레임을 관측합니다.",
        "우주": "『우주』는 창세 이전·이외의 근원 질문으로 읽으며, 여기서는 **질서가 펼쳐지기 전의 빈 틀**에 해당합니다.",
        "창조": "『창조』는 빛·경계·명명을 통해 질서가 단계적으로 드러나는 구간입니다.",
        "창조 원리": "『창조 원리』는 단일 공식이 아니라, 단계적 질서 전개의 **관측 프레임**입니다.",
        "창조의 원리": "『창조의 원리』는 단일 공식이 아니라, 단계적 질서 전개의 **관측 프레임**입니다.",
    },
}


def _slim_era_notes(notes: str) -> str:
    s = re.sub(r"^\[HYPO\]\s*", "", (notes or "").strip())
    s = re.sub(r"AI 합성 v\d+\([^)]*\)\.\s*", "", s)
    for drop in (
        "신학적 확정·예언 적중·실매매 신호가 아닙니다.",
        "1차 Field는 regime_map 실물 레짐, 본 연대기는 Logos Observatory 부록(NON_GATING) 전용입니다.",
    ):
        s = s.replace(drop, "")
    return " ".join(s.split())


def _era_answer_blocks(era: dict, *, slice_gap: bool) -> dict[str, str]:
    label = str(era.get("label_ko") or era.get("era_id") or "")
    era_id = str(era.get("era_id") or "")
    notes = _slim_era_notes(str(era.get("notes_ko") or ""))
    theme = ""
    tags = era.get("theme_tags") or []
    if tags:
        theme = "테마: " + ", ".join(str(t) for t in tags[:4]) + "."
    body_parts = []
    leads = ERA_KEYWORD_LEADS_KO.get(era_id, {})
    if leads.get("_default"):
        body_parts.append(leads["_default"])
    if notes:
        body_parts.append(notes)
    if theme:
        body_parts.append(theme)
    title = f"연대기 · {label}"
    body = "\n\n".join(p for p in body_parts if p)
    footer = "research_only · NON_GATING · 투자·실매매·신학적 확정 아님"
    if slice_gap:
        footer += " · slice GAP: era 허브만 표시"
    return {
        "answer_title_ko": title,
        "answer_body_ko": body,
        "answer_footer_ko": footer,
        "answer_ko": f"{title}\n\n{body}\n\n{footer}",
        "answer_ko_product": f"{title}\n\n{body}",
        "keyword_leads_ko": leads or None,
    }


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _nodes_by_kind(doc: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"verse": [], "theme": [], "regime": [], "other": []}
    for n in doc.get("nodes") or []:
        k = str(n.get("kind") or "other")
        out.setdefault(k, []).append(str(n["id"]))
    return out


def _daniel_aramaic_ids(doc: dict) -> list[str]:
    ids: list[str] = []
    for n in doc.get("nodes") or []:
        if n.get("kind") != "verse":
            continue
        ref = str(n.get("ref") or n.get("label") or "")
        if ref.startswith("Dan.2."):
            ids.append(str(n["id"]))
    return ids


def _era_keywords(era: dict) -> list[str]:
    eid = str(era.get("era_id") or "")
    label = str(era.get("label_ko") or "")
    label_en = str(era.get("label_en") or "")
    parts: list[str] = [eid]
    if label:
        parts.append(label)
        for tok in label.replace("(", " ").replace(")", " ").replace("·", " ").split():
            tok = tok.strip()
            if len(tok) >= 2:
                parts.append(tok)
    if label_en:
        for tok in label_en.replace(",", " ").split():
            tok = tok.strip().lower()
            if len(tok) >= 3:
                parts.append(tok)
    parts.extend(str(t) for t in (era.get("theme_tags") or []))
    parts.extend(ERA_KO_SYNONYMS.get(eid, []))
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        k = p.strip()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


def _era_highlight_node_ids(era: dict, doc: dict) -> tuple[list[str], bool]:
    """Return highlight ids and whether chronology verse_refs are absent from graph slice."""
    era_nid = f"era::{era.get('era_id')}"
    raw_refs = [str(r) for r in (era.get("verse_refs") or [])]
    from_slice = _job_verse_node_ids(doc, set(raw_refs)) if raw_refs else []
    highlights = list(dict.fromkeys(from_slice + [era_nid]))
    slice_gap = bool(raw_refs) and not from_slice
    return highlights, slice_gap


def _era_presets(chrono: dict | None, doc: dict) -> list[dict]:
    if not chrono:
        return []
    out: list[dict] = []
    for era in chrono.get("eras") or []:
        highlights, slice_gap = _era_highlight_node_ids(era, doc)
        label = str(era.get("label_ko") or era.get("era_id") or "")
        blocks = _era_answer_blocks(era, slice_gap=slice_gap)
        row = {
            "id": f"era_{era.get('era_id', 'x')}",
            "prompt_ko": label,
            "highlight_node_ids": highlights,
            "keywords": _era_keywords(era),
            "slice_gap": slice_gap,
            **blocks,
        }
        if blocks.get("keyword_leads_ko") is None:
            row.pop("keyword_leads_ko", None)
        out.append(row)
    return out


def match_preset_query(query: str, presets_doc: dict, *, chrono: dict | None = None) -> dict | None:
    """Mirror v6 `matchPreset` for offline golden tests."""
    t = (query or "").strip().lower()
    if not t:
        return None
    for p in presets_doc.get("presets") or []:
        prompt = str(p.get("prompt_ko") or "").lower()
        if prompt and prompt == t:
            return p
        for kw in p.get("keywords") or []:
            if str(kw).lower() in t:
                return p
    if chrono:
        for era in chrono.get("eras") or []:
            label = str(era.get("label_ko") or "").lower()
            eid = str(era.get("era_id") or "").lower()
            if (eid and eid in t) or (label and (label in t or label[:4] in t)):
                return {
                    "id": f"era_{era.get('era_id', 'x')}",
                    "prompt_ko": era.get("label_ko"),
                    "source": "chrono_inline_match",
                }
    return None


def _job_verse_node_ids(graph_doc: dict, verse_refs: set[str]) -> list[str]:
    canon_refs = {canonical_verse_ref(v) for v in verse_refs}
    ids: list[str] = []
    for n in graph_doc.get("nodes") or []:
        ref = canonical_verse_ref(str(n.get("ref") or ""))
        label = canonical_verse_ref(str(n.get("label") or "").replace(" ", "."))
        nid = str(n.get("id") or "")
        for vr in canon_refs:
            if not vr:
                continue
            if ref == vr or label == vr or nid == vr or nid.endswith(f"::{vr}"):
                ids.append(nid)
                break
    return list(dict.fromkeys(ids))


def _job_forced_node_ids(graph_doc: dict) -> list[str]:
    sel = graph_doc.get("selection") or {}
    bundle = sel.get("job_seed_bundle") or {}
    forced = list(bundle.get("forced_node_ids") or [])
    if forced:
        return forced
    return [str(n["id"]) for n in (graph_doc.get("nodes") or []) if str(n.get("kind") or "") == "stage"]


def _job_presets_from_reading_pack(job_doc: dict | None, graph_doc: dict) -> list[dict]:
    if not job_doc:
        return []
    verse_refs: set[str] = set()
    for stage in job_doc.get("narrative_route_public") or []:
        verse_refs.update(str(v) for v in (stage.get("verse_refs") or []))
    highlight_ids = list(
        dict.fromkeys(_job_forced_node_ids(graph_doc) + _job_verse_node_ids(graph_doc, verse_refs))
    )
    out: list[dict] = []
    for hp in job_doc.get("highlight_presets") or []:
        pid = str(hp.get("preset_id") or "job")
        out.append(
            {
                "id": f"job_{pid}",
                "prompt_ko": str(hp.get("label_ko") or pid),
                "answer_ko": (
                    f"[HYPO] {job_doc.get('query_ko') or '욥기'} — reading pack 3종 데모. "
                    "「왜 고난?」 인과 단답 없음(why_question_assembled=false). "
                    "**Job Reading Pack** 페이지에서 Pack 카드를 확인하세요."
                ),
                "answer_ko_product": (
                    f"[HYPO] Job reading pack demo · no causal why-answer · see insight cards."
                ),
                "highlight_node_ids": highlight_ids[:48],
                "keywords": list(hp.get("keywords_ko") or []),
                "job_reading_pack_preset_id": pid,
                "job_reading_pack_url": "public_showroom_logos_job_reading_pack_v1.html?preset=" + pid,
            }
        )
    return out


def build_presets(doc: dict, *, chrono: dict | None = None, job_doc: dict | None = None) -> dict:
    by_kind = _nodes_by_kind(doc)
    daniel = _daniel_aramaic_ids(doc)
    theme_ids = by_kind.get("theme") or []
    regime_ids = by_kind.get("regime") or []

    return {
        "schema_version": "showroom_meaning_topology_qa_presets_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "disclaimer": {
            "evidence_tier": "hypo_research_only",
            "gating_status": "NON_GATING",
            "no_trade_signals": True,
            "note_ko": "데모 프리셋 응답입니다. 실시간 LLM·실매매·종교적 단정이 아닙니다.",
            "note_ko_product": "Curated preset · research_only · NON_GATING · not investment advice.",
        },
        "graph_slice_path": "showroom_meaning_topology_graph_slice_v1.json",
        "presets": [
            {
                "id": "p1_empire_transition",
                "prompt_ko": "제국·왕조 전환(imperial / empire transition)과 연결된 구절은?",
                "answer_ko": (
                    "[HYPO] insight 허브 기준으로 **imperial_transition** 테마와 **empire_transition** "
                    "레짐이 다니엘 2장 구절 클러스터와 엣지로 연결됩니다. "
                    "이 화면은 연구용 부분 그래프이며 투자·매매·신학적 진리 단정이 아닙니다."
                ),
                "answer_ko_product": (
                    "[HYPO] **imperial_transition** 테마와 **empire_transition** 레짐이 "
                    "다니엘 2장 구절 클러스터와 그래프 엣지로 연결됩니다."
                ),
                "highlight_node_ids": list(
                    dict.fromkeys(theme_ids + regime_ids + daniel)
                ),
                "keywords": ["제국", "왕조", "empire", "imperial", "transition", "다니엘", "daniel"],
            },
            {
                "id": "p2_daniel2_cluster",
                "prompt_ko": "다니엘 2장(10–19절) 주변 구절만 보여줘",
                "answer_ko": (
                    "[HYPO] 아람어·히브리 렌즈 **Dan.2.10–Dan.2.19** 구절 노드와 "
                    "cross_lens_confirm 엣지가 강조됩니다. 전체 1,192노드 그래프가 아닌 **캡된 서브그래프**입니다."
                ),
                "highlight_node_ids": daniel,
                "keywords": ["다니엘", "dan.2", "daniel", "10", "19", "구절"],
            },
            {
                "id": "p3_theme_regime",
                "prompt_ko": "테마(theme)와 레짐(regime) 허브만 설명해줘",
                "answer_ko": (
                    "[HYPO] **theme::imperial_transition** · **regime::empire_transition** 두 허브가 "
                    "시드 후보이며, 주변 verse 노드로 의미 연결이 투영됩니다. 운영 게이트·주문 트리거와 무관합니다."
                ),
                "answer_ko_product": (
                    "[HYPO] **theme::imperial_transition** · **regime::empire_transition** 허브와 "
                    "연결된 verse 노드로 의미 경로가 투영됩니다."
                ),
                "highlight_node_ids": theme_ids + regime_ids,
                "keywords": ["테마", "레짐", "theme", "regime", "허브"],
            },
            {
                "id": "p4_full_map",
                "prompt_ko": "전체 부분 그래프 구조를 한눈에 보여줘",
                "answer_ko": (
                    f"[HYPO] 현재 슬라이스는 **{doc.get('stats', {}).get('node_count', '?')}노드 · "
                    f"{doc.get('stats', {}).get('edge_count', '?')}엣지**입니다. "
                    "verse·theme·regime 종류별 색으로 구분됩니다."
                ),
                "highlight_node_ids": [str(n["id"]) for n in (doc.get("nodes") or [])],
                "keywords": ["전체", "구조", "망", "그래프", "overview"],
            },
        ] + _era_presets(chrono, doc) + _job_presets_from_reading_pack(job_doc, doc),
        "fallback": {
            "abstention": True,
            "answer_ko": (
                "[HYPO] 매칭된 연구용 프리셋이 없습니다. 왼쪽 **제안 질문**을 선택하거나 "
                "연대기·테마 키워드를 포함해 보세요. 임의의 구절 클러스터(예: 다니엘 2)로 연결하지 않습니다. "
                "본선 Q&A API 연동 전 **데모 프리셋** · research_only · NON_GATING."
            ),
            "answer_ko_product": (
                "[HYPO] No curated preset match · select a suggested question · "
                "no fallback demo cluster · research_only · NON_GATING."
            ),
            "highlight_node_ids": [],
            "reasoning_path_v1": {
                "schema_version": "logos_reasoning_path_v1",
                "node_ids": [],
                "edges": [],
                "path_label_ko": "",
            },
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice-json", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--job-reading-pack-json", type=Path, default=DEFAULT_JOB_READING_PACK)
    ap.add_argument("--no-chronology", action="store_true")
    ap.add_argument("--no-job-reading-pack", action="store_true")
    ap.add_argument("--out-mvp", type=Path, default=OUT_MVP)
    ap.add_argument("--out-artifact", type=Path, default=OUT_ART)
    args = ap.parse_args()
    doc = _load(args.slice_json)
    chrono = None
    if not args.no_chronology and args.chronology_json.is_file():
        chrono = _load(args.chronology_json)
    job_doc = None
    if not args.no_job_reading_pack and args.job_reading_pack_json.is_file():
        job_doc = _load(args.job_reading_pack_json)
    payload = build_presets(doc, chrono=chrono, job_doc=job_doc)
    from compute_logos_reasoning_path_v1 import attach_paths_to_presets

    payload = attach_paths_to_presets(payload, doc)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    args.out_mvp.parent.mkdir(parents=True, exist_ok=True)
    args.out_mvp.write_text(text, encoding="utf-8")
    args.out_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.out_artifact.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "out_mvp": str(args.out_mvp), "presets": len(payload["presets"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
