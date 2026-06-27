# -*- coding: utf-8 -*-
"""사상 통찰 참조 번들 v1: 금화교역·보명지주·병증·약리·예측·렌즈 산출 포인터 + 해설(품질). 결정론·LLM 없음."""

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

from scripts.sasang_byeongjeung_symptom_weights_v1 import build_symptom_weights_v1
from scripts.track_b_commander_gate_v1 import HUMAN_COMMANDER_GATE_V1

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "sasang_interpretive_insight_bundle_v1_latest.json"

VERSION = "1.5.0"
SCHEMA_ID = "sasang_interpretive_insight_bundle_v1"

DISCLAIMER_KO = (
    "[TRACK B 참조 번들 v1.1] 금화교역·보명지주·병증·약리·예측·사상·시장 사상 축은 "
    "『판단 근거 묶음』이며 자동 결정이 아닙니다. 임상 진단·처방·실매매·포지션 크기의 최종 책임은 지휘관(사용자)에게만 있습니다. "
    "본 JSON은 통찰 후보·근거 링크·읽기 순서를 제공합니다."
)


SYNTHESIS_V1: dict[str, str] = {
    "how_to_synthesize_ko": (
        "① 운영·코드북 축(금화교역)은 『시장·레짐형 신호의 외곽』 참고용입니다—사상 체질 해석과 동일시하지 않습니다. "
        "② 보명지주 렉시콘은 『언어·개념 정렬』용이며, 명리 사주 판정이나 사상 사중 세력을 자동 대입하지 않습니다. "
        "③ 병증·약리·원전 교차참조는 『문헌 앵커』일 뿐이며, 라벨 코호트·실전 분류와 자동 합선하지 않습니다. "
        "④ 일반 예언 레일은 시간·확률 슬롯 관측용입니다. "
        "⑤ 사상 독립 렌즈→(선택) 시장 사상 렌즈 순으로 『동역학→시장 4분면』을 읽되, 성·명·사 3렌즈 역할 계약(성경 비게이팅·명리 중기·사상 단기)과 혼동하지 않습니다. "
        "최종 액션 문장은 사용자가 작성합니다—기계는 스코어·불확실도·금지 플래그만 제시합니다."
    ),
    "axis_order_rationale_ko": (
        "금화교역(운영 참조) → 보명지주(어휘) → 병증·약리(문헌 경계) → 예측(비가격 슬롯) → 사상 코어 → 시장 사상 순은 "
        "『외부 레짐·언어·의료 격벽·시간축·체질 동역학·시장 투영』으로 범주를 넓혀 가며, 나중 축이 앞 축을 덮어쓰지 않습니다."
    ),
    "disagreement_protocol_ko": (
        "축 간 불일치 시: (1) 임상·처방 관련은 원전·지휘관 검토 없이 단정 금지. "
        "(2) 시장 관련은 시장 사상 렌즈의 veto·uncertainty를 우선 확인하고, 금화교역 지표와 단일 방정식으로 묶지 않습니다. "
        "(3) 예언·사상 스코어가 엇갈리면 『관측 병치』만 하고, 자동 가중치 조정·실매매 트리거는 금지입니다. "
        "(4) force_hold(veto)는 『추격·레버리지 금지』 전술 leg이며, supplier_tight(Field/Joseph) 구조 leg와 분리합니다—"
        "veto를 매도·영구 관망으로 literal collapse하지 않습니다. "
        "(5) PersonaDiary/중기 레인(myeongni+sasang)은 prophecy vote·Track A quant와 격리—Sharpe·MDD 참고만. "
        "(6) fABBA ngram_lut sidecar는 merged LUT feature join 전용—prophecy vote·Primary score·Arm A quant에 자동 합류 금지."
    ),
    "forbidden_synthesis_ko": (
        "금화교역 수치만으로 체질 단정; 보명지주 어휘만으로 처방 근거 확정; "
        "SASANG_CROSS_REF_DRAFT 한 줄로 임상 코호트 라벨 치환; "
        "symptom_weights_v1 정충·부종 표만으로 체질·처방 단정; "
        "사상·시장 사상 렌즈만으로 주문·레버리지 확정; "
        "일반 예언 확률을 사상 스코어에 선형 합성; "
        "force_hold를 단독 매도·현금·영구 관망 신호로 collapse; "
        "PersonaDiary myeongni+sasang Sharpe를 prophecy vote·실매매 sizing에 직접 승격; "
        "fABBA ngram_lut dual-leg HR을 Arm A quant SSOT로 승격; merged LUT fabba 컬럼을 prophecy vote에 자동 주입—위 모두 금지(B-track)."
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exists(rel: str) -> bool:
    return (ROOT / Path(rel)).is_file()


def _read_json_optional(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return doc if isinstance(doc, dict) else {}


def _fabba_ngram_lut_sidecar_from_registration() -> dict[str, Any]:
    reg_p = ROOT / "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
    doc = _read_json_optional(reg_p)
    reg = doc.get("registration") or {}
    shadow = doc.get("shadow_hr_evidence") or {}
    ngram = shadow.get("ngram_lut_kospi_dual_leg_180d_2bps") or {}
    lut = doc.get("lut_ablation_smoke") or {}
    return {
        "artifact": str(reg_p.relative_to(ROOT)).replace("\\", "/"),
        "present": reg_p.is_file() and doc.get("ok") is True,
        "primary_sidecar_arm": reg.get("primary_sidecar_arm"),
        "vote_participation": reg.get("vote_participation"),
        "non_gating": reg.get("non_gating"),
        "opt_in_only": reg.get("opt_in_only"),
        "shadow_hr_kospi_dual_leg_180d_2bps": ngram.get("kospi_pooled_hr"),
        "shadow_hr_btc_dual_leg_180d_2bps": ngram.get("btc_pooled_hr"),
        "arm_a_panel_hr_180d": shadow.get("arm_a_science_sasang_panel_hr_180d"),
        "delta_ngram_kospi_vs_arm_a_pp": shadow.get("delta_ngram_kospi_vs_arm_a_pp"),
        "lut_feature_parity_ok": lut.get("feature_parity_ok"),
        "lut_wf_base_mean_hr": lut.get("base_lut_wf_mean_hr"),
        "lut_wf_fabba_opt_in_mean_hr": lut.get("merged_fabba_opt_in_wf_mean_hr"),
        "merged_lut": (doc.get("artifacts") or {}).get("merged_lut"),
    }


def _persona_diary_lane_from_phase3() -> dict[str, Any]:
    phase3_p = ROOT / "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
    doc = _read_json_optional(phase3_p)
    lane = doc.get("myeongni_sasang_lane") or {}
    metrics = lane.get("metrics") or {}
    return {
        "artifact": str(phase3_p.relative_to(ROOT)).replace("\\", "/"),
        "present": phase3_p.is_file(),
        "persona_diary_lane_recommended": lane.get("persona_diary_lane_recommended"),
        "prophecy_vote_recommended": lane.get("prophecy_vote_recommended", False),
        "shadow_metrics_180d_2bps": metrics if metrics else None,
        "vs_arm_a": lane.get("vs_arm_a_science_sasang"),
        "walkforward_mean_test_hr": (lane.get("walkforward_blocked") or {}).get(
            "mean_test_directional_hit_rate_active"
        ),
    }


def _upstream_flags() -> dict[str, Any]:
    sasang_p = "docs/final/artifacts/sasang_independent_lens_latest.json"
    market_p = "docs/final/artifacts/market_sasang_lens_latest.json"
    containment_p = "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"
    p2_p = "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"
    p3_p = "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json"
    unified_p = "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"
    stack_p = "docs/final/artifacts/sasang_rail_stack_gate_v1_latest.json"
    p5_p = "docs/final/artifacts/sasang_rail_p5_gate_v1_latest.json"
    p6_p = "docs/final/artifacts/sasang_rail_p6_gate_v1_latest.json"
    master_p = "docs/final/artifacts/sasang_rail_master_gate_v1_latest.json"
    curated_p = "docs/final/artifacts/sasang_curated_joint_unified_gate_v1_latest.json"
    counterfactual_p = "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json"
    fusion_ablation_p = "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json"
    phase3_p = "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json"
    fabba_reg_p = "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json"
    return {
        "sasang_independent_lens_latest": {"path": sasang_p, "present": _exists(sasang_p)},
        "market_sasang_lens_latest": {"path": market_p, "present": _exists(market_p)},
        "sasang_rail_containment_gate": {"path": containment_p, "present": _exists(containment_p)},
        "sasang_rail_p2_gate": {"path": p2_p, "present": _exists(p2_p)},
        "sasang_rail_p3_gate": {"path": p3_p, "present": _exists(p3_p)},
        "sasang_rail_unified_gate": {"path": unified_p, "present": _exists(unified_p)},
        "sasang_rail_stack_gate": {"path": stack_p, "present": _exists(stack_p)},
        "sasang_rail_p5_gate": {"path": p5_p, "present": _exists(p5_p)},
        "sasang_rail_p6_gate": {"path": p6_p, "present": _exists(p6_p)},
        "sasang_rail_master_gate": {"path": master_p, "present": _exists(master_p)},
        "sasang_curated_joint_unified_gate": {"path": curated_p, "present": _exists(curated_p)},
        "samsung_veto_hold_counterfactual": {"path": counterfactual_p, "present": _exists(counterfactual_p)},
        "sasang_regime_conditional_fusion_ablation": {
            "path": fusion_ablation_p,
            "present": _exists(fusion_ablation_p),
        },
        "prophecy_lens_profile_shadow_ablation_phase3": {
            "path": phase3_p,
            "present": _exists(phase3_p),
        },
        "prophecy_fabba_ngram_lut_sidecar_registration": {
            "path": fabba_reg_p,
            "present": _exists(fabba_reg_p),
        },
    }


def build_bundle() -> dict[str, Any]:
    up = _upstream_flags()
    persona_lane = _persona_diary_lane_from_phase3()
    fabba_sidecar = _fabba_ngram_lut_sidecar_from_registration()
    sections: list[dict[str, Any]] = [
        {
            "axis_id": "geumhwagyoyeok",
            "title_ko": "금화교역 (운영·코드북 참조)",
            "availability": "linked",
            "summary_ko": "금융 샤드·전략 코드에 구현된 『금화교역』 감지—사상 의학의 금·화·목·토 이론과 이름만 우연히 겹칠 수 있으나 동일 개념이 아닙니다.",
            "interpretive_depth_ko": (
                "이 축은 『시장·운영 레이어』에서의 위상·전이 감지용 수학·휴리스틱을 가리킵니다. "
                "소음인·태양인 같은 체질 서술과 자동 연결하지 마십시오. 해석할 때는 코드 경로를 열어 입력·출력 계약을 확인하고, "
                "레짐 필드·실물 게이트 문서와 함께 읽되, 사상 독립 렌즈의 direction_score와 단순 선형 결합하지 않습니다. "
                "목적은 『외생 변수와 내부 동역학 레이블을 섞지 않기 위한 상단 주석』입니다."
            ),
            "evidence_refs": [
                {
                    "kind": "repo_path",
                    "ref": "projects/bitcoin-trading/src/strategy/geum_hwa_detector.py",
                    "note_ko": "전략 모듈—임상·체질 추론 없음.",
                },
                {
                    "kind": "schema",
                    "ref": "codebook/shards/zone_e_finance.json",
                    "note_ko": "코드북 금융 존 용어·샤드 경계.",
                },
            ],
            "rail_note_ko": "매매·사이징 최종 결정 없음; 참고 링크만.",
        },
        {
            "axis_id": "bomyung_jiju",
            "title_ko": "보명지주 (SCM 렉시콘)",
            "availability": "linked",
            "summary_ko": "보명·지주 개념을 정규화한 어휘 레이어—명리 간지·사상 사중과 문자열이 겹치면 『표기 일치』를 의미 고유 일치로 오인하지 않습니다.",
            "interpretive_depth_ko": (
                "렉시콘은 검색·정합·충돌 검사용입니다. 한 글자가 간지 체계와 같아 보여도, 여기서의 『보명』은 SCM 도메인 태그입니다. "
                "통찰 보고서에 인용할 때는 원문 출처·행 ID를 함께 적고, 명리 판국이나 장부 허실 판단으로 승격시키지 마십시오. "
                "동음이의어를 줄이려면 렉시콘 JSON의 정의 필드를 우선 확인합니다."
            ),
            "evidence_refs": [
                {"kind": "artifact_json", "ref": "docs/final/artifacts/scm_boming_jiju_lexicon_v1.json"},
                {"kind": "repo_path", "ref": "scripts/core/scm_boming_jiju_lexicon_v1.py"},
                {"kind": "schema", "ref": "docs/final/schemas/scm_boming_jiju_lexicon_v1.schema.json"},
            ],
            "rail_note_ko": "어휘 SSOT; 명리·사상 결론 자동 생성 금지.",
        },
        {
            "axis_id": "byeongjeung_yakri",
            "title_ko": "병증·약리·원전 교차 (격벽)",
            "availability": "partial",
            "summary_ko": "원전·교차 매핑 초안은 연구용(HYPO); 라벨 코호트·본선 분류와 역할이 다릅니다.",
            "interpretive_depth_ko": (
                "『병증·약리』 서술은 한의 원전·교차참조 초안에서 인용 체인을 확인할 때 사용합니다. "
                "여기서 말하는 표한·표열 등은 문헌语境 안에서만 의미가 있으며, 시장 사상 softmax나 명리 4D 벡터와 자동 대응시키면 FAIL 격벽에 해당합니다. "
                "symptom_weights_v1의 정충·부종 표는 KoGES·KCMB 앵커에 따른 『문진 우선순위 참고』이며, 체질 라벨·처방을 자동 산출하지 않습니다. "
                "태양인 행은 ty_sparsity 불확실도 상향만 표시합니다. "
                "임상적으로 활용할 경우 반드시 면허·지휘관 경로를 따로 밟으며, 본 번들은 『어디를 열어볼지』 안내할 뿐 처방·진단을 출력하지 않습니다."
            ),
            "evidence_refs": [
                {
                    "kind": "handoff_doc",
                    "ref": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md",
                    "note_ko": "코호트 A vs 원전 B 분리·합선 금지.",
                },
                {
                    "kind": "artifact_json",
                    "ref": "docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json",
                    "note_ko": "[HYPO] 교차 초안—근거 행·근거 문헌 확인 필수.",
                },
                {
                    "kind": "handoff_doc",
                    "ref": "docs/research/FOUR_LENS_YINYANG_REGULARIZATION_V1.md",
                    "note_ko": "Adoptable slot #1 — symptom 가중 스펙.",
                },
                {
                    "kind": "artifact_json",
                    "ref": "docs/final/artifacts/sasang_boming_jiju_clinical_lens_pack_v1_latest.json",
                    "note_ko": "체질별 보명지주·원전 포인터 2차 패킹.",
                },
            ],
            "symptom_weights_v1": build_symptom_weights_v1(),
            "rail_note_ko": "임상 트리거·자동 처방 금지.",
        },
        {
            "axis_id": "prediction",
            "title_ko": "예측 (일반 예언 레일)",
            "availability": "linked",
            "summary_ko": "비가격 질문·확률·해석 레이어—사상 동역학과 시간 해상도가 다릅니다.",
            "interpretive_depth_ko": (
                "일반 예언은 레지스트리·Brier·해결 규칙이 명시된 관측 레일입니다. 사상 렌즈가 말하는 단기 심리·강도와 혼동하면 안 됩니다. "
                "같은 날짜라도 『예언 질문 단위』와 『렌즈 스냅샷』은 독립입니다. 통합 서술을 쓸 때는 문단을 나누고, "
                "예언 확률을 사상 스코어에 가중합하지 마십시오."
            ),
            "evidence_refs": [
                {"kind": "schema", "ref": "docs/final/GENERAL_PROPHECY_SCHEMA_V1.json"},
                {"kind": "repo_path", "ref": "scripts/generate_general_prophecy_v1.py"},
            ],
            "rail_note_ko": "B 레일 관측; 책임은 지휘관.",
        },
        {
            "axis_id": "sasang_lens_core",
            "title_ko": "사상 독립 렌즈 코어",
            "availability": "linked" if up["sasang_independent_lens_latest"]["present"] else "stub",
            "summary_ko": "Dynamics JSONL tail에서 추출한 방향·신뢰도—비의료·비트리거 고정.",
            "interpretive_depth_ko": (
                "산출 JSON의 direction_score·confidence·mapping_target을 먼저 읽으십시오. "
                "confidence가 낮으면 『방향만 보고 결론 내리기』를 금지합니다. "
                "machine_readables의 열·냉·희석 proxy는 해석 보조일 뿐, 단일 실수로 체질을 단정하지 마십시오. "
                "파일이 없으면(stub) 상류 JSONL·run_lens_sasang 재실행 여부를 확인합니다."
            ),
            "evidence_refs": [
                {"kind": "artifact_json", "ref": "docs/final/artifacts/sasang_independent_lens_latest.json"},
                {"kind": "repo_path", "ref": "scripts/run_lens_sasang.py"},
            ],
            "rail_note_ko": "관측 스코어만; 임상·주문 없음.",
        },
        {
            "axis_id": "market_sasang_lens",
            "title_ko": "시장 사상 렌즈",
            "availability": "linked" if up["market_sasang_lens_latest"]["present"] else "unavailable",
            "summary_ko": "사상 렌즈 상류 필수; 4분면 softmax·불확실도·veto로 시장 맥락 정렬.",
            "interpretive_depth_ko": (
                "state_vector_sasang_softmax 네 질량은 『시장 트랙에서의 체질형 분포 은유』이며 의료 상태가 아닙니다. "
                "uncertainty·veto가 켜지면 융합 스텁에서 가중치 축소 또는 HOLD를 고려합니다—그 결정도 규칙·지휘관 게이트 안에서만. "
                "fusion_bridge.direction_hint는 스텁 정렬용이며 단독 매매 신호가 아닙니다. 산출이 없으면 상류 sasang_independent_lens부터 재생성합니다."
            ),
            "evidence_refs": [
                {"kind": "contract", "ref": "docs/final/artifacts/MARKET_SASANG_LENS_V1_CONTRACT.json"},
                {"kind": "repo_path", "ref": "scripts/run_market_sasang_lens_v1.py"},
                {"kind": "artifact_json", "ref": "docs/final/artifacts/market_sasang_lens_latest.json"},
            ],
            "rail_note_ko": "시장 보조; 단독 실매매 금지.",
        },
        {
            "axis_id": "sasang_rail_gates",
            "title_ko": "사상 레일 격벽 게이트 (containment·enrichment·literature)",
            "availability": "linked"
            if up["sasang_rail_containment_gate"]["present"]
            else "stub",
            "summary_ko": "P1 containment → P2 enrichment → P3 ablation·문헌 resolver; unified gate로 스택 확인.",
            "interpretive_depth_ko": (
                "containment 게이트는 火剋金·金器 framing과 Track A 격벽을 고정합니다. "
                "P2는 interpretive bundle·4-agent smoke·joint benchmark smoke를 묶습니다. "
                "P3는 preregistered ablation과 literature majority resolver 산출을 검증합니다. "
                "세 게이트가 모두 통과해도 SEND는 HOLD이며, 실매매·Track A 승격은 지휘관 게이트만 가능합니다."
            ),
            "evidence_refs": [
                {"kind": "artifact_json", "ref": "docs/final/artifacts/sasang_rail_containment_gate_v1_latest.json"},
                {"kind": "artifact_json", "ref": "docs/final/artifacts/sasang_rail_p2_gate_v1_latest.json"},
                {"kind": "artifact_json", "ref": "docs/final/artifacts/sasang_rail_p3_gate_v1_latest.json"},
                {"kind": "artifact_json", "ref": "docs/final/artifacts/sasang_rail_unified_gate_v1_latest.json"},
                {"kind": "repo_path", "ref": "scripts/run_sasang_rail_containment_chain_v1.py"},
                {"kind": "repo_path", "ref": "scripts/run_sasang_rail_p2_chain_v1.py"},
                {"kind": "repo_path", "ref": "scripts/run_sasang_rail_p3_chain_v1.py"},
                {"kind": "repo_path", "ref": "scripts/run_sasang_rail_master_chain_v1.py"},
                {"kind": "repo_path", "ref": "scripts/seed_sasang_curated_joint_dummy_fixture_v1.py"},
            ],
            "rail_note_ko": "운영 격벽 포인터; 자동 승격 없음.",
        },
        {
            "axis_id": "regime_mkm_split_v1",
            "title_ko": "Regime MKM Split v1 (구조 leg × 전술 veto)",
            "availability": "linked" if up["samsung_veto_hold_counterfactual"]["present"] else "stub",
            "summary_ko": (
                "supplier_tight(Field/Joseph/geumhwa gated)일 때 구조적 롱; "
                "sasang force_hold는 추격 진입만 차단—매도·영구 관망 아님. "
                "counterfactual·fusion ablation로 falsifiable."
            ),
            "interpretive_depth_ko": (
                "이 축은 『제미나이식 generic 관망』과 literal veto-as-exit를 분리합니다. "
                "권장 composite는 field_hyst10|joseph_2025-06이며, geumhwa_execution은 sparse라 "
                "5일 연속 확인(gated5) 없이 단독 structural leg로 쓰지 않습니다. "
                "해석 시 counterfactual artifact의 regime_conditional_*와 "
                "sasang_regime_conditional_fusion_ablation policy_paths를 함께 읽되, "
                "Track A·실매매·자동 SEND로 승격하지 마십시오."
            ),
            "evidence_refs": [
                {
                    "kind": "repo_path",
                    "ref": "scripts/sasang_regime_mkm_split_v1.py",
                    "note_ko": "공유 규칙 SSOT (supplier_tight × veto split).",
                },
                {
                    "kind": "artifact_json",
                    "ref": "reports/samsung_sasang_veto_hold_counterfactual_v1_latest.json",
                    "note_ko": "삼성·하이닉스 BAH vs veto arms quant.",
                },
                {
                    "kind": "artifact_json",
                    "ref": "reports/sasang_regime_conditional_fusion_ablation_v1_latest.json",
                    "note_ko": "fusion policy arms daily posture ablation.",
                },
                {
                    "kind": "repo_path",
                    "ref": "scripts/run_samsung_sasang_veto_hold_counterfactual_v1.py",
                },
                {
                    "kind": "repo_path",
                    "ref": "scripts/run_sasang_regime_conditional_fusion_ablation_v1.py",
                },
            ],
            "rail_note_ko": "[HYPO] quant shadow; human commander final action.",
        },
        {
            "axis_id": "persona_diary_myeongni_sasang_lane",
            "title_ko": "PersonaDiary / 중기 레인 (myeongni+sasang)",
            "availability": "linked" if persona_lane.get("present") else "stub",
            "summary_ko": (
                "180d/2bps shadow: myeongni+sasang Sharpe·MDD 위험조정 우위 — "
                "prophecy vote·Track A quant와 물리 분리. science+sasang은 Quant SSOT."
            ),
            "interpretive_depth_ko": (
                "이 축은 『명리+사상』 2렌즈 조합을 중기 일기·상담(PersonaDiary) 레인으로만 씁니다. "
                "science_core Field leg 없이도 Sharpe가 높게 나올 수 있으나, "
                "science+sasang+myeongni 3-way linear blend는 prophecy 패널에서 열세이므로 "
                "데일리 방향 투표 체인에 명리를 다시 넣지 않습니다. "
                "수치는 phase3 shadow ablation artifact에서만 읽고, 자동 sizing·SEND·Track A로 승격하지 마십시오."
            ),
            "evidence_refs": [
                {
                    "kind": "artifact_json",
                    "ref": "reports/prophecy_lens_profile_shadow_ablation_phase3_v1_latest.json",
                    "note_ko": "myeongni_sasang_lane · Sharpe ranking · WF blocked",
                },
                {
                    "kind": "artifact_json",
                    "ref": "reports/prophecy_lens_profile_shadow_ablation_v2_latest.json",
                    "note_ko": "Arm A science+sasang quant baseline (180d)",
                },
                {
                    "kind": "repo_path",
                    "ref": "scripts/run_prophecy_lens_profile_shadow_ablation_phase3_v1.py",
                },
            ],
            "rail_note_ko": "PersonaDiary/중기 only; prophecy vote OFF; human_only.",
            "shadow_metrics_pointer": persona_lane if persona_lane.get("present") else None,
        },
        {
            "axis_id": "fabba_sidecar_ngram_lut",
            "title_ko": "fABBA ngram_lut sidecar (feature LUT join)",
            "availability": "linked" if fabba_sidecar.get("present") else "stub",
            "summary_ko": (
                "180d/2bps merged LUT의 fabba_ngram_* 컬럼 — dual-leg shadow KOSPI HR 참고용. "
                "vote=none · non_gating · Quant SSOT(Arm A) 불변."
            ),
            "interpretive_depth_ko": (
                "이 축은 symbolic fABBA ngram LUT를 OHLCV feature sidecar로만 등록합니다. "
                "linux dual-leg AB와 registration artifact에서 KOSPI pooled HR을 읽되, "
                "프로토콜이 science+sasang 패널(Arm A)과 다르므로 headline quant SSOT로 승격하지 마십시오. "
                "LUT WF ablation smoke는 Primary score join 경로에서 base vs merged parity를 검증합니다—"
                "fabba 컬럼은 opt-in join 전용이며 prophecy lens vote·Track A ensemble·send_gate에 자동 연결되지 않습니다. "
                "native fABBA backend는 stub 대비 KOSPI 열세이므로 sidecar 기본 backend는 apca_stub입니다."
            ),
            "evidence_refs": [
                {
                    "kind": "artifact_json",
                    "ref": "reports/prophecy_fabba_ngram_lut_sidecar_registration_v1_latest.json",
                    "note_ko": "governance registration · vote=none",
                },
                {
                    "kind": "artifact_json",
                    "ref": "reports/btrack_ohlcv_feature_lut_with_fabba_sidecar_v1_latest.json",
                    "note_ko": "merged LUT · fabba_ngram_* columns",
                },
                {
                    "kind": "artifact_json",
                    "ref": "reports/prophecy_fabba_lut_wf_ablation_smoke_v1_latest.json",
                    "note_ko": "WF parity smoke · Primary score unchanged",
                },
                {
                    "kind": "repo_path",
                    "ref": "scripts/register_prophecy_fabba_ngram_lut_sidecar_v1.py",
                },
            ],
            "rail_note_ko": "[HYPO] sidecar-only; prophecy vote OFF; human_only.",
            "shadow_metrics_pointer": fabba_sidecar if fabba_sidecar.get("present") else None,
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
        "synthesis_v1": dict(SYNTHESIS_V1),
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
