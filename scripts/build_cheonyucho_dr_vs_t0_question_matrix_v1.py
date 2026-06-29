#!/usr/bin/env python3
"""Build DR-closable vs T0-blocked question matrix from claim7 SSOT."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_dr_vs_t0_question_matrix_v1_latest.json"

SOURCES = {
    "claim7": ROOT / "docs/research/raw/IJEOMA_CLAIM7_FINAL_VERDICT_v1.json",
    "substitute_tier": ROOT / "docs/research/raw/IJEOMA_SECONDARY_SUBSTITUTE_TIER_v1.json",
    "appendix_sweep": ROOT / "docs/research/raw/CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json",
    "secondary_corpus": ROOT / "docs/research/raw/CHEONYUCHO_SECONDARY_CORPUS_v1.json",
    "fragment_ledger": ROOT / "docs/research/raw/CHEONYUCHO_FRAGMENT_LEDGER_v1.json",
    "proxy_index": ROOT / "reports/constitution/btrack_pilot/cheonyucho_physical_proxy_index_v1_latest.json",
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_matrix() -> dict[str, Any]:
    claim7 = _load(SOURCES["claim7"])
    tier = _load(SOURCES["substitute_tier"])
    appendix = _load(SOURCES["appendix_sweep"])
    corpus = _load(SOURCES["secondary_corpus"])
    ledger = _load(SOURCES["fragment_ledger"])
    proxy_index = _load(SOURCES["proxy_index"]) if SOURCES["proxy_index"].is_file() else {}

    primary_n = int((ledger.get("summary") or {}).get("primary_hanja_chunk_count") or 0)
    layers = claim7.get("four_layer_final") or {}

    closable_dr: list[dict[str, Any]] = [
        {
            "id": "Q-L4-existence",
            "question_ko": "천유초(闡幽抄)는 허구·유령 도서인가?",
            "claim_layer": "L4",
            "tier": "T2_list_mention",
            "status": "closed_at_T1_T2",
            "verdict": layers.get("L4_total_nonexistence_denial", {}).get("verdict"),
            "dr_sufficient": True,
            "evidence": [
                "encykorea E0045869",
                "DR-01 Lee 2005",
                "DR-02 Kim 2006",
            ],
        },
        {
            "id": "Q-L2-catalog-merge",
            "question_ko": "제중신편·유고초 키가 전산·2차 서지에서 격치고/천유초와 병합·오분류될 수 있는가?",
            "claim_layer": "L2",
            "tier": "T1_secondary",
            "status": "closed_at_T1",
            "verdict": layers.get("L2_catalog_merge_heojun_hwangdoyeon", {}).get("verdict"),
            "dr_sufficient": True,
            "evidence": [
                "cheonyucho_catalog_merge_probe_v1.json",
                "L2_CATALOG_MERGE_heojun_hwangdoyeon_nl_proxy.md",
            ],
        },
        {
            "id": "Q-L1-overclaim",
            "question_ko": "민간 단행본이 천유초를 '완벽 복원'했는가?",
            "claim_layer": "L1",
            "tier": "T1_secondary",
            "status": "closed_FALSE_overclaim",
            "verdict": layers.get("L1_standalone_complete_restoration", {}).get("verdict"),
            "dr_sufficient": True,
            "evidence": ["IJEOMA_SECONDARY_SUBSTITUTE_TIER_v1 overclaim_firewall"],
        },
        {
            "id": "Q-L3-dongmu-011",
            "question_ko": "이창일 1999 동무유고 역주본 목차에 011.천유초 편이 있는가?",
            "claim_layer": "L3",
            "tier": "T1_secondary",
            "status": "closed_TOC_verified_manual",
            "verdict": layers.get("L3_dongmu_yugo_1999_toc_011", {}).get("verdict"),
            "dr_sufficient": True,
            "note": "교보목차 수동 crossval — primary 한자 전문 아님",
            "evidence": ["T1-LEE-DONGMUYUGO-1999_kyobo_toc_manual_nl_proxy.md"],
        },
        {
            "id": "Q-S2-yakseongga",
            "question_ko": "동무유고 약성가·지풍兆·懋務 등 처방·문헌 교차 주장은?",
            "claim_layer": "S2-S4",
            "tier": "T1_secondary",
            "status": "closed_supported",
            "dr_sufficient": True,
            "evidence": ["FM-09", "FM-13", "FM-14", "FM-16", "DR-04 박성식 2001"],
        },
        {
            "id": "Q-park1985-biblio",
            "question_ko": "NLK 199.1-이617ㄱ 박석언 1985 격치고 서지·RDF·NLK 회신 요지는?",
            "claim_layer": "P1-meta",
            "tier": "T1_secondary",
            "status": "closed_nlk_briefing",
            "dr_sufficient": True,
            "evidence": [
                f"proxy_count={proxy_index.get('proxy_count', 0)}",
                "rear_index absent",
                "원문DB fulltext NOT_SUPPORTED",
            ],
        },
        {
            "id": "Q-p344-glyph",
            "question_ko": "사상임상편람2 p.344 타이틀 闡幽抄(抄) vs 草 오기 가능성?",
            "claim_layer": "P1-06",
            "tier": "T1_partial_paste",
            "status": "partial_excerpt_only",
            "dr_sufficient": True,
            "note": "user paste bound — scan hash 없음 · Park 1985 대체 아님",
            "evidence": ["CHEONYUCHO_PHYSICAL_SASANG_CLINICAL_P344_2026_nl_proxy.md"],
        },
    ]

    dr_partial: list[dict[str, Any]] = [
        {
            "id": "Q-L3-chobon-012",
            "question_ko": "사상초본권 내부 012편 = 闡幽抄인가? (동무 011과 별 트랙)",
            "claim_layer": "L3",
            "tier": "T1_secondary",
            "status": "open_optional",
            "verdict": layers.get("L3_chobon_internal_pian_012_cheonyucho", {}).get("verdict"),
            "dr_may_help": True,
            "dr_alone_closes": False,
            "next_dr_fetch": tier.get("recommended_secondary_fetch_p1", [])[:2],
            "evidence": ["ijeoma_t1_toc_fetch_v1.json toc_not_verified for chobon 012"],
        },
        {
            "id": "Q-thesis-appendix",
            "question_ko": "학위논문 부록에 천유초 한자 전문이 수록돼 있는가?",
            "claim_layer": "DR-sweep",
            "tier": "T1_secondary",
            "status": "negative_sweep",
            "dr_may_help": True,
            "dr_alone_closes": False,
            "verdict": appendix.get("verdict", {}).get("thesis_fulltext_appendix_found"),
            "evidence": ["CHEONYUCHO_APPENDIX_BIBLIO_SWEEP_v1.json"],
        },
        {
            "id": "Q-kci-pdf-grep",
            "question_ko": "기존 KCI/medhist PDF에 천유초 본문 인용(非서지)이 있는가?",
            "claim_layer": "DR-corpus",
            "tier": "T1_secondary",
            "status": "list_mention_only",
            "dr_may_help": True,
            "dr_alone_closes": False,
            "verdict": corpus.get("primary_fulltext_substitute"),
            "evidence": [
                "LEE 2005 mentions_cheonyucho_list_only",
                "Kim 2006 mentions_cheonyucho_list_only",
                "cheonyucho_fulltext_from_papers: false",
            ],
        },
    ]

    t0_blocked: list[dict[str, Any]] = [
        {
            "id": "Q-T0-primary-hanja",
            "question_ko": "闡幽抄 한자 원전 전문(primary_hanja) SSOT 확보",
            "claim_layer": "L0",
            "tier": "T0_physical_anchor",
            "status": "blocked",
            "dr_sufficient": False,
            "physical_required": True,
            "verdict": layers.get("L0_primary_hanja_canon", {}).get("verdict"),
            "evidence": [f"primary_hanja_chunk_count={primary_n}"],
        },
        {
            "id": "Q-P1-01-park1985-body",
            "question_ko": "박석언 1985 격치고 본문·역주·각주에 闡幽/遺稿/濟衆이 어떻게 실리는가?",
            "claim_layer": "P1-01",
            "tier": "T0_physical_anchor",
            "status": "blocked_human_library",
            "dr_sufficient": False,
            "physical_required": True,
            "next_human_action": (proxy_index.get("p1_01_verdict") or {}).get("next_human_action"),
            "evidence": ["NLK rear_index absent", "원문DB keyword search NOT_SUPPORTED"],
        },
        {
            "id": "Q-CANON-acquired",
            "question_ko": "hanja_canon_status → acquired / [CANON] 승격",
            "claim_layer": "gate",
            "tier": "T0_human_gate",
            "status": "blocked",
            "dr_sufficient": False,
            "physical_required": True,
            "verdict": claim7.get("canon_status"),
            "evidence": [
                "check_cheonyucho_acquisition_gate_v1.py",
                "bind --set-physical-verified human only",
            ],
        },
        {
            "id": "Q-scan-anchor",
            "question_ko": "scan_sha256 또는 협약 원문 flip 결과로 physical_verified=true",
            "claim_layer": "bind",
            "tier": "T0_physical_anchor",
            "status": "blocked",
            "dr_sufficient": False,
            "physical_required": True,
            "evidence": ["physical_verified: false", "scan_sha256: null"],
        },
    ]

    return {
        "schema": "cheonyucho_dr_vs_t0_question_matrix_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "canon_status": claim7.get("canon_status"),
        "primary_hanja_chunk_count": primary_n,
        "summary_ko": (
            "논문·Sci DR만으로 닫힌 질문 = L1/L2/L4·동무011 목차·NLK 서지·2차 처방 crossval. "
            "실물 없이 영구 개방 = L0 primary hanja·Park1985 본문각주·[CANON]·physical_verified."
        ),
        "closable_by_paper_dr_only": closable_dr,
        "dr_partial_may_help_not_close": dr_partial,
        "requires_t0_or_human_paste": t0_blocked,
        "counts": {
            "closable_dr": len(closable_dr),
            "dr_partial": len(dr_partial),
            "t0_blocked": len(t0_blocked),
        },
        "sources": {k: _rel(v) for k, v in SOURCES.items() if v.is_file()},
        "reproduce": "py scripts/build_cheonyucho_dr_vs_t0_question_matrix_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    missing = [k for k, p in SOURCES.items() if k != "proxy_index" and not p.is_file()]
    if missing:
        print(json.dumps({"ok": False, "missing_sources": missing}))
        return 1

    doc = build_matrix()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": _rel(args.out),
                "closable_dr": doc["counts"]["closable_dr"],
                "t0_blocked": doc["counts"]["t0_blocked"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
