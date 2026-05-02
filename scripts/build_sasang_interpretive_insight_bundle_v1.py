# -*- coding: utf-8 -*-
"""사상 통찰 참조 번들 v1: 금화교역·보명지주·병증·약리·예측·렌즈 산출 포인터를 한 JSON에 모음. 결정론·LLM 없음."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.track_b_commander_gate_v1 import HUMAN_COMMANDER_GATE_V1

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "sasang_interpretive_insight_bundle_v1_latest.json"

VERSION = "1.0.0"
SCHEMA_ID = "sasang_interpretive_insight_bundle_v1"

DISCLAIMER_KO = (
    "[TRACK B 참조 번들] 금화교역·보명지주·병증·약리·예측·사상/시장 사상 렌즈 등은 "
    "관측·문헌·레포 경로를 한데 모은 것입니다. 임상 진단·처방·실매매 최종 결정은 지휘관(사용자)에게만 있으며, "
    "본 산출물은 의견 라벨·근거 링크 제공용입니다."
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exists(rel: str) -> bool:
    return (ROOT / Path(rel)).is_file()


def _upstream_flags() -> dict[str, Any]:
    sasang_p = "docs/final/artifacts/sasang_independent_lens_latest.json"
    market_p = "docs/final/artifacts/market_sasang_lens_latest.json"
    return {
        "sasang_independent_lens_latest": {"path": sasang_p, "present": _exists(sasang_p)},
        "market_sasang_lens_latest": {"path": market_p, "present": _exists(market_p)},
    }


def build_bundle() -> dict[str, Any]:
    up = _upstream_flags()
    sections: list[dict[str, Any]] = [
        {
            "axis_id": "geumhwagyoyeok",
            "title_ko": "금화교역",
            "availability": "linked",
            "summary_ko": "코드베이스 내 금화교역 감지·운영 레이어 참조. 사상 해석과 자동 합선하지 않음.",
            "evidence_refs": [
                {
                    "kind": "repo_path",
                    "ref": "projects/bitcoin-trading/src/strategy/geum_hwa_detector.py",
                    "note_ko": "전략/측정 코드; B-track 사상 번들은 경로만 제공.",
                },
                {
                    "kind": "schema",
                    "ref": "codebook/shards/zone_e_finance.json",
                    "note_ko": "코드북 금융 샤드(존재 시 참조).",
                },
            ],
            "rail_note_ko": "운영 지표 참조일 뿐 매매 결정 아님.",
        },
        {
            "axis_id": "bomyung_jiju",
            "title_ko": "보명지주",
            "availability": "linked",
            "summary_ko": "SCM 보명지주 렉시콘·스크립트 SSOT.",
            "evidence_refs": [
                {
                    "kind": "artifact_json",
                    "ref": "docs/final/artifacts/scm_boming_jiju_lexicon_v1.json",
                },
                {"kind": "repo_path", "ref": "scripts/core/scm_boming_jiju_lexicon_v1.py"},
                {"kind": "schema", "ref": "docs/final/schemas/scm_boming_jiju_lexicon_v1.schema.json"},
            ],
            "rail_note_ko": "어휘·참조용; 명리/사상 단정 자동화 없음.",
        },
        {
            "axis_id": "byeongjeung_yakri",
            "title_ko": "병증·약리 (원전·교차참조)",
            "availability": "partial",
            "summary_ko": "원전 코호트는 본선 라벨과 역할 분리. 교차 매핑 초안은 가설([HYPO])로만 참조.",
            "evidence_refs": [
                {
                    "kind": "handoff_doc",
                    "ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                    "note_ko": "코호트 A vs 원전 B 분리 원칙(§ 한의 원전 인수인계 요지).",
                },
                {
                    "kind": "artifact_json",
                    "ref": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json",
                    "note_ko": "[HYPO] 교차 매핑 초안; 자동 처방·임상 결정 금지.",
                },
            ],
            "rail_note_ko": "임상 행위 트리거 없음.",
        },
        {
            "axis_id": "prediction",
            "title_ko": "예측 (일반 예언 레일)",
            "availability": "linked",
            "summary_ko": "비가격 일반 예언 스키마·생성 체인 포인터. 사상 번들과 합선된 자동 실행 없음.",
            "evidence_refs": [
                {"kind": "schema", "ref": "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json"},
                {"kind": "repo_path", "ref": "scripts/generate_general_prophecy_v1.py"},
            ],
            "rail_note_ko": "B 레일 관측·레지스트리; 최종 책임은 지휘관.",
        },
        {
            "axis_id": "sasang_lens_core",
            "title_ko": "사상 독립 렌즈 코어",
            "availability": "linked" if up["sasang_independent_lens_latest"]["present"] else "stub",
            "summary_ko": "Dynamics JSONL tail 기반 독립 렌즈 산출.",
            "evidence_refs": [
                {"kind": "artifact_json", "ref": "docs/final/artifacts/sasang_independent_lens_latest.json"},
                {"kind": "repo_path", "ref": "scripts/run_lens_sasang.py"},
            ],
            "rail_note_ko": "비의료·비트리거; 스코어는 관측.",
        },
        {
            "axis_id": "market_sasang_lens",
            "title_ko": "시장 사상 렌즈",
            "availability": "linked" if up["market_sasang_lens_latest"]["present"] else "unavailable",
            "summary_ko": "시장 트랙 4분면 softmax·불확실도 (상류 사상 렌즈 필수).",
            "evidence_refs": [
                {"kind": "contract", "ref": "docs/final/artifacts/MARKET_SASANG_LENS_V1_CONTRACT.json"},
                {"kind": "repo_path", "ref": "scripts/run_market_sasang_lens_v1.py"},
                {"kind": "artifact_json", "ref": "docs/final/artifacts/market_sasang_lens_latest.json"},
            ],
            "rail_note_ko": "시장 관측 보조; 단독 실매매 트리거 금지.",
        },
    ]

    return {
        "schema": SCHEMA_ID,
        "version": VERSION,
        "generated_at_utc": _utc_now(),
        "rail": "B_TRACK",
        "decision_authority": "human_only",
        "opinion_kind": "multi_axis_reference_bundle_v1",
        "disclaimer_ko": DISCLAIMER_KO,
        "human_commander_gate_v1": dict(HUMAN_COMMANDER_GATE_V1),
        "upstream_snapshot": up,
        "sections": sections,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Sasang interpretive insight bundle v1 (deterministic).")
    ap.add_argument(
        "-o",
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSON path",
    )
    args = ap.parse_args()
    doc = build_bundle()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
