#!/usr/bin/env python3
"""Build + validate Isaiah YouTube 16-chapter → MKM Logos bridge map [HYPO].

Reproduce:
  py scripts/build_isaiah_youtube_16chapter_mkm_bridge_map_v1.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "reports/logos_corpus_4d_topology_verses_v1_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/isaiah_youtube_16chapter_mkm_bridge_map_v1_latest.json"

# logos_corpus_4d_topology uses Jhn (not John); Mark·1Pet 등 일부 권 미포함(52 books).
CORPUS_BOOK_ALIASES = {"John": "Jhn"}
CORPUS_ABSENT_BOOKS = ("Mark", "1Pet", "2Pet", "1John", "2John", "3John", "Jude", "Phlm", "Titus", "1Tim", "2Tim", "2Thess", "1Thess")

CHAPTERS: list[dict[str, Any]] = [
    {
        "chapter_id": "ch01",
        "title_ko": "성경 66권 전체가 이사야 66장 속에 압축된 설계도",
        "video_claim_ko": "이사야 66장 = 성경 66권; 전반 39장 심판·후반 27장 구원 = 구약39·신약27",
        "mkm_evidence_tier": "C",
        "mkm_verdict": "partial",
        "anchor_verse_ids": ["Isa.1.1", "Isa.40.1", "Isa.66.22"],
        "mkm_paths": [
            {
                "path_id": "path_corpus_66_chapters",
                "source_artifact": "reports/logos_corpus_4d_topology_verses_v1_latest.jsonl",
                "steps": ["corpus_isaiah_chapter_count=66", "protestant_canon_ot39_nt27=66"],
                "note_ko": "산술·장 수는 Tier A. 장↔권 1:1 압축 지도는 MKM SSOT 없음 → Tier C 서사.",
            },
            {
                "path_id": "path_judgment_comfort_pivot",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_gold_q08_suffering_comfort_pattern_v1_latest.json",
                "steps": ["concept:suffering_comfort", "Isa.40.1"],
                "note_ko": "40장 전환(위로)만 그래프로 고정. 39=전심판·27=전은혜 단색 독해는 과장.",
            },
        ],
        "overclaim_flags": ["chapter_equals_book_1to1_map", "first_39_all_judgment_only"],
    },
    {
        "chapter_id": "ch02",
        "title_ko": "들포도의 배신: 제사는 있지만 마음을 잃어버린 자들",
        "video_claim_ko": "형식적 예배·제사; 이사야 1장·5장 들포도",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.1.11", "Isa.1.13", "Isa.5.1", "Isa.5.2", "Isa.5.7"],
        "mkm_paths": [
            {
                "path_id": "path_vineyard_wild_grapes",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_13_vine_branches.json",
                "steps": ["Isa.5.1", "ANCHOR_JOHN_15_1", "Jer.2.21"],
                "note_ko": "들포도·포도원 stewardship drift — 영상 5장 비유와 정합.",
            },
            {
                "path_id": "path_form_without_heart",
                "source_artifact": "docs/final/fixtures/logos_gold_query_eval_v1.json",
                "steps": ["q02:judgment_warning_collapse", "Isa.1.x"],
                "note_ko": "심판·경고 레인(q02) 보조. 1장 손 펼침 기도 거부는 정경 직독 Tier A.",
            },
        ],
    },
    {
        "chapter_id": "ch03",
        "title_ko": "보좌는 비지 않았다: 웃시아 왕의 죽음과 성전 환상",
        "video_claim_ko": "이사야 6장 보좌 환상; 땅 왕자는 비었으나 하늘 보좌는 차 있음",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.6.1", "Isa.6.3", "Isa.6.4", "Isa.6.5", "Isa.6.7"],
        "mkm_paths": [
            {
                "path_id": "path_throne_observation",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_07_revelation_throne.json",
                "steps": ["Isa.6.1", "Dan.7.9", "Rev.4.2", "Rev.21.4"],
                "note_ko": "보좌 관측 앵커 — 거시 서사 [NON_GATING].",
            },
            {
                "path_id": "path_coal_purification",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_1384_isaiah_coal_lips.json",
                "steps": ["Isa.6.6", "Isa.6.7"],
                "note_ko": "숯·입술 정결. theme_1067은 ops stub; 1384가 본문 근접.",
            },
        ],
    },
    {
        "chapter_id": "ch04",
        "title_ko": "내가 여기 있나이다: 부르신 자를 준비시키시는 은혜",
        "video_claim_ko": "이사야 6:8 소명; 준비된 자가 아닌 부르신 자를 준비",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.6.8"],
        "mkm_paths": [
            {
                "path_id": "path_send_me_echo",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_37_samuel_call.json",
                "steps": ["1Sam.3.10", "Isa.6.8", "Jer.1.5"],
                "note_ko": "send_me / on-call ack 패턴 — 영상 6:8과 직접 연결.",
            },
        ],
    },
    {
        "chapter_id": "ch05",
        "title_ko": "흑암 속의 두 씨앗: 임마누엘과 한 아기의 탄생 예언",
        "video_claim_ko": "7:14 임마누엘; 9:6 아기 탄생; 흑암 속 빛",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "partial",
        "anchor_verse_ids": ["Isa.7.14", "Isa.8.10", "Isa.9.6", "Matt.1.23", "Luke.2.12"],
        "mkm_paths": [
            {
                "path_id": "path_immanuel_sign",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_179_isaiah_virgin_sign.json",
                "steps": ["Isa.7.14", "Matt.1.23", "Isa.9.6", "Luke.2.12"],
                "note_ko": "신약 성취 인용 Tier A. 아하스 당대 표적 vs 메시아 독해는 Tier B 분쟁.",
            },
        ],
        "overclaim_flags": ["immanuel_only_messianic_no_ahaz_context"],
    },
    {
        "chapter_id": "ch06",
        "title_ko": "예루살렘의 통곡: 랍사게의 조롱과 히스기야의 협박 편지",
        "video_claim_ko": "산헤립·랍사게; 히스기야가 편지를 하나님 앞에 펼침",
        "mkm_evidence_tier": "A",
        "mkm_verdict": "partial",
        "anchor_verse_ids": ["Isa.36.1", "Isa.37.14", "Isa.37.15", "2Kgs.19.14", "2Kgs.19.19"],
        "mkm_paths": [
            {
                "path_id": "path_assyrian_siege_narrative",
                "source_artifact": "canonical_parallel_isaiah_kings",
                "steps": ["Isa.36-37", "2Kgs.18-19", "2Chr.32"],
                "note_ko": "역사·정경 서사 Tier A. MKM 전용 bridge 파일은 GAP — 정경 직독.",
            },
            {
                "path_id": "path_judgment_warning_q02",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_gold_q02_judgment_warning_collapse_gemini_v1_latest.json",
                "steps": ["concept:judgment_warning_collapse", "Isa.36.x"],
                "note_ko": "위기·경고 패턴 보조 [HYPO].",
            },
        ],
        "gap_notes_ko": "랍사게·히스기야 전용 metaphor theme 미등록; theme_258/212는 역병·해시계만.",
    },
    {
        "chapter_id": "ch07",
        "title_ko": "칼 한 번 쓰지 않은 승리: 밤새 쓰러진 앗수르 군대",
        "video_claim_ko": "이사야 37장; 천사가 진영 침; 산헤립 퇴각",
        "mkm_evidence_tier": "A",
        "mkm_verdict": "partial",
        "anchor_verse_ids": ["Isa.37.36", "Isa.37.37", "2Kgs.19.35"],
        "mkm_paths": [
            {
                "path_id": "path_divine_deliverance_without_sword",
                "source_artifact": "canonical_parallel_isaiah_kings",
                "steps": ["Isa.37.36", "2Kgs.19.35"],
                "note_ko": "정경·외부 역사(산헤립 기록) Tier A. MKM 그래프 edge GAP.",
            },
            {
                "path_id": "path_hezekiah_plague_metaphor_stub",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_1544_hezekiah_plague_angel.json",
                "steps": ["2Kgs.19.35", "Isa.37.36"],
                "note_ko": "천사·역병 은유 stub — 본문 앵커는 정경.",
            },
        ],
    },
    {
        "chapter_id": "ch08",
        "title_ko": "은혜 뒤의 치명적인 교만: 히스기야 보물창고와 바벨론 포로",
        "video_claim_ko": "이사야 39장; 바벨론 사신·보물 노출·포로 예언",
        "mkm_evidence_tier": "A",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.39.1", "Isa.39.6", "Isa.39.7", "2Kgs.20.12", "2Kgs.20.17"],
        "mkm_paths": [
            {
                "path_id": "path_pride_after_grace",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_gold_q04_judgment_covenant_remnant_v1_latest.json",
                "steps": ["judgment_warning", "covenant_remnant", "Isa.39.x"],
                "note_ko": "심판 후 언약 잔류·회개 레인(q04) — 40장 위로로 이어지는 서사 준비.",
            },
            {
                "path_id": "path_judgment_to_comfort_pivot",
                "source_artifact": "docs/final/fixtures/logos_gold_query_eval_v1.json",
                "steps": ["q03:judgment_and_restoration", "Isa.40.1"],
                "note_ko": "39장 어둠 직후 40장 위로 — gold q03 패턴.",
            },
        ],
    },
    {
        "chapter_id": "ch09",
        "title_ko": "위로하라, 내 백성을 위로하라: 39장 심판 뒤 아버지의 가슴",
        "video_claim_ko": "이사야 40:1-2 대전환; 위로 이중 반복",
        "mkm_evidence_tier": "A",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.40.1", "Isa.40.2"],
        "mkm_paths": [
            {
                "path_id": "path_comfort_isaiah_proclaim",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_gold_q08_suffering_comfort_pattern_v1_latest.json",
                "steps": ["concept:suffering_comfort", "lemma:nacham", "Isa.40.1"],
                "note_ko": "MKM gold q08/q32 핵심 앵커 — 영상 40장 전환과 1:1.",
            },
            {
                "path_id": "path_judgment_covenant_chain",
                "source_artifact": "docs/final/fixtures/logos_gold_query_eval_v1.json",
                "steps": ["q03", "Hos.11.8", "Isa.40.1"],
                "note_ko": "심판·회복 동시 엮임 레인.",
            },
        ],
    },
    {
        "chapter_id": "ch10",
        "title_ko": "광야에서 외치는 자의 소리: 독수리 새 힘",
        "video_claim_ko": "40:3 길 예비; 40:31 독수리 날개; 목자 비유",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.40.3", "Isa.40.11", "Isa.40.31", "Matt.3.3", "Luke.3.4"],
        "mkm_paths": [
            {
                "path_id": "path_wilderness_voice_nt_fulfillment",
                "source_artifact": "canonical_nt_citation",
                "steps": ["Isa.40.3", "Matt.3.3", "Luke.3.4"],
                "note_ko": "신약이 이사야 인용 명시 Tier A.",
            },
            {
                "path_id": "path_wait_on_lord_strength",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_43_isaiah_servant.json",
                "steps": ["Isa.40.31", "Isa.53.5"],
                "note_ko": "40:31은 다수 theme echo; 고난·위로 축 연결.",
            },
        ],
    },
    {
        "chapter_id": "ch11",
        "title_ko": "[이사야 53장] 700년 뒤의 골고다: 고난의 종",
        "video_claim_ko": "52:13-53:12 고난받는 종; 멸시·고난·침묵",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.52.13", "Isa.53.3", "Isa.53.5", "Isa.53.7", "Isa.53.9"],
        "mkm_paths": [
            {
                "path_id": "path_isa_53_suffering_bridge",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_themed_isa_53_suffering_v1_latest.json",
                "steps": ["Isa.53.1", "Isa.53.5", "Isa.53.12"],
                "note_ko": "53장 전절 themed bridge — MKM 최밀 매핑.",
            },
            {
                "path_id": "path_servant_songs_metaphor",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_43_isaiah_servant.json",
                "steps": ["Isa.42.1", "Isa.53.5", "1Pet.2.24", "Phil.2.7"],
                "note_ko": "종·대속·kenosis 프레임 [HYPO].",
            },
            {
                "path_id": "path_router_isa_53",
                "source_artifact": "docs/final/artifacts/logos_subgraph_graphrag_router_isa_53_suffering_latest.json",
                "steps": ["query:이사야53고난종", "q13", "q08"],
                "note_ko": "GraphRAG 라우터가 q13 passion + q08 comfort 동시 매칭.",
            },
        ],
    },
    {
        "chapter_id": "ch12",
        "title_ko": "그가 찔림은 우리의 허물 때문이라: 대속의 침묵",
        "video_claim_ko": "53:4-5 대속; 어린양 침묵; 십자가 예언",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.53.4", "Isa.53.5", "Isa.53.7", "Acts.8.32"],
        "mkm_paths": [
            {
                "path_id": "path_substitution_frame",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_43_isaiah_servant.json",
                "steps": ["Isa.53.5", "1Pet.2.24", "Job.9.33"],
                "note_ko": "대속·중보 gap 프레임.",
            },
            {
                "path_id": "path_passion_blood_atonement",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_gold_q13_passion_blood_water_symbolism_v1_latest.json",
                "steps": ["Lev.17.11", "John.19.34", "Isa.53.x"],
                "note_ko": "q13 피·속죄 축 — 53장 고난과 수렴.",
            },
        ],
        "overclaim_flags": ["crucifixion_detail_predated_before_rome"],
    },
    {
        "chapter_id": "ch13",
        "title_ko": "에티오피아 내시의 마차: 한 구절이 이방인 인생을 바꾼 역사",
        "video_claim_ko": "행 8:26-39; 이사야 53 읽다가 세례",
        "mkm_evidence_tier": "A",
        "mkm_verdict": "partial",
        "anchor_verse_ids": ["Acts.8.28", "Acts.8.30", "Acts.8.32", "Acts.8.35", "Isa.53.7", "Isa.53.8"],
        "mkm_paths": [
            {
                "path_id": "path_ethiopian_eunuch_canonical",
                "source_artifact": "canonical_acts",
                "steps": ["Acts.8.32", "Isa.53.7", "Acts.8.35"],
                "note_ko": "누가가 53장 인용 명시 Tier A.",
            },
            {
                "path_id": "path_isa_53_distill",
                "source_artifact": "docs/final/artifacts/logos_concept_bridge_themed_isa_53_suffering_v1_latest.json",
                "steps": ["Isa.53.7", "Isa.53.8"],
                "note_ko": "MKM bridge는 본문 앵커만; 행 8 narrative edge GAP.",
            },
        ],
        "gap_notes_ko": "Acts.8 전용 concept bridge 미구현.",
    },
    {
        "chapter_id": "ch14",
        "title_ko": "찢어진 성전 휘장: 임마누엘 약속 완성",
        "video_claim_ko": "임마누엘 성취; 세례 요한; 십자가; 휘장; 부활; 눅 4:61장",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": [
            "Matt.1.23",
            "Matt.3.3",
            "Matt.27.51",
            "Luke.4.18",
            "Luke.4.21",
            "Isa.61.1",
            "Jhn.19.30",
        ],
        "mkm_paths": [
            {
                "path_id": "path_immanuel_to_incarnation",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_179_isaiah_virgin_sign.json",
                "steps": ["Isa.7.14", "Matt.1.23"],
                "note_ko": "임마누엘 → 태생.",
            },
            {
                "path_id": "path_veil_torn",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_05_veil_access.json",
                "steps": ["Exod.26.33", "Matt.27.51", "Heb.10.19", "Rev.21.3"],
                "note_ko": "휘장·ACL 해제 → 공존 종말 echo.",
            },
            {
                "path_id": "path_luke_4_isaiah_61",
                "source_artifact": "docs/final/fixtures/logos_gold_query_eval_v1.json",
                "steps": ["Isa.61.1", "Luke.4.18", "Luke.4.21"],
                "note_ko": "gold q08 prefix Isa.61 — 회당 낭독 성취.",
            },
            {
                "path_id": "path_passion_week",
                "source_artifact": "docs/final/artifacts/logos_cross_ref_sample_shard_v1_latest.json",
                "steps": ["synoptic_passion_edges", "John.19.34"],
                "note_ko": "Passion cross-ref 샤드(~142 edges) 보조; TSK 전량 아님.",
            },
        ],
    },
    {
        "chapter_id": "ch15",
        "title_ko": "[새 하늘과 새 땅] 완벽한 회복: 요한계시록과 겹침",
        "video_claim_ko": "65:17 새 하늘·새 땅; 66장; 계 21장 평행",
        "mkm_evidence_tier": "B",
        "mkm_verdict": "pass",
        "anchor_verse_ids": ["Isa.65.17", "Isa.66.22", "Rev.21.1", "Rev.21.2", "Rev.21.4"],
        "mkm_paths": [
            {
                "path_id": "path_new_jerusalem_greenfield",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_20_new_jerusalem.json",
                "steps": ["Isa.65.17", "Rev.21.2", "Rev.21.4", "Heb.12.22"],
                "note_ko": "영상 결말 겹침 주장 — MKM theme_20과 직접 일치.",
            },
            {
                "path_id": "path_veil_to_colocation",
                "source_artifact": "docs/research/logos_metaphor_db_v1/theme_05_veil_access.json",
                "steps": ["Matt.27.51", "Rev.21.3"],
                "note_ko": "경계 제거 → 함께 거하심.",
            },
        ],
    },
    {
        "chapter_id": "ch16",
        "title_ko": "결론: 역사 결말을 알고 걷는 자",
        "video_claim_ko": "이사야로 성경 지도; 드라마 진행 중; 새 하늘·새 땅 미완",
        "mkm_evidence_tier": "C",
        "mkm_verdict": "partial",
        "anchor_verse_ids": ["Isa.1.1", "Isa.40.1", "Isa.53.5", "Isa.65.17", "Rev.21.4"],
        "mkm_paths": [
            {
                "path_id": "path_studio_reading_spine",
                "source_artifact": "synthetic_spine",
                "steps": ["Isa.6.8", "Isa.40.1", "Isa.53.5", "Isa.65.17", "Rev.21.2"],
                "note_ko": "Logos 스튜디오 권장 독해 spine — 영상 결론의 ‘지도’를 경로로 대체.",
            },
            {
                "path_id": "path_eschatology_non_gating",
                "source_artifact": "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
                "steps": ["Logos:[NON_GATING]", "Tier_D_prediction_null"],
                "note_ko": "종말 소망 서사는 연구·묵상; 예측·실행 게이트 아님.",
            },
        ],
        "overclaim_flags": ["isaiah_single_key_unlocks_whole_bible"],
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_corpus_verse_ids() -> set[str]:
    ids: set[str] = set()
    if not CORPUS.is_file():
        return ids
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        vid = row.get("verse_id")
        if isinstance(vid, str) and vid.strip():
            ids.add(vid.strip())
    return ids


def _corpus_verse_id(ref: str) -> str | None:
    m = re.match(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$", ref.strip())
    if not m:
        return None
    book, ch, vs = m.group(1), m.group(2), m.group(3)
    if book in CORPUS_ABSENT_BOOKS:
        return None
    book = CORPUS_BOOK_ALIASES.get(book, book)
    return f"{book}.{ch}.{vs}"


def validate_chapters(corpus_ids: set[str]) -> dict[str, Any]:
    missing: list[dict[str, str]] = []
    corpus_absent: list[dict[str, str]] = []
    hits = 0
    total = 0
    for ch in CHAPTERS:
        for vid in ch.get("anchor_verse_ids", []):
            total += 1
            raw = vid.strip()
            book = raw.split(".")[0] if "." in raw else ""
            if book in CORPUS_ABSENT_BOOKS:
                corpus_absent.append({"chapter_id": ch["chapter_id"], "verse_id": raw, "reason": "book_not_in_corpus_slice"})
                continue
            mapped = _corpus_verse_id(raw)
            if mapped and mapped in corpus_ids:
                hits += 1
            elif mapped:
                missing.append({"chapter_id": ch["chapter_id"], "verse_id": raw, "corpus_id": mapped})
    return {
        "corpus_verse_count": len(corpus_ids),
        "corpus_book_count": len({v.split(".")[0] for v in corpus_ids}),
        "corpus_absent_books_note": list(CORPUS_ABSENT_BOOKS),
        "anchor_refs_checked": total,
        "anchor_refs_in_corpus": hits,
        "anchor_refs_missing": missing,
        "anchor_refs_corpus_absent_book": corpus_absent,
        "isaiah_chapter_count": len({v.split(".")[1] for v in corpus_ids if v.startswith("Isa.")}),
    }


def build_doc(corpus_ids: set[str]) -> dict[str, Any]:
    validation = validate_chapters(corpus_ids)
    verdict_counts = Counter = __import__("collections").Counter
    vc = verdict_counts(ch["mkm_verdict"] for ch in CHAPTERS)
    return {
        "schema": "isaiah_youtube_16chapter_mkm_bridge_map_v1",
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "source": {
            "video": "youtube_isaiah_66_books_compression_sermon_ko",
            "transcript_chapters": 16,
            "mkm_lane": "logos_lens",
        },
        "policy": {
            "charter": "docs/final/LENS_UTILIZATION_CHARTER_V1.md",
            "note_ko": "전 장 [HYPO]·[NON_GATING]. Tier A=정경·코퍼스 사실; B=전형·bridge; C=서사 은유; D=예측(미사용).",
        },
        "summary": {
            "chapters": len(CHAPTERS),
            "verdict_pass": vc.get("pass", 0),
            "verdict_partial": vc.get("partial", 0),
            "verdict_gap": vc.get("gap", 0),
            "recommended_studio_spine": [
                "Isa.6.8",
                "Isa.40.1",
                "Isa.53.5",
                "Isa.65.17",
                "Rev.21.2",
            ],
        },
        "corpus_validation": validation,
        "chapters": CHAPTERS,
        "reproduce": "py scripts/build_isaiah_youtube_16chapter_mkm_bridge_map_v1.py",
    }


def main() -> int:
    corpus_ids = _load_corpus_verse_ids()
    doc = build_doc(corpus_ids)
    DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    v = doc["corpus_validation"]
    print(f"wrote {DEFAULT_OUT}")
    print(
        f"isaiah_chapters={v['isaiah_chapter_count']} "
        f"anchors_in_corpus={v['anchor_refs_in_corpus']}/{v['anchor_refs_checked']} "
        f"missing={len(v['anchor_refs_missing'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
