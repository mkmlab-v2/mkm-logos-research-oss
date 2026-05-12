# LoRA 1팩 v0 — Definition of Done (DoD) 초안 v1

**상태:** 초안 (지휘관 승인·스키마 확정 후 v1.1로 승격)  
**Fact-Lock:** 구현·경로·통과 여부는 `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`·호출 가능 스크립트·`pytest` exit code·산출 JSON만 근거로 한다.

---

## 0. PM 고정 결정 (본 초안의 전제)

**v0 학습 타깃(정답 레일) 고정:** **명리 만세력/사주 엔진의 결정론적·구조화 출력(JSON)** — 동일 입력(출생 순간·IANA TZ 등 엔진 계약)에 대해 **재현 가능한 필드 집합**을 `expected`로 둔 JSONL. 자연어 “풀이”만 단독 정답으로 쓰지 않는다.

**v0에서 학습 정답으로 쓰지 않는 것(명시 제외):** M31 호르몬 트렌드·`rag_metabolism`*·게마트리아 감사 꼬리표 등 **비생물학적 메타포·감사 지표** — Track C/감사·연구 레인 입력은 가능하나, **LoRA v0의 supervision 타깃으로는 채택하지 않음**(`track_wall`·Fact-Lock 정합; 임상·뇌·장 단정 회피).

---

## 1. “이미 디스크에 있는 LoRA 팩”과의 관계 (착각 방지)

레포에 **이미 고정된 별도 라인**이 있다: **MKM Control-Integrity Golden / LoRA (B-track, instruction eval)**.

| 구분 | 식별명 | SSOT | 비고 |
|------|--------|------|------|
| **Pack 0-A (기존·디스크 팩트)** | Control-Integrity LoRA | `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` **§1.2.1** | Golden 행은 `mkm_control_integrity_golden_set_v1` 스키마(`prompt` / `expected_response` 등). **명리 JSON·M31과 무관한 지시 준수 벤치**. |
| **Pack 0-B (본 DoD의 v0 신규 축)** | Myeongni deterministic LoRA v0 | **본 문서 + 추후 스키마·prep PR** | 정답=§0 고정. Prep/게이트는 §1.2.1과 **합선하지 않음**(데이터·스키마 분리). |

**Pack 0-A 출하(이미 문서화된 최소 DoD):**

- P0 경로에 스크립트 존재: `scripts/verify_p0_constitution_gate_paths.ps1`가 §1.2.1 표 경로와 정합.
- 회귀: `py -m pytest tests/test_mkm_control_integrity_pipeline_smoke_v1.py` **exit 0**.
- (실학습 호스트) 프로모션: `scripts/check_mkm_control_integrity_promotion_gate_v1.py` 산출 `reports/mkm_control_integrity_promotion_gate_latest.json`에서 **decision=GO** 및 정책 문서화된 임계와 일치.

**Pack 0-B(v0 명리 축)**는 위 파이프라인을 **복제·병합하지 않고**, 별도 JSONL 스키마·prep·pytest를 추가하는 것이 DoD다.

---

## 2. Pack 0-B — LoRA v0 (명리 결정론 JSON) DoD 체크리스트

아래는 **prep·스키마·게이트가 레포에 생긴 뒤** 채점 가능한 항목이다. 미구현 항목은 “확인 필요”로 두고 PR에서 경로를 박는다.

### 2.1 데이터 (Data)

- [ ] **입력 계약**이 한 줄로 고정됨: 예) `birth_instant_utc` + `iana_tz` (또는 동등 SSOT; `AGENTS.md` 만세력 절 참고).
- [ ] **정답 계약**이 JSON Schema로 고정됨: `docs/final/schemas/<myeongni_lora_row_v0>.schema.json` (파일명은 PR에서 확정).
- [ ] **JSONL** 생성 파이프라인이 스크립트로 재현됨 (수동 편집본만 있으면 불합격).
- [ ] **split**이 결정론적: `train` / `validation` / `test` / (선택) `locked_eval` — seed·행 수·버전 필드가 산출물에 기록됨.
- [ ] **최소 규모** 합의: 예) train ≥ N행, locked_eval ≥ K행 (숫자는 지휘관·리스크에 따라 별도 표로 박음).

### 2.2 게이트 (Gate / pytest)

- [ ] **스키마 검증**: JSONL 각 행이 스키마를 통과 (CI 또는 로컬 `pytest` 한 개 이상).
- [ ] **엔진 회귀**: 동일 입력에 대해 prep 단계 출력이 엔진 스모크와 충돌 없음 (기존 `run_manseryeok_validation_smoke_v1.py` / `run_saju_global_birth_v1.py` 등 **문서화된 스크립트**와 정합; 경로는 PR에서 `CONSTITUTION` 또는 본 문서에 포인터).
- [ ] **합선 금지 테스트**(권장): Pack 0-B 데이터에 M31·렌즈 뮤직 raw가 **정답 필드**로 끼어들지 않음을 검사하는 소형 assert.

### 2.3 학습·산출 (Train / Artifacts)

- [ ] **프로파일**: `docs/final/artifacts/mkm_control_integrity_lora_model_profiles_v1.json` 패턴을 **복붙하지 않고**, Pack 0-B 전용 profile 키 또는 별도 profiles JSON이 존재.
- [ ] **어댑터 경로·이름**이 한 줄 SSOT로 기록됨 (예: `models/adapters/...` — 실제 경로는 PR에서 확정).
- [ ] **평가 리포트** JSON이 커밋 또는 `reports/` 규약에 남고, **row_pass / locked_eval** 등 숫자가 재현 가능.

### 2.4 서술·대외 (Copy / risk)

- [ ] 대외·내부 브리프에 **“뇌신경·장내미생물·호르몬 치료 효능”** 단정 없음 — `docs/final/MKM_HEALTH_WELLNESS_COPY_GUARDRAILS_KR_V1.md`·`PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` 정렬.

---

## 3. “언제 끝나나”에 대한 유일한 답 (일정이 아니라 DoD)

**캘린더 날짜는 SSOT가 아니다.** 진도는 **§2 체크박스가 true가 되는 순서**로만 측정한다.  
우선순위: **Pack 0-A 회귀가 항상 녹색** → **Pack 0-B 스키마+prep+pytest 최소 세트** → 학습·평가·(선택) 프로모션 게이트.

---

## 4. 다음 액션 (초안 → 실행)

1. 지휘관: §0 고정(명리 JSON / M31 비타깃) **유지 또는 수정** 한 줄 확정.  
2. Architect: `myeongni_lora_row_v0` 스키마 초안 + `Invoke-*Prep` 또는 동급 prep 스크립트 초안 + `pytest` 1개.  
3. Sentinel: `verify_p0`·`dual-regime-integrity`에 넣을 경로만 최소 추가(과잉 경로 금지).

---

## 5. 근거 경로 (Librarian 스냅샷)

```json
{
  "evidence_path": "docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md §1.2.1; docs/final/schemas/mkm_control_integrity_golden_set_v1.schema.json; docs/final/LORA_PACK_V0_DOD_V1.md",
  "validated_at": "2026-05-12",
  "confidence_level": "B",
  "note": "Pack 0-B prep 경로는 아직 레포에 없을 수 있음 — 본 문서는 DoD 계약만 고정."
}
```
