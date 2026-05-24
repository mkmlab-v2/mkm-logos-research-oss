#!/usr/bin/env python3
"""AI-synthesized Logos chronology v2 (11 macro biblical eras + modern observational bridge).

Commander GO 2026-05-20: B-track [HYPO] only; NON_GATING; no MS/Track A merge.
Output: docs/final/artifacts/logos_chronology_v2_ai_synthesis_v1.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs/final/schemas/logos_chronology_v1.schema.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_chronology_v2_ai_synthesis_v1.json"
SSOT_OUT = ROOT / "docs/final/artifacts/logos_chronology_v1_latest.json"

POLICY = {
    "research_only": True,
    "non_gating": True,
    "no_trading_signal": True,
    "no_prophecy_certainty": True,
}

MERGE_TARGETS = {
    "logos_symbolic_event_map_v1": "docs/final/artifacts/logos_symbolic_event_map_v1.json",
    "bible_meaning_graph_nodes_jsonl": "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl",
    "bible_meaning_graph_edges_jsonl": "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl",
}


def _era(
    era_id: str,
    label_ko: str,
    label_en: str,
    notes_ko: str,
    *,
    theme_tags: list[str] | None = None,
    verse_refs: list[str] | None = None,
    regime_tags: list[str] | None = None,
    relative_phase: str | None = None,
    bce_start: int | None = None,
    bce_end: int | None = None,
    ce_start: int | None = None,
    ce_end: int | None = None,
) -> dict[str, Any]:
    time: dict[str, Any] = {}
    if relative_phase:
        time["relative_phase"] = relative_phase
    if bce_start is not None:
        time["bce_start"] = bce_start
    if bce_end is not None:
        time["bce_end"] = bce_end
    if ce_start is not None:
        time["ce_start"] = ce_start
    if ce_end is not None:
        time["ce_end"] = ce_end
    row: dict[str, Any] = {
        "era_id": era_id,
        "label_ko": label_ko,
        "label_en": label_en,
        "interpretation_class": "[HYPO]",
        "notes_ko": notes_ko,
    }
    if time:
        row["time"] = time
    if theme_tags:
        row["theme_tags"] = theme_tags
    if verse_refs:
        row["verse_refs"] = verse_refs
    if regime_tags:
        row["regime_tags_observational"] = regime_tags
    return row


def _bridge(
    era_id: str,
    kind: str,
    rationale_ko: str,
    *,
    window_id: str | None = None,
    regime_id: str | None = None,
    weight: float = 1.0,
) -> dict[str, Any]:
    b: dict[str, Any] = {
        "era_id": era_id,
        "bridge_kind": kind,
        "interpretation_class": "[HYPO]",
        "resonance_weight": weight,
        "rationale_ko": rationale_ko,
    }
    if window_id:
        b["window_id"] = window_id
    if regime_id:
        b["regime_id"] = regime_id
    return b


def build_document() -> dict[str, Any]:
    hypo = (
        "[HYPO] AI 합성 v2(지휘관 GO 2026-05-20). 성경 거시 서사의 **구조적 관측 은유**이며 "
        "신학적 확정·예언 적중·실매매 신호가 아닙니다. 1차 Field는 regime_map 실물 레짐, "
        "본 연대기는 Logos Observatory 부록(NON_GATING) 전용입니다."
    )
    eras = [
        _era(
            "genesis_order_and_fall",
            "창조와 타락 (Genesis)",
            "Creation, order, and fall",
            hypo + " 근원 질서·혼돈·경계 상실의 서사 프레임. 시장 인과 단정 없음.",
            theme_tags=["creation", "order", "fall", "boundary_loss"],
            verse_refs=["aramaic::Gen.1.1", "aramaic::Gen.3.6"],
            relative_phase="genesis_primeval",
            bce_start=4000,
            bce_end=2000,
        ),
        _era(
            "patriarch_covenant_arc",
            "족장 시대 · 언약 (Patriarchs)",
            "Patriarchal covenant arc",
            hypo + " 언약·가족·약속 네트워크 은유. 거버넌스 계약의 상징층.",
            theme_tags=["covenant", "promise", "lineage"],
            verse_refs=["aramaic::Gen.12.1", "aramaic::Gen.15.6", "aramaic::Gen.22.8"],
            relative_phase="patriarchs",
            bce_start=2000,
            bce_end=1500,
        ),
        _era(
            "exodus_wilderness_law",
            "출애굽·광야 · 율법 (Exodus/Wilderness)",
            "Exodus, wilderness, and law",
            hypo + " 해방·규칙(Rule)·훈련 루프. 구조적 돌파·제도화 은유만.",
            theme_tags=["liberation", "passover", "law", "training"],
            verse_refs=["aramaic::Exod.12.13", "aramaic::Exod.14.21", "aramaic::Exod.20.1"],
            regime_tags=["empire_transition"],
            relative_phase="exodus_wilderness",
            bce_start=1500,
            bce_end=1200,
        ),
        _era(
            "judges_risk_cycle",
            "사사 시대 · 순환 리스크 (Judges)",
            "Judges — cyclical risk and rescue",
            hypo + " 질서 붕괴·구원 반복. 변동성·조율 실패 키워드의 상징층.",
            theme_tags=["cyclical_chaos", "rescue", "volatility"],
            verse_refs=["aramaic::Judg.2.16", "aramaic::Judg.21.25"],
            regime_tags=["risk", "caution"],
            relative_phase="judges",
            bce_start=1200,
            bce_end=1000,
        ),
        _era(
            "united_divided_kingdom",
            "통일·분열 왕국 (Kingdoms)",
            "United and divided monarchy",
            hypo + " 거버넌스 수립·내부 분열·왕권 붕괴. 제도 신뢰 사이클 은유.",
            theme_tags=["governance", "succession", "civil_split"],
            verse_refs=["aramaic::1Sam.8.7", "aramaic::1Kgs.12.16"],
            regime_tags=["empire_transition", "it_bubble"],
            relative_phase="monarchy",
            bce_start=1000,
            bce_end=586,
        ),
        _era(
            "exile_and_return",
            "포로기·귀환 (Exile/Return)",
            "Exile and return",
            hypo + " 심판·고립·회복 사이클. 유동성·긴축 키워드와 **관측 유사**만.",
            theme_tags=["exile", "judgment", "return", "restoration"],
            verse_refs=["aramaic::Jer.29.10", "aramaic::Ezra.1.1"],
            regime_tags=["imf", "caution"],
            relative_phase="exile_return",
            bce_start=586,
            bce_end=400,
        ),
        _era(
            "intertestamental_empire_handoff",
            "침묵기·제국 교체 (Intertestamental)",
            "Intertestamental empire handoff",
            hypo + " 바벨론→페르시아→헬라→로마 교체와 다니엘 2 금속상 **구조 은유**.",
            theme_tags=["imperial_transition", "empire_transition", "succession", "silence"],
            verse_refs=[
                "aramaic::Dan.2.31",
                "aramaic::Dan.2.35",
                "aramaic::Dan.2.10",
                "aramaic::Gen.11.7",
            ],
            regime_tags=["empire_transition", "it_bubble"],
            relative_phase="intertestamental",
            bce_start=400,
            bce_end=4,
        ),
        _era(
            "gospel_logos_incarnate",
            "복음서 · Logos 현현 (Gospels)",
            "Incarnation of Logos",
            hypo + " 완전한 Logos 현현 **해설 프레임**; 치유·투자 확정 아님.",
            theme_tags=["incarnation", "logos", "revelation"],
            verse_refs=["aramaic::John.1.1", "aramaic::John.1.14"],
            regime_tags=["stability"],
            relative_phase="gospels",
            ce_start=4,
            ce_end=33,
        ),
        _era(
            "early_church_network",
            "초대교회·확장 (Acts)",
            "Early church network expansion",
            hypo + " 네트워크 확장·핍박·분산 조율. 협업·커뮤니케이션 은유.",
            theme_tags=["network", "persecution", "expansion"],
            verse_refs=["aramaic::Acts.2.42", "aramaic::Acts.8.1"],
            relative_phase="early_church",
            ce_start=33,
            ce_end=100,
        ),
        _era(
            "modern_observational_field",
            "현대 관측 필드 (Modern bridges)",
            "Modern observational field layer",
            hypo + " regime_map·chronology_windows와의 **2차 관측 정렬**만. Track A·MS Wire 무관.",
            theme_tags=["macro_observation", "regime_fingerprint", "non_gating"],
            regime_tags=["imf", "lehman", "covid", "it_bubble", "risk"],
            relative_phase="modern_observational",
            ce_start=1997,
            ce_end=2026,
        ),
        _era(
            "eschaton_restoration_hypo",
            "종말적 완성 (Eschaton · hypo)",
            "Eschatological restoration (hypo frame)",
            hypo + " 최종 질서 회복 **가설 프레임**; 날짜·시장 방향 예측 아님.",
            theme_tags=["eschaton", "restoration", "final_order"],
            verse_refs=["aramaic::Rev.21.1", "aramaic::Rev.22.13"],
            relative_phase="eschaton_hypo",
        ),
    ]

    bridges = [
        _bridge(
            "genesis_order_and_fall",
            "theme_only",
            "창조·질서 vs 타락·혼돈 — meaning topology **theme** 관측만.",
            weight=0.6,
        ),
        _bridge(
            "patriarch_covenant_arc",
            "theme_only",
            "언약 네트워크 — 계약·신뢰 메타포; 가격 게이트 무관.",
            weight=0.65,
        ),
        _bridge(
            "exodus_wilderness_law",
            "chronology_window",
            "해방·회복 키워드 vs post_gfc_repair 윈도우 구조 유사 [HYPO].",
            window_id="post_gfc_repair",
            weight=1.0,
        ),
        _bridge(
            "judges_risk_cycle",
            "regime_fingerprint",
            "순환 혼돈 vs lehman 레짐 지문 shadow (regime_map.lehman).",
            regime_id="lehman",
            weight=0.9,
        ),
        _bridge(
            "judges_risk_cycle",
            "chronology_window",
            "급격 shock vs pandemic_shock 윈도우 관측 정렬 [HYPO].",
            window_id="pandemic_shock",
            weight=0.72,
        ),
        _bridge(
            "united_divided_kingdom",
            "regime_fingerprint",
            "거버넌스·버블 상승 vs it_bubble 레짐 지문.",
            regime_id="it_bubble",
            weight=0.88,
        ),
        _bridge(
            "exile_and_return",
            "regime_fingerprint",
            "심판·유동성 압박 vs imf 레짐 관측 태그.",
            regime_id="imf",
            weight=0.85,
        ),
        _bridge(
            "exile_and_return",
            "chronology_window",
            "긴축·완화 사이클 vs rate_hike_cycle 구조 비교 [HYPO].",
            window_id="rate_hike_cycle",
            weight=0.78,
        ),
        _bridge(
            "intertestamental_empire_handoff",
            "regime_fingerprint",
            "제국·금속상 전환 vs it_bubble + covid shadow (다니엘 클러스터).",
            regime_id="covid",
            weight=0.7,
        ),
        _bridge(
            "intertestamental_empire_handoff",
            "theme_only",
            "theme::imperial_transition 허브 — 주문·레짐 게이트 무관.",
            weight=1.0,
        ),
        _bridge(
            "gospel_logos_incarnate",
            "theme_only",
            "Logos 현현 — 해설·쇼룸 프리셋층; NON_GATING.",
            weight=0.7,
        ),
        _bridge(
            "early_church_network",
            "theme_only",
            "네트워크 확장 — 분산 시스템 은유; 실매매 트리거 아님.",
            weight=0.65,
        ),
        _bridge(
            "modern_observational_field",
            "chronology_window",
            "현대 윈도우 post_gfc_repair — Field 보조.",
            window_id="post_gfc_repair",
            weight=0.95,
        ),
        _bridge(
            "modern_observational_field",
            "chronology_window",
            "pandemic_shock — risk-off·변동성 관측.",
            window_id="pandemic_shock",
            weight=0.9,
        ),
        _bridge(
            "modern_observational_field",
            "chronology_window",
            "rate_hike_cycle — 긴축·완화 구조.",
            window_id="rate_hike_cycle",
            weight=0.85,
        ),
        _bridge(
            "modern_observational_field",
            "regime_fingerprint",
            "lehman — coordination break shadow.",
            regime_id="lehman",
            weight=0.92,
        ),
        _bridge(
            "modern_observational_field",
            "regime_fingerprint",
            "imf — 저장·유동성 압박 shadow.",
            regime_id="imf",
            weight=0.88,
        ),
        _bridge(
            "modern_observational_field",
            "regime_fingerprint",
            "covid — 급격 판 전환 shadow.",
            regime_id="covid",
            weight=0.8,
        ),
        _bridge(
            "modern_observational_field",
            "regime_fingerprint",
            "it_bubble — 제국·버블 상승 shadow.",
            regime_id="it_bubble",
            weight=0.86,
        ),
        _bridge(
            "eschaton_restoration_hypo",
            "theme_only",
            "종말 완성 — **가설 프레임**만; 예언 확정·매매 금지.",
            weight=0.5,
        ),
    ]

    return {
        "schema": "logos_chronology_v1",
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_note": (
            "AI synthesis v2 (commander GO 2026-05-20): 11 macro biblical eras + modern_observational_field. "
            "Builder=build_logos_chronology_v2_ai_synthesis_v1.py. All narrative [HYPO]; supersedes 5-era SSOT stub."
        )[:512],
        "policy": POLICY,
        "hypothesis_tier": "[HYPO]",
        "eras": eras,
        "modern_bridges": bridges,
        "merge_targets": MERGE_TARGETS,
    }


def _validate(doc: dict[str, Any]) -> None:
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft7Validator(schema).validate(doc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--write-ssot", action="store_true", help="Also write logos_chronology_v1_latest.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    doc = build_document()
    _validate(doc)

    if args.dry_run:
        print(
            json.dumps(
                {
                    "eras": len(doc["eras"]),
                    "modern_bridges": len(doc["modern_bridges"]),
                    "would_write": str(args.out),
                },
                ensure_ascii=False,
            )
        )
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out.write_text(text, encoding="utf-8")
    print(f"Wrote {args.out} (eras={len(doc['eras'])}, bridges={len(doc['modern_bridges'])})")

    if args.write_ssot:
        SSOT_OUT.write_text(text, encoding="utf-8")
        print(f"Wrote SSOT {SSOT_OUT}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
