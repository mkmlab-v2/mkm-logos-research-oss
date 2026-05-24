#!/usr/bin/env python3
"""Emit MKM Life Anchor OS kernel + 4 skins SSOT (Fact-Lock pointers only)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_life_anchor_os_kernel_skins_v1_latest.json"
SCHEMA_PATH = ROOT / "docs/final/schemas/mkm_life_anchor_os_kernel_skins_v1.schema.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def build_doc(*, exist_ok: bool) -> dict[str, Any]:
    kernel_modules = [
        {
            "module_id": "profile_anchor",
            "label_ko": "프로필 Anchor (출생·명식·anchor_id)",
            "ssot_refs": [
                _rel(ROOT / "docs/final/artifacts/family_anchor_lived_calibration_our_daughter_v1_latest.json"),
                _rel(ROOT / "data/personadiary/profile_registry_v1.json"),
            ],
            "rag_graph_runtime": False,
        },
        {
            "module_id": "lived_calibration",
            "label_ko": "Lived facts (관찰·fact-check)",
            "ssot_refs": [
                _rel(ROOT / "scripts/apply_family_anchor_lived_fact_check_v1.py"),
                _rel(ROOT / "docs/final/artifacts/family_anchor_fact_check_session_daughter_v1_latest.json"),
            ],
            "rag_graph_runtime": False,
        },
        {
            "module_id": "sequential_layers",
            "label_ko": "순차 4층 (CORE→명리→사상→Logos) + pair contracts",
            "ssot_refs": [
                _rel(ROOT / "docs/final/artifacts/daughter_2026_lens_pair_contracts_v1_latest.json"),
                _rel(ROOT / "scripts/build_daughter_2026_monthly_sequential_v1.py"),
                _rel(ROOT / "docs/final/artifacts/daughter_2026_integrated_guide_v4_minimal_latest.json"),
            ],
            "rag_graph_runtime": False,
        },
        {
            "module_id": "eval_hypothesis_chain",
            "label_ko": "Hypothesis log · evolution · A/S flywheel",
            "ssot_refs": [
                _rel(ROOT / "scripts/Run-CommanderHypothesisEvolution_v1.ps1"),
                _rel(ROOT / "docs/final/artifacts/saving_the_news_flywheel_as_snapshot_v1_latest.json"),
                _rel(ROOT / "scripts/build_saving_the_news_flywheel_as_snapshot_v1.py"),
            ],
            "rag_graph_runtime": False,
        },
        {
            "module_id": "insight_bridge_envelope",
            "label_ko": "Insight bridge · sphere envelope (Layer A SSOT)",
            "ssot_refs": [
                _rel(ROOT / "scripts/build_family_anchor_insight_bridge_v1.py"),
                _rel(ROOT / "docs/final/artifacts/family_lens_fusion_governance_v1_latest.json"),
            ],
            "rag_graph_runtime": False,
        },
    ]

    skins = [
        {
            "skin_id": "mkmlife",
            "domain": "mkmlife.com",
            "label_ko": "MKM Life · 원퀘스천·프로필 허브",
            "role_ko": "프로필 → 원퀘스천 → 월별 순차 4층 · Layer A SSOT · explore=1 선택",
            "cta_ko": "원퀘스천 · 가족 프로필 구슬",
            "cta_href": "https://mkmlife.com/oracle-sphere?profile=family",
            "ssot_refs": [
                _rel(ROOT / "projects/mkm/mkm-life/app/oracle-sphere/page.tsx"),
                _rel(ROOT / "docs/final/artifacts/daughter_2026_monthly_sequential_v1_latest.json"),
            ],
            "upstream_kernel_modules": [
                "profile_anchor",
                "lived_calibration",
                "sequential_layers",
                "insight_bridge_envelope",
            ],
            "forbidden_ko": ["12×3 월별 합선", "GraphRAG 육아 실zeit 융합", "실매매·Track A 자동 합선"],
        },
        {
            "skin_id": "personadiary",
            "domain": "personadiary.com",
            "label_ko": "PersonaDiary · 일일 마음 가이드",
            "role_ko": "오늘의 뉴스×나 [HYPO] 스니펫 · reflect · mkmlife upstream 동기화",
            "cta_ko": "오늘의 마음 가이드",
            "cta_href": "https://personadiary.com/personadiary",
            "ssot_refs": [
                _rel(ROOT / "docs/final/artifacts/PERSONADIARY_DAILY_RESPONSE_PACKAGE_V1_CONTRACT.json"),
                _rel(ROOT / "scripts/assemble_personadiary_daily_response_package_v1.py"),
            ],
            "upstream_kernel_modules": ["profile_anchor", "eval_hypothesis_chain", "sequential_layers"],
            "forbidden_ko": ["mkmlife DB/API 합선 가정", "저장·결제 본선 단정"],
        },
        {
            "skin_id": "jemaai_cloud",
            "domain": "jemaai.cloud",
            "label_ko": "공개 관측 · Saving the News Matrix",
            "role_ko": "뉴스 Matrix · flywheel A/S 투명 표 · cms_publish human gate",
            "cta_ko": "Saving the News Matrix 보기",
            "cta_href": "https://jemaai.cloud/public_showroom_saving_the_news_matrix_v1.html",
            "ssot_refs": [
                _rel(ROOT / "docs/research/saving_the_news_blueprint_v1.md"),
                _rel(ROOT / "docs/final/artifacts/saving_the_news_phase3_poc_status_v1_latest.json"),
            ],
            "upstream_kernel_modules": ["eval_hypothesis_chain"],
            "forbidden_ko": ["84.5% 뉴스 적중 단정", "자동 송출·투자 권유"],
        },
        {
            "skin_id": "jema_ai_b2b",
            "domain": "jema-ai.com",
            "label_ko": "B2B · 매크로 경보·CMS gate",
            "role_ko": "Track C §3.8 거시 리스크 조기 경보 · enterprise / clinician 분기",
            "cta_ko": "B2B 도입 문의",
            "cta_href": "https://jema-ai.com/enterprise",
            "ssot_refs": [
                _rel(ROOT / "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md"),
                _rel(ROOT / "docs/final/P0_COMMERCIALIZATION_TRACKER.md"),
            ],
            "upstream_kernel_modules": ["eval_hypothesis_chain", "insight_bridge_envelope"],
            "forbidden_ko": ["buy/sell", "수익 보장", "할루시네이션 0%"],
        },
    ]

    forbidden_modes = [
        {
            "mode_id": "twelve_month_three_lens_matrix",
            "label_ko": "12×3 렌즈 셀 합선",
            "reason_ko": "월별 3렌즈 parallel merge — family v4·governance에서 금지.",
        },
        {
            "mode_id": "llm_soft_merge",
            "label_ko": "⑥ LLM soft merge",
            "reason_ko": "한 문장 AI 비빔 — Layer A/B 격벽 위반.",
        },
        {
            "mode_id": "family_graphrag_runtime_parenting",
            "label_ko": "가족 GraphRAG 실시간 육아 융합",
            "reason_ko": "Layer B explore만 Logos 쇼룸 링크 — parenting SSOT에 GraphRAG 금지.",
        },
        {
            "mode_id": "cms_auto_publish",
            "label_ko": "뉴스 CMS 자동 송출",
            "reason_ko": "Saving the News phase3 — cms_publish_allowed false, human sign-off 필수.",
        },
    ]

    forbidden_claims = [
        "84.5% 또는 47.5%를 뉴스·양육 Universal Policy 입증으로 서술 금지",
        "반려 AI·할루시네이션 제거·세계 유일 단정 금지",
        "가중치·캘리브레이션 human sign-off 없이 Track A·실매매 자동 승격 금지",
        "미성년 연애·투자·임상·○월 사건 단정 금지",
    ]

    doc: dict[str, Any] = {
        "schema": "mkm_life_anchor_os_kernel_skins_v1",
        "version": "1.0.0",
        "generated_at_utc": _now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": "none",
        "tagline_ko": "맞춘 것은 맞췄다, 틀린 것은 틀렸다 — 축별 투명 채점 · 사람 게이트 승격 [HYPO]",
        "tagline_en": (
            "Artifact-bound discipline: transparent hit/miss by axis, human sign-off for promotion — "
            "not hallucination-free magic."
        ),
        "kernel": {
            "label_ko": "Platform Kernel (재사용)",
            "modules": kernel_modules,
            "layer_contract": {
                "layer_a": {"role": "profile_ssot_sequential", "rag_graph_runtime": False},
                "layer_b": {
                    "role": "explore_showroom_optional",
                    "rag_graph_runtime": False,
                    "enable_query_flag": "explore=1",
                },
            },
        },
        "skins": skins,
        "forbidden_fusion_modes": forbidden_modes,
        "forbidden_claims_ko": forbidden_claims,
        "public_facing_ref": _rel(
            ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
        ),
        "track_c_ref": _rel(ROOT / "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md"),
        "domain_portfolio_ref": _rel(ROOT / "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md"),
    }

    if exist_ok:
        missing = []
        for mod in kernel_modules:
            for ref in mod["ssot_refs"]:
                if not (ROOT / ref).is_file():
                    missing.append(ref)
        if missing:
            raise SystemExit(f"missing kernel ssot paths: {missing[:8]}")

    return doc


def _validate(doc: dict[str, Any], strict: bool) -> list[str]:
    if not strict or not SCHEMA_PATH.is_file():
        return []
    try:
        import jsonschema

        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)
        return []
    except ImportError:
        return []
    except Exception as exc:
        return [str(exc)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-schema", action="store_true")
    ap.add_argument("--skip-path-exists", action="store_true")
    args = ap.parse_args()

    doc = build_doc(exist_ok=not args.skip_path_exists)
    errs = _validate(doc, args.strict_schema)
    if errs:
        raise SystemExit(f"schema validation failed: {errs}")

    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {_rel(out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
