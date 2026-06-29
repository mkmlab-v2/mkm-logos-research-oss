#!/usr/bin/env python3
"""UI depth boundary SSOT — oracle-sphere (D안 shallow) vs ask-one (deep paid)."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/mkm_ask_one_ui_depth_boundary_v1_latest.json"
PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/mkm_ask_one_ui_depth_boundary_v1.json"


def build() -> dict:
    return {
        "schema": "mkm_ask_one_ui_depth_boundary_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "charter_ref": "docs/final/MKM_DESIGN_PHILOSOPHY_CONSTITUTION_V1.md",
        "design_manifesto_ref": "docs/final/MKM_DESIGN_MANIFESTO_V1.md",
        "product_boundary_ref": "docs/final/artifacts/magic_orb_four_slot_product_boundary_v1_latest.json",
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "track_a_blocked": True,
        "send_gate_default": "HOLD",
        "depth_policy_ko": (
            "헌법 3조 D안 — oracle-sphere는 ritual·맥락망 쇼룸 깊이, "
            "ask-one은 유료 심화 리포트·확장 컨텍스트 깊이. 합성·Track A 승격 없음."
        ),
        "surfaces": {
            "oracle_sphere_public_demo": {
                "surface_id": "oracle_sphere_public_demo",
                "label_ko": "관측 구 · 공개 데모",
                "label_en": "Oracle Sphere · public demo",
                "href": "/oracle-sphere",
                "price_ko": "무료",
                "depth_tier": "ritual_showroom",
                "design_kernel_depth": [
                    "pathology",
                    "survival",
                    "harmony",
                    "valence",
                    "myeongni_accent_only",
                ],
            },
            "ask_one_premium_report": {
                "surface_id": "ask_one_premium_report",
                "label_ko": "원퀘스천 · 심화 리포트",
                "label_en": "Ask One · deep report",
                "href": "/ask-one",
                "price_ko": "유료 (Entry/Standard/Premium)",
                "depth_tier": "paid_l2_report",
                "design_kernel_depth": [
                    "pathology",
                    "survival",
                    "harmony",
                    "valence",
                    "myeongni_accent_only",
                    "client_context_l0_l2",
                ],
            },
        },
        "feature_rows": [
            {
                "id": "lattice_ritual",
                "label_ko": "질문 흡수 · 맥락망 ritual",
                "label_en": "Question lattice ritual",
                "oracle_sphere": "included",
                "ask_one": "link",
                "note_ko": "ask-one 완료 후 oracle 링크",
            },
            {
                "id": "four_slot_assembler",
                "label_ko": "탐구 파노라마 4슬롯 (assembler)",
                "label_en": "Four-slot panorama (assembler)",
                "oracle_sphere": "included",
                "ask_one": "included",
                "note_ko": "공개면 슬롯당 노출 cap",
            },
            {
                "id": "post_llm_fill",
                "label_ko": "Post-LLM slot fill (tier_15)",
                "label_en": "Post-LLM slot fill",
                "oracle_sphere": "off",
                "ask_one": "premium_candidate",
                "note_ko": "human gate · SEND HOLD",
            },
            {
                "id": "l2_structured_report",
                "label_ko": "L2 구조화 심화 리포트",
                "label_en": "L2 structured report",
                "oracle_sphere": "off",
                "ask_one": "included",
            },
            {
                "id": "multilens_full",
                "label_ko": "다중 렌즈 전체 envelope",
                "label_en": "Full multi-lens envelope",
                "oracle_sphere": "logos_only",
                "ask_one": "standard_plus",
            },
            {
                "id": "client_context",
                "label_ko": "건강·맥락 입력 (L0/L2)",
                "label_en": "Health & context intake",
                "oracle_sphere": "off",
                "ask_one": "included",
            },
            {
                "id": "fact_locked_slot",
                "label_ko": "Fact-Locked 슬롯",
                "label_en": "Fact-Locked slot",
                "oracle_sphere": "empty_honest",
                "ask_one": "empty_honest",
                "note_ko": "verified_anchor 없으면 비움",
            },
        ],
        "walls": {
            "no_track_a_auto_merge": True,
            "no_send_gate_open_without_human": True,
            "no_why_causality_auto_assembly": True,
            "no_oracle_depth_parity_claim": True,
        },
        "visual_contract": {
            "oracle_cta_href": "/ask-one",
            "oracle_compare_back_href": "/oracle-sphere",
            "highlight_delta_ids": ["post_llm_fill", "l2_structured_report", "client_context"],
        },
        "reproduce": "py scripts/build_mkm_ask_one_ui_depth_boundary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--skip-public-sync", action="store_true")
    args = ap.parse_args()
    doc = build()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    out.write_text(text, encoding="utf-8")
    if not args.skip_public_sync:
        PUBLIC.parent.mkdir(parents=True, exist_ok=True)
        PUBLIC.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out), "public": str(PUBLIC)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
